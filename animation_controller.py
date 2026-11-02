"""Resolve direct interaction > typing > music > personality > idle."""
from dance import Dance
from keyboard_overlay import KeyboardOverlay
from typing_animation import TypingAnimation


class AnimationController:
    def __init__(self):
        self.keyboard = KeyboardOverlay()
        self.hands = TypingAnimation()
        self.dance = Dance()
        self.emotion = 'idle'
        self.direct = False
        self.typing = False
        self.squash = 0.0

    def update(self, dt, now, base_emotion, direct=False, sleeping=False, quiet=False):
        self.direct = direct
        self.keyboard.update(dt, now, suppressed=direct or sleeping)
        self.hands.update(dt, now)
        self.typing = self.keyboard.alpha > .02 and not (direct or sleeping)
        beat, drop = self.dance.update(dt, now, self.typing, direct or sleeping, quiet)
        self.emotion = base_emotion
        if not (direct or sleeping):
            if self.typing:
                self.emotion = self.hands.emotion
            elif self.dance.blend > .15:
                self.emotion = 'surprised' if now < self.dance.drop_until else 'excited' if self.dance.mode == 'energetic' else 'happy'
        self.squash = self.hands.squash * self.keyboard.alpha if self.typing else 0
        return beat, drop

    @property
    def engaged(self):
        return self.typing or self.keyboard.alpha > .02 or self.dance.active or self.dance.blend > .02

    def clear_typing(self):
        self.keyboard.clear()
        self.hands = TypingAnimation()
        self.typing = False
