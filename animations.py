"""Frame-rate independent springs, blinking, and expression interpolation."""
import math
import random
from behavior import EMOTIONS


class Spring:
    def __init__(self, value=0.0):
        self.value = value
        self.velocity = 0.0

    def update(self, target, dt, stiffness=100, damping=15):
        # Small integration steps keep springs stable even after a slow frame.
        steps = max(1, math.ceil(dt / .008))
        step = dt / steps
        for _ in range(steps):
            self.velocity += ((target - self.value) * stiffness - self.velocity * damping) * step
            self.value += self.velocity * step
        return self.value


class Animation:
    def __init__(self):
        self.eye, self.smile, self.blush = 1.0, .25, .45
        self.gaze_x = self.gaze_y = 0.0
        self.tilt = Spring()
        self.stretch = Spring(1)
        self.next_blink = random.uniform(2, 5)
        self.blink_until = 0.0
        self.double_at = 0.0
        self.blink = 1.0
        self.action = ''
        self.action_start = 0.0
        self.red = 0.0
        self.opacity = 1.0

    def play(self, action, now):
        self.action, self.action_start = action, now
        if action == 'double_blink':
            self.next_blink = now
            self.double_at = now + .27

    def update(self, dt, now, emotion, gaze, drag_tilt=0, drag_stretch=0):
        spec = EMOTIONS[emotion]
        blend = 1 - math.exp(-dt * 9)
        for name in ('eye', 'smile', 'blush'):
            setattr(self, name, getattr(self, name) + (getattr(spec, name) - getattr(self, name)) * blend)
        gx, gy = gaze
        if emotion == 'embarrassed':
            gx, gy = -5, 3
        if self.action == 'look':
            gx = math.sin((now - self.action_start) * 3) * 5
        self.gaze_x += (gx - self.gaze_x) * blend
        self.gaze_y += (gy - self.gaze_y) * blend
        self.red += ((1 if emotion == 'angry' else 0) - self.red) * blend
        self.opacity += ((.65 if emotion == 'scared' else 1) - self.opacity) * blend
        if now >= self.next_blink or (self.double_at and now >= self.double_at):
            self.blink_until = now + .16
            if now >= self.next_blink:
                self.next_blink = now + random.uniform(3, 7)
                if random.random() < .25:
                    self.double_at = now + .27
            else:
                self.double_at = 0
        self.blink = max(.02, abs((self.blink_until - now) / .08 - 1)) if now < self.blink_until else 1
        tilt = spec.tilt + drag_tilt
        if emotion in ('confused', 'sleeping'):
            tilt += math.sin(now * 2) * 5
        self.tilt.update(tilt, dt)
        self.stretch.update(spec.stretch + abs(drag_tilt) * .004 + drag_stretch, dt)
        if now - self.action_start > 3:
            self.action = ''
