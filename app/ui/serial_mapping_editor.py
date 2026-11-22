
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QLabel,
    QGroupBox,
)


class SerialMappingEditor(QWidget):

    configuration_changed = Signal(dict)

    FIELD_NAMES = [
        "start_suffix",
        "end_suffix",
        "expected_value",
        "min_length",
        "max_length",
        "exact_length",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._loading = False
        self.configuration = {"models": {}}
        self.available_models = []

        self.build_ui()

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        selection_group = QGroupBox("Model Selection")
        selection_layout = QFormLayout(selection_group)

        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(
            self.on_model_changed
        )

        selection_layout.addRow(
            "Select Model:",
            self.model_combo
        )

        root.addWidget(selection_group)

        mapping_group = QGroupBox("Serial Mapping Parameters")
        mapping_layout = QFormLayout(mapping_group)

        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("Example: 1")

        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("Example: 3")

        self.expected_edit = QLineEdit()
        self.expected_edit.setPlaceholderText("Example: 13J")

        self.min_length_edit = QLineEdit()
        self.min_length_edit.setPlaceholderText("Optional")

        self.max_length_edit = QLineEdit()
        self.max_length_edit.setPlaceholderText("Optional")

        self.exact_length_edit = QLineEdit()
        self.exact_length_edit.setPlaceholderText("Optional")

        self.enabled_checkbox = QCheckBox(
            "Enable serial mapping for this model"
        )

        mapping_layout.addRow("Start Position:", self.start_edit)
        mapping_layout.addRow("End Position:", self.end_edit)
        mapping_layout.addRow("Expected Value:", self.expected_edit)
        mapping_layout.addRow("Minimum Length:", self.min_length_edit)
        mapping_layout.addRow("Maximum Length:", self.max_length_edit)
        mapping_layout.addRow("Exact Length:", self.exact_length_edit)
        mapping_layout.addRow("Status:", self.enabled_checkbox)

        root.addWidget(mapping_group)
        root.addStretch()

        self.status_label = QLabel()
        self.status_label.setObjectName("Muted")
        root.addWidget(self.status_label)

        self._field_widgets = {
            "start_suffix": self.start_edit,
            "end_suffix": self.end_edit,
            "expected_value": self.expected_edit,
            "min_length": self.min_length_edit,
            "max_length": self.max_length_edit,
            "exact_length": self.exact_length_edit,
        }

        for widget in self._field_widgets.values():
            widget.editingFinished.connect(
                self.on_parameter_changed
            )

        self.enabled_checkbox.stateChanged.connect(
            self.on_parameter_changed
        )

    # ==========================================
    # MODEL DATA
    # ==========================================

    def set_available_models(self, models):

        if not isinstance(models, list):
            raise ValueError("Models must be a list.")

        current_model_id = self.model_combo.currentData()

        self._loading = True

        try:

            self.available_models = models

            mappings = self.configuration.setdefault(
                "models",
                {}
            )

            self.model_combo.clear()

            for model in models:

                model_id = model.get("model_id")

                if not isinstance(model_id, str) or not model_id:
                    continue

                model_name = model.get(
                    "model_name",
                    model_id
                )

                enabled = model.get("enabled", False)

                label = f"{model_id} - {model_name}"

                if not enabled:
                    label += " (Model Disabled)"

                self.model_combo.addItem(
                    label,
                    model_id
                )

                # Automatically create mapping for new models.
                mappings.setdefault(
                    model_id,
                    self.empty_mapping()
                )

            index = self.model_combo.findData(
                current_model_id
            )

            if index < 0 and self.model_combo.count():
                index = 0

            self.model_combo.setCurrentIndex(index)

            self.load_selected_model()

        finally:
            self._loading = False

        self.update_status()

    @staticmethod
    def empty_mapping():

        return {
            "start_suffix": None,
            "end_suffix": None,
            "expected_value": "",
            "min_length": None,
            "max_length": None,
            "exact_length": None,
            "enabled": False,
        }

    def set_configuration(self, configuration):

        if not isinstance(configuration, dict):
            raise ValueError(
                "Serial mapping configuration must be an object."
            )

        models = configuration.get("models")

        if not isinstance(models, dict):
            raise ValueError(
                "Serial mapping models must be an object."
            )

        self._loading = True

        try:
            self.configuration = {
                "models": {
                    model_id: dict(mapping)
                    for model_id, mapping in models.items()
                }
            }

            for model_id, mapping in self.configuration["models"].items():

                defaults = self.empty_mapping()

                for key, value in defaults.items():
                    mapping.setdefault(key, value)

            self.load_selected_model()

        finally:
            self._loading = False

        self.update_status()

    def get_configuration(self):

        self.store_current_model()

        return {
            "models": {
                model_id: dict(mapping)
                for model_id, mapping
                in self.configuration["models"].items()
            }
        }

    # ==========================================
    # FORM
    # ==========================================

    def on_model_changed(self):

        if self._loading:
            return

        self.load_selected_model()
        self.update_status()

    def load_selected_model(self):

        model_id = self.model_combo.currentData()

        has_model = bool(model_id)

        for widget in self._field_widgets.values():
            widget.setEnabled(has_model)

        self.enabled_checkbox.setEnabled(has_model)

        if not has_model:
            self.clear_form()
            return

        mapping = self.configuration["models"].get(
            model_id,
            self.empty_mapping()
        )

        self._loading = True

        try:

            for field, widget in self._field_widgets.items():

                value = mapping.get(field)

                widget.setText(
                    "" if value is None else str(value)
                )

            self.enabled_checkbox.setChecked(
                mapping.get("enabled", False) is True
            )

        finally:
            self._loading = False

    def clear_form(self):

        for widget in self._field_widgets.values():
            widget.clear()

        self.enabled_checkbox.setChecked(False)

    def store_current_model(self):

        model_id = self.model_combo.currentData()

        if not model_id:
            return

        mapping = self.configuration["models"].setdefault(
            model_id,
            self.empty_mapping()
        )

        for field, widget in self._field_widgets.items():

            raw_value = widget.text().strip()

            if field == "expected_value":
                mapping[field] = raw_value

            elif not raw_value:
                mapping[field] = None

            else:
                try:
                    mapping[field] = int(raw_value)
                except ValueError:
                    # Preserve invalid text for validation feedback.
                    mapping[field] = raw_value

        mapping["enabled"] = self.enabled_checkbox.isChecked()

    def on_parameter_changed(self, *args):

        if self._loading:
            return

        self.store_current_model()
        self.update_status()

        self.configuration_changed.emit(
            self.get_configuration()
        )

    # ==========================================
    # STATUS
    # ==========================================

    def update_status(self):

        model_id = self.model_combo.currentData()

        if not model_id:
            self.status_label.setText(
                "No model available. Create a model first."
            )
            return

        mapping = self.configuration["models"].get(
            model_id,
            self.empty_mapping()
        )

        if mapping.get("enabled") is True:
            self.status_label.setText(
                "Mapping enabled. Parameters will be validated when saved."
            )
        else:
            self.status_label.setText(
                "Mapping disabled. Complete the parameters and enable it "
                "when ready."
            )
