from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
)
from PySide6.QtCore import Qt


def notification_dialog(parent=None, title="Notification", text=""):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setFixedSize(350, 150)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

    # Main layout
    main_layout = QVBoxLayout(dialog)

    # Notification text
    message_label = QLabel(text)
    message_label.setWordWrap(True)
    message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    main_layout.addWidget(message_label)

    # Button layout
    button_layout = QHBoxLayout()

    ok_button = QPushButton("OK")
    cancel_button = QPushButton("Cancel")

    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)

    main_layout.addLayout(button_layout)

    # Button connections
    ok_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    # Show dialog
    return dialog.exec() == QDialog.DialogCode.Accepted

def input_dialog(parent=None, title="Input", text="Please enter data:"):

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setFixedSize(350, 180)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

    # Main layout
    main_layout = QVBoxLayout(dialog)

    # Instruction text
    message_label = QLabel(text)
    message_label.setWordWrap(True)

    main_layout.addWidget(message_label)

    # Input field
    input_field = QLineEdit()
    main_layout.addWidget(input_field)

    # Button layout
    button_layout = QHBoxLayout()

    ok_button = QPushButton("OK")
    cancel_button = QPushButton("Cancel")

    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)

    main_layout.addLayout(button_layout)

    # Button connections
    ok_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    # Show dialog
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return input_field.text()

    return None