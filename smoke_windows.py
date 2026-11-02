"""Optional native Windows smoke check; exits after two seconds.

Briefly installs/removes the aggregate activity hook to test native API wiring.
Never enables the saved typing preference or injects/decodes keyboard input.
"""
import ctypes
import sys
import tempfile
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from ghost import GhostPet


def main():
    if sys.platform != 'win32':
        raise SystemExit('This smoke check is Windows-only.')
    app = QApplication([])
    failures = []
    with tempfile.TemporaryDirectory() as directory:
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, directory)
        user32 = ctypes.WinDLL('user32')
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        foreground = user32.GetForegroundWindow()
        pet = GhostPet()
        pet.show()

        def check():
            try:
                assert user32.GetForegroundWindow() == foreground, 'Pet stole foreground focus'
                assert pet.testAttribute(Qt.WA_TranslucentBackground)
                assert pet.windowFlags() & Qt.WindowStaysOnTopHint
                assert pet.activity._hook is None
                pet.activity.start()
                assert pet.activity._hook
                pet.activity.stop()
                assert pet.activity._hook is None
                assert not pet.settings.get('typing')
                if QSystemTrayIcon.isSystemTrayAvailable():
                    pet._set_click_through(True)
                    assert pet.windowFlags() & Qt.WindowTransparentForInput
                    pet._set_click_through(False)
                    assert not pet.windowFlags() & Qt.WindowTransparentForInput
                print('PASS: native window, no focus theft, hook start/stop, tray click-through recovery')
            except Exception as error:
                failures.append(error)
            finally:
                app.quit()

        QTimer.singleShot(2000, check)
        app.exec()
        pet.cleanup()
        if failures:
            raise failures[0]


if __name__ == '__main__':
    main()
