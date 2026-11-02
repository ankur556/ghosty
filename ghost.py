"""Desktop widget coordinating drawing, movement, behavior, and controls."""
import math
import random
import time
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QActionGroup, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget
from activity import KeyboardActivity, TypingReactions
from animations import Animation
from behavior import Behavior, EMOTIONS, State
from dialogue import Dialogue
from interactions import Interactions
from movement import Movement
from particles import Particles
from renderer import draw_ghost
from settings import Settings
from animation_controller import AnimationController
from audio_reactive import AudioMonitor


class GhostPet(QWidget):
    WIDTH, HEIGHT = 240, 290

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ghosty')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.settings, self.brain = Settings(), Behavior()
        self.animation, self.particles, self.dialogue = Animation(), Particles(), Dialogue()
        self.interactions = Interactions(self)
        self.interactions.gesture.connect(self._gesture)
        self.activity = KeyboardActivity(self)
        self.activity.sample.connect(self._typing_sample)
        self.layers = AnimationController()
        self.activity.pulse.connect(self._typing_pulse)
        self.activity.key_changed.connect(self._key_changed)
        self.activity.cleared.connect(self.layers.keyboard.clear_keys)
        self.audio = AudioMonitor(self)
        self.audio.features.connect(lambda features: self.layers.dance.feed(features, self.now))
        self.audio.unavailable.connect(self._audio_unavailable)
        self._next_music_particle = 0.0
        self._next_privacy_check = 0.0
        self._draw_emotion = 'idle'
        self.typing = TypingReactions()
        self.paused = self.click_through = False
        self.now = 0.0
        self._last_tick = time.monotonic()
        self._cursor = QCursor.pos()
        self._near = False
        self._near_since = self._cursor_cooldown = self._next_particle = 0.0
        self._last_click, self._click_count = -10.0, 0
        self._drag_offset = QPointF()
        self._place_near_bottom_right()
        self.movement = Movement(self.pos())
        self._build_menu()
        self._build_tray()
        self._animation_timer = QTimer(self)
        self._animation_timer.setTimerType(Qt.PreciseTimer)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start(16)
        app = QApplication.instance()
        app.aboutToQuit.connect(self.cleanup)
        app.screenRemoved.connect(lambda *_: self._repair_position())
        app.screenAdded.connect(self._watch_screen)
        for screen in app.screens():
            self._watch_screen(screen)
        if self.settings.get('typing'):
            QTimer.singleShot(0, lambda: self._set_typing(True))
        if self.settings.get('music'):
            QTimer.singleShot(0, lambda: self._set_music(True))

    def _watch_screen(self, screen):
        screen.availableGeometryChanged.connect(lambda *_: self._repair_position())

    def _repair_position(self):
        self.movement.set_target(self.pos(), self.size())
        self.move(self.movement.target.toPoint())
        self.movement.stop(self.pos())

    def _place_near_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.x() + max(0, area.width() - self.width() - 24),
                      area.y() + max(0, area.height() - self.height() - 24))

    def _check_action(self, label, checked, callback):
        action = self._menu.addAction(label)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(callback)
        return action

    def _choices(self, title, setting, options):
        menu = self._menu.addMenu(title)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for label, value in options:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.settings.get(setting) == value)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, k=setting, v=value: self.settings.set(k, v))

    def _build_menu(self):
        self._menu = QMenu(self)
        self._menu.addAction('Ghosty · your little desktop spirit').setEnabled(False)
        self._menu.addSeparator()
        self.pause_action = self._check_action('Pause', False, self._set_paused)
        self.sleep_action = self._check_action('Sleep', False, self._set_sleep)
        self._check_action('Quiet mode', self.settings.get('quiet'), self._set_quiet)
        self.typing_action = self._check_action('Typing companion (generic motions)',
                                               self.settings.get('typing'), self._set_typing)
        self.highlights_action = self._check_action('Show individual keys (approved editors only)',
                                                    self.settings.get('key_highlights'), self._set_highlights)
        self.music_action = self._check_action('Dance to computer audio', self.settings.get('music'), self._set_music)
        self._menu.addAction('Disable typing and key highlights now').triggered.connect(self._disable_typing)
        self._check_action('Allow wandering', self.settings.get('wandering'),
                           lambda value: self.settings.set('wandering', value))
        self.through_action = self._check_action('Click-through (use tray to disable)', False, self._set_click_through)
        self._choices('Animation intensity', 'intensity', [('Gentle', .5), ('Normal', 1.0), ('Lively', 1.5)])
        self._choices('Movement speed', 'speed', [('Slow', .5), ('Normal', 1.0), ('Quick', 1.5)])
        self._choices('Speech frequency', 'dialogue', [(x.title(), x) for x in ('off', 'rare', 'normal', 'chatty')])
        preview = self._menu.addMenu('Preview emotion')
        for emotion in EMOTIONS:
            preview.addAction(emotion.title()).triggered.connect(
                lambda checked=False, e=emotion: self._react(e, 3))
        self._menu.addSeparator()
        self._menu.addAction('Bring Ghosty home').triggered.connect(self._home)
        self._menu.addAction('Exit').triggered.connect(QApplication.quit)

    def _build_tray(self):
        icon = QPixmap(64, 64)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.translate(32, 32)
        painter.scale(.44, .44)
        draw_ghost(painter, Animation(), 'idle', 0)
        painter.end()
        self.setWindowIcon(QIcon(icon))
        self.tray = QSystemTrayIcon(QIcon(icon), self)
        self.tray.setToolTip('Ghosty · right-click for controls')
        self.tray.setContextMenu(self._menu)
        self.tray.activated.connect(self._tray_activated)
        self.through_action.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._set_click_through(False)
            self._home()

    def _home(self):
        self._place_near_bottom_right()
        self.movement.stop(self.pos())
        self.show()

    def _set_click_through(self, enabled):
        if enabled and not self.tray.isVisible():
            self.through_action.setChecked(False)
            return
        self.click_through = enabled
        self.through_action.setChecked(enabled)
        self.interactions.cancel()
        if self.brain.state == State.DRAGGED:
            self.brain.until = self.now
        self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
        self.show()

    def _set_quiet(self, enabled):
        self.settings.set('quiet', enabled)
        if enabled:
            self.dialogue.text = ''

    def _set_paused(self, enabled):
        self.paused = enabled
        self.pause_action.setChecked(enabled)
        self.interactions.cancel()
        if self.brain.state == State.DRAGGED:
            self.brain.until = self.now
        self.movement.stop(self.pos())
        self.typing = TypingReactions()
        if enabled:
            self.activity.stop()
            self.audio.stop()
            self.layers.clear_typing()
            self.layers.dance.clear()
        elif self.settings.get('typing'):
            self._set_typing(True)
        if not enabled and self.settings.get('music'):
            self._set_music(True)
        self.update()
        self._last_tick = time.monotonic()

    def _set_sleep(self, enabled):
        if enabled:
            self.layers.clear_typing()
            self._react('sleeping', 3)
            self.brain.manual_sleep = True
            self.movement.stop(self.pos())
        else:
            self.brain.manual_sleep = False
            self._react('happy', 3)
        self.sleep_action.setChecked(enabled)

    def _set_typing(self, enabled):
        self.activity.stop()
        self.layers.clear_typing()
        self.typing = TypingReactions()
        self.activity.set_visualization(enabled and self.settings.get('key_highlights'))
        if enabled and not self.paused:
            try:
                self.activity.start()
            except OSError as error:
                enabled = False
                self.tray.showMessage('Typing reactions unavailable', str(error), QSystemTrayIcon.Warning)
        self.settings.set('typing', enabled)
        self.typing_action.setChecked(enabled)

    def _set_highlights(self, enabled):
        self.settings.set('key_highlights', enabled)
        self.highlights_action.setChecked(enabled)
        if enabled and not self.settings.get('typing'):
            self._set_typing(True)
        self.activity.set_visualization(enabled and self.settings.get('typing'))
        self.layers.keyboard.clear_keys()
        self.update()

    def _disable_typing(self):
        self._set_highlights(False)
        self._set_typing(False)
        self.update()

    def _set_music(self, enabled):
        self.settings.set('music', enabled)
        self.music_action.setChecked(enabled)
        if enabled and not self.paused:
            try:
                self.audio.start()
            except Exception:
                self._audio_unavailable()
        else:
            self.audio.stop()
            self.layers.dance.clear()

    def _audio_unavailable(self):
        self.audio.stop()
        self.layers.dance.clear()
        self.settings.set('music', False)
        self.music_action.setChecked(False)
        self.tray.showMessage('Music reactions unavailable',
            'Output loopback could not be opened. Ghosty still works. Check the default audio output and retry from the tray.',
            QSystemTrayIcon.Warning)

    def _typing_pulse(self):
        if self.paused or self.brain.manual_sleep or not self.settings.get('typing'):
            return
        self.brain.last_interaction = self.now
        if self.interactions.origin is not None:
            return
        self.layers.keyboard.notice(self.now)
        self.layers.hands.tap(self.now)
        self.animation.action = ''
        self.movement.stop(self.pos())
        self._animation_timer.setInterval(16)

    def _key_changed(self, key, down):
        if self.paused or self.brain.manual_sleep or self.interactions.origin is not None:
            return
        keyboard = self.layers.keyboard
        if down:
            keyboard.down.add(key)
            keyboard.pulses[key] = self.now + .11
            self.layers.hands.tap(self.now, keyboard.key_center(key))
            if key == 'ENTER':
                self.animation.stretch.velocity += .4
        else:
            keyboard.down.discard(key)

    def _react(self, emotion, priority=1, duration=None, state=None):
        if self.paused or not self.brain.react(emotion, self.now, priority, duration, state):
            return False
        if priority >= 2:
            self.animation.action = ''
            if not self.interactions.dragging:
                self.movement.stop(self.pos())
        self.sleep_action.setChecked(self.brain.manual_sleep)
        self.dialogue.say(emotion, self.now, self.settings.get('dialogue'), self.settings.get('quiet'))
        if emotion in ('happy', 'love'):
            self.particles.emit('heart', 3)
        if emotion == 'surprised':
            self.animation.stretch.velocity += 1.2
        return True

    def _gesture(self, kind):
        if self.paused:
            return
        if kind in ('click', 'double'):
            self._click_count = self._click_count + (2 if kind == 'double' else 1) if self.now - self._last_click < 2 else 1
            self._last_click = self.now
            emotion = 'angry' if self._click_count >= 5 else ('excited' if kind == 'double' else 'happy')
            self._react(emotion, 3)
            self.animation.stretch.velocity += 1.3
        elif kind == 'hold':
            self._react('embarrassed', 3, state=State.INTERACTING)
        elif kind == 'drag':
            self._react('surprised', 3, duration=3600, state=State.DRAGGED)
            self.setCursor(Qt.ClosedHandCursor)
        elif kind == 'drop':
            self._react('happy', 3)
            self.animation.stretch.velocity = -3
            self.setCursor(Qt.PointingHandCursor)

    def _typing_sample(self, count):
        if self.paused or self.brain.manual_sleep:
            return
        if count:
            self.brain.last_interaction = self.now
        # Immediate taps drive the layered expression; no delayed state overrides.
        self.typing.feed(count, self.now)

    def _cursor_behavior(self, dt):
        cursor = QCursor.pos()
        center = self.pos() + self.rect().center()
        dx, dy = cursor.x() - center.x(), cursor.y() - center.y()
        distance = math.hypot(dx, dy)
        speed = (cursor - self._cursor).manhattanLength() / max(dt, .001)
        old_distance = math.hypot(self._cursor.x() - center.x(), self._cursor.y() - center.y())
        self._cursor = cursor
        if not self.layers.engaged and self.interactions.origin is None and not self._menu.isVisible() and self.now > self._cursor_cooldown:
            if distance < 100 and old_distance - distance > 20 and speed > 1200:
                if self._react('scared', 2):
                    self.movement.set_target(QPointF(self.pos()) - QPointF(dx * .35, dy * .35), self.size())
                    self._cursor_cooldown = self.now + 10
            elif distance < 140 and not self._near:
                accepted = self._react('curious', 1)
                if accepted and distance > 80 and self.settings.get('wandering') and not self.settings.get('quiet'):
                    self.movement.set_target(QPointF(self.pos()) + QPointF(dx * .07, dy * .07), self.size())
                self._near_since = self.now
                self._cursor_cooldown = self.now + 5
            elif distance < 140 and self.now - self._near_since > 12:
                self._react('embarrassed', 1)
                self._near_since = self.now
                self._cursor_cooldown = self.now + 15
            elif distance > 170 and self._near and self.settings.get('wandering') and not self.settings.get('quiet'):
                if random.random() < .25 and self._react('curious', 1):
                    self.movement.set_target(QPointF(self.pos()) + QPointF(dx * .12, dy * .12), self.size())
        self._near = distance < 170
        return max(-5, min(5, dx / 35)), max(-4, min(4, dy / 40))

    def _personality(self, action):
        self.animation.play(action, self.now)
        if action in ('sneeze', 'vanish'):
            self.particles.emit('dust', 5)
        if action == 'sneeze':
            self.animation.stretch.velocity = -3
        if action in ('wander', 'catch') and self.settings.get('wandering') and not self.settings.get('quiet'):
            offset = QPointF(random.uniform(-120, 120), random.uniform(-65, 65))
            if action == 'catch':
                offset = (QPointF(QCursor.pos()) - QPointF(self.pos()) - QPointF(120, 150)) * .2
            self.movement.set_target(QPointF(self.pos()) + offset, self.size())
            self.brain.state = State.WANDERING

    def _animate(self):
        stamp = time.monotonic()
        dt = min(.05, stamp - self._last_tick)
        self._last_tick = stamp
        if self.paused:
            self._animation_timer.setInterval(100)
            return
        self.now += dt
        if self.now >= self._next_privacy_check and self.activity._hook:
            if not self.activity.guard.native.desktop_safe():
                self.layers.clear_typing()
            elif self.settings.get('key_highlights') and not self.activity.guard.allowed():
                self.layers.keyboard.clear_keys()
            self._next_privacy_check = self.now + .08
        gaze = self._cursor_behavior(dt)
        if self.interactions.origin is not None:
            self.brain.last_interaction = self.now
        if self.layers.dance.active and self.layers.dance.energy > .2 and not self.brain.manual_sleep:
            self.brain.last_interaction = self.now
            if self.brain.emotion in ('sleeping', 'sleepy'):
                self._react('curious', 2)
        action = self.brain.update(dt, self.now, allow_random=not self.layers.engaged) if self.interactions.origin is None else None
        if action and self.interactions.origin is None:
            self._personality(action)
        if self.brain.emotion in ('sleeping', 'sleepy'):
            self.dialogue.say(self.brain.emotion, self.now, self.settings.get('dialogue'), self.settings.get('quiet'))
        tilt = max(-18, min(18, self.movement.x.velocity * .035)) if self.interactions.dragging else 0
        stretch = min(.16, abs(self.movement.y.velocity) * .0005) if self.interactions.dragging else 0
        direct = self.interactions.origin is not None or (self.brain.priority >= 3 and self.now < self.brain.until)
        beat, drop = self.layers.update(dt, self.now, self.brain.emotion, direct,
            self.brain.manual_sleep or self.brain.emotion == 'sleeping', self.settings.get('quiet'))
        self._draw_emotion = self.layers.emotion
        if self.layers.engaged and not direct:
            self.animation.action = ''
            self.movement.stop(self.pos())
        if self.layers.typing:
            gaze = (0, 4)
        self.animation.update(dt, self.now, self._draw_emotion, gaze, tilt, stretch)
        if self.layers.typing:
            self.animation.eye += (1.15 - self.animation.eye) * (1 - math.exp(-dt * 10))
        if beat and self.layers.dance.beats % 5 == 0 and not self.layers.typing:
            self.animation.next_blink = self.now
        if drop:
            self.particles.emit('sparkle', 5)
        if self.now > self._next_music_particle and not direct:
            if self.layers.dance.active:
                self.particles.emit('note', 1)
            if self.layers.typing and self.layers.hands.rate > 7:
                self.particles.emit('star' if self.layers.hands.rate > 11 else 'sparkle', 1)
            self._next_music_particle = self.now + 3.5
        self.move(self.movement.update(dt, self.size(), self.interactions.dragging, self.settings.get('speed')))
        self.particles.update(dt)
        if self.now >= self._next_particle:
            kind = {'sleeping': 'zzz', 'excited': 'sparkle', 'sad': 'tear', 'confused': 'question', 'love': 'heart'}.get(self.brain.emotion)
            if kind:
                self.particles.emit(kind, 1)
            self._next_particle = self.now + random.uniform(1.1, 2.2)
        idle = not self.layers.engaged and self.brain.emotion in ('idle', 'sleeping', 'sleepy') and not self._near and not self.movement.moving
        self._animation_timer.setInterval(33 if idle else 16)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.save()
        painter.translate(self.WIDTH / 2, 154)
        intensity = self.settings.get('intensity') * (.6 if self.settings.get('quiet') else 1)
        draw_ghost(painter, self.animation, self._draw_emotion, self.now, intensity, self.layers)
        self.particles.draw(painter)
        painter.restore()
        self.layers.keyboard.draw(painter, self.WIDTH / 2, 196)
        self.layers.hands.draw(painter, self.WIDTH / 2, 220, self.layers.keyboard.alpha)
        if not self.settings.get('quiet'):
            self.dialogue.draw(painter, self.now, self.width())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = event.globalPosition().toPoint()
            self._drag_offset = QPointF(point - self.pos())
            self.brain.last_interaction = self.now
            self.movement.stop(self.pos())
            self.layers.clear_typing()
            self.interactions.press(point)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.interactions.double_click(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.interactions.origin is not None and event.buttons() & Qt.LeftButton:
            point = event.globalPosition().toPoint()
            self.interactions.move(point)
            if self.interactions.dragging:
                target = QPointF(point) - self._drag_offset
                self.movement.set_target(target, self.size())
                if self.paused:
                    self.move(self.movement.target.toPoint())
                    self.movement.stop(self.pos())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.interactions.release()
            self.setCursor(Qt.PointingHandCursor)
            event.accept()

    def contextMenuEvent(self, event):
        self._menu.popup(event.globalPos())
        event.accept()

    def cleanup(self):
        self._animation_timer.stop()
        self.interactions.cancel()
        self.activity.stop()
        self.audio.stop()
        self.layers.clear_typing()
        self.tray.hide()

    def closeEvent(self, event):
        self.cleanup()
        event.accept()
