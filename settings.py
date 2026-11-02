"""Small persisted preferences. Never stores keyboard activity."""
from PySide6.QtCore import QSettings


class Settings:
    DEFAULTS = {'typing': False, 'key_highlights': False, 'music': False,
                'quiet': False, 'intensity': 1.0,
                'speed': 1.0, 'dialogue': 'normal', 'wandering': True}

    def __init__(self):
        self.store = QSettings('Ghosty', 'DesktopCompanion')
        self.values = {}
        for name, default in self.DEFAULTS.items():
            value = self.store.value(name, default, type=type(default))
            if name in ('intensity', 'speed') and value not in (.5, 1.0, 1.5):
                value = default
            if name == 'dialogue' and value not in ('off', 'rare', 'normal', 'chatty'):
                value = default
            self.values[name] = value

    def get(self, name):
        return self.values[name]

    def set(self, name, value):
        self.values[name] = value
        self.store.setValue(name, value)
        self.store.sync()
