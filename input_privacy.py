"""Fail-closed editor checks. Reads accessibility metadata, never field content.

UI Automation lives in a disposable worker process: a stalled provider cannot
block the keyboard hook or prevent Ghosty from shutting down.
"""
import ctypes
from ctypes import wintypes as W
import multiprocessing as mp
import ntpath
import queue
import sys
import time
from PySide6.QtCore import QObject, QTimer, Signal


def approved_control(exe, control_type, class_name, password, focused):
    if password is not False or not focused:
        return False
    name = class_name.lower()
    if exe == 'notepad.exe':
        return control_type in (50004, 50030) and ('richedit' in name or name == 'edit')
    if exe == 'code.exe':
        # Monaco's editor textarea, not terminals, generic textboxes, or dialogs.
        return control_type == 50004 and 'inputarea' in name.split()
    return False


class GUIInfo(ctypes.Structure):
    _fields_ = [('cbSize', W.DWORD), ('flags', W.DWORD),
                *[(name, W.HWND) for name in ('active', 'focus', 'capture', 'menu', 'move', 'caret')],
                ('rect', W.RECT)]


class NativeContext:
    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.u.GetForegroundWindow.restype = W.HWND
        self.u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
        self.u.GetWindowThreadProcessId.restype = W.DWORD
        self.u.GetGUIThreadInfo.argtypes = [W.DWORD, ctypes.POINTER(GUIInfo)]
        self.u.OpenInputDesktop.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.u.OpenInputDesktop.restype = W.HANDLE
        self.u.CloseDesktop.argtypes = [W.HANDLE]
        self.u.GetUserObjectInformationW.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.POINTER(W.DWORD)]
        self.k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.k.OpenProcess.restype = W.HANDLE
        self.k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
        self.k.CloseHandle.argtypes = [W.HANDLE]

    def desktop_safe(self):
        handle = self.u.OpenInputDesktop(0, False, 1)
        if not handle:
            return False
        try:
            name, size = ctypes.create_unicode_buffer(128), W.DWORD()
            ok = self.u.GetUserObjectInformationW(handle, 2, name, ctypes.sizeof(name), ctypes.byref(size))
            return bool(ok and name.value.lower() == 'default')
        finally:
            self.u.CloseDesktop(handle)

    def identity(self):
        hwnd = self.u.GetForegroundWindow()
        pid = W.DWORD()
        thread = self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = GUIInfo()
        info.cbSize = ctypes.sizeof(info)
        if not hwnd or not self.u.GetGUIThreadInfo(thread, ctypes.byref(info)):
            return None
        return (int(hwnd), int(info.focus or 0), pid.value)

    def executable(self, pid):
        handle = self.k.OpenProcess(0x1000, False, pid)
        if not handle:
            return ''
        try:
            path, size = ctypes.create_unicode_buffer(32768), W.DWORD(32768)
            if self.k.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                return ntpath.basename(path.value).lower()
            return ''
        finally:
            self.k.CloseHandle(handle)


def _offer(channel, value):
    try:
        channel.put_nowait(value)
    except queue.Full:
        pass


def _focus_worker(channel, stop):
    try:
        sys.coinit_flags = 0
        import comtypes
        import comtypes.client
        module = comtypes.client.GetModule('UIAutomationCore.dll')
        automation = comtypes.client.CreateObject(module.CUIAutomation, interface=module.IUIAutomation)
        native = NativeContext()
        while not stop.is_set():
            before = time.monotonic()
            identity = native.identity()
            safe = False
            if identity and native.desktop_safe():
                exe = native.executable(identity[2])
                if exe in ('notepad.exe', 'code.exe'):
                    try:
                        element = automation.GetFocusedElement()
                        # No Name, Value, TextPattern, document, title, or clipboard reads.
                        safe = (element.CurrentProcessId == identity[2] and approved_control(
                            exe, element.CurrentControlType, element.CurrentClassName,
                            bool(element.CurrentIsPassword), bool(element.CurrentHasKeyboardFocus)))
                    except Exception:
                        safe = False
            if identity != native.identity():
                safe = False
            _offer(channel, (before, identity, safe))
            stop.wait(.06)
        del automation
        comtypes.CoUninitialize()
    except Exception:
        # Missing UIA/provider/dependency: generic motions only, never permissive.
        _offer(channel, (time.monotonic(), None, False))


class FocusGuard(QObject):
    invalidated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.native = NativeContext() if sys.platform == 'win32' else None
        self.process = None
        self.token = None
        self.invalid_since = 0.0
        self._hooks = []
        self._callback = None
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.poll)

    def invalidate(self):
        self.invalid_since = time.monotonic()
        self.token = None
        self.invalidated.emit()

    def start(self):
        if self.process or not self.native:
            return
        context = mp.get_context('spawn')
        self.channel, self.stop_event = context.Queue(1), context.Event()
        self.process = context.Process(target=_focus_worker, args=(self.channel, self.stop_event), daemon=True)
        self.process.start()
        u = self.native.u
        callback_type = ctypes.WINFUNCTYPE(None, W.HANDLE, W.DWORD, W.HWND, ctypes.c_long, ctypes.c_long, W.DWORD, W.DWORD)
        self._callback = callback_type(lambda *args: self.invalidate())
        u.SetWinEventHook.argtypes = [W.DWORD, W.DWORD, W.HMODULE, callback_type, W.DWORD, W.DWORD, W.DWORD]
        u.SetWinEventHook.restype = W.HANDLE
        u.UnhookWinEvent.argtypes = [W.HANDLE]
        # Foreground, focused accessible object, and input-desktop switches.
        for event in (3, 0x8005, 0x20):
            hook = u.SetWinEventHook(event, event, None, self._callback, 0, 0, 0)
            if hook:
                self._hooks.append(hook)
        self.timer.start()

    def poll(self):
        try:
            self.token = self.channel.get_nowait()
        except queue.Empty:
            pass
        if not self.allowed():
            self.invalidated.emit()

    def allowed(self):
        if not self.native or len(self._hooks) != 3 or not self.token:
            return False
        stamp, identity, safe = self.token
        return bool(safe and stamp > self.invalid_since and time.monotonic() - stamp < .2
                    and self.native.desktop_safe() and identity == self.native.identity())

    def stop(self):
        self.timer.stop()
        for hook in self._hooks:
            self.native.u.UnhookWinEvent(hook)
        self._hooks.clear()
        self._callback = None
        self.invalidate()
        if self.process:
            self.stop_event.set()
            self.process.join(.25)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(1)
            self.channel.close()
            self.process.close()
            self.process = None
