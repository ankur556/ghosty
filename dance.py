"""Heuristic music activity, beat impulses, and smooth dance envelopes.

No song recognition or BPM estimation. Continuous audio can include speech.
"""
import math
from animations import Spring
from audio_reactive import AudioFeatures


class Dance:
    def __init__(self):
        self.features = AudioFeatures()
        self.received = -100.0
        self.active = False
        self.audible = self.silent = self.blend = self.energy = 0.0
        self.pulse = self.beat_density = 0.0
        self.jump = Spring()
        self.phase = 0.0
        self.mode = 'chill'
        self.next_style = 0.0
        self.drop_until = 0.0
        self.beat_pending = self.drop_pending = False
        self.rotation = self.x = self.y = self.stretch = self.glow = 0.0
        self.next_spin = 15.0
        self.spin_start = -100.0
        self.spin = 0.0
        self.beats = 0

    def feed(self, features, now):
        self.features, self.received = features, now
        self.beat_pending |= features.beat
        self.drop_pending |= features.bass_drop

    def update(self, dt, now, typing=False, blocked=False, quiet=False):
        features = self.features if now - self.received < .5 else AudioFeatures()
        if features.rms > .003:
            self.audible += dt
            self.silent = 0
        else:
            self.silent += dt
            if self.silent > .2:
                self.audible = 0
        if self.audible > 2:
            self.active = True
        if self.silent > 2:
            self.active = False
        target = 1.0 if self.active and not blocked else 0.0
        self.blend += (target - self.blend) * (1 - math.exp(-dt * 3))
        self.energy += (min(1, features.rms * 7) - self.energy) * (1 - math.exp(-dt * 4))
        self.beat_density *= math.exp(-dt / 3)
        beat = self.beat_pending and self.active and not blocked
        drop = self.drop_pending and self.active and not blocked and not typing and not quiet
        self.beat_pending = self.drop_pending = False
        if beat:
            self.beats += 1
            self.pulse = 1
            self.beat_density = min(5, self.beat_density + .65)
            self.jump.velocity -= 30 if typing or quiet else 80
        if drop:
            self.jump.velocity = -230
            self.drop_until = now + .8
        self.pulse *= math.exp(-dt * 6)
        self.jump.update(0, dt, 65, 9)
        if now >= self.next_style:
            self.mode = ('energetic' if self.energy > .4 and self.beat_density > 1.3 else
                         'happy' if self.energy > .22 else 'bounce' if self.beat_density > 1 else
                         'vibe' if self.energy > .08 else 'chill')
            self.next_style = now + 4
        if self.active and self.mode in ('happy', 'energetic') and now > self.next_spin and not (typing or blocked or quiet):
            self.spin_start, self.next_spin = now, now + 22
        self.phase += dt * (1.6 + self.energy * 3)
        amount = self.blend * (.3 if typing else .45 if quiet else 1)
        self.x = math.sin(self.phase) * (2 + self.energy * 4) * amount
        self.y = (math.cos(self.phase * 2) * 2 + self.jump.value) * amount
        self.rotation = math.sin(self.phase) * (4 + self.energy * 9) * amount
        spin = (now - self.spin_start) / 1.4
        self.spin = 0.0
        if 0 <= spin < 1 and not (typing or blocked):
            self.spin = 360 * spin * spin * (3 - 2 * spin)
        self.stretch = (-self.jump.value * .005 + math.sin(self.phase * 2) * .018) * amount
        self.glow = (self.energy * .6 + self.pulse * .4) * self.blend
        return beat, drop

    def clear(self):
        self.__init__()
