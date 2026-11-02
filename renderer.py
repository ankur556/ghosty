"""Vector artwork: the original rounded ghost, now with a living silhouette."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen


def body_path(t):
    path = QPainterPath()
    path.moveTo(-50, 44)
    path.lineTo(-50, -14)
    path.cubicTo(-50, -80, 50, -80, 50, -14)
    path.lineTo(50, 44)
    for index in range(5):
        x = 50 - index * 20
        wave = math.sin(t * 2.7 + index * .9) * 3
        path.cubicTo(x - 3, 60 + wave, x - 16, 60 + wave, x - 20, 44 + wave)
    path.closeSubpath()
    return path


def draw_ghost(p, a, emotion, now, intensity=1, layers=None):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    slow = .45 if emotion in ('sleepy', 'sleeping', 'sad') else 1
    hover = (math.sin(now * 2 * slow) * 5 + math.sin(now * 3.3 * slow) * 1.5) * intensity
    bounce = abs(math.sin(now * (9 if emotion == 'excited' else 5))) * 7 * intensity if emotion in ('happy', 'excited', 'love') else 0
    shake = math.sin(now * 43) * 1.8 * intensity if emotion in ('scared', 'angry') else 0
    elapsed = now - a.action_start
    rotation = a.tilt.value * intensity
    if emotion == 'surprised':
        rotation += math.sin(now * 10) * 3 * intensity
    if a.action == 'dizzy':
        rotation += math.sin(elapsed * 8) * 12 * intensity
    alpha = a.opacity
    if a.action == 'spin':
        progress = min(1, elapsed / 1.2)
        rotation += 360 * progress ** 2 * (3 - 2 * progress)
    if a.action == 'vanish':
        alpha *= .15 + .85 * abs(math.cos(min(elapsed / 3, 1) * math.pi))
    if a.action == 'circle':
        shake += math.sin(elapsed * 3) * 10 * intensity
        hover += math.cos(elapsed * 3) * 6 * intensity
    if a.action == 'hiccup':
        bounce += max(0, math.sin(elapsed * 10)) ** 12 * 8 * intensity
    glow = 0.0
    extra_stretch = 0.0
    if layers:
        dance = layers.dance
        glow = dance.glow
        if not layers.direct:
            shake += dance.x * intensity
            hover += dance.y * intensity
            rotation += dance.rotation * intensity
            rotation += dance.spin
            extra_stretch = dance.stretch * intensity - layers.squash
        if layers.typing:
            bounce *= .2
            if layers.hands.rate > 11:
                rotation += math.sin(now * 9) * 3 * intensity
                shake += math.sin(now * 13) * 1.2 * intensity
    p.translate(shake, hover - bounce + (7 if emotion == 'sad' else 0))
    p.rotate(rotation)
    stretch = max(.75, min(1.3, 1 + (a.stretch.value - 1) * intensity + extra_stretch))
    breath = math.sin(now * 2.3) * .015 * intensity
    p.scale((1 + breath) / stretch, stretch + breath)
    p.setOpacity(alpha)
    body = body_path(now)
    for width, opacity in ((20, 5), (14, 9), (8, 16)):
        hue = int(151 + math.sin(now * .4) * 16 * glow)
        p.setPen(QPen(QColor(hue, 156, 255, int(opacity * (1 + glow * 2))), width + glow * 3))
        p.setBrush(Qt.NoBrush)
        p.drawPath(body)
    fill = QLinearGradient(0, -60, 15, 60)
    fill.setColorAt(0, QColor('white'))
    fill.setColorAt(.65, QColor(255, int(253 - 28 * a.red), int(255 - 24 * a.red)))
    fill.setColorAt(1, QColor('#dfe7ff'))
    p.setBrush(fill)
    p.setPen(QPen(QColor('#c9d4f4'), 1.2))
    p.drawPath(body)
    # Tiny arms give waves and tail-play a readable silhouette.
    p.setPen(QPen(QColor('#edf1ff'), 9, Qt.SolidLine, Qt.RoundCap))
    arm = math.sin(elapsed * 10) * 8 if a.action in ('wave', 'tail') else 0
    if not layers or not layers.typing:
        p.drawLine(QPointF(-43, 10), QPointF(-54, 5 + arm))
        p.drawLine(QPointF(43, 10), QPointF(54, 5 - arm))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 131, 175, int(80 + a.blush * 125)))
    p.drawEllipse(QRectF(-38, 6, 20, 10))
    p.drawEllipse(QRectF(18, 6, 20, 10))
    ink = QColor('#29304c')
    p.setPen(QPen(ink, 3, Qt.SolidLine, Qt.RoundCap))
    for side in (-1, 1):
        x = side * 18 + a.gaze_x * (1 if side == -1 else .85)
        y = -8 + a.gaze_y
        openness = a.eye * a.blink
        if emotion == 'confused' and side == 1:
            openness *= .45
        if openness < .24:
            eye = QPainterPath(QPointF(x - 6, y))
            eye.quadTo(x, y - (5 if a.smile > .6 else -3), x + 6, y)
            p.setBrush(Qt.NoBrush)
            p.drawPath(eye)
        else:
            h = 20 * openness
            p.setBrush(ink)
            p.drawEllipse(QRectF(x - 6, y - h / 2, 12, h))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('white'))
            p.drawEllipse(QRectF(x - 3, y - h / 2 + 3, 3.5, 4.5))
            p.setPen(QPen(ink, 3, Qt.SolidLine, Qt.RoundCap))
        if emotion in ('angry', 'sad'):
            slope = (-4 if emotion == 'angry' else 3) * side
            p.drawLine(QPointF(x - 7, y - 18 - slope), QPointF(x + 7, y - 18 + slope))
    p.setBrush(Qt.NoBrush)
    mouth = QPainterPath(QPointF(-8, 20))
    mouth.quadTo(0, 20 + a.smile * 16, 8, 20)
    yawn = emotion == 'sleepy' and math.sin(now * 1.5) > .6
    if emotion in ('surprised', 'scared') or yawn:
        p.setBrush(ink)
        p.drawEllipse(QRectF(-4, 17, 8, 12 if yawn else 9))
    else:
        p.drawPath(mouth)
    p.restore()
