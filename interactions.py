"""Gesture recognition independent of painting and behavior."""
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication


class Interactions(QObject):
    gesture = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.origin = None
        self.dragging = self.held = self.double = False
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(lambda: self.gesture.emit('click'))
        self.hold_timer = QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.setInterval(650)
        self.hold_timer.timeout.connect(self._hold)

    def press(self, point):
        self.origin = point
        self.dragging = self.held = self.double = False
        self.hold_timer.start()

    def move(self, point):
        if self.origin is not None and not self.dragging:
            if (point - self.origin).manhattanLength() >= QApplication.startDragDistance():
                self.dragging = True
                self.hold_timer.stop()
                self.click_timer.stop()
                self.gesture.emit('drag')

    def double_click(self, point):
        self.press(point)
        self.double = True
        self.click_timer.stop()
        self.hold_timer.stop()
        self.gesture.emit('double')

    def _hold(self):
        self.held = True
        self.click_timer.stop()
        self.gesture.emit('hold')

    def release(self):
        if self.origin is None:
            return
        self.hold_timer.stop()
        if self.dragging:
            self.gesture.emit('drop')
        elif not self.held and not self.double:
            self.click_timer.start(QApplication.doubleClickInterval())
        self.origin = None
        self.dragging = False

    def cancel(self):
        self.origin = None
        self.dragging = False
        self.hold_timer.stop()
        self.click_timer.stop()
