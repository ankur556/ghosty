"""Ghosty: a small, hand-drawn desktop companion. Run with python main.py."""

import math
import sys

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget


class GhostPet(QWidget):
    """A transparent pet window with floating, dragging, and click reactions."""

    WIDTH = 160
    HEIGHT = 160
    FLOAT_AMPLITUDE = 6
    FLOAT_PERIOD_MS = 2800

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ghosty")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

        self._float_offset = 0.0
        self._smiling = False
        self._press_position = None
        self._drag_offset = QPoint()
        self._dragging = False

        self._clock = QElapsedTimer()
        self._clock.start()
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start()

        self._smile_timer = QTimer(self)
        self._smile_timer.setSingleShot(True)
        self._smile_timer.setInterval(1500)
        self._smile_timer.timeout.connect(self._stop_smiling)

        self._menu = QMenu(self)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(exit_action)
        self._place_near_bottom_right()

    def _place_near_bottom_right(self):
        # Available geometry excludes the Windows taskbar.
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.x() + max(0, area.width() - self.width() - 24),
                area.y() + max(0, area.height() - self.height() - 24),
            )

    def _animate(self):
        phase = self._clock.elapsed() / self.FLOAT_PERIOD_MS * math.tau
        self._float_offset = math.sin(phase) * self.FLOAT_AMPLITUDE
        self.update()

    def _stop_smiling(self):
        self._smiling = False
        self.update()

    @staticmethod
    def _body_path():
        # Local coordinates: 100 pixels wide and approximately 120 tall.
        body = QPainterPath()
        body.moveTo(0, 108)
        body.lineTo(0, 50)
        body.cubicTo(0, -16, 100, -16, 100, 50)
        body.lineTo(100, 108)
        body.cubicTo(100, 124, 84, 124, 80, 110)
        body.cubicTo(74, 124, 66, 124, 60, 110)
        body.cubicTo(54, 124, 46, 124, 40, 110)
        body.cubicTo(34, 124, 26, 124, 20, 110)
        body.cubicTo(16, 124, 0, 124, 0, 108)
        body.closeSubpath()
        return body

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Move only the artwork so floating does not interfere with dragging.
        painter.translate(30, 20 + self._float_offset)
        painter.setPen(QPen(QColor("#dedeea"), 1.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(self._body_path())

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffb5ca"))
        painter.drawEllipse(14, 68, 18, 10)
        painter.drawEllipse(68, 68, 18, 10)

        painter.setBrush(QColor("#171721"))
        painter.drawEllipse(28, 46, 12, 21)
        painter.drawEllipse(60, 46, 12, 21)

        if self._smiling:
            smile = QPainterPath()
            smile.moveTo(39, 76)
            smile.cubicTo(44, 88, 56, 88, 61, 76)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#171721"), 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawPath(smile)
        else:
            painter.drawEllipse(47, 76, 6, 7)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_position = event.globalPosition().toPoint()
            self._drag_offset = self._press_position - self.pos()
            self._dragging = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_position is not None and event.buttons() & Qt.LeftButton:
            position = event.globalPosition().toPoint()
            distance = (position - self._press_position).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._dragging = True
                self.setCursor(Qt.ClosedHandCursor)
            if self._dragging:
                self.move(position - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_position is not None:
            if not self._dragging:
                self._smiling = True
                self._smile_timer.start()
                self.update()
            self._press_position = None
            self._dragging = False
            self.setCursor(Qt.PointingHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self._menu.popup(event.globalPos())
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ghosty")
    ghost = GhostPet()
    ghost.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
