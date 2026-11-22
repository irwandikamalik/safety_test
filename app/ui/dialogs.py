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

from app.services.config_service import ConfigService


class OperatorDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        cf = ConfigService()
        self.operator_config = cf.load_json("global/operator.json")

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

        for operator in self.operator_config["operators"]:

            if operator_id == operator["id"]:
                self.operator = {
                    "name": operator["name"],
                    "id": operator["id"],
                    "rule": operator["rule"]
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

        print("\n========== MEASUREMENT DIALOG DEBUG ==========")
        print("RESULT:", result)
        print("FUNCTION:", result.get("function"))
        print("JUDGMENT:", result.get("judgment"))
        print("MEASURED CURRENT:", result.get("measured_current_mA"))
        print("==============================================\n")

        function = result.get("function")

        test_titles = {
            "acw": "AC Hipot Test",
            "ecac": "Ground Bond Test (AC)",
            "ecdc": "Ground Bond Test (DC)"
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
        # MEASUREMENT RESULTS
        # ======================================

        form = QFormLayout()

        def add_row(label, value, unit=""):

            if value is None:
                return

            if isinstance(value, float):
                value_text = f"{value:g}"
            else:
                value_text = str(value)

            form.addRow(
                label,
                QLabel(f"{value_text} {unit}".strip())
            )

        # ======================================
        # AC HIPOT TEST
        # ======================================

        if function == "acw":

            measured_current_A = result.get("current_A")

            if measured_current_A is not None:

                measured_current_mA = measured_current_A * 1000

                add_row(
                    "Measured Current:",
                    measured_current_mA,
                    "mA"
                )

        # ======================================
        # GROUND BOND TEST (AC / DC)
        # ======================================

        elif function in (
            "ecac",
            "ecdc"
        ):

            add_row(
                "Test Current:",
                result.get("test_current_A"),
                "A"
            )

            add_row(
                "Frequency:",
                result.get("frequency_Hz"),
                "Hz"
            )

            add_row(
                "Measured Resistance:",
                result.get("measured_resistance_mOhm"),
                "mΩ"
            )

            add_row(
                "Lower Resistance Limit:",
                result.get("lower_resistance_mOhm"),
                "mΩ"
            )

            add_row(
                "Upper Resistance Limit:",
                result.get(
                    "upper_resistance_mOhm",
                    result.get("resistance_limit_mOhm")
                ),
                "mΩ"
            )

            add_row(
                "Test Time:",
                result.get(
                    "test_time_s",
                    result.get("test_duration_s")
                ),
                "s"
            )

            add_row(
                "Rise Time:",
                result.get("rise_time_s"),
                "s"
            )

            add_row(
                "Fall Time:",
                result.get("fall_time_s"),
                "s"
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

        self.measurement_display = {
            "voltage": ("Voltage", "V"),
            "current": ("Current", "A"),
            "active_power": ("Active Power", "W"),
            "voltage_frequency": ("Voltage Frequency", "Hz")
        }

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

        display_name, _ = self.measurement_display[
            measurement_id
        ]

        row = QFrame()
        row.setObjectName("ACMeasurementRow")

        row.setStyleSheet("""
            QFrame#ACMeasurementRow {
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

        name = QLabel(display_name)
        name.setMinimumWidth(180)

        name.setStyleSheet("""
            font-size: 10pt;
            font-weight: 500;
            color: #CBD5E1;
            border: none;
            background: transparent;
        """)

        value = QLabel("--")

        value.setMinimumWidth(180)

        value.setAlignment(
            Qt.AlignmentFlag.AlignRight |
            Qt.AlignmentFlag.AlignVCenter
        )

        value.setStyleSheet("""
            font-size: 12pt;
            font-weight: bold;
            color: #F8FAFC;
            border: none;
            background: transparent;
        """)

        row_layout.addWidget(name)
        row_layout.addStretch()
        row_layout.addWidget(value)

        self.measurement_layout.addWidget(row)

        self.value_labels[measurement_id] = value

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
        result,
        sample_number,
        elapsed_s,
        simulation
    ):

        measurements = result.get(
            "measurements",
            {}
        )

        self.source_label.setText(
            "SOURCE: SIMULATION"
            if simulation
            else "SOURCE: LIVE HARDWARE"
        )

        self.sample_label.setText(
            f"Samples: {sample_number}"
        )

        self.time_label.setText(
            f"Elapsed: {elapsed_s:.1f} s"
        )

        progress = min(
            100,
            int(
                elapsed_s /
                self.evaluation_duration_s * 100
            )
        )

        self.progress_bar.setValue(progress)

        for measurement_id, measurement in measurements.items():

            # Skip measurement yang tidak ingin ditampilkan.
            if measurement_id not in self.measurement_display:
                continue

            if measurement_id not in self.value_labels:
                self.create_measurement_row(
                    measurement_id
                )

            value = measurement.get("value")

            if isinstance(value, (int, float)):
                display_value = f"{value:,.3f}"
            else:
                display_value = str(value)

            self.value_labels[measurement_id].setText(
                display_value
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


class ACVoltConfirmationDialog(QDialog):

    enable_output_requested = Signal()
    pass_confirmation_requested = Signal()
    cancel_requested = Signal()

    def __init__(
        self,
        evaluation_duration_s=10,
        sample_interval_s=1,
        parent=None
    ):

        super().__init__(parent)

        self.evaluation_duration_s = float(
            evaluation_duration_s
        )

        self.sample_interval_s = float(
            sample_interval_s
        )

        self.is_running = True
        self.is_passed = False
        self.value_labels = {}

        self.cancel_requested_once = False

        self.setWindowTitle("AC Volt Confirmation")
        self.setMinimumSize(680, 540)
        self.resize(720, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # ======================================
        # HEADER
        # ======================================

        title = QLabel("AC Volt Confirmation")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        description = QLabel(
            "PCR500M AC Power Supply + WT310E Power Measurement"
        )

        description.setWordWrap(True)
        layout.addWidget(description)

        # ======================================
        # STATUS
        # ======================================

        self.status_label = QLabel(
            "WAITING FOR INSTRUMENT CONNECTION..."
        )

        self.status_label.setStyleSheet("""
            font-size: 10pt;
            font-weight: bold;
            color: #D69E36;
            padding: 8px;
        """)

        layout.addWidget(self.status_label)

        self.source_label = QLabel("SOURCE: WAITING")

        self.source_label.setStyleSheet(
            "color: #94A3B8; font-weight: bold;"
        )

        layout.addWidget(self.source_label)

        # ======================================
        # EVALUATION INFORMATION
        # ======================================

        info_layout = QHBoxLayout()

        self.time_label = QLabel(
            f"Evaluation: 0.0 / "
            f"{self.evaluation_duration_s:.1f} s"
        )

        self.sample_label = QLabel("Samples: 0")

        info_layout.addWidget(self.time_label)
        info_layout.addStretch()
        info_layout.addWidget(self.sample_label)

        layout.addLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)

        layout.addWidget(self.progress_bar)

        # ======================================
        # MEASUREMENT PANEL
        # ======================================

        section_title = QLabel("LIVE MEASUREMENTS")

        section_title.setStyleSheet("""
            font-size: 9pt;
            font-weight: bold;
            letter-spacing: 1px;
            color: #94A3B8;
        """)

        layout.addWidget(section_title)

        self.measurement_container = QFrame()
        self.measurement_container.setObjectName(
            "ACMeasurementPanel"
        )

        self.measurement_container.setStyleSheet("""
            QFrame#ACMeasurementPanel {
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

        layout.addWidget(
            self.measurement_container,
            1
        )

        # ======================================
        # BUTTONS
        # ======================================

        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton(
            "Cancel (ESC)"
        )

        self.cancel_button.setObjectName(
            "DangerButton"
        )

        self.enable_button = QPushButton(
            "Enable AC Output"
        )

        self.enable_button.setObjectName(
            "SuccessButton"
        )

        self.enable_button.setEnabled(False)

        self.ok_button = QPushButton("OK")

        self.ok_button.setObjectName(
            "PrimaryButton"
        )

        self.ok_button.setEnabled(False)

        self.cancel_button.clicked.connect(
            self.cancel_confirmation
        )

        self.enable_button.clicked.connect(
            self.request_output_enable
        )

        self.ok_button.clicked.connect(
            self.request_pass_confirmation
        )

        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.enable_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    # ==========================================
    # MEASUREMENT ROW
    # ==========================================

    def create_measurement_row(self, measurement_id):

        row = QFrame()
        row.setObjectName("ACMeasurementRow")

        row.setStyleSheet("""
            QFrame#ACMeasurementRow {
                background-color: #263449;
                border: 1px solid #3B4B60;
                border-radius: 7px;
            }
        """)

        row_layout = QHBoxLayout(row)

        row_layout.setContentsMargins(
            16, 10, 16, 10
        )

        name = QLabel(
            measurement_id.replace("_", " ").title()
        )

        name.setMinimumWidth(180)

        value = QLabel("--")

        value.setMinimumWidth(180)

        value.setAlignment(
            Qt.AlignmentFlag.AlignRight |
            Qt.AlignmentFlag.AlignVCenter
        )

        value.setStyleSheet("""
            font-size: 12pt;
            font-weight: bold;
            color: #F8FAFC;
        """)

        row_layout.addWidget(name)
        row_layout.addStretch()
        row_layout.addWidget(value)

        self.measurement_layout.addWidget(row)

        self.value_labels[measurement_id] = value

    # ==========================================
    # STATUS UPDATE
    # ==========================================

    def update_status(self, message):

        self.status_label.setText(message)

    def configuration_ready(self, configuration):

        self.status_label.setText(
            "PCR500M CONFIGURATION VERIFIED"
        )

        self.enable_button.setEnabled(True)

    # ==========================================
    # OUTPUT APPROVAL
    # ==========================================

    def request_output_enable(self):

        self.enable_button.setEnabled(False)

        self.status_label.setText(
            "ACTIVATING PCR500M OUTPUT..."
        )

        self.enable_output_requested.emit()

    # ==========================================
    # LIVE MEASUREMENT
    # ==========================================

    def update_measurement(
        self,
        result,
        sample_number,
        elapsed_s,
        simulation
    ):

        measurements = result.get(
            "measurements",
            {}
        )

        self.source_label.setText(
            "SOURCE: SIMULATION"
            if simulation
            else "SOURCE: LIVE HARDWARE"
        )

        self.sample_label.setText(
            f"Samples: {sample_number}"
        )

        self.time_label.setText(
            f"Elapsed: {elapsed_s:.1f} s"
        )

        progress = min(
            100,
            int(
                elapsed_s /
                self.evaluation_duration_s * 100
            )
        )

        self.progress_bar.setValue(progress)

        for measurement_id, measurement in measurements.items():

            if measurement_id not in self.value_labels:
                self.create_measurement_row(
                    measurement_id
                )

            value = measurement.get("value")
            unit = measurement.get("unit", "")

            if isinstance(value, (int, float)):
                display_value = f"{value:,.3f}"
            else:
                display_value = str(value)

            self.value_labels[measurement_id].setText(
                f"{display_value} {unit}"
            )


    # ==========================================
    # EVALUATION PASS
    # ==========================================

    def show_pass(self, result):

        self.is_passed = True

        self.progress_bar.setValue(100)

        self.status_label.setText(
            "PASS - AC OUTPUT REMAINS ON"
        )

        self.status_label.setStyleSheet("""
            font-size: 11pt;
            font-weight: bold;
            color: #77D6A5;
            padding: 8px;
        """)

        self.time_label.setText(
            f"Evaluation completed: "
            f"{result.get('elapsed_s', 0):.2f} s"
        )

        self.enable_button.setEnabled(False)
        self.ok_button.setEnabled(True)

        self.ok_button.setFocus()

    # ==========================================
    # WORKER COMPLETED
    # ==========================================

    def finish_confirmation(self, result):

        self.is_running = False

        judgment = result.get(
            "judgment",
            "UNKNOWN"
        )

        if judgment == "PASS":

            self.status_label.setText(
                "PASS - PCR500M OUTPUT OFF"
            )

            self.status_label.setStyleSheet("""
                font-size: 11pt;
                font-weight: bold;
                color: #77D6A5;
                padding: 8px;
            """)

        else:

            self.status_label.setText(
                "NG - AC VOLTAGE OUTSIDE LIMITS"
            )

            self.status_label.setStyleSheet("""
                font-size: 11pt;
                font-weight: bold;
                color: #FF8585;
                padding: 8px;
            """)

        self.cancel_button.setText("Close")
        self.cancel_button.setObjectName("PrimaryButton")

        self.cancel_button.clicked.disconnect(
            self.cancel_confirmation
        )

        self.cancel_button.clicked.connect(
            self.accept
        )

        self.enable_button.setEnabled(False)
        self.ok_button.setEnabled(False)

        self.cancel_button.setEnabled(True)

    # ==========================================
    # WORKER ERROR
    # ==========================================

    def show_error(self, message):

        self.is_running = False

        self.status_label.setText(
            "AC VOLT CONFIRMATION FAILED"
        )

        self.status_label.setStyleSheet("""
            font-size: 11pt;
            font-weight: bold;
            color: #FF8585;
            padding: 8px;
        """)

        self.time_label.setText(message)
        self.time_label.setWordWrap(True)

        self.enable_button.setEnabled(False)
        self.ok_button.setEnabled(False)

        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect(
            self.cancel_confirmation
        )

        self.cancel_button.clicked.connect(
            self.accept
        )

    # ==========================================
    # PASS CONFIRMATION
    # ==========================================

    def request_pass_confirmation(self):

        if not self.is_passed:
            return

        self.ok_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        self.status_label.setText(
            "OPERATOR CONFIRMED PASS. "
            "SHUTTING DOWN INSTRUMENTS..."
        )

        self.pass_confirmation_requested.emit()

    # ==========================================
    # CANCEL
    # ==========================================

    def cancel_confirmation(self):

        if self.is_running:

            # Hindari mengirim cancel berkali-kali.
            if self.cancel_requested_once:
                return

            self.cancel_requested_once = True

            self.cancel_button.setEnabled(False)
            self.enable_button.setEnabled(False)
            self.ok_button.setEnabled(False)

            self.status_label.setText(
                "CANCELLATION REQUESTED. "
                "WAITING FOR SAFE SHUTDOWN..."
            )

            self.cancel_requested.emit()

        else:
            self.reject()

    def finish_abort(self, message=""):

        self.is_running = False

        self.status_label.setText(
            "WORKFLOW ABORTED"
        )

        self.reject()
    
    def closeEvent(self, event):

        if self.is_running:

            # X tidak boleh menutup dialog sebelum
            # worker menyelesaikan safe shutdown.
            self.cancel_confirmation()

            event.ignore()
            return

        event.accept()

    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_Escape:
            self.cancel_confirmation()
            return

        super().keyPressEvent(event)
