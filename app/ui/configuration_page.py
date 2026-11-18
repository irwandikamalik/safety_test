
import json

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
)

from app.services.config_service import ConfigService
from app.services.model_service import ModelService


class ConfigurationPage(QWidget):

    def __init__(
        self,
        title,
        configurations,
        parent=None,
        dynamic_model=False
    ):
        super().__init__(parent)

        self.service = ConfigService()
        self.model_service = ModelService()

        self.configurations = configurations
        self.dynamic_model = dynamic_model

        self.editors = {}
        self.editor_pages = {}
        self.current_model_id = None

        self.build_ui(title)

        if self.dynamic_model:
            self.load_model_list()
        else:
            for _, path in self.configurations:
                self.load_file(path)

    # ==========================================
    # USER INTERFACE
    # ==========================================

    def build_ui(self, title):

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")

        subtitle = QLabel(
            "Edit configuration directly using JSON."
        )
        subtitle.setObjectName("Muted")

        root.addWidget(heading)
        root.addWidget(subtitle)

        if self.dynamic_model:

            model_group = QGroupBox("Model Selection")
            model_group.setObjectName("SequenceModelGroup")

            model_layout = QFormLayout(model_group)

            self.model_selector = QComboBox()
            self.model_selector.setObjectName(
                "SequenceModelSelector"
            )
            self.model_selector.setMinimumHeight(38)

            self.model_selector.currentIndexChanged.connect(
                self.on_model_changed
            )

            model_layout.addRow(
                "Available Model:",
                self.model_selector
            )

            root.addWidget(model_group)

        self.tabs = QTabWidget()

        for label, path in self.configurations:

            page = QWidget()
            layout = QVBoxLayout(page)

            path_label = QLabel(path)
            path_label.setObjectName("Muted")

            editor = QPlainTextEdit()
            editor.setLineWrapMode(QPlainTextEdit.NoWrap)

            self.editors[path] = editor
            self.editor_pages[path] = page

            layout.addWidget(path_label)
            layout.addWidget(editor, 1)

            self.tabs.addTab(page, label)

        root.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()

        format_button = QPushButton("Format JSON")
        validate_button = QPushButton("Validate")

        save_button = QPushButton("Save")
        save_button.setObjectName("PrimaryButton")

        format_button.clicked.connect(self.format_json)
        validate_button.clicked.connect(self.validate_json)
        save_button.clicked.connect(self.save_json)

        buttons.addWidget(format_button)
        buttons.addWidget(validate_button)
        buttons.addStretch()
        buttons.addWidget(save_button)

        root.addLayout(buttons)

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

            QMessageBox.warning(
                self,
                "No Models Found",
                "No model configuration was found."
            )

            return

        # Set model ID before loading its configuration.
        self.current_model_id = (
            self.model_selector.currentData()
        )

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

        if not self.current_model_id:
            return True

        _, editor = self.current_editor()

        if not editor.document().isModified():
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The current sequence configuration has unsaved changes.\n\n"
            "Do you want to save before switching models?",
            QMessageBox.Save
            | QMessageBox.Discard
            | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if answer == QMessageBox.Save:

            return self.save_current_configuration(
                show_message=False
            )

        if answer == QMessageBox.Discard:
            return True

        return False

    def model_configuration_path(self):

        if not self.current_model_id:
            raise ValueError("No model selected.")

        return (
            f"models/{self.current_model_id}/sequence.json"
        )

    def load_model_configuration(self):

        path = self.model_configuration_path()

        # Create the editor only when this model is first selected.
        if path not in self.editors:

            page = QWidget()
            layout = QVBoxLayout(page)

            path_label = QLabel(path)
            path_label.setObjectName("Muted")

            editor = QPlainTextEdit()
            editor.setLineWrapMode(QPlainTextEdit.NoWrap)

            layout.addWidget(path_label)
            layout.addWidget(editor, 1)

            self.editors[path] = editor
            self.editor_pages[path] = page

            self.tabs.addTab(
                page,
                self.current_model_id
            )

        # Reload the selected model's own JSON file.
        self.load_file(path)

        # Important: select the tab belonging to this model,
        # not simply the last tab.
        page = self.editor_pages[path]
        tab_index = self.tabs.indexOf(page)

        if tab_index >= 0:
            self.tabs.setCurrentIndex(tab_index)

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

        # Pertahankan model yang sedang dipilih.
        selected_index = self.model_selector.findData(
            previous_model_id
        )

        if selected_index < 0:
            selected_index = 0

        self.model_selector.setCurrentIndex(selected_index)
        self.model_selector.blockSignals(False)

        selected_model_id = self.model_selector.currentData()

        # Jangan reload editor jika model yang dipilih tidak berubah.
        # Ini mencegah perubahan JSON yang belum disimpan tertimpa.
        if selected_model_id == previous_model_id:
            return

        if not self.confirm_model_switch():
            self.model_selector.blockSignals(True)

            previous_index = self.model_selector.findData(
                previous_model_id
            )

            if previous_index >= 0:
                self.model_selector.setCurrentIndex(previous_index)

            self.model_selector.blockSignals(False)
            return

        self.current_model_id = selected_model_id
        self.load_model_configuration()

    # ==========================================
    # JSON EDITOR
    # ==========================================

    def current_editor(self):

        if self.dynamic_model:

            path = self.model_configuration_path()

            return path, self.editors[path]

        path = self.configurations[
            self.tabs.currentIndex()
        ][1]

        return path, self.editors[path]

    def load_file(self, path):

        editor = self.editors[path]

        try:

            content = self.service.read_config(path)
            editor.setPlainText(content)

            editor.document().setModified(False)

        except Exception as error:

            editor.setPlainText("{}")
            editor.document().setModified(False)

            print(
                f"Configuration load error ({path}): {error}"
            )

    def format_json(self):

        path, editor = self.current_editor()

        try:

            formatted = self.service.format_json(
                editor.toPlainText()
            )

            editor.setPlainText(formatted)

            QMessageBox.information(
                self,
                "Format JSON",
                "JSON formatted successfully."
            )

        except json.JSONDecodeError as error:

            QMessageBox.warning(
                self,
                "Invalid JSON",
                f"Line {error.lineno}: {error.msg}"
            )

    def validate_json(self):

        path, editor = self.current_editor()

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

    def save_current_configuration(
        self,
        show_message=True
    ):

        path, editor = self.current_editor()

        valid, message = self.service.validate_json(
            editor.toPlainText()
        )

        if not valid:

            if show_message:

                QMessageBox.warning(
                    self,
                    "Cannot Save",
                    message
                )

            return False

        try:

            self.service.save_config(
                path,
                editor.toPlainText()
            )

            editor.document().setModified(False)

            if show_message:

                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    f"Saved successfully:\n{path}"
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

    def save_json(self):

        self.save_current_configuration(
            show_message=True
        )
