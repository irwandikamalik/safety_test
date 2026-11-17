import json

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QPlainTextEdit,
    QMessageBox
)

from app.services.config_service import ConfigService


class ConfigurationPage(QWidget):

    def __init__(self, title, configurations, parent=None):

        super().__init__(parent)

        self.service = ConfigService()

        self.configurations = configurations

        self.editors = {}

        self.build_ui(title)

    def build_ui(self, title):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            22, 18, 22, 18
        )

        heading = QLabel(title)
        heading.setObjectName("PageTitle")

        root.addWidget(heading)

        subtitle = QLabel(
            "Edit configuration directly using JSON."
        )

        subtitle.setObjectName("Muted")

        root.addWidget(subtitle)

        self.tabs = QTabWidget()

        for label, path in self.configurations:

            page = QWidget()

            layout = QVBoxLayout(page)

            path_label = QLabel(path)
            path_label.setObjectName("Muted")

            editor = QPlainTextEdit()

            editor.setLineWrapMode(
                QPlainTextEdit.NoWrap
            )

            self.editors[path] = editor

            layout.addWidget(path_label)
            layout.addWidget(editor, 1)

            self.tabs.addTab(page, label)

            self.load_file(path)

        root.addWidget(
            self.tabs,
            1
        )

        buttons = QHBoxLayout()

        format_button = QPushButton("Format JSON")
        validate_button = QPushButton("Validate")

        save_button = QPushButton("Save")
        save_button.setObjectName("PrimaryButton")

        format_button.clicked.connect(
            self.format_json
        )

        validate_button.clicked.connect(
            self.validate_json
        )

        save_button.clicked.connect(
            self.save_json
        )

        buttons.addWidget(format_button)
        buttons.addWidget(validate_button)

        buttons.addStretch()

        buttons.addWidget(save_button)

        root.addLayout(buttons)

    def current_editor(self):

        path = self.configurations[
            self.tabs.currentIndex()
        ][1]

        return path, self.editors[path]

    def load_file(self, path):

        editor = self.editors[path]

        try:

            content = self.service.read_config(path)

            editor.setPlainText(content)

        except Exception as error:

            editor.setPlainText("{}")

            print(
                f"Configuration load error: {error}"
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

    def save_json(self):

        path, editor = self.current_editor()

        valid, message = self.service.validate_json(
            editor.toPlainText()
        )

        if not valid:

            QMessageBox.warning(
                self,
                "Cannot Save",
                message
            )

            return

        try:

            self.service.save_config(
                path,
                editor.toPlainText()
            )

            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Saved successfully:\n{path}"
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save Error",
                str(error)
            )