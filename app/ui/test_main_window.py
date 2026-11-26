
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt

from app.ui.function_ui import notification_dialog, input_dialog


class TestMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("UI Function Tester")
        self.setMinimumSize(500, 350)

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("UI FUNCTION TESTER")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.notification_button = QPushButton(
            "Test Notification"
        )
        
        self.input_button = QPushButton(
            "Test Input"
        )

        self.result_label = QLabel("Result: -")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title_label)
        main_layout.addWidget(self.notification_button)
        main_layout.addWidget(self.input_button)
        main_layout.addWidget(self.result_label)

    def setup_connections(self):

        self.notification_button.clicked.connect(
            self.test_notification
        )

        self.input_button.clicked.connect(
            self.test_input
        )

    def test_notification(self):

        result = notification_dialog(
            parent=self,
            title="Test Confirmation",
            text="Are you sure you want to continue?"
        )

        if result:
            self.result_label.setText("Result: OK")
        else:
            self.result_label.setText("Result: Cancel")

    def test_input(self):
        
        input = input_dialog(
            parent=None,
            title="Input",
            text="Please enter data:"
        )

        if input == "":
            self.result_label.setText("Result: Text kosong")
            return
        if input:
            self.result_label.setText(f"Result: {input}")
        else:
            self.result_label.setText("Cancel button triggered")
