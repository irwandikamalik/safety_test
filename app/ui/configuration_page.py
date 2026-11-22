
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
    QComboBox,
    QFormLayout,
    QGroupBox,
)

from app.services.config_service import ConfigService
from app.services.model_service import ModelService
from app.ui.workflow_sequence_editor import WorkflowSequenceEditor
from app.core.workflow_validator import WorkflowValidator


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

        self.sequence_editors = {}
        self.sequence_tabs = {}

        self._syncing_sequence = False
        self._sequence_source = {}

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
        root.setContentsMargins(20, 8, 20, 8)
        root.setSpacing(10)

        if self.dynamic_model:

            model_group = QGroupBox("Workflow Configuration")
            model_group.setObjectName("SequenceModelGroup")
            model_group.setMinimumHeight(80)

            model_layout = QHBoxLayout(model_group)
            model_layout.setContentsMargins(20, 1, 20, 1)
            model_layout.setSpacing(10)
            model_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            model_label = QLabel("Available Model:")
            model_label.setObjectName("Muted")

            self.model_selector = QComboBox()
            self.model_selector.setObjectName("SequenceModelSelector")
            self.model_selector.setMinimumHeight(36)
            self.model_selector.setMinimumWidth(100)

            self.model_selector.currentIndexChanged.connect(
                self.on_model_changed
            )

            model_layout.addWidget(
                model_label,
                alignment=Qt.AlignmentFlag.AlignVCenter
            )
            model_layout.addWidget(
                self.model_selector,
                1,
                alignment=Qt.AlignmentFlag.AlignVCenter
            )

            model_layout.addSpacing(12)

            format_button = QPushButton("Format")
            validate_button = QPushButton("Validate")
            save_button = QPushButton("Save")

            save_button.setObjectName("PrimaryButton")

            format_button.setMinimumHeight(36)
            validate_button.setMinimumHeight(36)
            save_button.setMinimumHeight(36)

            format_button.clicked.connect(self.format_json)
            validate_button.clicked.connect(self.validate_json)
            save_button.clicked.connect(self.save_json)

            model_layout.addWidget(
                format_button,
                alignment=Qt.AlignmentFlag.AlignVCenter
            )

            model_layout.addWidget(
                validate_button,
                alignment=Qt.AlignmentFlag.AlignVCenter
            )

            model_layout.addWidget(
                save_button,
                alignment=Qt.AlignmentFlag.AlignVCenter
            )

            root.addWidget(model_group)

        self.tabs = QTabWidget()

        if self.dynamic_model:
            self.tabs.tabBar().hide()

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

        if not self.dynamic_model:

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

    def get_current_sequence(self):

        path, editor = self.current_editor()

        source = self._sequence_source.get(
            path,
            "advanced"
        )

        if source == "visual":

            return self.sequence_editors[path].get_sequence()

        sequence = json.loads(
            editor.toPlainText()
        )

        if not isinstance(sequence, dict):
            raise ValueError(
                "Sequence configuration must be a JSON object."
            )

        return sequence


    def validate_current_workflow(self):

        if not self.dynamic_model:
            return True, []

        try:

            sequence = self.get_current_sequence()

            configuration = self.model_service.load_model(
                self.current_model_id
            )

            # Replace sequence from disk with the latest
            # sequence currently being edited.
            configuration["sequence"] = sequence

            result = WorkflowValidator().validate(
                configuration,
                expected_model_id=self.current_model_id
            )

            return (
                result.get("valid", False),
                result.get("errors", [])
            )

        except Exception as error:

            return False, [str(error)]

    def load_model_configuration(self):

        path = self.model_configuration_path()

        if path not in self.editors:

            page = QWidget()
            layout = QVBoxLayout(page)

            path_label = QLabel(path)

            sequence_tabs = QTabWidget()
            sequence_tabs.setObjectName("WorkflowSequenceTabs")
            sequence_tabs.setDocumentMode(True)

            sequence_tabs.setStyleSheet("""
                QTabWidget#WorkflowSequenceTabs {
                    background-color: #F3F5F8;
                    border: none;
                }

                QTabWidget#WorkflowSequenceTabs::pane {
                    background-color: #FFFFFF;
                    border: 1px solid #DFE5EC;
                    border-radius: 8px;
                    top: -1px;
                }

                QTabWidget#WorkflowSequenceTabs QTabBar {
                    background-color: #FFFFFF;
                    border: none;
                }

                QTabWidget#WorkflowSequenceTabs QTabBar::tab {
                    background-color: #E8EDF3;
                    color: #263449;
                    border: 1px solid #D6DEE8;
                    border-radius: 7px;
                    padding: 6px 14px;
                    margin-right: 5px;
                    min-height: 22px;
                }

                QTabWidget#WorkflowSequenceTabs QTabBar::tab:selected {
                    background-color: #1769AA;
                    color: #FFFFFF;
                    border: 1px solid #1769AA;
                }

                QTabWidget#WorkflowSequenceTabs QTabBar::tab:hover:!selected {
                    background-color: #DCE6F0;
                    color: #263449;
                }
            """)

            # Visual Editor
            sequence_editor = WorkflowSequenceEditor()

            # Advanced JSON Editor
            json_editor = QPlainTextEdit()
            json_editor.setLineWrapMode(QPlainTextEdit.NoWrap)

            sequence_tabs.addTab(
                sequence_editor,
                "Visual Editor"
            )

            sequence_tabs.addTab(
                json_editor,
                "Advanced JSON"
            )

            path_label.setAlignment(
                Qt.AlignmentFlag.AlignRight |
                Qt.AlignmentFlag.AlignVCenter
            )

            path_label.setStyleSheet("""
                QLabel {
                    color: #738197;
                    font-size: 9pt;
                    padding-right: 8px;
                }
            """)

            sequence_tabs.setCornerWidget(
                path_label,
                Qt.Corner.TopRightCorner
            )

            layout.addWidget(sequence_tabs, 1)

            self.editors[path] = json_editor
            self.editor_pages[path] = page
            self.sequence_editors[path] = sequence_editor
            self.sequence_tabs[path] = sequence_tabs

            sequence_editor.sequence_changed.connect(
                lambda sequence, p=path:
                    self.on_visual_sequence_changed(p, sequence)
            )

            json_editor.textChanged.connect(
                lambda p=path:
                    self.on_advanced_json_changed(p)
            )

            self.tabs.addTab(
                page,
                self.current_model_id
            )

        self.load_file(path)

        page = self.editor_pages[path]
        tab_index = self.tabs.indexOf(page)

        if tab_index >= 0:
            self.tabs.setCurrentIndex(tab_index)

    def on_visual_sequence_changed(self, path, sequence):

        if self._syncing_sequence:
            return

        self._syncing_sequence = True

        try:

            editor = self.editors[path]

            editor.setPlainText(
                json.dumps(
                    sequence,
                    indent=4,
                    ensure_ascii=False
                )
            )

            editor.document().setModified(True)

            self._sequence_source[path] = "visual"

        finally:
            self._syncing_sequence = False


    def on_advanced_json_changed(self, path):

        if self._syncing_sequence:
            return

        self._sequence_source[path] = "advanced"

        editor = self.editors[path]
        sequence_editor = self.sequence_editors[path]

        try:

            sequence = json.loads(
                editor.toPlainText()
            )

            if not isinstance(sequence, dict):
                return

            if not isinstance(sequence.get("steps"), list):
                return

            self._syncing_sequence = True

            sequence_editor.set_sequence(sequence)

        except (json.JSONDecodeError, ValueError, TypeError):
            # JSON belum valid atau belum memiliki struktur sequence.
            # Jangan mengubah teks Advanced JSON.
            return

        finally:
            self._syncing_sequence = False

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

            if self.dynamic_model and path in self.sequence_editors:

                try:

                    sequence = json.loads(content)

                    if (
                        isinstance(sequence, dict)
                        and isinstance(sequence.get("steps"), list)
                    ):

                        self._syncing_sequence = True

                        self.sequence_editors[path].set_sequence(
                            sequence
                        )

                        self._sequence_source[path] = "advanced"

                    else:
                        raise ValueError(
                            "Sequence JSON must contain a steps list."
                        )

                except (json.JSONDecodeError, ValueError, TypeError) as error:

                    print(
                        f"Sequence editor load error ({path}): {error}"
                    )

                finally:
                    self._syncing_sequence = False

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

        if not valid:

            QMessageBox.warning(
                self,
                "JSON Validation Error",
                message
            )

            return

        if self.dynamic_model:

            valid, errors = self.validate_current_workflow()

            if not valid:

                QMessageBox.warning(
                    self,
                    "Workflow Validation Failed",
                    "\n".join(
                        f"- {error}" for error in errors
                    )
                )

                return

            QMessageBox.information(
                self,
                "Workflow Validation",
                "Workflow configuration is valid."
            )

            return

        QMessageBox.information(
            self,
            "JSON Validation",
            message
        )

    def save_current_configuration(
        self,
        show_message=True
    ):

        path, editor = self.current_editor()

        # 1. Validate JSON syntax.
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

        # 2. Validate complete workflow configuration.
        if self.dynamic_model:

            valid, errors = self.validate_current_workflow()

            if not valid:

                if show_message:

                    QMessageBox.warning(
                        self,
                        "Workflow Validation Failed",
                        "\n".join(
                            f"- {error}" for error in errors
                        )
                    )

                return False

        # 3. Save configuration.
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
