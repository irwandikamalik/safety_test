
import json

from PySide6.QtCore import Qt

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


class InstrumentConfigurationPage(QWidget):

    CATALOG_PATH = "global/instrument_catalog.json"
    MODEL_PATH = "models/MODEL-A/instruments.json"

    def __init__(self, parent=None):

        super().__init__(parent)

        self.service = ConfigService()
        self.driver_registry = DriverRegistry()

        self.measurement_checks = {}
        self.current_instrument_id = None

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
            "MODEL-A Measurement Configuration"
        )

        model_layout = QVBoxLayout(self.model_group)

        self.element_input = QSpinBox()
        self.element_input.setRange(1, 3)
        self.element_input.setValue(1)

        element_layout = QFormLayout()

        element_layout.addRow(
            "Measurement Element:",
            self.element_input
        )

        model_layout.addLayout(element_layout)

        measurement_group = QGroupBox(
            "Available Measurements"
        )

        self.measurement_container = QVBoxLayout(
            measurement_group
        )

        model_layout.addWidget(measurement_group)

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
            self.save_settings
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
            "MODEL-A Mapping"
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

            self.catalog_editor.setPlainText(
                self.service.read_config(
                    self.CATALOG_PATH
                )
            )

            self.model_editor.setPlainText(
                self.service.read_config(
                    self.MODEL_PATH
                )
            )

            self.refresh_instrument_list()

        except Exception as error:

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

            self.refresh_connection_controls(catalog)

            self.refresh_measurement_controls(
                catalog_id,
                catalog
            )

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

    # ==========================================
    # MODEL MEASUREMENT SETTINGS
    # ==========================================

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

            self.measurement_container.addWidget(
                QLabel(
                    "This instrument is not enabled "
                    "for MODEL-A."
                )
            )

            return

        overrides = model_entry.get(
            "overrides", {}
        )

        self.element_input.setValue(
            int(overrides.get("element", 1))
        )

        definitions = catalog.get(
            "measurements", {}
        )

        selected = overrides.get(
            "selected_measurements",
            list(definitions.keys())
        )

        if not definitions:

            self.measurement_container.addWidget(
                QLabel(
                    "No measurement definitions available "
                    "for this instrument."
                )
            )

            return

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
                measurement_id in selected
            )

            self.measurement_container.addWidget(
                checkbox
            )

            self.measurement_checks[
                measurement_id
            ] = checkbox

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
                f"Instrument {catalog_id} is not mapped to MODEL-A."
            )

        catalog_data = self.get_catalog_data()

        definitions = catalog_data.get(
            "instruments", {}
        ).get(
            catalog_id, {}
        ).get(
            "measurements", {}
        )

        selected = self.selected_measurements()

        if definitions and not selected:
            raise ValueError(
                "Select at least one measurement."
            )

        overrides = model_entry.setdefault(
            "overrides", {}
        )

        if definitions:
            overrides["selected_measurements"] = selected
            overrides["element"] = self.element_input.value()

    def save_settings(self, show_message=True):

        try:

            catalog_id, catalog = (
                self.current_instrument_configuration()
            )

            catalog_data = self.get_catalog_data()
            model_data = self.get_model_data()

            # Save connection to GLOBAL catalog.
            self.update_global_connection(catalog)

            # Save measurement selection to MODEL configuration.
            self.update_model_measurements(
                catalog_id,
                model_data
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

            # Persist global configuration.
            self.service.save_config(
                self.CATALOG_PATH,
                catalog_text
            )

            # Persist model-specific configuration.
            self.service.save_config(
                self.MODEL_PATH,
                model_text
            )

            self.catalog_editor.setPlainText(
                catalog_text
            )

            self.model_editor.setPlainText(
                model_text
            )

            if show_message:

                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    "Global and model configurations saved."
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

        if self.json_tabs.currentIndex() == 0:
            return self.catalog_editor, self.CATALOG_PATH

        return self.model_editor, self.MODEL_PATH

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

    def save_json(self):

        editor, path = self.current_editor()

        valid, message = self.service.validate_json(
            editor.toPlainText()
        )

        if not valid:

            QMessageBox.warning(
                self,
                "Invalid JSON",
                message
            )

            return

        try:

            # Validate the expected top-level structure.
            parsed = json.loads(
                editor.toPlainText()
            )

            if not isinstance(parsed.get("instruments"), dict):
                raise ValueError(
                    "JSON must contain an 'instruments' object."
                )

            self.service.save_config(
                path,
                editor.toPlainText()
            )

            self.load_configuration()

            QMessageBox.information(
                self,
                "JSON Saved",
                f"Saved successfully:\n{path}"
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save Error",
                str(error)
            )
