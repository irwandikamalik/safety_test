import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.utils.styles import APP_STYLE


def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "Industrial Safety Test Platform"
    )

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()