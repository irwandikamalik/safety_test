
import copy
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QPlainTextEdit,
    QMessageBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QCheckBox,
    QDoubleSpinBox,
    QSpinBox,
    QScrollArea,
)

from app.services.config_service import ConfigService
from app.services.model_service import ModelService


class JsonFormEditor(QWidget):
    """
    Generic visual editor for nested JSON dictionaries.
    Supports string, boolean, integer, float, and nested objects.
    """

    configuration_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._original_data = {}
        self._widgets = {}

        self.build_ui()


    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.setStyleSheet("""
            QWidget {
                background-color: #F3F5F8;
                color: #263449;
            }
        """)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #F3F5F8;
                border: none;
            }

            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #F3F5F8;
            }
        """)

        self.form_container = QWidget()
        self.form_container.setObjectName("ModelFormContainer")
        self.form_container.setStyleSheet("""
            QWidget#ModelFormContainer {
                background-color: #F3F5F8;
            }

            QGroupBox {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #DFE5EC;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
            }

            QLabel {
                background-color: transparent;
                color: #263449;
            }

            QLineEdit,
            QSpinBox,
            QDoubleSpinBox {
                background-color: #FFFFFF;
                color: #263449;
                border: 1px solid #CCD5E0;
                border-radius: 6px;
                padding: 6px;
            }

            QCheckBox {
                background-color: transparent;
                color: #263449;
            }
        """)

        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.scroll_area.setWidget(self.form_container)

        root.addWidget(self.scroll_area)

    def clear_form(self):

        while self.form_layout.count():

            item = self.form_layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

        self._widgets.clear()

    def set_configuration(self, configuration):

        self._original_data = copy.deepcopy(configuration)

        self.clear_form()

        if not isinstance(configuration, dict):
            return

        self._build_form(
            configuration,
            self.form_layout,
            ()
        )

    def _build_form(self, data, layout, parent_path):

        for key, value in data.items():

            current_path = parent_path + (key,)

            if isinstance(value, dict):

                group = QGroupBox(
                    key.replace("_", " ").title()
                )

                group_layout = QFormLayout(group)

                self._build_form(
                    value,
                    group_layout,
                    current_path
                )

                layout.addRow(group)

            elif isinstance(value, bool):

                widget = QCheckBox()
                widget.setChecked(value)

                widget.stateChanged.connect(
                    self.emit_configuration_changed
                )

                self._widgets[current_path] = widget

                layout.addRow(
                    key.replace("_", " ").title(),
                    widget
                )

            elif isinstance(value, int):

                widget = QSpinBox()
                widget.setRange(-2147483647, 2147483647)
                widget.setValue(value)

                widget.valueChanged.connect(
                    self.emit_configuration_changed
                )

                self._widgets[current_path] = widget

                layout.addRow(
                    key.replace("_", " ").title(),
                    widget
                )

            elif isinstance(value, float):

                widget = CleanDoubleSpinBox()
                widget.setRange(-1000000000000, 1000000000000)
                widget.setDecimals(6)
                widget.setMinimum(0)
                widget.setValue(value)
                widget.setKeyboardTracking(False)

                widget.valueChanged.connect(
                    self.emit_configuration_changed
                )

                self._widgets[current_path] = widget

                layout.addRow(
                    key.replace("_", " ").title(),
                    widget
                )

            elif isinstance(value, str):

                widget = QLineEdit(value)

                widget.textChanged.connect(
                    self.emit_configuration_changed
                )

                self._widgets[current_path] = widget

                layout.addRow(
                    key.replace("_", " ").title(),
                    widget
                )

            else:

                # Unsupported values remain in the original JSON.
                continue

    def get_configuration(self):

        configuration = copy.deepcopy(
            self._original_data
        )

        for path, widget in self._widgets.items():

            target = configuration

            for key in path[:-1]:
                target = target[key]

            key = path[-1]

            if isinstance(widget, QCheckBox):
                value = widget.isChecked()

            elif isinstance(widget, QSpinBox):
                value = widget.value()

            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()

            elif isinstance(widget, QLineEdit):
                value = widget.text()

            else:
                continue

            target[key] = value

        return configuration

    def emit_configuration_changed(self, *args):

        self.configuration_changed.emit(
            self.get_configuration()
        )

class CleanDoubleSpinBox(QDoubleSpinBox):

    def textFromValue(self, value):
        return f"{value:g}"


class ModelConfigurationPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_service = ConfigService()
        self.model_service = ModelService()

        self.current_model_id = None
        self._previous_model_id = None

        self._syncing = False
        self._sources = {
            "model": "advanced",
            "parameters": "advanced",
        }

        self._dirty = False

        self.build_ui()
        self.refresh_model_list()

    # ==========================================
    # USER INTERFACE
    # ==========================================

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 8, 20, 8)
        root.setSpacing(10)

        # HEADER

        header = QHBoxLayout()

        title = QLabel("Model Configuration")
        title.setStyleSheet(
            "font-size: 14pt; font-weight: 600;"
        )

        header.addWidget(title)
        header.addStretch()

        root.addLayout(header)

        # MODEL SELECTOR

        selector_layout = QHBoxLayout()

        selector_label = QLabel("Select Model")

        self.model_selector = QComboBox()
        self.model_selector.setMinimumWidth(260)

        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.model_selector)
        selector_layout.addStretch()

        root.addLayout(selector_layout)

        # MAIN TABS

        self.tabs = QTabWidget()

        self.model_tab = self.create_configuration_tab(
            "model"
        )

        self.parameters_tab = self.create_configuration_tab(
            "parameters"
        )

        self.tabs.addTab(
            self.model_tab["widget"],
            "Model Information"
        )

        self.tabs.addTab(
            self.parameters_tab["widget"],
            "Test Parameters"
        )

        # SAVE BUTTON

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setMinimumSize(100, 32)

        self.save_button.clicked.connect(
            self.save_configuration
        )

        self.tabs.setCornerWidget(
            self.save_button,
            Qt.Corner.TopRightCorner
        )

        root.addWidget(self.tabs, 1)

        # SIGNALS

        self.model_selector.currentIndexChanged.connect(
            self.on_model_changed
        )

    def create_configuration_tab(self, configuration_type):

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()

        visual_editor = JsonFormEditor()

        json_editor = QPlainTextEdit()
        json_editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        tabs.addTab(
            visual_editor,
            "Visual Editor"
        )

        tabs.addTab(
            json_editor,
            "Advanced JSON"
        )

        layout.addWidget(tabs)

        visual_editor.configuration_changed.connect(
            lambda configuration, key=configuration_type:
            self.on_visual_changed(key, configuration)
        )

        json_editor.textChanged.connect(
            lambda key=configuration_type:
            self.on_advanced_changed(key)
        )

        return {
            "widget": container,
            "tabs": tabs,
            "visual": visual_editor,
            "json": json_editor,
        }

    # ==========================================
    # MODEL DISCOVERY
    # ==========================================

    def refresh_model_list(self):

        selected_model = self.current_model_id

        self._syncing = True

        try:

            self.model_selector.clear()

            models = self.model_service.discover_models()

            for model in models:

                model_id = model["model_id"]
                model_name = model.get(
                    "model_name",
                    model_id
                )

                self.model_selector.addItem(
                    f"{model_id} - {model_name}",
                    model_id
                )

            index = self.model_selector.findData(
                selected_model
            )

            if index < 0 and self.model_selector.count() > 0:
                index = 0

            self.model_selector.setCurrentIndex(index)

        finally:
            self._syncing = False

        if self.model_selector.currentIndex() >= 0:

            self.load_model_configuration(
                self.model_selector.currentData()
            )

    # ==========================================
    # MODEL SELECTION
    # ==========================================

    def on_model_changed(self, index):

        if self._syncing or index < 0:
            return

        new_model_id = self.model_selector.itemData(index)

        if new_model_id == self.current_model_id:
            return

        if self._dirty:

            answer = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes.\n\n"
                "Do you want to save them before switching models?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if answer == QMessageBox.StandardButton.Cancel:

                self._syncing = True

                old_index = self.model_selector.findData(
                    self.current_model_id
                )

                self.model_selector.setCurrentIndex(
                    old_index
                )

                self._syncing = False
                return

            if answer == QMessageBox.StandardButton.Save:

                if not self.save_configuration():
                    self._syncing = True

                    old_index = self.model_selector.findData(
                        self.current_model_id
                    )

                    self.model_selector.setCurrentIndex(
                        old_index
                    )

                    self._syncing = False
                    return

        self.load_model_configuration(new_model_id)

    # ==========================================
    # LOAD CONFIGURATION
    # ==========================================

    def get_configuration_path(self, configuration_type):

        filename = (
            "model.json"
            if configuration_type == "model"
            else "parameters.json"
        )

        return (
            f"models/{self.current_model_id}/{filename}"
        )

    def load_model_configuration(self, model_id):

        if not model_id:
            return

        self.current_model_id = model_id
        self._previous_model_id = model_id

        self._syncing = True

        try:

            for configuration_type, tab in (
                ("model", self.model_tab),
                ("parameters", self.parameters_tab),
            ):

                path = self.get_configuration_path(
                    configuration_type
                )

                content = self.config_service.read_config(path)

                configuration = json.loads(content)

                if not isinstance(configuration, dict):
                    raise ValueError(
                        f"{path} must contain a JSON object."
                    )

                tab["json"].setPlainText(
                    json.dumps(
                        configuration,
                        indent=4,
                        ensure_ascii=False
                    )
                )

                tab["visual"].set_configuration(
                    configuration
                )

                tab["json"].document().setModified(False)

                self._sources[configuration_type] = "advanced"

            self._dirty = False

        except Exception as error:

            QMessageBox.critical(
                self,
                "Model Configuration Load Error",
                str(error)
            )

        finally:
            self._syncing = False

    # ==========================================
    # VISUAL -> JSON
    # ==========================================

    def on_visual_changed(self, configuration_type, configuration):

        if self._syncing:
            return

        self._sources[configuration_type] = "visual"
        self._dirty = True

        tab = self.get_tab(configuration_type)

        self._syncing = True

        try:

            tab["json"].setPlainText(
                json.dumps(
                    configuration,
                    indent=4,
                    ensure_ascii=False
                )
            )

            tab["json"].document().setModified(True)

        finally:
            self._syncing = False

    # ==========================================
    # JSON -> VISUAL
    # ==========================================

    def on_advanced_changed(self, configuration_type):

        if self._syncing:
            return

        self._sources[configuration_type] = "advanced"
        self._dirty = True

        tab = self.get_tab(configuration_type)

        try:

            configuration = json.loads(
                tab["json"].toPlainText()
            )

            if not isinstance(configuration, dict):
                return

            self._syncing = True

            tab["visual"].set_configuration(
                configuration
            )

        except (json.JSONDecodeError, ValueError, TypeError):
            # Keep incomplete JSON in Advanced JSON.
            pass

        finally:
            self._syncing = False

    # ==========================================
    # GET CURRENT CONFIGURATION
    # ==========================================

    def get_tab(self, configuration_type):

        return (
            self.model_tab
            if configuration_type == "model"
            else self.parameters_tab
        )

    def get_current_configuration(self, configuration_type):

        tab = self.get_tab(configuration_type)

        if self._sources[configuration_type] == "visual":

            return tab["visual"].get_configuration()

        configuration = json.loads(
            tab["json"].toPlainText()
        )

        if not isinstance(configuration, dict):
            raise ValueError(
                f"{configuration_type} configuration "
                "must be a JSON object."
            )

        return configuration

    # ==========================================
    # VALIDATION
    # ==========================================

    def validate_configurations(self, model, parameters):

        if model.get("model_id") != self.current_model_id:
            raise ValueError(
                "Model ID in model.json does not match "
                "the selected model."
            )

        if not isinstance(model.get("model_name"), str) or not model["model_name"].strip():
            raise ValueError(
                "Model name cannot be empty."
            )

        if not isinstance(model.get("description"), str):
            raise ValueError(
                "Model description must be a string."
            )

        if not isinstance(model.get("enabled"), bool):
            raise ValueError(
                "Model enabled must be a boolean."
            )

        version = model.get("version")

        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
        ):
            raise ValueError(
                "Model version must be a positive integer."
            )

        if parameters.get("model_id") != self.current_model_id:
            raise ValueError(
                "Model ID in parameters.json does not match "
                "the selected model."
            )

        if not isinstance(
            parameters.get("hardware_approved"), bool
        ):
            raise ValueError(
                "hardware_approved must be a boolean."
            )

        if parameters.get("configuration_status") not in (
            "DRAFT",
            "APPROVED",
            "REJECTED",
        ):
            raise ValueError(
                "Invalid configuration_status."
            )

        test_parameters = parameters.get("test_parameters")

        if not isinstance(test_parameters, dict) or not test_parameters:
            raise ValueError(
                "test_parameters must be a non-empty object."
            )

        for function, values in test_parameters.items():

            if not isinstance(values, dict):
                raise ValueError(
                    f"Test parameters for {function} must be an object."
                )

    # ==========================================
    # SAVE CONFIGURATION
    # ==========================================

    def save_configuration(self):

        try:

            if not self.current_model_id:
                raise ValueError(
                    "No model is selected."
                )

            model = self.get_current_configuration("model")

            parameters = self.get_current_configuration(
                "parameters"
            )

            self.validate_configurations(
                model,
                parameters
            )

            model_path = self.get_configuration_path("model")
            parameters_path = self.get_configuration_path("parameters")

            # Save each file using ConfigService.
            # ConfigService creates a backup by default.

            self.config_service.save_json(
                model_path,
                model
            )

            self.config_service.save_json(
                parameters_path,
                parameters
            )

            self._syncing = True

            try:

                for configuration_type, configuration in (
                    ("model", model),
                    ("parameters", parameters),
                ):

                    tab = self.get_tab(configuration_type)

                    content = json.dumps(
                        configuration,
                        indent=4,
                        ensure_ascii=False
                    )

                    tab["json"].setPlainText(content)

                    tab["visual"].set_configuration(
                        configuration
                    )

                    tab["json"].document().setModified(False)

                    self._sources[configuration_type] = "advanced"

            finally:
                self._syncing = False

            self._dirty = False

            QMessageBox.information(
                self,
                "Configuration Saved",
                "Model configuration saved successfully.\n\n"
                "Backups of the previous configuration were created."
            )

            return True

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save Error",
                str(error)
            )

            return False
