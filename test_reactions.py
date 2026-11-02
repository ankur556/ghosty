"""Synthetic audio/input tests: no real keyboard hook or capture is enabled."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import unittest
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from test_ghosty import APP
from animation_controller import AnimationController
from audio_reactive import AudioFeatures, FeatureExtractor
from dance import Dance
from input_privacy import approved_control
from input_privacy import FocusGuard
from keyboard_overlay import KeyboardOverlay, VK_KEYS
from settings import Settings


class KeyboardTests(unittest.TestCase):
    def test_full_layout(self):
        keyboard = KeyboardOverlay()
        keys = {key for key, _, _ in keyboard.keys}
        self.assertTrue(set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') <= keys)
        self.assertTrue({'SPACE', 'ENTER', 'BACK', 'LSHIFT', 'RSHIFT', 'LCTRL', 'LALT', 'TAB', 'ESC'} <= keys)
        self.assertEqual(len(keys), len(keyboard.keys))
        self.assertEqual(VK_KEYS[0xA1], 'RSHIFT')

    def test_show_hide_reverse_and_held_modifiers(self):
        keyboard = KeyboardOverlay()
        keyboard.notice(0)
        keyboard.snapshot({'LSHIFT', 'A'}, {'A'}, 0)
        for index in range(30):
            keyboard.update(1/60, index/60)
        self.assertGreater(keyboard.alpha, .98)
        self.assertGreater(keyboard.levels['LSHIFT'], .98)
        keyboard.snapshot({'LSHIFT'}, set(), .5)
        for index in range(240):
            keyboard.update(1/60, .5 + index/60)
        self.assertGreater(keyboard.alpha, .98)
        self.assertLess(keyboard.levels['A'], .01)
        keyboard.snapshot(set(), set(), 4.5)
        keyboard.update(.1, 4.6)
        fading = keyboard.alpha
        keyboard.notice(4.6)
        keyboard.update(.1, 4.7)
        self.assertGreater(keyboard.alpha, fading)
        keyboard.clear()
        self.assertFalse(keyboard.down)
        self.assertEqual(keyboard.alpha, 0)

    def test_layer_priority_and_combination(self):
        controller = AnimationController()
        for index in range(240):
            now = index / 60
            controller.dance.feed(AudioFeatures(.08, .02), now)
            controller.update(1/60, now, 'idle')
        self.assertTrue(controller.dance.active)
        controller.keyboard.notice(4)
        controller.hands.tap(4)
        controller.update(.1, 4, 'idle')
        self.assertTrue(controller.typing)
        self.assertGreater(controller.dance.glow, 0)
        controller.update(.1, 4.1, 'angry', direct=True)
        self.assertFalse(controller.typing)
        self.assertEqual(controller.emotion, 'angry')
        for index in range(300):
            now = 4.2 + index / 60
            controller.dance.feed(AudioFeatures(.08, .02), now)
            controller.update(1/60, now, 'idle')
        self.assertEqual(controller.keyboard.alpha, 0)
        self.assertTrue(controller.dance.active)

    def test_keyboard_and_hands_paint_with_transparent_corners(self):
        controller = AnimationController()
        controller.keyboard.notice(0)
        controller.keyboard.snapshot({'A', 'SPACE'}, {'A'}, 0)
        controller.hands.tap(0)
        controller.update(.1, .1, 'idle')
        image = QImage(240, 290, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        controller.keyboard.draw(painter, 120, 196)
        controller.hands.draw(painter, 120, 220, controller.keyboard.alpha)
        painter.end()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertGreater(image.pixelColor(120, 250).alpha(), 100)


class PrivacyTests(unittest.TestCase):
    def test_expired_or_changed_focus_never_authorizes_keys(self):
        import time
        from unittest.mock import Mock
        guard = FocusGuard()
        guard.native = Mock()
        guard.native.desktop_safe.return_value = True
        guard.native.identity.return_value = (10, 20, 30)
        guard._hooks = [1, 2, 3]
        guard.token = (time.monotonic(), (10, 20, 30), True)
        self.assertTrue(guard.allowed())
        guard.native.identity.return_value = (10, 21, 30)
        self.assertFalse(guard.allowed())
        guard.native.identity.return_value = (10, 20, 30)
        guard.token = (time.monotonic() - 1, (10, 20, 30), True)
        self.assertFalse(guard.allowed())
        guard.token = (time.monotonic(), (10, 20, 30), True)
        guard.native.desktop_safe.return_value = False
        self.assertFalse(guard.allowed())
        guard.invalidate()
        self.assertIsNone(guard.token)
        guard._hooks.clear()

    def test_gate_denies_unknown_password_and_non_editors(self):
        self.assertTrue(approved_control('notepad.exe', 50004, 'Edit', False, True))
        self.assertTrue(approved_control('notepad.exe', 50030, 'RichEditD2DPT', False, True))
        self.assertTrue(approved_control('code.exe', 50004, 'inputarea monaco-mouse-cursor-text', False, True))
        for app, kind, cls, password, focused in (
            ('chrome.exe', 50004, 'Edit', False, True),
            ('notepad.exe', 50004, 'Edit', True, True),
            ('notepad.exe', 50004, 'Edit', None, True),
            ('code.exe', 50004, 'textarea', False, True),
            ('code.exe', 50004, 'inputarea', False, False),
            ('code.exe', 50000, 'inputarea', False, True),
        ):
            self.assertFalse(approved_control(app, kind, cls, password, focused))

    def test_defaults_are_opt_in(self):
        from PySide6.QtCore import QSettings
        QSettings('Ghosty', 'DesktopCompanion').clear()
        settings = Settings()
        for key in ('typing', 'key_highlights', 'music'):
            self.assertFalse(settings.get(key))


class AudioTests(unittest.TestCase):
    def tone(self, hz, amplitude=.1):
        return amplitude * np.sin(np.arange(1024) * 2 * np.pi * hz / 24000)

    def test_rms_bass_and_stereo_phase(self):
        tone = self.tone(93.75)
        features = FeatureExtractor().process(tone)
        stereo = FeatureExtractor().process(np.column_stack((tone, -tone)))
        high = FeatureExtractor().process(self.tone(3000))
        self.assertAlmostEqual(features.rms, .1 / np.sqrt(2), places=4)
        self.assertAlmostEqual(stereo.rms, features.rms, places=6)
        self.assertAlmostEqual(stereo.bass, features.bass, places=6)
        self.assertGreater(features.bass, high.bass * 100)

    def test_onset_drop_cooldowns_and_invalid_samples(self):
        extractor = FeatureExtractor()
        for _ in range(80):
            extractor.process(self.tone(93.75, .005))
        first = extractor.process(self.tone(93.75, .3))
        second = extractor.process(self.tone(93.75, .3))
        self.assertTrue(first.beat)
        self.assertTrue(first.bass_drop)
        self.assertFalse(second.beat)
        self.assertFalse(second.bass_drop)
        self.assertEqual(extractor.process(np.full(1024, np.nan)), AudioFeatures())

    def test_notifications_hysteresis_and_stale_audio(self):
        dance = Dance()
        for index in range(60):
            now = index / 60
            dance.feed(AudioFeatures(.1), now)
            dance.update(1/60, now)
        self.assertFalse(dance.active)
        for index in range(120):
            dance.update(1/60, 1 + index/60)
        self.assertFalse(dance.active)
        for index in range(180):
            now = 3 + index / 60
            dance.feed(AudioFeatures(.08), now)
            dance.update(1/60, now)
        self.assertTrue(dance.active)
        dance.update(.05, 6.1)
        self.assertTrue(dance.active)
        for index in range(300):
            dance.update(1/60, 6.2 + index/60)
        self.assertFalse(dance.active)
        self.assertLess(dance.blend, .01)


if __name__ == '__main__':
    unittest.main()
