"""Ghosty desktop companion. Run in your PySide6 environment: python main.py."""
import sys
import multiprocessing
from PySide6.QtWidgets import QApplication
from ghost import GhostPet


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Ghosty')
    app.setOrganizationName('Ghosty')
    ghost = GhostPet()
    ghost.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
