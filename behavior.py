"""Emotion lifetimes, interaction priorities, and a small autonomous brain."""
from dataclasses import dataclass
from enum import Enum, auto
import random


class State(Enum):
    IDLE = auto()
    WANDERING = auto()
    CURIOUS = auto()
    HAPPY = auto()
    SAD = auto()
    ANGRY = auto()
    EXCITED = auto()
    SCARED = auto()
    SLEEPY = auto()
    SLEEPING = auto()
    PLAYFUL = auto()
    INTERACTING = auto()
    DRAGGED = auto()


@dataclass(frozen=True)
class Emotion:
    duration: float
    eye: float = 1.0
    smile: float = 0.25
    blush: float = 0.45
    tilt: float = 0.0
    stretch: float = 1.0


EMOTIONS = {
    'idle': Emotion(5),
    'happy': Emotion(4, .16, 1, .85),
    'sad': Emotion(6, .55, -.7, .25, -5),
    'angry': Emotion(3, .35, -.4, .7),
    'excited': Emotion(4, 1.3, 1, .9, 0, 1.05),
    'sleepy': Emotion(12, .3, 0, .3, -6),
    'sleeping': Emotion(60, .02, 0, .2, -8),
    'surprised': Emotion(2.5, 1.5, 0, .5, 0, 1.12),
    'scared': Emotion(3, 1.4, 0, .2, 5, 1.08),
    'curious': Emotion(5, 1.05, .35, .5, 12),
    'confused': Emotion(3.5, .8, -.15, .4, -12),
    'embarrassed': Emotion(4, .7, .5, 1, -8, .93),
    'love': Emotion(5, .15, 1, 1, 7),
}


class Behavior:
    def __init__(self):
        self.state = State.IDLE
        self.emotion = 'idle'
        self.until = self.lock_until = 0.0
        self.priority = 0
        self.last_interaction = 0.0
        self.happiness, self.energy = 70.0, 85.0
        self.affection, self.curiosity = 40.0, 60.0
        self.next_random = random.uniform(15, 28)
        self.last_random = None
        self.manual_sleep = False

    def react(self, emotion, now, priority=1, duration=None, state=None):
        if self.manual_sleep and priority < 3:
            return False
        if priority < self.priority and now < self.until:
            return False
        if priority < 3 and now < self.lock_until:
            return False
        if priority >= 3:
            self.manual_sleep = False
            self.last_interaction = now
        self.emotion = emotion
        self.priority = priority
        self.until = now + (duration or EMOTIONS[emotion].duration)
        self.lock_until = now + (2.5 if priority < 3 else .2)
        self.state = state or State.__members__.get(emotion.upper(), State.PLAYFUL)
        if emotion in ('happy', 'love', 'excited'):
            self.happiness = min(100, self.happiness + 4)
            self.affection = min(100, self.affection + 2)
        return True

    def update(self, dt, now, allow_random=True):
        asleep = self.emotion == 'sleeping'
        self.energy = max(0, min(100, self.energy + dt * (.3 if asleep else -.015)))
        self.happiness = max(0, self.happiness - dt * .005)
        self.curiosity = max(20, min(100, self.curiosity + dt * .02))
        if self.manual_sleep:
            return None
        if now >= self.until:
            self.emotion, self.state, self.priority = 'idle', State.IDLE, 0
        idle_for = now - self.last_interaction
        if self.priority < 3 and now >= self.lock_until:
            if idle_for > 300 or self.energy < 15:
                self.react('sleeping', now, duration=60)
            elif idle_for > 150 or self.energy < 30:
                self.react('sleepy', now)
        if not allow_random or now < self.next_random or self.emotion != 'idle':
            return None
        self.next_random = now + random.uniform(18, 40)
        choices = ['look', 'double_blink', 'spin', 'sneeze', 'yawn', 'hiccup',
                   'vanish', 'circle', 'tail', 'wave', 'wander', 'excited']
        if self.happiness < 45:
            choices += ['sad']
        if self.affection > 55:
            choices += ['love']
        if self.curiosity > 55:
            choices += ['catch']
        choice = random.choice([x for x in choices if x != self.last_random])
        self.last_random = choice
        self.react({'yawn': 'sleepy', 'sneeze': 'surprised', 'love': 'love',
                    'sad': 'sad', 'catch': 'curious', 'excited': 'excited'}.get(choice, 'curious'),
                   now, duration=3, state=State.PLAYFUL)
        return choice
