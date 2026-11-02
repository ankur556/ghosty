"""Opt-in aggregate activity; separately opted-in, guarded transient key states.

Never translates keys to text or stores an event history. In aggregate mode the
key-data pointer is untouched. Secure desktops suppress all activity.
"""
import ctypes
import sys
from PySide6.QtCore import QObject, QTimer, Signal
from input_privacy import FocusGuard
from keyboard_overlay import VK_KEYS


class KeyboardActivity(QObject):
    sample = Signal(int)
    pulse = Signal()
    key_changed = Signal(str, bool)
    cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self._hook = None
        self._callback = None
        self._user32 = None
        self.visualize = False
        self.guard = FocusGuard(self)
        self.guard.invalidated.connect(self.cleared)
        self._down = set()
        self.cleared.connect(self._down.clear)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._sample)

    def start(self):
        if self._hook:
            return
        if sys.platform != 'win32':
            raise OSError('Global typing activity is available on Windows only.')
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                         wintypes.WPARAM, wintypes.LPARAM)
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = wintypes.HANDLE
        user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        def on_event(code, message, opaque_data):
            try:
                if code >= 0 and self.guard.native.desktop_safe():
                    down = message in (0x0100, 0x0104)
                    up = message in (0x0101, 0x0105)
                    if down:
                        self._count = min(1000, self._count + 1)
                        self.pulse.emit()
                    if (down or up) and self.visualize and self.guard.allowed():
                        # Only vkCode is read; never decode a character or inspect text.
                        vk = ctypes.cast(opaque_data, ctypes.POINTER(wintypes.DWORD))[0]
                        key = VK_KEYS.get(vk)
                        if key:
                            self._down.add(key) if down else self._down.discard(key)
                            self.key_changed.emit(key, down)
                    elif self._down:
                        self.cleared.emit()
                elif self._down:
                    self.cleared.emit()
            except Exception:
                self.cleared.emit()
            return user32.CallNextHookEx(None, code, message, opaque_data)

        self._callback = callback_type(on_event)
        self._user32 = user32
        self._hook = user32.SetWindowsHookExW(13, self._callback, kernel32.GetModuleHandleW(None), 0)
        if not self._hook:
            self._callback = None
            raise ctypes.WinError(ctypes.get_last_error())
        # Qt's Windows event loop dispatches the hook; no blocking worker loop.
        self._count = 0
        self.timer.start()
        if self.visualize:
            self.guard.start()

    def set_visualization(self, enabled):
        self.visualize = enabled
        self.cleared.emit()
        if enabled and self._hook:
            self.guard.start()
        else:
            self.guard.stop()

    def _sample(self):
        count, self._count = self._count, 0
        self.sample.emit(count)

    def stop(self):
        self.timer.stop()
        self.guard.stop()
        if self._hook:
            self._user32.UnhookWindowsHookEx(self._hook)
        self._hook = self._callback = None
        self._count = 0
        self.cleared.emit()


class TypingReactions:
    """One-second aggregate samples, hysteresis, and a reaction cooldown."""
    def __init__(self):
        self.active_seconds = self.quiet_seconds = 0
        self.last_reaction = -10.0
        self.was_typing = False

    def feed(self, count, now):
        reaction = None
        if count:
            self.active_seconds += 1
            self.quiet_seconds = 0
            if not self.was_typing:
                reaction = 'curious'
            elif count >= 9:
                reaction = 'surprised'
            elif self.active_seconds >= 4:
                reaction = 'excited'
            self.was_typing = True
        else:
            self.quiet_seconds += 1
            if self.was_typing and self.quiet_seconds >= 3:
                reaction = 'confused'
        if reaction and now - self.last_reaction >= 5:
            self.last_reaction = now
            if reaction == 'confused':
                self.was_typing = False
                self.active_seconds = 0
            return reaction
        return None
