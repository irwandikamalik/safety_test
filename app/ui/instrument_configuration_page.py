
import json

from PySide6.QtCore import Qt, QLocale

from PySide6.QtGui import QDoubleValidator

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QTabWidget,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
    QComboBox,
    QScrollArea,
    QFrame,
)


from app.services.config_service import ConfigService
from app.instruments.simulation_instrument import SimulationInstrument
from app.instruments.driver_registry import DriverRegistry
from app.services.model_service import ModelService


class InstrumentConfigurationPage(QWidget):

    CATALOG_PATH = "global/instrument_catalog.json"

    TEST_FUNCTION_LABELS = {
        "acw": "ACW — AC Hipot Test",
        "ecac": "ECAC — Ground Bond Test (AC)",
        "ecdc": "ECDC — Ground Bond Test (DC)",
    }

    def parameter_configuration_path(self):

        if not self.current_model_id:
            raise ValueError("No model selected.")

        return (
            f"models/{self.current_model_id}/parameters.json"
        )

    def model_configuration_path(self):

        if not self.current_model_id:
            raise ValueError("No model selected.")

        return (
            f"models/{self.current_model_id}/instruments.json"
        )

    def __init__(self, parent=None):

        super().__init__(parent)

        self.service = ConfigService()
        self.model_service = ModelService()
        self.driver_registry = DriverRegistry()

        self.measurement_checks = {}
        self.function_checks = {}
        self.parameter_inputs = {}
        self.parameter_form_dirty = False
        self.current_instrument_id = None
        self.current_model_id = None
        self.loading_configuration = False
        self.form_dirty = False

        self.build_ui()
        self.load_configuration()

    # ==========================================
    # USER INTERFACE
    # ==========================================

    def build_ui(self):

        # MAIN PAGE LAYOUT
        page_layout = QVBoxLayout(self)

        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # SCROLL AREA
        scroll_area = QScrollArea()

        scroll_area.setObjectName(
            "InstrumentConfigurationScrollArea"
        )

        scroll_area.setWidgetResizable(True)

        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # SCROLL CONTENT
        content_widget = QWidget()

        content_widget.setObjectName(
            "InstrumentConfigurationContent"
        )

        root = QVBoxLayout(content_widget)

        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        
        
        heading = QLabel("Instrument Configuration")
        heading.setObjectName("PageTitle")

        subtitle = QLabel(
            "Manage global instrument connections and "
            "model-specific measurement settings."
        )
        subtitle.setObjectName("Muted")

        root.addWidget(heading)
        root.addWidget(subtitle)


        # MODEL SELECTOR

        model_selector_group = QGroupBox("Model Selection")
        model_selector_layout = QFormLayout(
            model_selector_group
        )

        self.model_selector = QComboBox()

        self.model_selector.currentIndexChanged.connect(
            self.on_model_changed
        )

        model_selector_layout.addRow(
            "Available Model:",
            self.model_selector
        )

        root.addWidget(model_selector_group)


        # INSTRUMENT SELECTOR

        selector_group = QGroupBox("Instrument Selection")
        selector_layout = QFormLayout(selector_group)

        self.instrument_selector = QComboBox()

        self.instrument_selector.currentIndexChanged.connect(
            self.on_instrument_changed
        )

        selector_layout.addRow(
            "Available Instrument:",
            self.instrument_selector
        )

        root.addWidget(selector_group)

        # CONNECTION CONFIGURATION

        self.connection_group = QGroupBox(
            "Global Connection Configuration"
        )

        connection_layout = QFormLayout(
            self.connection_group
        )

        self.interface_input = QComboBox()

        self.interface_input.addItems([
            "USB",
            "SERIAL",
            "GPIB",
            "TCPIP"
        ])
        self.interface_input.currentTextChanged.connect(
           self.on_interface_changed
        )

        self.resource_input = QLineEdit()
        self.resource_input.setPlaceholderText(
            "USB0::...::INSTR or GPIB0::...::INSTR"
        )

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("COM4")

        self.baudrate_input = QSpinBox()
        self.baudrate_input.setRange(300, 2000000)
        self.baudrate_input.setValue(9600)

        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(100, 120000)
        self.timeout_input.setValue(5000)
        self.timeout_input.setSuffix(" ms")

        # Track unsaved connection changes.
        self.interface_input.currentTextChanged.connect(
            self.mark_form_dirty
        )

        self.resource_input.textChanged.connect(
            self.mark_form_dirty
        )

        self.port_input.textChanged.connect(
            self.mark_form_dirty
        )

        self.baudrate_input.valueChanged.connect(
            self.mark_form_dirty
        )

        self.timeout_input.valueChanged.connect(
            self.mark_form_dirty
        )

        connection_layout.addRow(
            "Interface:",
            self.interface_input
        )

        connection_layout.addRow(
            "VISA Resource:",
            self.resource_input
        )

        connection_layout.addRow(
            "Serial Port:",
            self.port_input
        )

        connection_layout.addRow(
            "Baudrate:",
            self.baudrate_input
        )

        connection_layout.addRow(
            "Timeout:",
            self.timeout_input
        )

        root.addWidget(self.connection_group)

        # MODEL-SPECIFIC CONFIGURATION

        self.model_group = QGroupBox(
            "Model Measurement Configuration"
        )

        model_layout = QVBoxLayout(self.model_group)

        self.element_input = QSpinBox()
        self.element_input.setRange(1, 3)
        self.element_input.setValue(1)
        self.element_input.valueChanged.connect(
            self.mark_form_dirty
        )

        element_layout = QFormLayout()

        element_layout.addRow(
            "Measurement Element:",
            self.element_input
        )

        model_layout.addLayout(element_layout)

        # TEST FUNCTION SELECTION

        self.function_group = QGroupBox(
            "Available Test Functions"
        )

        self.function_container = QVBoxLayout(
            self.function_group
        )

        model_layout.addWidget(self.function_group)

        # MEASUREMENT SELECTION

        self.measurement_group = QGroupBox(
            "Available Measurements"
        )

        self.measurement_container = QVBoxLayout(
            self.measurement_group
        )

        model_layout.addWidget(self.measurement_group)

        # TEST PARAMETER CONFIGURATION

        self.parameter_group = QGroupBox(
            "Test Parameter Configuration"
        )

        parameter_layout = QVBoxLayout(
            self.parameter_group
        )

        self.parameter_tabs = QTabWidget()

        parameter_layout.addWidget(
            self.parameter_tabs
        )

        self.parameter_container = {}

        self.build_parameter_forms()

        model_layout.addWidget(
            self.parameter_group
        )

        root.addWidget(self.model_group)

        # ACTION BUTTONS

        action_layout = QHBoxLayout()

        self.save_button = QPushButton(
            "Save Settings"
        )

        self.save_button.setObjectName(
            "PrimaryButton"
        )

        self.connection_button = QPushButton(
            "Test Connection"
        )

        self.read_button = QPushButton(
            "Read Measurement"
        )

        self.simulation_button = QPushButton(
            "Simulation Preview"
        )

        self.save_button.clicked.connect(
            lambda: self.save_settings()
        )

        self.connection_button.clicked.connect(
            self.test_connection
        )

        self.read_button.clicked.connect(
            self.read_measurement
        )

        self.simulation_button.clicked.connect(
            self.simulation_preview
        )

        action_layout.addWidget(self.save_button)
        action_layout.addWidget(self.connection_button)
        action_layout.addWidget(self.read_button)
        action_layout.addWidget(self.simulation_button)

        root.addLayout(action_layout)

        # MEASUREMENT RESULTS

        result_group = QGroupBox(
            "Measurement Results"
        )

        result_layout = QVBoxLayout(result_group)

        self.result_table = QTableWidget(0, 3)
        self.result_table.setMinimumHeight(400)

        self.result_table.setHorizontalHeaderLabels([
            "Measurement",
            "Value",
            "Unit"
        ])

        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.result_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        result_layout.addWidget(self.result_table)

        # ADVANCED JSON EDITOR

        json_group = QGroupBox(
            "Advanced JSON Configuration"
        )

        json_layout = QVBoxLayout(json_group)

        self.json_tabs = QTabWidget()

        self.catalog_editor = QPlainTextEdit()
        self.catalog_editor.setMinimumHeight(800)
        self.model_editor = QPlainTextEdit()
        self.model_editor.setMinimumHeight(800)
        self.parameter_editor = QPlainTextEdit()
        self.parameter_editor.setMinimumHeight(800)

        self.catalog_editor.setLineWrapMode(
            QPlainTextEdit.NoWrap
        )

        self.model_editor.setLineWrapMode(
            QPlainTextEdit.NoWrap
        )

        self.json_tabs.addTab(
            self.catalog_editor,
            "Global Catalog"
        )

        self.json_tabs.addTab(
            self.model_editor,
            "Model Mapping"
        )

        self.json_tabs.addTab(
            self.parameter_editor,
            "Test Parameters"
        )

        json_layout.addWidget(self.json_tabs)

        json_buttons = QHBoxLayout()

        reload_button = QPushButton("Reload JSON")
        format_button = QPushButton("Format JSON")
        validate_button = QPushButton("Validate JSON")
        save_json_button = QPushButton("Save JSON")

        reload_button.clicked.connect(
            self.load_configuration
        )

        format_button.clicked.connect(
            self.format_json
        )

        validate_button.clicked.connect(
            self.validate_json
        )

        save_json_button.clicked.connect(
            self.save_json
        )

        json_buttons.addWidget(reload_button)
        json_buttons.addWidget(format_button)
        json_buttons.addWidget(validate_button)

        json_buttons.addStretch()

        json_buttons.addWidget(save_json_button)

        json_layout.addLayout(json_buttons)

        # Measurement Results
        root.addWidget(result_group, 2)

        # Advanced JSON Configuration
        root.addWidget(json_group, 3)

        # Scroll Content
        scroll_area.setWidget(content_widget)

        page_layout.addWidget(scroll_area)


    def on_interface_changed(self, interface):

        is_serial = interface.upper() == "SERIAL"

        self.port_input.setEnabled(is_serial)
        self.baudrate_input.setEnabled(is_serial)

        self.resource_input.setEnabled(not is_serial)


    # ==========================================
    # MODEL SELECTION
    # ==========================================

    def load_model_list(self):

        models = self.model_service.discover_models()

        self.model_selector.blockSignals(True)
        self.model_selector.clear()

        for model in models:

            model_id = model["model_id"]
            model_name = model["model_name"]

            self.model_selector.addItem(
                f"{model_id} - {model_name}",
                model_id
            )

        if models:
            self.model_selector.setCurrentIndex(0)

        self.model_selector.blockSignals(False)

        if not models:

            self.current_model_id = None

            QMessageBox.warning(
                self,
                "No Models Found",
                "No model configuration was found."
            )

            return

        self.current_model_id = (
            self.model_selector.currentData()
        )

    def refresh_model_list(self):

        models = self.model_service.discover_models()

        previous_model_id = self.current_model_id

        self.model_selector.blockSignals(True)
        self.model_selector.clear()

        for model in models:

            model_id = model["model_id"]
            model_name = model["model_name"]

            self.model_selector.addItem(
                f"{model_id} - {model_name}",
                model_id
            )

        if not models:

            self.model_selector.blockSignals(False)

            QMessageBox.warning(
                self,
                "No Models Found",
                "No model configuration was found."
            )

            return

        # Pertahankan model yang sebelumnya dipilih.
        selected_index = self.model_selector.findData(
            previous_model_id
        )

        if selected_index < 0:
            selected_index = 0

        self.model_selector.setCurrentIndex(selected_index)
        self.model_selector.blockSignals(False)

        selected_model_id = self.model_selector.currentData()

        # Model yang aktif tidak berubah.
        # Tidak perlu memuat ulang editor.
        if selected_model_id == previous_model_id:
            return

        # Model sebelumnya sudah tidak tersedia.
        if not self.confirm_model_switch():

            self.model_selector.blockSignals(True)

            previous_index = self.model_selector.findData(
                previous_model_id
            )

            if previous_index >= 0:
                self.model_selector.setCurrentIndex(
                    previous_index
                )

            self.model_selector.blockSignals(False)

            return

        self.current_model_id = selected_model_id

        self.load_model_configuration()

    def on_model_changed(self, index):

        if index < 0:
            return

        new_model_id = self.model_selector.currentData()

        if new_model_id == self.current_model_id:
            return

        if not self.confirm_model_switch():

            self.model_selector.blockSignals(True)

            previous_index = self.model_selector.findData(
                self.current_model_id
            )

            self.model_selector.setCurrentIndex(
                previous_index
            )

            self.model_selector.blockSignals(False)

            return

        self.current_model_id = new_model_id

        self.load_model_configuration()

    def confirm_model_switch(self):

        catalog_modified = (
            self.catalog_editor.document().isModified()
        )

        model_modified = (
            self.model_editor.document().isModified()
        )

        parameter_modified = (
            self.parameter_editor.document().isModified()
        )

        has_unsaved_changes = (
            catalog_modified
            or model_modified
            or parameter_modified
            or self.form_dirty
        )

        if not has_unsaved_changes:
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            "There are unsaved configuration changes.\n\n"
            "Do you want to save before switching models?",
            QMessageBox.Save
            | QMessageBox.Discard
            | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if answer == QMessageBox.Save:

            return self.save_settings(
                show_message=False
            )

        if answer == QMessageBox.Discard:
            return True

        return False
    
    def save_json_before_switch(self):

        catalog_modified = (
            self.catalog_editor.document().isModified()
        )

        model_modified = (
            self.model_editor.document().isModified()
        )

        if catalog_modified:

            if not self.save_editor(
                self.catalog_editor,
                self.CATALOG_PATH
            ):
                return False

        if model_modified:

            if not self.save_editor(
                self.model_editor,
                self.model_configuration_path()
            ):
                return False

        return True

    def load_model_configuration(self):

        try:

            path = self.model_configuration_path()

            self.loading_configuration = True

            self.model_editor.setPlainText(
                self.service.read_config(path)
            )

            self.model_editor.document().setModified(False)

            parameter_text = self.service.read_config(
                self.parameter_configuration_path()
            )

            self.parameter_editor.setPlainText(
                parameter_text
            )

            self.parameter_editor.document().setModified(False)

            parameter_data = json.loads(parameter_text)

            self.load_parameter_controls(
                parameter_data
            )

            self.json_tabs.setTabText(
                1,
                f"{self.current_model_id} Mapping"
            )

            self.model_group.setTitle(
                f"{self.current_model_id} Measurement Configuration"
            )

            self.refresh_instrument_list()
            self.form_dirty = False
            self.parameter_form_dirty = False

            self.loading_configuration = False

        except Exception as error:

            self.loading_configuration = False

            QMessageBox.critical(
                self,
                "Model Configuration Error",
                str(error)
            )


    # ==========================================
    # JSON CONFIGURATION
    # ==========================================

    def get_catalog_data(self):

        return json.loads(
            self.catalog_editor.toPlainText()
        )

    def get_model_data(self):

        return json.loads(
            self.model_editor.toPlainText()
        )

    def get_catalog_entries(self):

        data = self.get_catalog_data()

        instruments = data.get(
            "instruments", {}
        )

        if not isinstance(instruments, dict):
            raise ValueError(
                "Global instrument catalog must be an object."
            )

        return instruments

    def get_model_instruments(self):

        data = self.get_model_data()

        instruments = data.get(
            "instruments", {}
        )

        if not isinstance(instruments, dict):
            raise ValueError(
                "Model instruments must be an object."
            )

        return instruments

    def get_model_entry(self, catalog_id):

        model_instruments = self.get_model_instruments()

        for instrument_id, entry in model_instruments.items():

            if not isinstance(entry, dict):
                continue

            if entry.get("catalog_id") == catalog_id:
                return instrument_id, entry

        return None, None


    def load_configuration(self):

        try:

            self.loading_configuration = True

            self.catalog_editor.setPlainText(
                self.service.read_config(
                    self.CATALOG_PATH
                )
            )

            self.catalog_editor.document().setModified(False)

            self.loading_configuration = False

            self.load_model_list()

            if self.current_model_id:
                self.load_model_configuration()

        except Exception as error:

            self.loading_configuration = False

            QMessageBox.critical(
                self,
                "Configuration Error",
                str(error)
            )

    # ==========================================
    # INSTRUMENT SELECTION
    # ==========================================

    def refresh_instrument_list(self):

        self.instrument_selector.blockSignals(True)

        self.instrument_selector.clear()

        instruments = self.get_catalog_entries()

        for catalog_id, configuration in instruments.items():

            name = configuration.get(
                "name",
                catalog_id
            )

            self.instrument_selector.addItem(
                name,
                catalog_id
            )

        self.instrument_selector.blockSignals(False)

        if self.instrument_selector.count():

            self.instrument_selector.setCurrentIndex(0)

            self.on_instrument_changed(0)

    def current_catalog_id(self):

        return self.instrument_selector.currentData()

    def current_instrument_configuration(self):

        catalog_id = self.current_catalog_id()

        if not catalog_id:
            raise ValueError(
                "No instrument selected."
            )

        catalog = self.get_catalog_entries().get(
            catalog_id
        )

        if not isinstance(catalog, dict):
            raise ValueError(
                f"Instrument not found: {catalog_id}"
            )

        return catalog_id, catalog

    def on_instrument_changed(self, index):

        if index < 0:
            return

        try:

            catalog_id, catalog = (
                self.current_instrument_configuration()
            )

            self.current_instrument_id = catalog_id

            self.loading_configuration = True

            self.refresh_connection_controls(catalog)

            self.refresh_measurement_controls(
                catalog_id,
                catalog
            )

            self.loading_configuration = False

            self.form_dirty = False

            self.result_table.setRowCount(0)

            driver = catalog.get("driver", "")

            self.connection_button.setEnabled(
                driver in self.driver_registry.available_drivers()
                and driver != "simulation"
            )

            self.read_button.setEnabled(
                driver == "generic_scpi"
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Instrument Configuration",
                str(error)
            )

    # ==========================================
    # GLOBAL CONNECTION SETTINGS
    # ==========================================

    def refresh_connection_controls(self, catalog):

        connection = catalog.get(
            "connection", {}
        )

        interface = connection.get(
            "interface",
            "USB"
        ).upper()

        index = self.interface_input.findText(
            interface
        )

        if index >= 0:
            self.interface_input.setCurrentIndex(index)

        self.resource_input.setText(
            connection.get("resource", "")
        )

        self.port_input.setText(
            connection.get("port", "")
        )

        self.baudrate_input.setValue(
            int(connection.get("baudrate", 9600))
        )

        self.timeout_input.setValue(
            int(connection.get("timeout", 5000))
        )

        is_serial = interface == "SERIAL"

        self.port_input.setEnabled(is_serial)
        self.baudrate_input.setEnabled(is_serial)
        self.resource_input.setEnabled(not is_serial)

    def mark_form_dirty(self, *args):

        if not self.loading_configuration:
            self.form_dirty = True

    # ==========================================
    # MODEL MEASUREMENT SETTINGS
    # ==========================================

    def clear_function_controls(self):

        while self.function_container.count():

            item = self.function_container.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.function_checks.clear()


    def clear_measurement_controls(self):

        while self.measurement_container.count():

            item = self.measurement_container.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.measurement_checks.clear()

    def refresh_measurement_controls(
        self,
        catalog_id,
        catalog
    ):

        self.clear_function_controls()
        self.clear_measurement_controls()

        instrument_id, model_entry = self.get_model_entry(
            catalog_id
        )

        enabled = (
            model_entry is not None
            and model_entry.get("enabled") is True
        )

        self.model_group.setEnabled(enabled)

        if not enabled:

            self.function_group.setVisible(False)
            self.measurement_group.setVisible(False)

            self.measurement_container.addWidget(
                QLabel(
                    "This instrument is not enabled "
                    f"for {self.current_model_id}."
                )
            )

            self.parameter_group.setVisible(False)

            return

        overrides = model_entry.get(
            "overrides", {}
        )

        self.element_input.setValue(
            int(overrides.get("element", 1))
        )

        # ======================================
        # TOS9302 TEST FUNCTIONS
        # ======================================

        supported_functions = catalog.get(
            "supported_functions", []
        )

        available_functions = [
            function_id
            for function_id in self.TEST_FUNCTION_LABELS
            if function_id in supported_functions
        ]

        selected_functions = overrides.get(
            "selected_functions",
            available_functions
        )

        self.function_group.setVisible(
            bool(available_functions)
        )

        self.parameter_group.setVisible(
            bool(available_functions)
        )

        for function_id in available_functions:

            checkbox = QCheckBox(
                self.TEST_FUNCTION_LABELS[function_id]
            )

            checkbox.setChecked(
                function_id in selected_functions
            )

            checkbox.toggled.connect(
                self.mark_form_dirty
            )

            self.function_container.addWidget(
                checkbox
            )

            self.function_checks[
                function_id
            ] = checkbox

        # ======================================
        # WT310E MEASUREMENTS
        # ======================================

        definitions = catalog.get(
            "measurements", {}
        )

        selected_measurements = overrides.get(
            "selected_measurements",
            list(definitions.keys())
        )

        self.measurement_group.setVisible(
            bool(definitions)
        )

        for measurement_id, definition in definitions.items():

            name = definition.get(
                "name",
                measurement_id
            )

            unit = definition.get(
                "unit",
                ""
            )

            checkbox = QCheckBox(
                f"{name} ({unit})"
            )

            checkbox.setChecked(
                measurement_id in selected_measurements
            )

            checkbox.toggled.connect(
                self.mark_form_dirty
            )

            self.measurement_container.addWidget(
                checkbox
            )

            self.measurement_checks[
                measurement_id
            ] = checkbox

        # ======================================
        # EMPTY CONFIGURATION
        # ======================================

        if (
            not available_functions
            and not definitions
        ):

            self.measurement_group.setVisible(True)

            self.measurement_container.addWidget(
                QLabel(
                    "No measurement or test function "
                    "definitions available for this instrument."
                )
            )


    def selected_functions(self):

        return [
            function_id
            for function_id, checkbox
            in self.function_checks.items()
            if checkbox.isChecked()
        ]

    def selected_measurements(self):

        return [
            measurement_id
            for measurement_id, checkbox
            in self.measurement_checks.items()
            if checkbox.isChecked()
        ]

    # ==========================================
    # SAVE CONFIGURATION
    # ==========================================

    def update_global_connection(self, catalog):

        connection = catalog.setdefault(
            "connection", {}
        )

        interface = self.interface_input.currentText().upper()

        connection["interface"] = interface
        connection["timeout"] = self.timeout_input.value()

        if interface == "SERIAL":

            port = self.port_input.text().strip()

            if not port:
                raise ValueError(
                    "Serial port cannot be empty."
                )

            connection["port"] = port
            connection["baudrate"] = (
                self.baudrate_input.value()
            )

            connection.pop("resource", None)

        else:

            resource = self.resource_input.text().strip()

            if not resource:
                raise ValueError(
                    "VISA Resource cannot be empty."
                )

            connection["resource"] = resource

            connection.pop("port", None)
            connection.pop("baudrate", None)

    def update_model_measurements(
        self,
        catalog_id,
        model_data
    ):

        instruments = model_data.setdefault(
            "instruments", {}
        )

        model_entry = None

        for entry in instruments.values():

            if (
                isinstance(entry, dict)
                and entry.get("catalog_id") == catalog_id
            ):

                model_entry = entry
                break

        if model_entry is None:

            raise ValueError(
                f"Instrument {catalog_id} is not mapped to "
                f"{self.current_model_id}."
            )

        catalog_data = self.get_catalog_data()

        catalog = catalog_data.get(
            "instruments", {}
        ).get(
            catalog_id, {}
        )

        definitions = catalog.get(
            "measurements", {}
        )

        supported_functions = catalog.get(
            "supported_functions", []
        )

        overrides = model_entry.setdefault(
            "overrides", {}
        )

        # Save TOS9302 test function selection.

        available_functions = [
            function_id
            for function_id in self.TEST_FUNCTION_LABELS
            if function_id in supported_functions
        ]

        if available_functions:

            overrides["selected_functions"] = (
                self.selected_functions()
            )

        # Save WT310E measurement selection.

        if definitions:

            selected = self.selected_measurements()

            if not selected:

                raise ValueError(
                    "Select at least one measurement."
                )

            overrides["selected_measurements"] = selected

            overrides["element"] = (
                self.element_input.value()
            )

    def save_settings(self, show_message=True):

        try:

            catalog_id, catalog = (
                self.current_instrument_configuration()
            )

            catalog_data = self.get_catalog_data()
            model_data = self.get_model_data()

            parameter_data = json.loads(
                self.parameter_editor.toPlainText()
            )

            if not isinstance(parameter_data, dict):
                raise ValueError(
                    "Parameter configuration must be a JSON object."
                )

            # Save global connection.
            self.update_global_connection(catalog)

            # Save instrument selection.
            self.update_model_measurements(
                catalog_id,
                model_data
            )

            # Save parameter form changes.
            if self.parameter_form_dirty:

                self.collect_parameter_controls(
                    parameter_data
                )

            catalog_data["instruments"][catalog_id] = catalog

            catalog_text = json.dumps(
                catalog_data,
                indent=4,
                ensure_ascii=False
            )

            model_text = json.dumps(
                model_data,
                indent=4,
                ensure_ascii=False
            )

            parameter_text = json.dumps(
                parameter_data,
                indent=4,
                ensure_ascii=False
            )

            # Persist global catalog.
            self.service.save_config(
                self.CATALOG_PATH,
                catalog_text
            )

            # Persist model instrument mapping.
            self.service.save_config(
                self.model_configuration_path(),
                model_text
            )

            # Persist model test parameters.
            self.service.save_config(
                self.parameter_configuration_path(),
                parameter_text
            )

            # Refresh editors.
            self.catalog_editor.setPlainText(
                catalog_text
            )

            self.model_editor.setPlainText(
                model_text
            )

            self.parameter_editor.setPlainText(
                parameter_text
            )

            self.catalog_editor.document().setModified(False)
            self.model_editor.document().setModified(False)
            self.parameter_editor.document().setModified(False)

            self.form_dirty = False
            self.parameter_form_dirty = False

            if show_message:

                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    "Global, model mapping, and test parameter "
                    "configurations saved successfully."
                )

            return True

        except Exception as error:

            if show_message:

                QMessageBox.critical(
                    self,
                    "Save Error",
                    str(error)
                )

            return False

    # ==========================================
    # BUILD DRIVER CONFIGURATION
    # ==========================================

    def build_driver_configuration(self):

        catalog_id, catalog = (
            self.current_instrument_configuration()
        )

        configuration = dict(catalog)

        _, model_entry = self.get_model_entry(
            catalog_id
        )

        if model_entry is not None:

            overrides = model_entry.get(
                "overrides", {}
            )

            configuration["selected_measurements"] = (
                overrides.get(
                    "selected_measurements", []
                )
            )

            configuration["element"] = (
                overrides.get("element", 1)
            )

        return configuration

    # ==========================================
    # HARDWARE DIAGNOSTICS
    # ==========================================


    def test_connection(self):

        if not self.save_settings(show_message=False):
            return

        instrument = None

        try:

            configuration = self.build_driver_configuration()

            driver_id = configuration.get("driver")

            instrument = self.driver_registry.create(
                driver_id,
                configuration
            )

            instrument.connect()

            if hasattr(instrument, "identify"):
                identity = instrument.identify()
            else:
                identity = "Simulation Instrument (No physical connection)"

            expected_name = configuration.get(
                "name", "Instrument"
            )

            QMessageBox.information(
                self,
                "Connection Successful",
                (
                    f"{expected_name} connected successfully.\n\n"
                    f"Identification:\n{identity}"
                )
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Connection Failed",
                str(error)
            )

        finally:

            if instrument is not None:

                try:
                    instrument.disconnect()
                except Exception:
                    pass

    def read_measurement(self):

        if not self.save_settings(show_message=False):
            return

        instrument = None

        try:

            configuration = self.build_driver_configuration()

            driver_id = configuration.get("driver")

            if driver_id != "generic_scpi":
                raise ValueError(
                    "Measurement reading is not supported "
                    "by this instrument driver."
                )

            selected = configuration.get(
                "selected_measurements", []
            )

            if not selected:
                raise ValueError(
                    "No measurements selected."
                )

            instrument = self.driver_registry.create(
                driver_id,
                configuration
            )

            instrument.connect()

            result = instrument.read_measurements({
                "measurements": [
                    {
                        "id": measurement_id,
                        **configuration["measurements"][measurement_id]
                    }
                    for measurement_id in selected
                ],
                "element": configuration.get("element", 1)
            })

            self.display_measurements(result)

        except Exception as error:

            QMessageBox.critical(
                self,
                "Measurement Error",
                str(error)
            )

        finally:

            if instrument is not None:

                try:
                    instrument.disconnect()
                except Exception:
                    pass

    # ==========================================
    # SIMULATION
    # ==========================================

    def simulation_preview(self):

        try:

            if not self.save_settings(show_message=False):
                return

            configuration = self.build_driver_configuration()

            selected = configuration.get(
                "selected_measurements", []
            )

            definitions = configuration.get(
                "measurements", {}
            )

            measurement_list = []

            for measurement_id in selected:

                definition = definitions.get(
                    measurement_id
                )

                if definition is None:
                    raise ValueError(
                        f"Unknown measurement: {measurement_id}"
                    )

                measurement_list.append({
                    "id": measurement_id,
                    **definition
                })

            if not measurement_list:
                raise ValueError(
                    "No measurement definitions selected."
                )

            instrument = SimulationInstrument(
                configuration
            )

            instrument.connect()

            try:

                result = instrument.read_measurements({
                    "measurements": measurement_list
                })

            finally:

                instrument.disconnect()

            self.display_measurements(result)

        except Exception as error:

            QMessageBox.critical(
                self,
                "Simulation Error",
                str(error)
            )

    # ==========================================
    # RESULT DISPLAY
    # ==========================================

    def display_measurements(self, result):

        measurements = result.get(
            "measurements", {}
        )

        self.result_table.setRowCount(
            len(measurements)
        )

        for row, (measurement_id, data) in enumerate(
            measurements.items()
        ):

            name = measurement_id.replace(
                "_", " "
            ).title()

            value = data.get("value")
            unit = data.get("unit", "")

            self.result_table.setItem(
                row,
                0,
                QTableWidgetItem(name)
            )

            self.result_table.setItem(
                row,
                1,
                QTableWidgetItem(str(value))
            )

            self.result_table.setItem(
                row,
                2,
                QTableWidgetItem(unit)
            )

        self.result_table.resizeRowsToContents()

    # ==========================================
    # ADVANCED JSON EDITOR
    # ==========================================

    def current_editor(self):

        index = self.json_tabs.currentIndex()

        if index == 0:
            return (
                self.catalog_editor,
                self.CATALOG_PATH
            )

        if index == 1:
            return (
                self.model_editor,
                self.model_configuration_path()
            )

        return (
            self.parameter_editor,
            self.parameter_configuration_path()
        )

    def format_json(self):

        editor, _ = self.current_editor()

        try:

            parsed = json.loads(
                editor.toPlainText()
            )

            editor.setPlainText(
                json.dumps(
                    parsed,
                    indent=4,
                    ensure_ascii=False
                )
            )

        except json.JSONDecodeError as error:

            QMessageBox.warning(
                self,
                "Invalid JSON",
                f"Line {error.lineno}: {error.msg}"
            )

    def validate_json(self):

        editor, _ = self.current_editor()

        valid, message = self.service.validate_json(
            editor.toPlainText()
        )

        if valid:

            QMessageBox.information(
                self,
                "JSON Validation",
                message
            )

        else:

            QMessageBox.warning(
                self,
                "JSON Validation Error",
                message
            )


    def save_editor(self, editor, path):

        valid, message = self.service.validate_json(
            editor.toPlainText()
        )

        if not valid:

            QMessageBox.warning(
                self,
                "Invalid JSON",
                message
            )

            return False

        try:

            parsed = json.loads(
                editor.toPlainText()
            )

            if not isinstance(parsed, dict):
                raise ValueError(
                    "JSON root must be an object."
                )

            if path == self.model_configuration_path():

                if not isinstance(
                    parsed.get("instruments"),
                    dict
                ):
                    raise ValueError(
                        "JSON must contain an 'instruments' object."
                    )

            elif path == self.parameter_configuration_path():

                if "limits" in parsed and not isinstance(
                    parsed["limits"],
                    dict
                ):
                    raise ValueError(
                        "'limits' must be a JSON object."
                    )

                if "test_parameters" in parsed and not isinstance(
                    parsed["test_parameters"],
                    dict
                ):
                    raise ValueError(
                        "'test_parameters' must be a JSON object."
                    )

            self.service.save_config(
                path,
                editor.toPlainText()
            )

            editor.document().setModified(False)

            return True

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save Error",
                str(error)
            )

            return False


    def save_json(self):

        editor, path = self.current_editor()

        if self.save_editor(editor, path):

            QMessageBox.information(
                self,
                "JSON Saved",
                f"Saved successfully:\n{path}"
            )

            if editor == self.catalog_editor:

                self.refresh_instrument_list()

            elif editor == self.model_editor:

                self.refresh_instrument_list()

            elif editor == self.parameter_editor:

                parameter_data = json.loads(
                    self.parameter_editor.toPlainText()
                )

                self.loading_configuration = True

                self.load_parameter_controls(
                    parameter_data
                )

                self.loading_configuration = False


    def build_parameter_forms(self):

        definitions = {
            "acw": {
                "title": "ACW — AC Hipot Test",
                "fields": [
                    ("test_voltage_V", "Test Voltage (V)"),
                    ("limit_voltage_V", "Limit Voltage (V)"),
                    ("frequency_Hz", "Frequency (Hz)"),
                    ("upper_mA", "Upper Current Limit (mA)"),
                    ("lower_mA", "Lower Current Limit (mA)"),
                    ("test_time_s", "Test Time (s)"),
                    ("rise_time_s", "Rise Time (s)"),
                    ("fall_time_s", "Fall Time (s)"),
                ],
            },
            "ecac": {
                "title": "ECAC — Ground Bond Test (AC)",
                "fields": [
                    ("test_current_A", "Test Current (A)"),
                    ("limit_current_A", "Limit Current (A)"),
                    ("frequency_Hz", "Frequency (Hz)"),
                    ("upper", "Upper Limit"),
                    ("lower", "Lower Limit"),
                    ("test_time_s", "Test Time (s)"),
                    ("rise_time_s", "Rise Time (s)"),
                    ("fall_time_s", "Fall Time (s)"),
                ],
            },
            "ecdc": {
                "title": "ECDC — Ground Bond Test (DC)",
                "fields": [
                    ("test_current_A", "Test Current (A)"),
                    ("limit_current_A", "Limit Current (A)"),
                    ("upper", "Upper Limit"),
                    ("lower", "Lower Limit"),
                    ("test_time_s", "Test Time (s)"),
                    ("rise_time_s", "Rise Time (s)"),
                    ("fall_time_s", "Fall Time (s)"),
                ],
            },
        }

        self.parameter_definitions = definitions
        self.parameter_focus_order = []

        for function_id, definition in definitions.items():

            page = QWidget()
            form = QFormLayout(page)

            self.parameter_inputs[function_id] = {}

            for field_id, label in definition["fields"]:

                input_field = QLineEdit()
                input_field.setPlaceholderText("Enter value")

                validator = QDoubleValidator(
                    0.0,
                    1000000000.0,
                    6,
                    input_field
                )

                validator.setNotation(
                    QDoubleValidator.Notation.StandardNotation
                )

                validator.setLocale(
                    QLocale(QLocale.Language.English)
                )

                input_field.setValidator(validator)

                input_field.textChanged.connect(
                    self.mark_parameter_dirty
                )

                input_field.returnPressed.connect(
                    lambda field=input_field:
                        self.focus_next_parameter(field)
                )

                form.addRow(label, input_field)

                self.parameter_inputs[function_id][field_id] = (
                    input_field
                )

                self.parameter_focus_order.append(
                    (function_id, input_field)
                )

            if function_id in ("ecac", "ecdc"):

                judge_type = QComboBox()

                judge_type.addItem(
                    "Resistance (Ω)",
                    "resistance"
                )

                judge_type.addItem(
                    "Voltage (V)",
                    "voltage"
                )

                judge_type.currentIndexChanged.connect(
                    self.mark_parameter_dirty
                )

                form.addRow("Judge Type:", judge_type)

                self.parameter_inputs[function_id]["judge_type"] = (
                    judge_type
                )

            self.parameter_tabs.addTab(
                page,
                definition["title"]
            )


    def focus_next_parameter(self, current_widget):

        if not self.parameter_focus_order:
            return

        current_index = None

        for index, (_, widget) in enumerate(
            self.parameter_focus_order
        ):
            if widget is current_widget:
                current_index = index
                break

        if current_index is None:
            return

        next_index = (
            current_index + 1
        ) % len(self.parameter_focus_order)

        next_function, next_widget = (
            self.parameter_focus_order[next_index]
        )

        tab_index = list(
            self.parameter_inputs.keys()
        ).index(next_function)

        self.parameter_tabs.setCurrentIndex(tab_index)

        next_widget.setFocus()
        next_widget.selectAll()
        
    def mark_parameter_dirty(self, *args):

        if self.loading_configuration:
            return

        self.parameter_form_dirty = True
        self.form_dirty = True


    def load_parameter_controls(self, parameter_data):

        test_parameters = parameter_data.get(
            "test_parameters", {}
        )

        for function_id, fields in self.parameter_inputs.items():

            values = test_parameters.get(
                function_id, {}
            )

            for field_id, widget in fields.items():

                value = values.get(field_id)

                if isinstance(widget, QComboBox):

                    index = widget.findData(
                        value or "resistance"
                    )

                    if index < 0:
                        index = 0

                    widget.setCurrentIndex(index)

                else:

                    widget.setText(
                        "" if value is None else str(value)
                    )

        self.parameter_form_dirty = False

    def collect_parameter_controls(self, parameter_data):

        test_parameters = parameter_data.setdefault(
            "test_parameters",
            {}
        )

        for function_id, fields in self.parameter_inputs.items():

            function_parameters = test_parameters.setdefault(
                function_id,
                {}
            )

            for field_id, widget in fields.items():

                if isinstance(widget, QComboBox):

                    function_parameters[field_id] = (
                        widget.currentData()
                    )

                    continue

                value = widget.text().strip()

                if not value:

                    function_parameters.pop(
                        field_id,
                        None
                    )

                else:

                    try:
                        function_parameters[field_id] = float(value)

                    except ValueError:
                        raise ValueError(
                            f"{function_id.upper()}: "
                            f"Invalid numeric value for {field_id}: {value}"
                        )

            self.validate_parameter_group(
                function_id,
                function_parameters
            )

        return parameter_data

    def validate_parameter_group(
        self,
        function_id,
        parameters
    ):

        if "frequency_Hz" in parameters:

            frequency = parameters["frequency_Hz"]

            if frequency not in (50, 60):

                raise ValueError(
                    f"{function_id.upper()}: "
                    "Frequency must be 50 or 60 Hz."
                )

        if (
            "lower" in parameters
            and "upper" in parameters
            and parameters["lower"] > parameters["upper"]
        ):

            raise ValueError(
                f"{function_id.upper()}: "
                "Lower Limit cannot exceed Upper Limit."
            )

        if (
            "lower_mA" in parameters
            and "upper_mA" in parameters
            and parameters["lower_mA"] > parameters["upper_mA"]
        ):

            raise ValueError(
                "ACW: Lower Current Limit cannot exceed "
                "Upper Current Limit."
            )
