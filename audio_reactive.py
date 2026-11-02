"""Default-output WASAPI loopback in a disposable worker process.

Only small feature tuples cross into Qt. Audio blocks are overwritten/discarded,
never written, uploaded, or forwarded. Capture never falls back to a microphone.
"""
from dataclasses import dataclass
import math
import multiprocessing as mp
import queue
import time
from PySide6.QtCore import QObject, QTimer, Signal


@dataclass(frozen=True)
class AudioFeatures:
    rms: float = 0.0
    bass: float = 0.0
    onset: float = 0.0
    beat: bool = False
    bass_drop: bool = False


class FeatureExtractor:
    def __init__(self, sample_rate=24000, frames=1024):
        import numpy as np
        self.np = np
        self.sample_rate, self.frames = sample_rate, frames
        self.window = np.hanning(frames)
        frequencies = np.fft.rfftfreq(frames, 1 / sample_rate)
        self.bass_mask = (frequencies >= 30) & (frequencies <= 180)
        self.mean_energy = self.mean_bass = .001
        self.last_beat = self.last_drop = -10.0
        self.age = 0.0

    def process(self, data):
        np = self.np
        samples = np.asarray(data, dtype=np.float32)
        if samples.ndim == 1:
            samples = samples[:, None]
        if len(samples) != self.frames or not np.isfinite(samples).all():
            return AudioFeatures()
        dt = self.frames / self.sample_rate
        self.age += dt
        rms = float(np.sqrt(np.mean(samples * samples)))
        # Average channel powers, avoiding cancellation with anti-phase stereo.
        spectrum = np.fft.rfft(samples * self.window[:, None], axis=0)
        power = np.mean(np.abs(spectrum) ** 2, axis=1)
        bass = float(np.sqrt(np.sum(power[self.bass_mask]) * 2) / self.frames)
        onset = max(0.0, rms / max(.004, self.mean_energy) - 1)
        beat = rms > .009 and onset > .55 and self.age - self.last_beat > .25
        drop = (self.age > 2 and bass > .018 and bass > self.mean_bass * 2.8
                and self.age - self.last_drop > 5)
        if beat:
            self.last_beat = self.age
        if drop:
            self.last_drop = self.age
        blend = 1 - math.exp(-dt * 2)
        self.mean_energy += (rms - self.mean_energy) * blend
        self.mean_bass += (bass - self.mean_bass) * blend
        return AudioFeatures(rms, bass, min(3, onset), beat, drop)


def _audio_worker(channel, stop):
    def send(value):
        try:
            channel.put_nowait(value)
        except queue.Full:
            pass
    try:
        # SoundCard owns COM initialization in this otherwise unused process.
        # Pre-initializing COM produces S_FALSE, which some versions reject.
        import soundcard as sc
        while not stop.is_set():
            speaker = sc.default_speaker()
            if speaker is None:
                raise RuntimeError('No default output device')
            loopback = sc.get_microphone(id=speaker.id, include_loopback=True)
            if not loopback.isloopback:
                raise RuntimeError('Output loopback is unavailable')
            extractor = FeatureExtractor()
            next_device_check = time.monotonic() + 2
            # All channels: SoundCard documents a Windows single-channel issue.
            with loopback.recorder(samplerate=24000, blocksize=1024) as recorder:
                while not stop.is_set():
                    data = recorder.record(numframes=1024)
                    features = extractor.process(data)
                    del data
                    send(('features', time.monotonic(), features))
                    if time.monotonic() >= next_device_check:
                        current = sc.default_speaker()
                        if current is None or current.id != speaker.id:
                            break
                        next_device_check = time.monotonic() + 2
    except Exception:
        send(('error', time.monotonic(), None))


class AudioMonitor(QObject):
    features = Signal(object)
    unavailable = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.timer = QTimer(self)
        self.timer.setInterval(35)
        self.timer.timeout.connect(self._poll)
        self.last_sample = 0.0

    def start(self):
        if self.process:
            return
        context = mp.get_context('spawn')
        self.channel, self.stop_event = context.Queue(4), context.Event()
        self.process = context.Process(target=_audio_worker, args=(self.channel, self.stop_event), daemon=True)
        self.process.start()
        self.last_sample = time.monotonic()
        self.timer.start()

    def _poll(self):
        failed = False
        for _ in range(4):
            try:
                kind, stamp, features = self.channel.get_nowait()
            except queue.Empty:
                break
            if kind == 'error':
                failed = True
            elif time.monotonic() - stamp < .4:
                self.last_sample = time.monotonic()
                self.features.emit(features)
        if failed or not self.process.is_alive() or time.monotonic() - self.last_sample > 10:
            self.stop()
            self.unavailable.emit()

    def stop(self):
        self.timer.stop()
        if self.process:
            self.stop_event.set()
            self.process.join(.2)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(1)
            self.channel.close()
            self.process.close()
            self.process = None
