"""A transient US-QWERTY prop, painted in Ghosty's existing window."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPen


# Stable virtual-key identifiers, not characters decoded from keyboard input.
ROWS = [
    [('ESC', 'Esc', 1), *[(str(i), str(i), 1) for i in (1,2,3,4,5,6,7,8,9,0)],
     ('MINUS', '-', 1), ('PLUS', '=', 1), ('BACK', '⌫', 1.6)],
    [('TAB', 'Tab', 1.4), *[(c, c, 1) for c in 'QWERTYUIOP'],
     ('LBRACKET', '[', 1), ('RBRACKET', ']', 1), ('SLASHBACK', '\\', 1.2)],
    [('CAPS', 'Caps', 1.7), *[(c, c, 1) for c in 'ASDFGHJKL'],
     ('SEMICOLON', ';', 1), ('QUOTE', "'", 1), ('ENTER', 'Enter', 1.9)],
    [('LSHIFT', 'Shift', 2.1), *[(c, c, 1) for c in 'ZXCVBNM'],
     ('COMMA', ',', 1), ('PERIOD', '.', 1), ('SLASH', '/', 1), ('RSHIFT', 'Shift', 2.5)],
    [('LCTRL', 'Ctrl', 1.5), ('LWIN', 'Win', 1.3), ('LALT', 'Alt', 1.3),
     ('SPACE', '', 6.2), ('RALT', 'Alt', 1.3), ('RCTRL', 'Ctrl', 1.5)],
]
VK_KEYS = {ord(c): c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'}
VK_KEYS.update({0x1B:'ESC', 0x08:'BACK', 0x09:'TAB', 0x14:'CAPS', 0x0D:'ENTER',
    0x20:'SPACE', 0xA0:'LSHIFT', 0xA1:'RSHIFT', 0xA2:'LCTRL', 0xA3:'RCTRL',
    0xA4:'LALT', 0xA5:'RALT', 0x5B:'LWIN', 0x5C:'LWIN', 0x10:'LSHIFT',
    0x11:'LCTRL', 0x12:'LALT', 0xBD:'MINUS', 0xBB:'PLUS', 0xDB:'LBRACKET',
    0xDD:'RBRACKET', 0xDC:'SLASHBACK', 0xBA:'SEMICOLON', 0xDE:'QUOTE',
    0xBC:'COMMA', 0xBE:'PERIOD', 0xBF:'SLASH'})


class KeyboardOverlay:
    WIDTH, HEIGHT = 218, 79

    def __init__(self):
        self.alpha = 0.0
        self.last_activity = -100.0
        self.down = set()
        self.levels = {}
        self.pulses = {}
        self.font = QFont('Segoe UI')
        self.font.setPixelSize(6)
        self.keys = []
        for row_index, row in enumerate(ROWS):
            unit = (self.WIDTH - 12) / sum(width for _, _, width in row)
            x = -self.WIDTH / 2 + 6
            for key, label, width in row:
                rect = QRectF(x, 5 + row_index * 13.5, unit * width - 1.6, 11.5)
                self.keys.append((key, label, rect))
                x += unit * width

    def notice(self, now):
        self.last_activity = now

    def snapshot(self, down, pulses, now):
        self.down = set(down)
        for key in pulses:
            self.pulses[key] = now + .11

    def clear_keys(self):
        self.down.clear()
        self.levels.clear()
        self.pulses.clear()

    def clear(self):
        self.clear_keys()
        self.last_activity = -100
        self.alpha = 0

    def update(self, dt, now, suppressed=False):
        visible = not suppressed and (now - self.last_activity < 2.5 or bool(self.down))
        self.alpha += ((1 if visible else 0) - self.alpha) * (1 - math.exp(-dt * (16 if visible else 5)))
        self.pulses = {k: until for k, until in self.pulses.items() if until > now}
        for key, _, _ in self.keys:
            target = float(key in self.down or key in self.pulses)
            value = self.levels.get(key, 0)
            self.levels[key] = value + (target - value) * (1 - math.exp(-dt * 24))
        if not visible and self.alpha < .005:
            self.alpha = 0
            self.clear_keys()

    def key_center(self, key):
        return next((r.center() for k, _, r in self.keys if k == key), QPointF())

    def draw(self, p, center_x, top):
        if self.alpha < .005:
            return
        p.save()
        p.translate(center_x, top + (1 - self.alpha) * 9)
        p.scale(.92 + self.alpha * .08, .92 + self.alpha * .08)
        p.setOpacity(self.alpha)
        panel = QRectF(-self.WIDTH / 2, 0, self.WIDTH, self.HEIGHT)
        for width, opacity in ((10, 12), (5, 24)):
            p.setPen(QPen(QColor(150, 140, 255, opacity), width))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(panel, 9, 9)
        gradient = QLinearGradient(0, 0, 0, self.HEIGHT)
        gradient.setColorAt(0, QColor(57, 53, 90, 232))
        gradient.setColorAt(1, QColor(31, 33, 58, 225))
        p.setPen(QPen(QColor(188, 181, 245, 180), .8))
        p.setBrush(gradient)
        p.drawRoundedRect(panel, 8, 8)
        p.setFont(self.font)
        for key, label, rect in self.keys:
            level = self.levels.get(key, 0)
            depressed = rect.translated(0, level * 1.1)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(13, 15, 34, 150))
            p.drawRoundedRect(rect.translated(0, 1.6), 2.3, 2.3)
            p.setBrush(QColor(int(87 + 65 * level), int(85 + 85 * level), int(123 + 120 * level), 240))
            p.setPen(QPen(QColor(200, 200, 255, int(35 + level * 150)), .6))
            p.drawRoundedRect(depressed, 2.3, 2.3)
            p.setPen(QColor('#f3f0ff'))
            p.drawText(depressed, Qt.AlignCenter, label)
        p.restore()
