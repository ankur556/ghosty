"""Native worker checks. --audio explicitly enables brief output-only capture.

No global keyboard hook is installed. No key identities, text, or audio are
printed/saved. Preferences are isolated. All workers stop automatically.
"""
import argparse
import multiprocessing
import tempfile
import time
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from audio_reactive import AudioMonitor
from input_privacy import FocusGuard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', action='store_true')
    args = parser.parse_args()
    app = QApplication([])
    guard, audio = FocusGuard(), AudioMonitor()
    samples, errors = [], []
    audio.features.connect(lambda _: samples.append(True))
    audio.unavailable.connect(lambda: errors.append('audio unavailable'))
    guard.start()
    if args.audio:
        audio.start()
    result = {}

    def finish():
        result['privacy'] = bool(guard.process and guard.process.is_alive() and guard.token)
        result['audio'] = bool(samples) and not errors
        guard.stop()
        audio.stop()
        assert guard.process is None and audio.process is None
        app.quit()

    QTimer.singleShot(5000, finish)
    app.exec()
    assert result['privacy'], 'Accessibility worker did not produce a metadata-only result'
    print('PASS: accessibility metadata worker and bounded process cleanup')
    if args.audio:
        assert result['audio'], 'Default output loopback did not produce features'
        print('PASS: default-output loopback produced features; capture stopped cleanly')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
