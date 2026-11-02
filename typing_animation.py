"""Transient alternating hands and a smoothed tap envelope; no input history."""
import math
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen


class TypingAnimation:
    def __init__(self):
        self.rate = 0.0
        self.last_tap = -100.0
        self.hand = 0
        self.taps = [0.0, 0.0]
        self.targets = [-29.0, 29.0]
        self.positions = [-29.0, 29.0]

    def tap(self, now, key_position=None):
        interval = now - self.last_tap
        if interval > .025:
            instantaneous = min(18, 1 / max(.055, interval))
            self.rate = self.rate * .65 + instantaneous * .35
            self.hand = 1 - self.hand
            self.taps[self.hand] = 1
            self.last_tap = now
        if key_position is not None:
            self.targets[self.hand] = max(-88, min(88, key_position.x()))

    def update(self, dt, now):
        for hand in range(2):
            self.taps[hand] *= math.exp(-dt * 12)
            self.positions[hand] += (self.targets[hand] - self.positions[hand]) * (1 - math.exp(-dt * 18))
        if now - self.last_tap > .4:
            self.rate *= math.exp(-dt * 2)

    @property
    def squash(self):
        return max(self.taps) * .035

    @property
    def emotion(self):
        return 'surprised' if self.rate > 11 else 'excited' if self.rate > 7 else 'happy' if self.rate > 3 else 'curious'

    def draw(self, p, x, y, alpha):
        if alpha < .005:
            return
        p.save()
        p.setOpacity(alpha)
        p.setPen(QPen(QColor('#cdd9ff'), .8))
        for hand in range(2):
            lift = math.sin(self.taps[hand] * math.pi) * 6
            px, py = x + self.positions[hand], y - lift + self.taps[hand] * 3
            p.setBrush(QColor(161, 175, 255, 55))
            p.drawEllipse(QRectF(px - 10, py - 5, 20, 12))
            p.setBrush(QColor(250, 252, 255, 245))
            p.drawEllipse(QRectF(px - 7, py - 6, 14, 10))
        p.restore()
