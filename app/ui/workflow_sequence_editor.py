import copy
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,    
    QSplitter,
    QSpinBox,
)

from app.core.step_registry import StepRegistry
from app.core.workflow_validator import WorkflowValidator


class WorkflowSequenceEditor(QWidget):

    sequence_changed = Signal(dict)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.registry = StepRegistry()
        self.validator = WorkflowValidator()

        self._sequence = {
            "sequence_id": "test_sequence",
            "name": "Test Sequence",
            "version": 1,
            "steps": [],
        }

        self._loading = False
        self.parameter_widgets = {}

        self.build_ui()
        self.refresh_step_list()

    # ==================================================
    # UI
    # ==================================================

    def build_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #DCE3EB;
                border: none;
                border-radius: 3px;
            }

            QSplitter::handle:hover {
                background-color: #287FC0;
            }
        """)
        main_splitter.setChildrenCollapsible(False)

        # ----------------------------------------------
        # STEP LIST
        # ----------------------------------------------

        step_group = QGroupBox("Workflow Steps")
        step_group.setObjectName("WorkflowStepsGroup")

        step_group.setStyleSheet("""
            QGroupBox#WorkflowStepsGroup {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #E0E6ED;
                border-radius: 8px;
            }
        """)
        step_layout = QVBoxLayout(step_group)

        self.step_list = QListWidget()
        self.step_list.setObjectName("StepList")
        self.step_list.setStyleSheet("""
            QListWidget#StepList {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #E0E6ED;
                border-radius: 7px;
                outline: none;
                padding: 4px;
            }

            QListWidget#StepList::item {
                padding: 9px;
                margin: 2px;
                border-radius: 5px;
            }

            QListWidget#StepList::item:hover {
                background-color: #E8EDF3;
            }

            QListWidget#StepList::item:selected {
                background-color: #1769AA;
                color: #FFFFFF;
            }
        """)

        self.step_list.currentRowChanged.connect(
            self.on_step_selected
        )

        step_layout.addWidget(self.step_list)

        add_layout = QHBoxLayout()

        self.step_type_combo = QComboBox()
        
        self.step_type_combo.setMinimumHeight(38)

        self.step_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #CCD5E0;
                border-radius: 6px;
                padding: 6px 10px;
                selection-background-color: #1769AA;
                selection-color: #FFFFFF;
            }

            QComboBox:hover {
                border: 1px solid #287FC0;
            }

            QComboBox:focus {
                border: 1px solid #287FC0;
            }

            QComboBox::drop-down {
                background-color: #F3F5F8;
                border: none;
                border-left: 1px solid #D6DEE8;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                width: 28px;
            }

            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #CCD5E0;
                selection-background-color: #1769AA;
                selection-color: #FFFFFF;
                outline: none;
            }

            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 5px;
            }
        """)

        for step_type in self.registry.available_types():
            self.step_type_combo.addItem(
                step_type,
                step_type
            )

        self.add_button = QPushButton("Add Step")
        self.add_button.clicked.connect(
            self.add_step
        )

        add_layout.addWidget(self.step_type_combo)
        add_layout.addWidget(self.add_button)

        step_layout.addLayout(add_layout)

        action_layout = QHBoxLayout()

        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.clicked.connect(
            self.duplicate_step
        )

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(
            self.remove_step
        )

        self.up_button = QPushButton("Move Up")
        self.up_button.clicked.connect(
            lambda: self.move_step(-1)
        )

        self.down_button = QPushButton("Move Down")
        self.down_button.clicked.connect(
            lambda: self.move_step(1)
        )

        action_layout.addWidget(self.duplicate_button)
        action_layout.addWidget(self.remove_button)
        action_layout.addWidget(self.up_button)
        action_layout.addWidget(self.down_button)

        step_layout.addLayout(action_layout)

        step_group.setMinimumWidth(280)
        step_group.setMaximumWidth(420)

        step_layout.setContentsMargins(12, 18, 12, 12)
        step_layout.setSpacing(10)

        main_splitter.addWidget(step_group)

        right_panel = QWidget()
        right_panel.setObjectName("WorkflowRightPanel")

        right_panel.setStyleSheet("""
            QWidget#WorkflowRightPanel {
                background-color: #F3F5F8;
            }
        """)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # ----------------------------------------------
        # SEQUENCE METADATA
        # ----------------------------------------------

        metadata_group = QGroupBox("Sequence Metadata")
        metadata_group.setObjectName("SequenceMetadataGroup")

        metadata_group.setStyleSheet("""
            QGroupBox#SequenceMetadataGroup {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #E0E6ED;
                border-radius: 8px;
            }
        """)

        metadata_layout = QFormLayout(metadata_group)

        self.sequence_id_edit = QLineEdit()
        self.sequence_id_edit.setPlaceholderText(
            "e.g. safety_test_sequence"
        )

        self.sequence_name_edit = QLineEdit()
        self.sequence_name_edit.setPlaceholderText(
            "e.g. Product Safety Test"
        )

        self.sequence_version_spin = QSpinBox()
        self.sequence_version_spin.setRange(1, 999999)
        self.sequence_version_spin.setValue(1)

        metadata_layout.addRow(
            "Sequence ID:",
            self.sequence_id_edit
        )

        metadata_layout.addRow(
            "Sequence Name:",
            self.sequence_name_edit
        )

        metadata_layout.addRow(
            "Version:",
            self.sequence_version_spin
        )

        metadata_layout.setContentsMargins(12, 18, 12, 12)
        metadata_layout.setVerticalSpacing(10)
        metadata_layout.setHorizontalSpacing(14)

        right_layout.addWidget(metadata_group)

        # ----------------------------------------------
        # STEP PROPERTIES
        # ----------------------------------------------

        properties_group = QGroupBox("Step Properties")
        properties_group.setObjectName("StepProperties")
        properties_group.setStyleSheet("""
            QGroupBox#StepProperties {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #E0E6ED;
                border-radius: 8px;
            }
        """)

        properties_layout = QFormLayout(properties_group)

        self.step_id_edit = QLineEdit()
        self.step_name_edit = QLineEdit()

        self.step_type_label = QLabel("-")

        self.step_enabled_checkbox = QCheckBox(
            "Enabled"
        )

        self.sequence_id_edit.editingFinished.connect(
            self.update_sequence_metadata
        )

        self.sequence_name_edit.editingFinished.connect(
            self.update_sequence_metadata
        )

        self.sequence_version_spin.valueChanged.connect(
            self.update_sequence_metadata
        )

        properties_layout.addRow(
            "Step ID:",
            self.step_id_edit
        )

        properties_layout.addRow(
            "Step Name:",
            self.step_name_edit
        )

        properties_layout.addRow(
            "Step Type:",
            self.step_type_label
        )

        properties_layout.addRow(
            "",
            self.step_enabled_checkbox
        )

        properties_layout.setContentsMargins(12, 18, 12, 12)
        properties_layout.setVerticalSpacing(10)
        properties_layout.setHorizontalSpacing(14)

        right_layout.addWidget(properties_group)

        # ----------------------------------------------
        # STEP PARAMETERS
        # ----------------------------------------------

        parameter_group = QGroupBox("Step Parameters")
        parameter_group.setObjectName("StepParametersGroup")
        parameter_group.setStyleSheet("""
            QGroupBox#StepParametersGroup {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #E0E6ED;
                border-radius: 8px;
            }
        """)
        
        parameter_layout = QVBoxLayout(parameter_group)

        self.parameter_container = QWidget()
        self.parameter_container.setObjectName("ParameterContainer")

        self.parameter_form = QFormLayout(
            self.parameter_container
        )

        self.parameter_form.setContentsMargins(8, 8, 8, 8)
        self.parameter_form.setVerticalSpacing(12)
        self.parameter_form.setHorizontalSpacing(14)

        self.parameter_container.setStyleSheet("""
            QWidget#ParameterContainer {
                background-color: transparent;
            }

            QWidget#ParameterContainer QPlainTextEdit {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #CCD5E0;
                border-radius: 6px;
                padding: 8px;
                font-family: "Consolas";
                font-size: 9pt;
            }

            QWidget#ParameterContainer QPlainTextEdit:focus {
                background-color: #FFFFFF;
                border: 1px solid #287FC0;
            }
        """)


        parameter_layout.addWidget(
            self.parameter_container
        )

        self.apply_parameters_button = QPushButton(
            "Apply Parameters"
        )

        self.apply_parameters_button.clicked.connect(
            self.apply_step_parameters
        )

        parameter_layout.addWidget(
            self.apply_parameters_button,
            alignment=Qt.AlignmentFlag.AlignRight
        )
        
        right_layout.addWidget(parameter_group, 1)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        right_scroll.setWidget(right_panel)
        right_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #F3F5F8;
                border: none;
            }

            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #F3F5F8;
                border: none;
            }

            QScrollBar:vertical {
                background-color: #E8EDF3;
                width: 9px;
                margin: 2px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical {
                background-color: #AABBCD;
                min-height: 30px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #287FC0;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background-color: transparent;
            }
        """)

        main_splitter.addWidget(right_scroll)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(main_splitter, 1)

        self.apply_parameters_button.setEnabled(False)



        self.step_id_edit.editingFinished.connect(
            self.update_selected_step
        )

        self.step_name_edit.editingFinished.connect(
            self.update_selected_step
        )

        self.step_enabled_checkbox.stateChanged.connect(
            self.update_selected_step
        )

        self.set_properties_enabled(False)




    # ==================================================
    # PARAMETER EDITOR
    # ==================================================

    def clear_parameter_form(self):

        while self.parameter_form.count():

            item = self.parameter_form.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.parameter_widgets.clear()

    def create_parameter_widget(
        self,
        expected_type,
        value
    ):

        if isinstance(expected_type, tuple):
            expected_types = expected_type
        else:
            expected_types = (expected_type,)

        if bool in expected_types:

            widget = QCheckBox()
            widget.setChecked(bool(value))

        elif any(
            item in (dict, list, object)
            for item in expected_types
        ):

            widget = QPlainTextEdit()

            widget.setPlainText(
                json.dumps(
                    value,
                    indent=4,
                    ensure_ascii=False
                )
            )

            widget.setMinimumHeight(90)

        else:

            widget = QLineEdit()

            if value is not None:
                widget.setText(str(value))

        return widget

    def build_parameter_form(self, step):

        self.clear_parameter_form()

        step_type = step.get("type")

        schema = self.validator.STEP_SCHEMAS.get(
            step_type
        )

        if schema is None:

            self.parameter_form.addRow(
                QLabel(
                    "No parameter schema available."
                )
            )

            self.apply_parameters_button.setEnabled(False)
            return

        parameters = step.setdefault(
            "parameters",
            {}
        )

        self.parameter_widgets = {}

        for section in ("required", "optional"):

            fields = schema.get(section, {})

            if not fields:
                continue

            if section == "optional":

                self.parameter_form.addRow(
                    QLabel("Optional Parameters")
                )

            for key, expected_type in fields.items():

                exists = key in parameters

                value = parameters.get(key)

                if not exists:
                    value = self.default_parameter_value(
                        expected_type
                    )

                widget = self.create_parameter_widget(
                    expected_type,
                    value
                )

                include_checkbox = None

                if section == "optional":

                    include_checkbox = QCheckBox(
                        "Include"
                    )

                    include_checkbox.setChecked(exists)
                    widget.setEnabled(exists)

                    include_checkbox.toggled.connect(
                        widget.setEnabled
                    )

                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)

                    row_layout.setContentsMargins(
                        0, 0, 0, 0
                    )

                    row_layout.addWidget(include_checkbox)
                    row_layout.addWidget(widget)

                    self.parameter_form.addRow(
                        key,
                        row_widget
                    )

                else:

                    self.parameter_form.addRow(
                        key,
                        widget
                    )

                self.parameter_widgets[key] = {
                    "widget": widget,
                    "type": expected_type,
                    "optional": section == "optional",
                    "include_checkbox": include_checkbox,
                }

        self.apply_parameters_button.setEnabled(True)

    def default_parameter_value(self, expected_type):

        if isinstance(expected_type, tuple):
            expected_type = expected_type[0]

        if expected_type is str:
            return ""

        if expected_type is bool:
            return False

        if expected_type is int:
            return 0

        if expected_type is float:
            return 0.0

        if expected_type is dict:
            return {}

        if expected_type is list:
            return []

        return None

    def read_parameter_widget(
        self,
        widget,
        expected_type
    ):

        if isinstance(expected_type, tuple):
            expected_types = expected_type
        else:
            expected_types = (expected_type,)

        if bool in expected_types:
            return widget.isChecked()

        if any(
            item in (dict, list, object)
            for item in expected_types
        ):

            content = widget.toPlainText().strip()

            if not content:
                raise ValueError(
                    "JSON parameter cannot be empty."
                )

            return json.loads(content)

        content = widget.text()

        if int in expected_types and float in expected_types:

            number = float(content)

            if number.is_integer():
                return int(number)

            return number

        if int in expected_types:
            return int(content)

        if float in expected_types:
            return float(content)

        if str in expected_types:
            return content

        return content

    def apply_step_parameters(self):

        row = self.step_list.currentRow()

        if row < 0:
            return

        step = self._sequence["steps"][row]

        parameters = step.setdefault(
            "parameters",
            {}
        )

        updated_parameters = copy.deepcopy(parameters)

        try:

            for key, field in self.parameter_widgets.items():

                if field["optional"]:

                    include_checkbox = field[
                        "include_checkbox"
                    ]

                    if not include_checkbox.isChecked():

                        updated_parameters.pop(key, None)
                        continue

                value = self.read_parameter_widget(
                    field["widget"],
                    field["type"]
                )

                updated_parameters[key] = value

            step["parameters"] = updated_parameters

        except (
            ValueError,
            TypeError,
            json.JSONDecodeError
        ) as error:

            QMessageBox.warning(
                self,
                "Invalid Parameter",
                f"Unable to apply parameters:\n{error}"
            )

            return

        self.emit_sequence_changed()


    def validate_selected_step_parameters(self):

        row = self.step_list.currentRow()

        if row < 0:
            return False, ["No step selected."]

        step = self._sequence["steps"][row]

        step_type = step.get("type")

        schema = self.validator.STEP_SCHEMAS.get(
            step_type
        )

        if schema is None:
            return False, [
                f"Unknown step type: {step_type}"
            ]

        parameters = step.get("parameters", {})

        if not isinstance(parameters, dict):
            return False, [
                "Step parameters must be a dictionary."
            ]

        errors = []

        required = schema.get("required", {})

        for key, expected_type in required.items():

            if key not in parameters:

                errors.append(
                    f"Missing required parameter: {key}"
                )

                continue

            value = parameters[key]

            expected_types = (
                expected_type
                if isinstance(expected_type, tuple)
                else (expected_type,)
            )

            if not isinstance(value, expected_types):

                errors.append(
                    f"Parameter '{key}' has invalid type."
                )

        optional = schema.get("optional", {})

        for key, value in parameters.items():

            if key in required:
                continue

            if key not in optional:

                errors.append(
                    f"Unknown parameter: {key}"
                )

                continue

            expected_type = optional[key]

            expected_types = (
                expected_type
                if isinstance(expected_type, tuple)
                else (expected_type,)
            )

            if not isinstance(value, expected_types):

                errors.append(
                    f"Parameter '{key}' has invalid type."
                )

        return not errors, errors

    # ==================================================
    # SEQUENCE API
    # ==================================================

    def set_sequence(self, sequence):

        if not isinstance(sequence, dict):
            raise ValueError(
                "Sequence must be a dictionary."
            )

        steps = sequence.get("steps")

        if not isinstance(steps, list):
            raise ValueError(
                "Sequence steps must be a list."
            )

        self._sequence = copy.deepcopy(sequence)

        self._sequence.setdefault("sequence_id", "")
        self._sequence.setdefault("name", "")
        self._sequence.setdefault("version", 1)

        self.refresh_metadata_fields()
        self.refresh_step_list()

        if self._sequence["steps"]:
            self.step_list.setCurrentRow(0)

        else:
            self.clear_properties()

    def get_sequence(self):

        return copy.deepcopy(self._sequence)

    def refresh_metadata_fields(self):

        self._loading = True

        self.sequence_id_edit.setText(
            str(self._sequence.get("sequence_id", ""))
        )

        self.sequence_name_edit.setText(
            str(self._sequence.get("name", ""))
        )

        try:
            version = int(self._sequence.get("version", 1))
        except (TypeError, ValueError):
            version = 1

        self.sequence_version_spin.setValue(
            max(1, min(version, 999999))
        )

        self._loading = False

    def update_sequence_metadata(self, *args):

        if self._loading:
            return

        self._sequence["sequence_id"] = (
            self.sequence_id_edit.text().strip()
        )

        self._sequence["name"] = (
            self.sequence_name_edit.text().strip()
        )

        self._sequence["version"] = (
            self.sequence_version_spin.value()
        )

        self.emit_sequence_changed()

    # ==================================================
    # STEP LIST
    # ==================================================

    def refresh_step_list(self, selected_row=None):

        self._loading = True

        self.step_list.clear()

        steps = self._sequence.get("steps", [])

        for index, step in enumerate(steps):

            step_name = step.get(
                "name",
                step.get("type", "Unknown Step")
            )

            step_type = step.get(
                "type",
                "unknown"
            )

            enabled = step.get("enabled", True)

            status = "" if enabled else " [Disabled]"

            item = QListWidgetItem(
                f"{index + 1:02d}. {step_name} "
                f"({step_type}){status}"
            )

            self.step_list.addItem(item)

        self._loading = False

        if selected_row is not None and steps:

            selected_row = max(
                0,
                min(selected_row, len(steps) - 1)
            )

            self.step_list.setCurrentRow(
                selected_row
            )

        elif not steps:

            self.clear_properties()

    # ==================================================
    # ADD STEP
    # ==================================================

    def create_default_parameters(self, step_type):

        schema = self.validator.STEP_SCHEMAS.get(
            step_type,
            {}
        )

        parameters = {}

        for key, expected_type in schema.get(
            "required",
            {}
        ).items():

            if isinstance(expected_type, tuple):
                expected_type = expected_type[0]

            if expected_type is str:
                parameters[key] = ""

            elif expected_type is bool:
                parameters[key] = False

            elif expected_type is int:
                parameters[key] = 0

            elif expected_type is float:
                parameters[key] = 0.0

            elif expected_type is dict:
                parameters[key] = {}

            elif expected_type is list:
                parameters[key] = []

            else:
                parameters[key] = None

        return parameters

    def generate_step_id(self):

        existing_ids = {
            step.get("id")
            for step in self._sequence["steps"]
        }

        number = 1

        while True:

            step_id = f"step_{number:03d}"

            if step_id not in existing_ids:
                return step_id

            number += 1

    def add_step(self):

        step_type = self.step_type_combo.currentData()

        if not self.registry.is_registered(step_type):
            return

        step_name = step_type.replace(
            "_",
            " "
        ).title()

        step = {
            "id": self.generate_step_id(),
            "type": step_type,
            "name": step_name,
            "enabled": True,
            "parameters": self.create_default_parameters(
                step_type
            ),
        }

        self._sequence["steps"].append(step)

        row = len(self._sequence["steps"]) - 1

        self.refresh_step_list(row)

        self.emit_sequence_changed()

    # ==================================================
    # DUPLICATE STEP
    # ==================================================

    def duplicate_step(self):

        row = self.step_list.currentRow()

        if row < 0:
            return

        original_step = self._sequence["steps"][row]

        duplicated_step = copy.deepcopy(
            original_step
        )

        # Generate unique ID
        duplicated_step["id"] = self.generate_step_id()

        # Update step name
        original_name = original_step.get(
            "name",
            original_step.get("type", "Unknown Step")
        )

        duplicated_step["name"] = (
            f"{original_name} (Copy)"
        )

        # Insert immediately after original step
        new_row = row + 1

        self._sequence["steps"].insert(
            new_row,
            duplicated_step
        )

        self.refresh_step_list(new_row)

        self.emit_sequence_changed()

    # ==================================================
    # REMOVE STEP
    # ==================================================

    def remove_step(self):

        row = self.step_list.currentRow()

        if row < 0:
            return

        step = self._sequence["steps"][row]

        answer = QMessageBox.question(
            self,
            "Remove Workflow Step",
            f"Remove step '{step.get('name', step.get('id'))}'?"
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self._sequence["steps"].pop(row)

        selected_row = min(
            row,
            len(self._sequence["steps"]) - 1
        )

        self.refresh_step_list(selected_row)

        self.emit_sequence_changed()

    # ==================================================
    # MOVE STEP
    # ==================================================

    def move_step(self, direction):

        row = self.step_list.currentRow()

        if row < 0:
            return

        new_row = row + direction

        if not 0 <= new_row < len(self._sequence["steps"]):
            return

        steps = self._sequence["steps"]

        steps[row], steps[new_row] = (
            steps[new_row],
            steps[row]
        )

        self.refresh_step_list(new_row)

        self.emit_sequence_changed()

    # ==================================================
    # STEP SELECTION
    # ==================================================

    def on_step_selected(self, row):

        if self._loading:
            return

        if row < 0 or row >= len(self._sequence["steps"]):
            self.clear_properties()
            return

        step = self._sequence["steps"][row]

        self._loading = True

        self.step_id_edit.setText(
            str(step.get("id", ""))
        )

        self.step_name_edit.setText(
            str(step.get("name", ""))
        )

        self.step_type_label.setText(
            str(step.get("type", ""))
        )

        self.step_enabled_checkbox.setChecked(
            step.get("enabled", True)
        )

        self._loading = False

        self.set_properties_enabled(True)
        self.build_parameter_form(step)

    # ==================================================
    # UPDATE STEP
    # ==================================================

    def update_selected_step(self, *args):

        if self._loading:
            return

        row = self.step_list.currentRow()

        if row < 0:
            return

        step = self._sequence["steps"][row]

        new_id = self.step_id_edit.text().strip()

        if not new_id:

            QMessageBox.warning(
                self,
                "Invalid Step ID",
                "Step ID cannot be empty."
            )

            self.on_step_selected(row)
            return

        for index, other_step in enumerate(
            self._sequence["steps"]
        ):

            if index != row and other_step.get("id") == new_id:

                QMessageBox.warning(
                    self,
                    "Duplicate Step ID",
                    f"Step ID '{new_id}' already exists."
                )

                self.on_step_selected(row)
                return

        step["id"] = new_id

        step["name"] = (
            self.step_name_edit.text().strip()
        )

        step["enabled"] = (
            self.step_enabled_checkbox.isChecked()
        )

        self.refresh_step_list(row)

        self.emit_sequence_changed()

    # ==================================================
    # PROPERTY HELPERS
    # ==================================================

    def clear_properties(self):

        self._loading = True

        self.step_id_edit.clear()
        self.step_name_edit.clear()
        self.step_type_label.setText("-")
        self.step_enabled_checkbox.setChecked(False)

        self._loading = False

        self.set_properties_enabled(False)
        self.clear_parameter_form()
        self.apply_parameters_button.setEnabled(False)

    def set_properties_enabled(self, enabled):

        self.step_id_edit.setEnabled(enabled)
        self.step_name_edit.setEnabled(enabled)
        self.step_enabled_checkbox.setEnabled(enabled)

        self.duplicate_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.up_button.setEnabled(enabled)
        self.down_button.setEnabled(enabled)

    # ==================================================
    # SIGNAL
    # ==================================================

    def emit_sequence_changed(self):

        self.sequence_changed.emit(
            self.get_sequence()
        )
