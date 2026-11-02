"""Short event-based dialogue painted inside the screen-clamped pet window."""
import random
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPen


LINES = {
    'happy': ['Hehe!', 'That tickles!', 'I believe in you!'],
    'love': ['You make my day!', 'My favorite human.'],
    'curious': ['Whatcha doing?', 'Boo!'],
    'excited': ['Look at you go!', 'Wheee!'],
    'surprised': ["You're typing so fast!", 'Whoa!'],
    'confused': ['Where did you go?', 'Hmm?'],
    'angry': ['I am a scary ghost! Boo!'],
    'sleepy': ["I'm sleepy..."],
    'embarrassed': ['Oh! Hello...', 'Hehe!'],
    'scared': ['Eep!'],
    'sad': ['A little company?'],
}


class Dialogue:
    def __init__(self):
        self.text = ''
        self.start = -100.0
        self.next_allowed = 0.0

    def say(self, emotion, now, frequency='normal', quiet=False):
        if quiet or frequency == 'off' or now < self.next_allowed or emotion not in LINES:
            return
        self.text = random.choice(LINES[emotion])
        self.start = now
        self.next_allowed = now + {'rare': 60, 'normal': 25, 'chatty': 10}[frequency]

    def draw(self, p, now, width):
        age = now - self.start
        if not self.text or not 0 <= age < 4:
            return
        p.save()
        p.setOpacity(min(1, age / .3, (4 - age) / .6))
        p.setBrush(QColor(250, 250, 255, 242))
        p.setPen(QPen(QColor('#dcdcf2'), 1))
        p.drawRoundedRect(QRectF(12, 9, width - 24, 48), 15, 15)
        p.setPen(QColor('#5c587e'))
        p.setFont(QFont('Segoe UI', 9))
        p.drawText(QRectF(22, 12, width - 44, 42), Qt.AlignCenter | Qt.TextWordWrap, self.text)
        p.restore()
