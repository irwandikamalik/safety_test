from PySide6.QtCore import Qt, QEvent

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QDialogButtonBox
)


class OperatorDialog(QDialog):

    OPERATORS = {
        "049928": "Irwandika",
        "049929": "Dika",
        "049930": "Wan"
    }

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Operator Login")
        self.setMinimumWidth(400)
        self.setModal(True)

        self.operator = None

        layout = QVBoxLayout(self)

        title = QLabel("Operator Identification")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        layout.addWidget(
            QLabel("Masukkan ID Operator.")
        )

        self.operator_input = QLineEdit()
        self.operator_input.setPlaceholderText(
            "Masukkan ID Operator"
        )

        layout.addWidget(self.operator_input)

        self.error_label = QLabel()
        self.error_label.setStyleSheet(
            "color: #C0392B;"
        )

        layout.addWidget(self.error_label)

        login_button = QPushButton("Login")
        login_button.setObjectName("PrimaryButton")
        login_button.clicked.connect(
            self.validate_operator
        )

        layout.addWidget(login_button)

        self.operator_input.returnPressed.connect(
            self.validate_operator
        )

    def validate_operator(self):

        operator_id = self.operator_input.text().strip()

        if operator_id in self.OPERATORS:

            self.operator = {
                "id": operator_id,
                "name": self.OPERATORS[operator_id]
            }

            self.accept()

        else:

            self.error_label.setText(
                "ID Operator tidak ditemukan."
            )


class InputDialog(QDialog):

    def __init__(self, title, fields, parent=None):

        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(430)
        self.setModal(True)

        self.inputs = {}

        layout = QVBoxLayout(self)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        layout.addWidget(
            QLabel(
                "Lengkapi data berikut untuk melanjutkan proses."
            )
        )

        form = QFormLayout()

        for key, label, placeholder in fields:

            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)

            self.inputs[key] = edit

            form.addRow(label, edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok |
            QDialogButtonBox.Cancel
        )

        buttons.button(
            QDialogButtonBox.Ok
        ).setText("Submit")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def get_values(self):

        return {
            key: widget.text().strip()
            for key, widget in self.inputs.items()
        }



class ApprovalDialog(QDialog):

    def __init__(
        self,
        parent=None,
        title="Safety Preparation Approval",
        message=None
    ):

        super().__init__(parent)

        self.setWindowTitle("Operator Approval")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        if message is None:
            message = (
                "Pastikan produk sudah terpasang dengan benar, "
                "area pengujian aman, dan seluruh koneksi telah diperiksa."
            )

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # BUTTONS
        buttons = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel (ESC)")
        self.approve_button = QPushButton("Approve (Y)")

        self.approve_button.setObjectName("SuccessButton")

        # Disable automatic default button behavior.
        for button in (
            self.cancel_button,
            self.approve_button
        ):
            button.setAutoDefault(False)
            button.setDefault(False)
            button.installEventFilter(self)

        self.cancel_button.clicked.connect(self.reject)
        self.approve_button.clicked.connect(self.accept)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.approve_button)

        layout.addLayout(buttons)

        # Allow keyboard handling even when dialog has focus.
        self.installEventFilter(self)

    def eventFilter(self, watched, event):

        if event.type() == QEvent.Type.KeyPress:

            key = event.key()

            if key == Qt.Key.Key_Y:
                self.accept()
                return True

            if key == Qt.Key.Key_Escape:
                self.reject()
                return True

            if key in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter
            ):
                # Enter must not activate either button.
                return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):

        key = event.key()

        if key == Qt.Key.Key_Y:
            self.accept()
            return

        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        if key in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter
        ):
            event.ignore()
            return

        event.ignore()


class MeasurementDialog(QDialog):

    def __init__(self, result=None, parent=None):

        super().__init__(parent)

        result = result or {}

        self.setWindowTitle("Measurement Result")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        title = QLabel("AC Withstanding Test")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        judgment = result.get("judgment", "UNKNOWN")

        status = QLabel(judgment)

        if judgment == "PASS":
            background = "#D8F3E7"
            foreground = "#14734F"
        else:
            background = "#FCE4E4"
            foreground = "#B93838"

        status.setStyleSheet(
            f"""
            background: {background};
            color: {foreground};
            padding: 10px;
            font-weight: bold;
            """
        )

        layout.addWidget(status)

        form = QFormLayout()

        form.addRow(
            "Test Voltage:",
            QLabel(
                f'{result.get("test_voltage_V", 0)} V'
            )
        )

        form.addRow(
            "Measured Current:",
            QLabel(
                f'{result.get("measured_current_mA", 0)} mA'
            )
        )

        form.addRow(
            "Test Duration:",
            QLabel(
                f'{result.get("test_duration_s", 0)} s'
            )
        )

        form.addRow(
            "Current Limit:",
            QLabel(
                f'{result.get("current_limit_mA", 0)} mA'
            )
        )

        layout.addLayout(form)

        note = QLabel(
            "SIMULATION DATA - No hardware connected."
        )

        note.setStyleSheet("color: #738197;")
        layout.addWidget(note)

        button = QPushButton("Continue")
        button.setObjectName("PrimaryButton")
        button.clicked.connect(self.accept)

        layout.addWidget(button)
