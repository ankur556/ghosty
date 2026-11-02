"""Render synthetic examples; no audio or input monitoring. python preview_reactions.py"""
import math
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication
from animations import Animation
from animation_controller import AnimationController
from audio_reactive import AudioFeatures
from renderer import draw_ghost


def main():
    app = QApplication([])
    image = QImage(1040, 360, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor('#171c32'))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    for index, title in enumerate(('Quiet company', 'Music time', 'Typing buddy', 'Coding + music')):
        layers, animation = AnimationController(), Animation()
        music, typing = index in (1, 3), index in (2, 3)
        for frame in range(240):
            now = frame / 60
            if music:
                layers.dance.feed(AudioFeatures(.08, .02, .4, frame % 30 == 0), now)
            if typing and frame % 8 == 0:
                layers.keyboard.notice(now)
                layers.keyboard.snapshot({'A', 'LSHIFT'}, {'A'}, now)
                layers.hands.tap(now, layers.keyboard.key_center('A' if frame % 16 else 'L'))
            layers.update(1/60, now, 'idle')
            animation.update(1/60, now, layers.emotion, (0, 4) if typing else (1, 0))
        painter.save()
        painter.translate(index * 260 + 10, 4)
        painter.save()
        painter.translate(120, 154)
        draw_ghost(painter, animation, layers.emotion, now, 1, layers)
        painter.restore()
        layers.keyboard.draw(painter, 120, 196)
        layers.hands.draw(painter, 120, 220, layers.keyboard.alpha)
        painter.setPen(QColor('#dcdaf7'))
        painter.setFont(QFont('Segoe UI', 10))
        painter.drawText(QRectF(0, 305, 240, 30), Qt.AlignCenter, title)
        painter.restore()
    painter.end()
    image.save('ghosty-reactions.png')
    print('Saved ghosty-reactions.png (synthetic examples)')


if __name__ == '__main__':
    main()
