"""Screen-safe movement with spring following and soft release."""
import math
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QGuiApplication
from animations import Spring


def constrain(position, size):
    screens = QGuiApplication.screens()
    if not screens:
        return QPointF(position)
    center = position + QPointF(size.width() / 2, size.height() / 2)
    screen = QGuiApplication.screenAt(center.toPoint())
    if screen is None:
        screen = min(screens, key=lambda s: (s.availableGeometry().center() - center.toPoint()).manhattanLength())
    r = screen.availableGeometry()
    return QPointF(max(r.left(), min(position.x(), r.right() + 1 - size.width())),
                   max(r.top(), min(position.y(), r.bottom() + 1 - size.height())))


class Movement:
    def __init__(self, position):
        self.x, self.y = Spring(position.x()), Spring(position.y())
        self.target = QPointF(position)
        self.moving = False

    def set_target(self, position, size):
        self.target = constrain(QPointF(position), size)
        self.moving = True

    def update(self, dt, size, dragging=False, speed=1):
        self.target = constrain(self.target, size)
        stiffness, damping = (170, 24) if dragging else (8 * speed, 6)
        self.x.update(self.target.x(), dt, stiffness, damping)
        self.y.update(self.target.y(), dt, stiffness, damping)
        point = constrain(QPointF(self.x.value, self.y.value), size)
        if point.x() != self.x.value:
            self.x.velocity = 0
        if point.y() != self.y.value:
            self.y.velocity = 0
        self.x.value, self.y.value = point.x(), point.y()
        self.moving = math.hypot(self.target.x() - point.x(), self.target.y() - point.y()) > .7
        return point.toPoint()

    def stop(self, position):
        self.target = QPointF(position)
        self.x.value, self.y.value = position.x(), position.y()
        self.x.velocity = self.y.velocity = 0
        self.moving = False
