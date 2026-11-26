
import sys

from PySide6.QtWidgets import QApplication

from app.ui.test_main_window import TestMainWindow


def main():

    app = QApplication(sys.argv)

    window = TestMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
