"""A capped, short-lived particle pool rendered without external assets."""
from dataclasses import dataclass
import math
import random
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen


@dataclass
class Particle:
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    scale: float
    age: float = 0


class Particles:
    def __init__(self):
        self.items = []

    def emit(self, kind, count=3):
        for _ in range(min(count, 28 - len(self.items))):
            self.items.append(Particle(kind, random.uniform(-45, 45), random.uniform(-35, 5),
                                       random.uniform(-10, 10), -random.uniform(13, 25),
                                       random.uniform(1.4, 2.4), random.uniform(.7, 1.2)))

    def update(self, dt):
        for item in self.items:
            item.age += dt
            item.x += item.vx * dt
            item.y += (25 if item.kind == 'tear' else item.vy) * dt
        self.items = [p for p in self.items if p.age < p.lifetime]

    def draw(self, p):
        for item in self.items:
            p.save()
            progress = item.age / item.lifetime
            p.setOpacity(min(1, item.age * 7) * (1 - progress) ** 1.5)
            p.translate(item.x, item.y)
            p.scale(item.scale * (.8 + progress * .4), item.scale * (.8 + progress * .4))
            p.setPen(Qt.NoPen)
            if item.kind == 'heart':
                heart = QPainterPath(QPointF(0, 6))
                heart.cubicTo(-15, -3, -4, -12, 0, -5)
                heart.cubicTo(4, -12, 15, -3, 0, 6)
                p.setBrush(QColor('#ff8cb5'))
                p.drawPath(heart)
            elif item.kind == 'note':
                # Vector note avoids dependence on music glyph availability.
                p.setBrush(QColor('#c5b8ff'))
                p.drawEllipse(QRectF(-5, 0, 7, 4))
                p.setPen(QPen(QColor('#c5b8ff'), 1.8))
                p.drawLine(QPointF(1, 1), QPointF(1, -9))
                p.drawLine(QPointF(1, -9), QPointF(6, -7))
            elif item.kind in ('zzz', 'question'):
                p.setPen(QColor('#9c9bd8'))
                p.setFont(QFont('Segoe UI', 13, QFont.Bold))
                p.drawText(QPointF(0, 0), 'z' if item.kind == 'zzz' else '?')
            elif item.kind == 'tear':
                p.setBrush(QColor('#8fceff'))
                p.drawEllipse(QRectF(-2, -4, 4, 8))
            else:
                p.setBrush(QColor('#c4b5ff' if item.kind == 'dust' else '#ffdc87'))
                star = QPainterPath()
                for index in range(8):
                    angle = index * math.pi / 4
                    radius = 6 if index % 2 == 0 else 2
                    point = QPointF(math.cos(angle) * radius, math.sin(angle) * radius)
                    star.moveTo(point) if index == 0 else star.lineTo(point)
                star.closeSubpath()
                p.drawPath(star)
            p.restore()
