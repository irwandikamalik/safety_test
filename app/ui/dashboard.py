
from datetime import datetime

from PySide6.QtCore import Qt
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
    QComboBox
)

from app.services.config_service import ConfigService
from app.core.workflow_engine import WorkflowEngine
from app.services.model_service import ModelService

from app.ui.dialogs import (
    InputDialog,
    ApprovalDialog,
    MeasurementDialog
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

        self.selected_model_id = None
        self.model_configuration = None
        self.model_validation = None

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
        # MODEL SELECTOR
        # ==========================================

        model_frame, model_layout = create_panel(
            "Product Model Selection"
        )

        model_row = QHBoxLayout()

        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(36)

        self.refresh_model_button = QPushButton(
            "Refresh Models"
        )

        self.refresh_model_button.setMinimumHeight(36)

        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.refresh_model_button)

        model_layout.addLayout(model_row)

        self.model_status_label = QLabel(
            "No model selected."
        )

        self.model_status_label.setWordWrap(True)

        model_layout.addWidget(
            self.model_status_label
        )

        root.addWidget(model_frame)

        self.model_combo.currentIndexChanged.connect(
            self.on_model_changed
        )

        self.refresh_model_button.clicked.connect(
            self.refresh_models
        )

        self.refresh_models()

        top_layout = QHBoxLayout()

        operator_frame, operator_layout = create_panel(
            "Operator Information"
        )

        self.operator_label = QLabel("Not logged in")
        self.operator_label.setStyleSheet(
            "font-size: 14pt; font-weight: bold;"
        )

        operator_layout.addWidget(self.operator_label)

        product_frame, product_layout = create_panel(
            "Product Information"
        )

        self.serial_label = QLabel("Serial Number: -")
        self.door_top_label = QLabel("Door Top: -")
        self.door_bottom_label = QLabel("Door Bottom: -")

        product_layout.addWidget(self.serial_label)
        product_layout.addWidget(self.door_top_label)
        product_layout.addWidget(self.door_bottom_label)

        top_layout.addWidget(operator_frame, 1)
        top_layout.addWidget(product_frame, 2)

        root.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)

        sequence_frame, sequence_layout = create_panel(
            "Test Sequence"
        )

        self.sequence_table = QTableWidget(0, 3)
        self.sequence_table.verticalHeader().setVisible(False)

        self.sequence_table.setHorizontalHeaderLabels(
            ["NO", "STEP", "STATUS"]
        )

        self.sequence_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )

        self.sequence_table.setColumnWidth(0, 45)
        self.sequence_table.setColumnWidth(2, 100)

        self.sequence_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.sequence_table.setSelectionMode(
            QTableWidget.NoSelection
        )

        sequence_layout.addWidget(self.sequence_table)

        terminal_frame, terminal_layout = create_panel(
            "Execution Terminal"
        )

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)

        terminal_layout.addWidget(self.terminal, 1)

        self.progress = QProgressBar()
        self.progress.setValue(0)

        terminal_layout.addWidget(self.progress)

        controls = QHBoxLayout()

        self.start_button = QPushButton(
            "Start Sequence (Y)"
        )

        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(
            self.start_sequence
        )

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

        terminal_layout.addLayout(controls)

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
            self.start_sequence
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

        splitter.addWidget(sequence_frame)
        splitter.addWidget(terminal_frame)

        splitter.setSizes([430, 700])

        root.addWidget(splitter, 1)

    def refresh_models(self):

        if self.engine and self.engine.is_running:
            return

        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        self.selected_model_id = None
        self.model_configuration = None
        self.model_validation = None

        try:

            models = self.model_service.discover_models()

            for model in models:

                if model.get("enabled") is not True:
                    continue

                self.model_combo.addItem(
                    f'{model["model_id"]} - {model["model_name"]}',
                    model["model_id"]
                )

        except Exception as error:

            self.model_status_label.setText(
                f"Model discovery failed: {error}"
            )

        self.model_combo.blockSignals(False)

        if self.model_combo.count() == 0:

            self.model_status_label.setText(
                "No enabled model found."
            )

            return

        self.model_combo.setCurrentIndex(0)

        self.on_model_changed(0)


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

        self.operator_label.setText(
            f'{operator["name"]} - {operator["id"]}'
        )

    def load_sequence_table(self, steps):

        self.sequence_table.setRowCount(0)

        for index, step in enumerate(steps):

            if not step.get("enabled", True):
                continue

            row = self.sequence_table.rowCount()

            self.sequence_table.insertRow(row)

            name = step.get(
                "name",
                step.get("id", "Unnamed Step")
            )

            self.sequence_table.setItem(
                row, 0,
                QTableWidgetItem(str(row + 1))
            )

            self.sequence_table.setItem(
                row, 1,
                QTableWidgetItem(name)
            )

            self.sequence_table.setItem(
                row, 2,
                QTableWidgetItem("WAITING")
            )


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

        if not self.selected_model_id:

            QMessageBox.warning(
                self,
                "Model Required",
                "Select a product model first."
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

            sequence = self.model_configuration["sequence"]

            if sequence.get("version") != 1:

                raise ValueError(
                    "Unsupported sequence version."
                )

            # ----------------------------------
            # PREPARE DASHBOARD
            # ----------------------------------

            self.load_sequence_table(
                sequence.get("steps", [])
            )

            self.serial_label.setText(
                "Serial Number: -"
            )

            self.door_top_label.setText(
                "Door Top: -"
            )

            self.door_bottom_label.setText(
                "Door Bottom: -"
            )

            self.terminal.clear()
            self.progress.setValue(0)

            # ----------------------------------
            # CREATE WORKFLOW ENGINE
            # ----------------------------------

            self.engine = WorkflowEngine(
                self.model_configuration,
                self.operator,
                self
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

            self.start_button.setEnabled(False)
            self.abort_button.setEnabled(True)

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

        if row < self.sequence_table.rowCount():

            self.sequence_table.item(
                row, 2
            ).setText("RUNNING")

            if row > 0:

                previous = self.sequence_table.item(
                    row - 1, 2
                )

                if previous:
                    previous.setText("DONE")

    def on_step_finished(self, current, message):

        row = current - 1

        if row < self.sequence_table.rowCount():

            self.sequence_table.item(
                row, 2
            ).setText("DONE")

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

        else:

            self.workflow_failed(
                f"Unsupported interaction: {interaction_type}"
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

    def abort_sequence(self):

        if not self.engine:
            return

        if not self.engine.is_running:
            return

        self.add_log(
            "ABORT",
            "Sequence aborted by operator."
        )

        self.engine.stop()

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

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

        color = colors.get(category, "#D6E1EE")

        self.terminal.append(
            f'<span style="color:#8496AA">'
            f'[{timestamp}]</span> '
            f'<span style="color:{color};font-weight:bold">'
            f'[{category}]</span> '
            f'<span style="color:#D6E1EE">'
            f'{message}</span>'
        )

    def finish_sequence(self):

        if self.sequence_table.rowCount():

            last = self.sequence_table.rowCount() - 1

            self.sequence_table.item(
                last, 2
            ).setText("DONE")

        self.add_log(
            "DONE",
            "Workflow completed successfully."
        )

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

        QMessageBox.information(
            self,
            "Workflow Completed",
            "Test sequence completed and result saved."
        )

    def workflow_failed(self, message):

        self.add_log("ERROR", message)

        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

        QMessageBox.critical(
            self,
            "Workflow Failed",
            message
        )
