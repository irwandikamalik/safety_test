
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QPlainTextEdit,
    QMessageBox,
)

from app.services.config_service import ConfigService
from app.services.model_service import ModelService
from app.ui.serial_mapping_editor import SerialMappingEditor


class SerialMappingPage(QWidget):

    CONFIGURATION_PATH = "global/serial_model_mapping.json"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_service = ConfigService()
        self.model_service = ModelService()

        self._syncing = False
        self._source = "visual"

        self.build_ui()
        self.load_configuration()

    # ==========================================
    # USER INTERFACE
    # ==========================================

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 8, 20, 8)
        root.setSpacing(10)

        header = QHBoxLayout()

        title = QLabel("Serial Mapping Configuration")
        title.setStyleSheet(
            "font-size: 14pt; font-weight: 600;"
        )

        path_label = QLabel(self.CONFIGURATION_PATH)
        path_label.setObjectName("Muted")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(path_label)

        root.addLayout(header)

        self.tabs = QTabWidget()

        self.visual_editor = SerialMappingEditor()

        self.json_editor = QPlainTextEdit()
        self.json_editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self.tabs.addTab(
            self.visual_editor,
            "Model Mapping Form"
        )

        self.tabs.addTab(
            self.json_editor,
            "Advanced JSON"
        )

        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)

        corner_layout.setContentsMargins(0, 0, 30, 20)
        corner_layout.setSpacing(0)


        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setFixedSize(93, 30)        

        self.save_button.clicked.connect(
            self.save_configuration
        )

        corner_layout.addWidget(self.save_button)

        self.tabs.setCornerWidget(
            corner_widget,
            Qt.Corner.TopRightCorner
        )

        root.addWidget(self.tabs, 1)

        self.visual_editor.configuration_changed.connect(
            self.on_visual_changed
        )

        self.json_editor.textChanged.connect(
            self.on_advanced_changed
        )

    # ==========================================
    # CONFIGURATION
    # ==========================================

    def load_configuration(self):

        try:

            content = self.config_service.read_config(
                self.CONFIGURATION_PATH
            )

            configuration = json.loads(content)

            configuration = (
                self.model_service.normalize_serial_model_mapping(
                    configuration
                )
            )

            self.model_service.validate_serial_model_mapping(
                configuration
            )

            self._syncing = True

            self.visual_editor.set_configuration(
                configuration
            )

            self.refresh_models()

            self.json_editor.setPlainText(
                json.dumps(
                    self.visual_editor.get_configuration(),
                    indent=4,
                    ensure_ascii=False
                )
            )

            self.json_editor.document().setModified(False)
            self._source = "visual"

        except Exception as error:

            QMessageBox.critical(
                self,
                "Serial Mapping Load Error",
                str(error)
            )

        finally:
            self._syncing = False

    def refresh_models(self):

        models = self.model_service.discover_models()

        # Preserve current form/JSON data while updating model choices.
        self.visual_editor.set_available_models(models)

        if self._source == "visual":

            self._syncing = True

            try:
                self.json_editor.setPlainText(
                    json.dumps(
                        self.visual_editor.get_configuration(),
                        indent=4,
                        ensure_ascii=False
                    )
                )
            finally:
                self._syncing = False

    # ==========================================
    # VISUAL -> JSON
    # ==========================================

    def on_visual_changed(self, configuration):

        if self._syncing:
            return

        self._source = "visual"

        self._syncing = True

        try:

            self.json_editor.setPlainText(
                json.dumps(
                    configuration,
                    indent=4,
                    ensure_ascii=False
                )
            )

            self.json_editor.document().setModified(True)

        finally:
            self._syncing = False

    # ==========================================
    # JSON -> VISUAL
    # ==========================================

    def on_advanced_changed(self):

        if self._syncing:
            return

        self._source = "advanced"

        try:

            configuration = json.loads(
                self.json_editor.toPlainText()
            )

            configuration = (
                self.model_service.normalize_serial_model_mapping(
                    configuration
                )
            )

            if not isinstance(configuration.get("models"), dict):
                return

            self._syncing = True

            try:

                self.visual_editor.set_configuration(
                    configuration
                )

                models = self.model_service.discover_models()

                self.visual_editor.set_available_models(
                    models
                )

            finally:
                self._syncing = False

        except (json.JSONDecodeError, ValueError, TypeError):
            # Keep incomplete JSON in the Advanced Editor.
            pass

    # ==========================================
    # CURRENT CONFIGURATION
    # ==========================================

    def get_current_configuration(self):

        if self._source == "visual":
            return self.visual_editor.get_configuration()

        configuration = json.loads(
            self.json_editor.toPlainText()
        )

        return self.model_service.normalize_serial_model_mapping(
            configuration
        )

    # ==========================================
    # VALIDATION
    # ==========================================

    def validate_configuration(self):

        try:

            configuration = self.get_current_configuration()

            self.model_service.validate_serial_model_mapping(
                configuration
            )

            QMessageBox.information(
                self,
                "Validation Successful",
                "Serial mapping configuration is valid."
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Validation Failed",
                str(error)
            )

    # ==========================================
    # SAVE CONFIGURATION
    # ==========================================

    def save_configuration(self):

        try:

            configuration = self.get_current_configuration()

            # Include every currently registered model.
            models = self.model_service.discover_models()

            for model in models:

                model_id = model.get("model_id")

                if not model_id:
                    continue

                configuration["models"].setdefault(
                    model_id,
                    self.model_service.empty_serial_mapping()
                )

            self.model_service.validate_serial_model_mapping(
                configuration
            )

            content = json.dumps(
                configuration,
                indent=4,
                ensure_ascii=False
            )

            self.config_service.save_config(
                self.CONFIGURATION_PATH,
                content
            )

            self._syncing = True

            try:

                self.visual_editor.set_configuration(
                    configuration
                )

                self.visual_editor.set_available_models(
                    models
                )

                self.json_editor.setPlainText(content)
                self.json_editor.document().setModified(False)

                self._source = "visual"

            finally:
                self._syncing = False

            QMessageBox.information(
                self,
                "Configuration Saved",
                "Serial mapping configuration saved successfully."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save Error",
                str(error)
            )
