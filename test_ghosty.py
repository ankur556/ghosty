"""Run: python -m unittest -v test_ghosty (offscreen; no global hook enabled)."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import math
import tempfile
import unittest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from activity import TypingReactions
from animations import Animation, Spring
from behavior import Behavior, EMOTIONS, State
from ghost import GhostPet
from interactions import Interactions
from movement import constrain
from particles import Particles
from renderer import draw_ghost
from settings import Settings

APP = QApplication.instance() or QApplication([])
TEMP = tempfile.TemporaryDirectory()
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, TEMP.name)


class BehaviorTests(unittest.TestCase):
    def test_user_priority_and_expiration(self):
        brain = Behavior()
        self.assertTrue(brain.react('happy', 1, 3))
        self.assertFalse(brain.react('sad', 2, 1))
        brain.update(.1, 6)
        self.assertEqual(brain.emotion, 'idle')

    def test_sleep_and_wake(self):
        brain = Behavior()
        brain.update(.1, 160)
        self.assertEqual(brain.emotion, 'sleepy')
        brain.update(.1, 310)
        self.assertEqual(brain.emotion, 'sleeping')
        brain.manual_sleep = True
        self.assertFalse(brain.react('excited', 320, 2))
        self.assertTrue(brain.react('happy', 320, 3))
        self.assertFalse(brain.manual_sleep)

    def test_typing_sequence_and_cooldown(self):
        typing = TypingReactions()
        self.assertEqual(typing.feed(3, 0), 'curious')
        self.assertIsNone(typing.feed(15, 1))
        for second in range(2, 5):
            typing.feed(5, second)
        self.assertEqual(typing.feed(6, 5), 'excited')
        self.assertEqual(typing.feed(14, 10), 'surprised')
        typing.feed(0, 13)
        typing.feed(0, 14)
        self.assertEqual(typing.feed(0, 15), 'confused')

    def test_spring_frame_rate_and_stability(self):
        results = []
        for fps in (20, 30, 60, 144):
            spring = Spring()
            for _ in range(fps * 3):
                spring.update(1, 1 / fps)
            self.assertTrue(math.isfinite(spring.value))
            results.append(spring.value)
        for result in results:
            self.assertAlmostEqual(result, 1, places=4)

    def test_short_typing_stop_survives_cooldown(self):
        typing = TypingReactions()
        self.assertEqual(typing.feed(1, 0), 'curious')
        for second in range(1, 5):
            self.assertIsNone(typing.feed(0, second))
        self.assertEqual(typing.feed(0, 5), 'confused')
        self.assertIsNone(typing.feed(0, 6))

    def test_particle_cap_and_expiry(self):
        particles = Particles()
        particles.emit('heart', 100)
        self.assertEqual(len(particles.items), 28)
        particles.update(3)
        self.assertEqual(particles.items, [])


class QtTests(unittest.TestCase):
    def setUp(self):
        QSettings('Ghosty', 'DesktopCompanion').clear()

    def test_gestures_are_exclusive(self):
        gestures = Interactions()
        seen = []
        gestures.gesture.connect(seen.append)
        gestures.press(QPoint(10, 10))
        gestures.release()
        gestures.double_click(QPoint(10, 10))
        gestures.release()
        QTest.qWait(APP.doubleClickInterval() + 30)
        self.assertEqual(seen, ['double'])
        seen.clear()
        gestures.press(QPoint(10, 10))
        QTest.qWait(700)
        gestures.release()
        QTest.qWait(APP.doubleClickInterval() + 30)
        self.assertEqual(seen, ['hold'])
        seen.clear()
        gestures.press(QPoint(10, 10))
        gestures.move(QPoint(100, 100))
        gestures.release()
        self.assertEqual(seen, ['drag', 'drop'])
        gestures.cancel()

    def test_settings_defaults_and_persistence(self):
        settings = Settings()
        self.assertFalse(settings.get('typing'))
        settings.set('intensity', .5)
        self.assertEqual(Settings().get('intensity'), .5)

    def test_all_expressions_transparency_and_drawing(self):
        for emotion in EMOTIONS:
            image = QImage(240, 250, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
            animation = Animation()
            for frame in range(90):
                animation.update(1 / 60, frame / 60, emotion, (2, 1))
            painter = QPainter(image)
            painter.translate(120, 150)
            draw_ghost(painter, animation, emotion, 1.5)
            painter.end()
            self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
            self.assertGreater(image.pixelColor(120, 140).alpha(), 100)

    def test_widget_lifecycle_pause_drag_and_bounds(self):
        pet = GhostPet()
        try:
            pet.show()
            QTest.qWait(80)
            self.assertTrue(pet.testAttribute(Qt.WA_TranslucentBackground))
            self.assertTrue(pet.windowFlags() & Qt.WindowDoesNotAcceptFocus)
            self.assertIsNone(pet.activity._hook)
            pet._gesture('drag')
            self.assertEqual(pet.brain.state, State.DRAGGED)
            pet._set_paused(True)
            now = pet.now
            QTest.qWait(120)
            self.assertEqual(pet.now, now)
            pet._set_paused(False)
            QTest.qWait(120)
            self.assertNotEqual(pet.brain.state, State.DRAGGED)
            constrained = constrain(QPointF(-99999, 99999), pet.size())
            screen = APP.primaryScreen().availableGeometry()
            self.assertTrue(screen.contains(constrained.toPoint()))
            self.assertTrue(screen.contains((constrained + QPointF(pet.width()-1, pet.height()-1)).toPoint()))
        finally:
            pet.close()
            self.assertFalse(pet._animation_timer.isActive())


if __name__ == '__main__':
    unittest.main()
