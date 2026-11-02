"""Generate an expression contact sheet: python preview.py."""
import os
import sys
if sys.platform != 'win32':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication
from animations import Animation
from behavior import EMOTIONS
from renderer import draw_ghost


def main():
    app = QApplication([])
    image = QImage(1040, 920, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor('#171c32'))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setFont(QFont('Segoe UI', 11))
    for index, emotion in enumerate(EMOTIONS):
        x, y = (index % 4) * 260, (index // 4) * 230
        painter.save()
        painter.translate(x + 130, y + 115)
        animation = Animation()
        for frame in range(120):
            animation.update(1 / 60, frame / 60, emotion, (1, 0))
        draw_ghost(painter, animation, emotion, 2)
        painter.restore()
        painter.setPen(QColor('#d9def6'))
        painter.drawText(QRectF(x, y + 190, 260, 28), Qt.AlignCenter, emotion.title())
    painter.end()
    image.save('ghosty-expressions.png')
    print('Saved ghosty-expressions.png')


if __name__ == '__main__':
    main()
