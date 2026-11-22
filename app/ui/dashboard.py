
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QProgressBar,
    QSplitter,
    QMessageBox,
    QComboBox,
    QLineEdit
)

from app.services.config_service import ConfigService
from app.core.workflow_engine import WorkflowEngine
from app.services.model_service import ModelService

from app.ui.dialogs import (
    InputDialog,
    ApprovalDialog,
    MeasurementDialog,
    LiveMeasurementDialog,
    ACVoltConfirmationDialog
)


def create_panel(title):

    frame = QFrame()
    frame.setObjectName("Panel")

    layout = QVBoxLayout(frame)

    heading = QLabel(title)
    heading.setStyleSheet(
        "font-weight: bold; font-size: 11pt;"
    )

    layout.addWidget(heading)

    return frame, layout


class DashboardPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.operator = None
        self.engine = None

        self.service = ConfigService()
        self.model_service = ModelService()
        self.current_step_row = None

        self.build_ui()

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)

        title = QLabel("Test Execution")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Execute and monitor JSON-based test workflows."
        )
        subtitle.setObjectName("Muted")
        root.addWidget(subtitle)


        # ==========================================
        # SERIAL NUMBER / AUTOMATIC MODEL DETECTION
        # ==========================================
        model_frame, model_layout = create_panel(
            "Product Identification"
        )

        serial_row = QHBoxLayout()

        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText(
            "Scan or enter product serial number"
        )
        self.serial_input.setMinimumHeight(38)

        self.check_model_button = QPushButton(
            "Check"
        )
        self.check_model_button.setMinimumHeight(38)

        serial_row.addWidget(self.serial_input, 1)
        serial_row.addWidget(self.check_model_button)

        model_layout.addLayout(serial_row)

        self.model_status_label = QLabel(
            "Enter serial number to detect product model."
        )
        self.model_status_label.setWordWrap(True)

        model_layout.addWidget(
            self.model_status_label
        )

        root.addWidget(model_frame)

        self.serial_input.returnPressed.connect(
            self.detect_model
        )
 
        self.check_model_button.clicked.connect(
            self.detect_model
        )

        self.serial_input.textChanged.connect(
            self.on_serial_number_changed
        )

        self.serial_label = QLabel("Serial Number: -")
        self.door_top_label = QLabel("Door Top: -")
        self.door_bottom_label = QLabel("Door Bottom: -")

        sequence_frame, sequence_layout = create_panel(
            "Test Sequence"
        )
        sequence_frame.setMinimumHeight(300)
        self.sequence_table = QTableWidget(0, 7)
        self.sequence_table.verticalHeader().setVisible(False)
        self.sequence_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.sequence_table.setShowGrid(True)

        self.sequence_table.setHorizontalHeaderLabels(
            ["NO", "TEST","DESCRIPTION","LOW LIMIT","HIGH LIMIT","MEASUREMENT","JUDGEMENT"]
        )

        self.sequence_table.setColumnWidth(0, 50)
        self.sequence_table.setColumnWidth(1, 300)
        self.sequence_table.setColumnWidth(2, 300)
        self.sequence_table.setColumnWidth(3, 150)
        self.sequence_table.setColumnWidth(4, 150)
        self.sequence_table.setColumnWidth(5, 150)
        self.sequence_table.setColumnWidth(6, 150)

        self.sequence_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )
        self.sequence_table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.sequence_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.sequence_table.setSelectionMode(
            QTableWidget.NoSelection
        )
        sequence_layout.addWidget(self.sequence_table)



        self.progress = QProgressBar()
        self.progress.setValue(0)

        sequence_layout.addWidget(self.progress)

        controls = QHBoxLayout()

        self.start_button = QPushButton(
            "Start Sequence (Y)"
        )

        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(
            self.start_sequence
        )

        # BUTTON START
        self.abort_button = QPushButton(
            "Abort (ESC)"
        )

        self.abort_button.setObjectName("DangerButton")
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(
            self.abort_sequence
        )

        controls.addWidget(self.start_button)
        controls.addWidget(self.abort_button)

        sequence_layout.addLayout(controls)

        # ==========================================
        # KEYBOARD SHORTCUTS
        # ==========================================

        # START SEQUENCE - Y

        self.start_shortcut = QShortcut(
            QKeySequence("Y"),
            self
        )

        self.start_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.start_shortcut.activated.connect(
            self.start_button.click
        )

        # ABORT SEQUENCE - ESC

        self.abort_shortcut = QShortcut(
            QKeySequence("Escape"),
            self
        )

        self.abort_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.abort_shortcut.activated.connect(
            self.abort_sequence
        )

        root.addWidget(sequence_frame)


    # ==========================================
    # AC VOLT CONFIRMATION
    # ==========================================

    def handle_ac_volt_confirmation(self, request):

        parameters = request.get("parameters", {})

        dialog = ACVoltConfirmationDialog(
            evaluation_duration_s=parameters.get(
                "evaluation_duration_s", 10
            ),
            sample_interval_s=parameters.get(
                "sample_interval_s", 1
            ),
            parent=self
        )

        engine = self.engine

        # Operator approval
        dialog.enable_output_requested.connect(
            engine.approve_ac_volt_output
        )

        dialog.pass_confirmation_requested.connect(
            engine.confirm_ac_volt_pass
        )

        dialog.cancel_requested.connect(
            engine.cancel_ac_volt_confirmation
        )

        # Worker status
        engine.ac_volt_status_changed.connect(
            dialog.update_status
        )

        engine.ac_volt_configuration_ready.connect(
            dialog.configuration_ready
        )

        engine.ac_volt_sample_received.connect(
            dialog.update_measurement
        )

        engine.ac_volt_evaluation_passed.connect(
            dialog.show_pass
        )

        engine.ac_volt_completed.connect(
            dialog.finish_confirmation
        )

        engine.ac_volt_failed.connect(
            dialog.show_error
        )
 
        engine.aborted.connect(
            dialog.finish_abort
        )

        try:

            engine.start_ac_volt_confirmation(
                parameters
            )

            dialog.exec()

        finally:

            # Disconnect dialog-specific signals
            connections = [
                (dialog.enable_output_requested, engine.approve_ac_volt_output),
                (dialog.pass_confirmation_requested, engine.confirm_ac_volt_pass),
                (dialog.cancel_requested, engine.cancel_ac_volt_confirmation),
                (engine.ac_volt_status_changed, dialog.update_status),
                (engine.ac_volt_configuration_ready, dialog.configuration_ready),
                (engine.ac_volt_sample_received, dialog.update_measurement),
                (engine.ac_volt_evaluation_passed, dialog.show_pass),
                (engine.ac_volt_completed, dialog.finish_confirmation),
                (engine.ac_volt_failed, dialog.show_error),
                (engine.aborted, dialog.finish_abort),
            ]

            for signal, slot in connections:
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass

    # ==========================================
    # SERIAL NUMBER MODEL DETECTION
    # ==========================================

    def on_serial_number_changed(self, value):

        if self.engine and self.engine.is_running:
            return

        self.selected_model_id = None
        self.model_configuration = None
        self.model_validation = None
        self.serial_mapping_result = None
        self.detected_serial_number = None

        self.model_status_label.setStyleSheet("")
        self.model_status_label.setText(
            "Serial number changed. Detect model again."
        )

        if hasattr(self, "start_button"):
            self.start_button.setEnabled(False)

    def detect_model(self):

        if self.engine and self.engine.is_running:
            return

        serial_number = self.serial_input.text().strip()

        # Reset previous detection
        self.selected_model_id = None
        self.model_configuration = None
        self.model_validation = None
        self.serial_mapping_result = None
        self.detected_serial_number = None

        if hasattr(self, "start_button"):
            self.start_button.setEnabled(False)

        if not serial_number:

            QMessageBox.warning(
                self,
                "Serial Number Required",
                "Scan or enter serial number first."
            )

            self.serial_input.setFocus()
            return

        try:

            # ----------------------------------
            # RESOLVE MODEL
            # ----------------------------------

            mapping = (
                self.model_service.resolve_model_by_serial(
                    serial_number
                )
            )

            model_id = mapping["model_id"]

            # ----------------------------------
            # LOAD MODEL
            # ----------------------------------

            configuration = (
                self.model_service.load_model(model_id)
            )

            # ----------------------------------
            # VALIDATE MODEL
            # ----------------------------------

            validation = (
                self.model_service.validate_model(model_id)
            )

            if not validation["valid"]:

                errors = "\n".join(
                    f"- {error}"
                    for error in validation["errors"]
                )

                raise ValueError(
                    f"Model {model_id} configuration is invalid:\n"
                    f"{errors}"
                )

            # ----------------------------------
            # SAVE DETECTION RESULT
            # ----------------------------------

            self.selected_model_id = model_id
            self.model_configuration = configuration
            self.model_validation = validation

            self.serial_mapping_result = mapping
            self.detected_serial_number = (
                mapping["serial_number"]
            )

            model_name = configuration["model"].get(
                "model_name",
                model_id
            )

            self.model_status_label.setStyleSheet(
                "color: #77D6A5; font-weight: bold;"
            )

            self.model_status_label.setText(
                f"Model Name: {model_name}\n"
                "Configuration validation passed."
            )

            # ----------------------------------
            # LOAD TEST SEQUENCE
            # ----------------------------------

            sequence = self.model_configuration.get(
                "sequence", {}
            )

            steps = sequence.get("steps", [])

            self.load_sequence_table(steps)
            
            self.serial_label.setText(
                f"Serial Number: {self.detected_serial_number}"
            )



            # ----------------------------------
            # ENABLE EXECUTION
            # ----------------------------------

            self.start_button.setEnabled(True)
            self.start_button.setFocus()

            self.add_log(
                "SYSTEM",
                f"Serial number detected: "
                f"{self.detected_serial_number}"
            )

            self.add_log(
                "SUCCESS",
                f"Model automatically selected: {model_id}"
            )


        except Exception as error:

            self.selected_model_id = None
            self.model_configuration = None
            self.model_validation = None
            self.serial_mapping_result = None
            self.detected_serial_number = None

            self.model_status_label.setStyleSheet(
                "color: #FF8585; font-weight: bold;"
            )

            self.model_status_label.setText(
                f"MODEL DETECTION FAILED\n{error}"
            )

            QMessageBox.warning(
                self,
                "Model Detection Failed",
                str(error)
            )

            self.serial_input.setFocus()

    def on_model_changed(self, index):

        if index < 0:
            return

        if self.engine and self.engine.is_running:
            return

        model_id = self.model_combo.itemData(index)

        if not model_id:
            return

        self.selected_model_id = model_id

        self.model_configuration = None
        self.model_validation = None

        try:

            self.model_configuration = (
                self.model_service.load_model(model_id)
            )

            self.model_validation = (
                self.model_service.validate_model(model_id)
            )

            if self.model_validation["valid"]:

                self.model_status_label.setStyleSheet(
                    "color: #77D6A5; font-weight: bold;"
                )

                self.model_status_label.setText(
                    f"MODEL READY: {model_id}\n"
                    "Configuration validation passed. "
                    "Execution integration is still pending."
                )

            else:

                errors = self.model_validation["errors"]

                error_text = "\n".join(
                    f"• {error}" for error in errors
                )

                self.model_status_label.setStyleSheet(
                    "color: #FF8585; font-weight: bold;"
                )

                self.model_status_label.setText(
                    f"MODEL INVALID: {model_id}\n"
                    f"{error_text}"
                )

        except Exception as error:

            self.model_status_label.setStyleSheet(
                "color: #FF8585; font-weight: bold;"
            )

            self.model_status_label.setText(
                f"MODEL ERROR: {error}"
            )

            self.model_configuration = None
            self.model_validation = None

    def set_operator(self, operator):
        self.operator = operator

    def set_table_item(self, row, column, value):

        item = QTableWidgetItem(str(value))

        if column in [0, 3, 4, 5, 6]:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

        self.sequence_table.setItem(
            row, column, item
        )

    def load_sequence_table(self, steps):

        self.sequence_table.setRowCount(0)

        test_parameters = (
            self.model_configuration
            .get("parameters", {})
            .get("test_parameters", {})
        )

        for step in steps:

            if not isinstance(step, dict):
                raise TypeError(
                    f"Invalid step configuration: "
                    f"expected dict, got {type(step).__name__}: {step}"
                )

            row = self.sequence_table.rowCount()
            self.sequence_table.insertRow(row)

            name = step.get(
                "name",
                step.get("id", "Unnamed Step")
            )

            step_parameters = step.get("parameters", {})
            step_type = step.get("type")
            function = step_parameters.get("function")

            lower = "-"
            upper = "-"
            description = "-"

            if step_type == "validate_serial":
                description = self.detected_serial_number or "-"

            if step_type == "instrument_test":

                if function in test_parameters:

                    function_parameters = test_parameters[function]

                    lower = function_parameters.get("lower", "-")
                    upper = function_parameters.get("upper", "-")

            if step_type == "ac_volt_confirmation":

                confirmation_parameters = test_parameters.get(
                    "ac_volt_confirmation", {}
                )

                lower = confirmation_parameters.get("lower", "-")
                upper = confirmation_parameters.get("upper", "-")

            status = (
                "WAITING"
                if step.get("enabled", True)
                else "SKIPPED"
            )

            self.set_table_item(row, 0, row + 1)
            self.set_table_item(row, 1, name)
            self.set_table_item(row, 2, description)
            self.set_table_item(row, 3, lower)
            self.set_table_item(row, 4, upper)
            self.set_table_item(row, 5, "-")
            self.set_table_item(row, 6, status)

    def start_sequence(self):

        if not self.operator:

            QMessageBox.warning(
                self,
                "Operator Required",
                "Login operator terlebih dahulu."
            )

            return

        # --------------------------------------
        # MODEL VALIDATION
        # --------------------------------------

        if (
            not self.selected_model_id
            or not self.model_configuration
            or not self.detected_serial_number
        ):

            QMessageBox.warning(
                self,
                "Product Identification Required",
                "Detect a valid product model using serial number first."
            )

            return

        if (
            self.serial_input.text().strip().upper()
            != self.detected_serial_number.upper()
        ):

            QMessageBox.warning(
                self,
                "Serial Number Changed",
                "Serial number has changed. Detect the model again."
            )

            return

        try:

            validation = self.model_service.validate_model(
                self.selected_model_id
            )

            self.model_validation = validation

            if not validation["valid"]:

                errors = "\n".join(
                    f"• {error}"
                    for error in validation["errors"]
                )

                QMessageBox.warning(
                    self,
                    "Invalid Model Configuration",
                    "The selected model cannot be executed.\n\n"
                    f"{errors}"
                )

                return

            # Reload configuration before execution.
            self.model_configuration = (
                self.model_service.load_model(
                    self.selected_model_id
                )
            )

            self.door_top_label.setText(
                "Door Top: -"
            )

            self.door_bottom_label.setText(
                "Door Bottom: -"
            )

            # self.terminal.clear()
            self.progress.setValue(0)

            # ----------------------------------
            # CREATE WORKFLOW ENGINE
            # ----------------------------------

            self.engine = WorkflowEngine(
                self.model_configuration,
                self.operator,
                self,
                initial_data={
                    "serial_number": self.detected_serial_number
                }
            )

            self.engine.log_message.connect(
                self.add_log
            )

            self.engine.step_started.connect(
                self.on_step_started
            )

            self.engine.step_finished.connect(
                self.on_step_finished
            )

            self.engine.interaction_requested.connect(
                self.handle_interaction
            )

            self.engine.finished.connect(
                self.finish_sequence
            )

            self.engine.failed.connect(
                self.workflow_failed
            )

            self.engine.aborted.connect(
                self.workflow_aborted
            )

            self.start_button.setEnabled(False)
            self.abort_button.setEnabled(True)
            
            self.serial_input.setEnabled(False)
            self.check_model_button.setEnabled(False)

            self.engine.start()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Workflow Error",
                str(error)
            )

    def on_step_started(self, current, total, name):

        self.progress.setMaximum(total)
        self.progress.setValue(current)

        row = current - 1

        self.current_step_row = row

        if 0 <= row < self.sequence_table.rowCount():

            item = self.sequence_table.item(row, 6)

            if item:
                item.setText("RUNNING")

    def on_step_finished(self, current, message):

        row = current - 1

        if 0 <= row < self.sequence_table.rowCount():

            item = self.sequence_table.item(row, 6)

            if item:
                item.setText("OK")

    def handle_interaction(self, request):

        interaction_type = request.get("type")

        if interaction_type == "input":

            dialog = InputDialog(
                request.get("title", "Input"),
                [
                    (
                        request["field"],
                        request.get("label", "Input"),
                        request.get("placeholder", "")
                    )
                ],
                self
            )

            if not dialog.exec():

                self.abort_sequence()

                QTimer.singleShot(
                    0,
                    self.focus_start_button
                )

                return

            values = dialog.get_values()

            value = values.get(
                request["field"], ""
            )

            if request.get("required", True) and not value:
                QMessageBox.warning(
                    self,
                    "Input Required",
                    "Field tidak boleh kosong."
                )
                self.abort_sequence()
                return

            self.update_product_information(
                request["field"],
                value
            )

            self.update_sequence_input_result(
                request["field"],
                value
            )

            self.engine.submit_interaction({
                "value": value
            })

        elif interaction_type == "approval":

            dialog = ApprovalDialog(
                self,
                request.get("title"),
                request.get("message")
            )

            approved = bool(dialog.exec())

            if not approved:
                self.abort_sequence()
                return

            self.engine.submit_interaction({
                "approved": True
            })

        elif interaction_type == "measurement":

            dialog = MeasurementDialog(
                request.get("result", {}),
                self
            )

            dialog.exec()

            self.engine.submit_interaction({
                "continue": True
            })

        elif interaction_type == "live_measurement":

            dialog = LiveMeasurementDialog(
                instrument=request.get(
                    "instrument",
                    "WT310E"
                ),
                duration_s=request.get(
                    "duration_s",
                    10
                ),
                sample_interval_s=request.get(
                    "sample_interval_s",
                    1
                ),
                parent=self
            )

            self.engine.measurement_sample.connect(
                dialog.update_measurement
            )

            self.engine.measurement_completed.connect(
                dialog.finish_measurement
            )

            self.engine.measurement_failed.connect(
                dialog.show_error
            )

            dialog.cancel_requested.connect(
                self.abort_sequence
            )

            try:
                dialog.exec()

            finally:

                self.engine.measurement_sample.disconnect(
                    dialog.update_measurement
                )

                self.engine.measurement_completed.disconnect(
                    dialog.finish_measurement
                )

                self.engine.measurement_failed.disconnect(
                    dialog.show_error
                )

                dialog.cancel_requested.disconnect(
                    self.abort_sequence
                )

        elif interaction_type == "ac_volt_confirmation":

            self.handle_ac_volt_confirmation(request)
        
        else:

            self.workflow_failed(
                f"Unsupported interaction: {interaction_type}"
            )

    def update_sequence_input_result(self, field, value):

        if field not in (
            "door_top",
            "door_bottom"
        ):
            return

        row = self.current_step_row

        if row is None:
            return

        if row >= self.sequence_table.rowCount():
            return

        self.set_table_item(
            row,
            2,
            value
        )

    def update_product_information(self, field, value):

        labels = {
            "serial_number": self.serial_label,
            "door_top": self.door_top_label,
            "door_bottom": self.door_bottom_label
        }

        label = labels.get(field)

        if label:
            label.setText(
                f"{field.replace('_', ' ').title()}: {value}"
            )

    def focus_start_button(self):
        if self.start_button.isEnabled():
            self.start_button.setFocus()

    def abort_sequence(self):

        if not self.engine:
            return

        if not self.engine.is_running:
            return

        self.add_log(
            "ABORT",
            "Abort requested. Waiting for safe shutdown..."
        )

        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(False)

        self.serial_input.setEnabled(False)
        self.check_model_button.setEnabled(False)

        self.engine.stop()

    def workflow_aborted(self, message):

        self.add_log("ABORT", message)

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

        self.serial_input.setEnabled(True)
        self.check_model_button.setEnabled(True)

        QTimer.singleShot(
            0,
            self.focus_start_button
        )
        
    def add_log(self, category, message):

        timestamp = datetime.now().strftime("%H:%M:%S")

        colors = {
            "SYSTEM": "#78B7ED",
            "STEP": "#D6E1EE",
            "SUCCESS": "#77D6A5",
            "DATABASE": "#75C8D0",
            "INSTRUMENT": "#75C8D0",
            "MEASUREMENT": "#8BB7F0",
            "DONE": "#77D6A5",
            "ERROR": "#FF8585",
            "ABORT": "#FF8585"
        }

    def finish_sequence(self):

        if self.sequence_table.rowCount():

            last = self.sequence_table.rowCount() - 1

            item = self.sequence_table.item(last, 6)

            if item:
                item.setText("OK")

        self.add_log(
            "DONE",
            "Workflow completed successfully."
        )

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

        self.serial_input.setEnabled(True)
        self.check_model_button.setEnabled(True)

        QMessageBox.information(
            self,
            "Workflow Completed",
            "Test sequence completed and result saved."
        )

        self.serial_input.clear()

        QTimer.singleShot(0, self.serial_input.setFocus)

    def workflow_failed(self, message):

        self.add_log("ERROR", message)

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

        self.serial_input.setEnabled(True)
        self.check_model_button.setEnabled(True)

        QMessageBox.critical(
            self,
            "Workflow Failed",
            message
        )

        QTimer.singleShot(0, self.serial_input.setFocus)