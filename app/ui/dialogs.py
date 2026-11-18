from PySide6.QtCore import (
    Qt,
    QEvent,
    Signal
)

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QDialogButtonBox,
    QProgressBar,
    QFrame
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

        function = result.get("function")

        test_titles = {
            "ac_withstanding": "AC Hipot Test",
            "ground_bond": "Ground Bond Test"
        }

        test_title = test_titles.get(
            function,
            "Test Result"
        )

        self.setWindowTitle(f"{test_title} Result")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        title = QLabel(test_title)
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ======================================
        # JUDGMENT STATUS
        # ======================================

        judgment = result.get("judgment", "UNKNOWN")

        status = QLabel(judgment)

        if judgment == "PASS":
            background = "#D8F3E7"
            foreground = "#14734F"
        elif judgment == "FAIL":
            background = "#FCE4E4"
            foreground = "#B93838"
        else:
            background = "#FFF3CD"
            foreground = "#856404"

        status.setStyleSheet(
            f"""
            background: {background};
            color: {foreground};
            padding: 10px;
            font-weight: bold;
            """
        )

        layout.addWidget(status)

        # ======================================
        # TEST MEASUREMENT RESULTS
        # ======================================

        form = QFormLayout()

        if function == "ac_withstanding":

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

        elif function == "ground_bond":

            form.addRow(
                "Test Current:",
                QLabel(
                    f'{result.get("test_current_A", 0)} A'
                )
            )

            form.addRow(
                "Measured Resistance:",
                QLabel(
                    f'{result.get("measured_resistance_mOhm", 0)} mΩ'
                )
            )

            form.addRow(
                "Test Duration:",
                QLabel(
                    f'{result.get("test_duration_s", 0)} s'
                )
            )

            form.addRow(
                "Resistance Limit:",
                QLabel(
                    f'{result.get("resistance_limit_mOhm", 0)} mΩ'
                )
            )

        layout.addLayout(form)

        # ======================================
        # DATA SOURCE
        # ======================================

        if result.get("simulation") is True:
            note_text = (
                "SIMULATION DATA - No hardware connected."
            )
        else:
            note_text = "HARDWARE TEST DATA."

        note = QLabel(note_text)
        note.setStyleSheet("color: #738197;")
        layout.addWidget(note)

        # ======================================
        # CONTINUE BUTTON
        # ======================================

        button = QPushButton("Continue")
        button.setObjectName("PrimaryButton")
        button.clicked.connect(self.accept)

        layout.addWidget(button)

class LiveMeasurementDialog(QDialog):

    cancel_requested = Signal()

    def __init__(
        self,
        instrument,
        duration_s,
        sample_interval_s,
        parent=None
    ):

        super().__init__(parent)

        self.instrument = instrument
        self.duration_s = float(duration_s)
        self.sample_interval_s = float(sample_interval_s)

        self.is_running = True
        self.value_labels = {}

        self.setWindowTitle("Live Measurement")
        self.setMinimumSize(680, 500)
        self.resize(720, 560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # ======================================
        # HEADER
        # ======================================

        title = QLabel("WT310E Live Measurement")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.instrument_label = QLabel(
            f"Instrument: {instrument}"
        )
        self.instrument_label.setStyleSheet(
            "font-size: 10pt; color: #94A3B8;"
        )
        layout.addWidget(self.instrument_label)

        # ======================================
        # STATUS
        # ======================================

        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        self.source_indicator = QLabel("●")
        self.source_indicator.setStyleSheet("""
            font-size: 15pt;
            color: #94A3B8;
        """)

        self.source_status_label = QLabel(
            "SOURCE: CONNECTING..."
        )

        self.source_status_label.setStyleSheet("""
            font-size: 9pt;
            font-weight: bold;
            color: #D69E36;
        """)

        self.status_label = QLabel("CONNECTING...")
        self.status_label.setStyleSheet("""
            font-size: 9pt;
            font-weight: bold;
            color: #D69E36;
        """)

        status_layout.addWidget(self.source_indicator)
        status_layout.addWidget(self.source_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.status_label)

        layout.addLayout(status_layout)

        # ======================================
        # MEASUREMENT INFORMATION
        # ======================================

        info_layout = QHBoxLayout()

        self.time_label = QLabel(
            f"Elapsed: 0.0 / {self.duration_s:.1f} s"
        )

        self.sample_label = QLabel("Samples: 0")

        info_layout.addWidget(self.time_label)
        info_layout.addStretch()
        info_layout.addWidget(self.sample_label)

        layout.addLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(18)

        layout.addWidget(self.progress_bar)

        # ======================================
        # MEASUREMENT PANEL
        # ======================================

        section_title = QLabel("MEASUREMENT RESULTS")
        section_title.setStyleSheet("""
            font-size: 9pt;
            font-weight: bold;
            letter-spacing: 1px;
            color: #94A3B8;
            padding-top: 5px;
        """)

        layout.addWidget(section_title)

        self.measurement_container = QFrame()
        self.measurement_container.setObjectName(
            "MeasurementPanel"
        )

        self.measurement_container.setStyleSheet("""
            QFrame#MeasurementPanel {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)

        self.measurement_layout = QVBoxLayout(
            self.measurement_container
        )

        self.measurement_layout.setContentsMargins(
            14, 12, 14, 12
        )

        self.measurement_layout.setSpacing(8)

        layout.addWidget(self.measurement_container, 1)

        # ======================================
        # BUTTON
        # ======================================

        self.cancel_button = QPushButton(
            "Cancel Measurement (ESC)"
        )

        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.setMinimumHeight(42)

        self.cancel_button.clicked.connect(
            self.cancel_measurement
        )

        layout.addWidget(self.cancel_button)

    # ==========================================
    # CREATE MEASUREMENT ROW
    # ==========================================

    def create_measurement_row(self, measurement_id):

        row = QFrame()
        row.setObjectName("MeasurementRow")

        row.setStyleSheet("""
            QFrame#MeasurementRow {
                background-color: #263449;
                border: 1px solid #3B4B60;
                border-radius: 7px;
            }
        """)

        row_layout = QHBoxLayout(row)

        row_layout.setContentsMargins(
            16, 10, 16, 10
        )

        row_layout.setSpacing(12)

        display_name = (
            measurement_id
            .replace("_", " ")
            .title()
        )

        name_label = QLabel(display_name)

        name_label.setMinimumWidth(180)
        name_label.setStyleSheet("""
            font-size: 10pt;
            font-weight: 500;
            color: #CBD5E1;
            border: none;
            background: transparent;
        """)

        value_label = QLabel("--")

        value_label.setMinimumWidth(180)
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight |
            Qt.AlignmentFlag.AlignVCenter
        )

        value_label.setStyleSheet("""
            font-size: 12pt;
            font-weight: bold;
            color: #F8FAFC;
            border: none;
            background: transparent;
        """)

        row_layout.addWidget(name_label)
        row_layout.addStretch()
        row_layout.addWidget(value_label)

        self.measurement_layout.addWidget(row)

        self.value_labels[measurement_id] = value_label

    def update_source_status(self, simulation):

        if simulation:

            self.source_indicator.setStyleSheet("""
                font-size: 15pt;
                color: #94A3B8;
            """)

            self.source_status_label.setText(
                "NOT LIVE (SIMULATION)"
            )

            self.source_status_label.setStyleSheet("""
                font-size: 10pt;
                font-weight: bold;
                color: #94A3B8;
                padding: 5px 0px;
            """)

        else:

            self.source_indicator.setStyleSheet("""
                font-size: 15pt;
                color: #EF4444;
            """)

            self.source_status_label.setText("LIVE")

            self.source_status_label.setStyleSheet("""
                font-size: 10pt;
                font-weight: bold;
                color: #EF4444;
                padding: 5px 0px;
            """)
            
    # ==========================================
    # UPDATE LIVE MEASUREMENT
    # ==========================================

    def update_measurement(
        self,
        measurements,
        sample_number,
        elapsed_s,
        simulation
    ):

        if not self.is_running:
            return

        self.update_source_status(simulation)

        self.sample_label.setText(
            f"Samples: {sample_number}"
        )

        self.time_label.setText(
            f"Elapsed: {elapsed_s:.1f} / "
            f"{self.duration_s:.1f} s"
        )

        progress = min(
            100,
            int(elapsed_s / self.duration_s * 100)
        )

        self.progress_bar.setValue(progress)

        for measurement_id, measurement in measurements.items():

            value = measurement.get("value")
            unit = measurement.get("unit", "")

            if measurement_id not in self.value_labels:
                self.create_measurement_row(
                    measurement_id
                )

            if isinstance(value, (int, float)):
                display_value = f"{value:,.3f}"
            else:
                display_value = str(value)

            self.value_labels[measurement_id].setText(
                f"{display_value} {unit}"
            )

    # ==========================================
    # MEASUREMENT COMPLETED
    # ==========================================

    def finish_measurement(self, result):

        # Update final values BEFORE setting is_running False.
        self.update_measurement(
            result.get("measurements", {}),
            result.get("sample_count", 0),
            result.get("duration_s", 0),
            result.get("simulation", False)
        )

        self.is_running = False

        self.progress_bar.setValue(100)

        self.status_label.setText(
            "MEASUREMENT COMPLETED"
        )

        self.status_label.setStyleSheet("""
            font-size: 10pt;
            font-weight: bold;
            color: #77D6A5;
            padding: 5px 0px;
        """)

        self.time_label.setText(
            f"Elapsed: {result.get('duration_s', 0):.2f} s"
        )

        self.sample_label.setText(
            f"Total Samples: {result.get('sample_count', 0)}"
        )

        self.cancel_button.setText("Close (ESC)")

        self.cancel_button.clicked.disconnect(
            self.cancel_measurement
        )

        self.cancel_button.setObjectName("PrimaryButton")
        self.cancel_button.clicked.connect(self.accept)

        self.cancel_button.style().unpolish(
            self.cancel_button
        )
        self.cancel_button.style().polish(
            self.cancel_button
        )

    # ==========================================
    # MEASUREMENT FAILED
    # ==========================================

    def show_error(self, message):

        self.is_running = False

        self.status_label.setText(
            "MEASUREMENT FAILED"
        )

        self.status_label.setStyleSheet("""
            font-size: 10pt;
            font-weight: bold;
            color: #FF8585;
            padding: 5px 0px;
        """)

        self.time_label.setText(message)
        self.time_label.setWordWrap(True)

        self.cancel_button.setText("Close (ESC)")

        self.cancel_button.clicked.disconnect(
            self.cancel_measurement
        )

        self.cancel_button.setObjectName("PrimaryButton")
        self.cancel_button.clicked.connect(self.accept)

        self.cancel_button.style().unpolish(
            self.cancel_button
        )
        self.cancel_button.style().polish(
            self.cancel_button
        )

    # ==========================================
    # CANCEL
    # ==========================================

    def cancel_measurement(self):

        if self.is_running:
            self.cancel_requested.emit()

        self.reject()

    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_Escape:
            self.cancel_measurement()
            return

        super().keyPressEvent(event)
