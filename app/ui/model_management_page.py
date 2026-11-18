
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
    QTextEdit,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from app.services.model_service import ModelService


class ModelEditorDialog(QDialog):

    def __init__(
        self,
        model_service,
        model=None,
        parent=None
    ):

        super().__init__(parent)

        self.model_service = model_service
        self.model = model

        self.setWindowTitle(
            "Edit Model" if model else "Add New Model"
        )

        self.setMinimumWidth(480)

        self.build_ui()

    def build_ui(self):

        root = QVBoxLayout(self)

        form_group = QGroupBox("Model Information")
        form = QFormLayout(form_group)

        self.model_id_input = QLineEdit()
        self.model_id_input.setPlaceholderText(
            "Example: MODEL-C"
        )

        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText(
            "Enter model name"
        )

        self.description_input = QTextEdit()
        self.description_input.setObjectName(
            "ModelDescriptionInput"
        )
        self.description_input.setPlaceholderText(
            "Enter model description"
        )
        self.description_input.setMaximumHeight(100)

        form.addRow("Model ID:", self.model_id_input)
        form.addRow("Model Name:", self.model_name_input)
        form.addRow("Description:", self.description_input)

        root.addWidget(form_group)

        self.template_group = QGroupBox(
            "Configuration Template"
        )

        template_layout = QFormLayout(
            self.template_group
        )

        self.template_selector = QComboBox()
        self.template_selector.setObjectName(
            "ModelTemplateSelector"
        )

        if self.model is None:

            for item in self.model_service.discover_models():

                self.template_selector.addItem(
                    f'{item["model_id"]} - {item["model_name"]}',
                    item["model_id"]
                )

            template_layout.addRow(
                "Copy From:",
                self.template_selector
            )

            root.addWidget(self.template_group)

        else:

            self.model_id_input.setText(
                self.model["model_id"]
            )

            self.model_id_input.setReadOnly(True)

            self.model_name_input.setText(
                self.model["model_name"]
            )

            self.description_input.setPlainText(
                self.model.get("description", "")
            )

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save |
            QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root.addWidget(buttons)

    def get_values(self):

        return {
            "model_id": self.model_id_input.text().strip().upper(),
            "model_name": self.model_name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "template_model_id": self.template_selector.currentData()
        }


class ModelManagementPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.model_service = ModelService()
        self.dashboard = None

        self.models = []

        self.build_ui()
        self.refresh_models()

    # ==========================================
    # USER INTERFACE
    # ==========================================

    def build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        heading = QLabel("Model Management")
        heading.setObjectName("PageTitle")

        subtitle = QLabel(
            "Create, edit, enable, disable, and manage "
            "product model configurations."
        )
        subtitle.setObjectName("Muted")

        root.addWidget(heading)
        root.addWidget(subtitle)

        # SUMMARY

        summary_group = QGroupBox("Model Overview")
        summary_layout = QHBoxLayout(summary_group)

        self.total_label = QLabel("Total Models: 0")
        self.enabled_label = QLabel("Enabled: 0")
        self.disabled_label = QLabel("Disabled: 0")
        self.draft_label = QLabel("Draft: 0")

        for label in (
            self.total_label,
            self.enabled_label,
            self.disabled_label,
            self.draft_label
        ):
            label.setStyleSheet(
                "font-weight: bold; padding: 6px;"
            )
            summary_layout.addWidget(label)

        root.addWidget(summary_group)

        # MODEL LIST

        list_group = QGroupBox("Registered Models")
        list_layout = QVBoxLayout(list_group)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search Model ID or Model Name..."
        )

        self.search_input.textChanged.connect(
            self.filter_models
        )

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(
            self.refresh_models
        )

        self.add_button = QPushButton("Add Model")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(
            self.add_model
        )

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.add_button)

        list_layout.addLayout(toolbar)

        self.model_table = QTableWidget(0, 7)

        self.model_table.setHorizontalHeaderLabels([
            "Model ID",
            "Model Name",
            "Description",
            "Enabled",
            "Configuration",
            "Hardware",
            "Actions"
        ])

        self.model_table.verticalHeader().setVisible(False)

        self.model_table.setAlternatingRowColors(True)

        self.model_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.model_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.model_table.setSelectionMode(
            QTableWidget.SingleSelection
        )

        header = self.model_table.horizontalHeader()

        header.setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            2, QHeaderView.Stretch
        )

        for column in (3, 4, 5, 6):

            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents
            )

        self.model_table.setMinimumHeight(420)

        list_layout.addWidget(self.model_table)

        root.addWidget(list_group, 1)

        # FOOTER

        self.status_label = QLabel(
            "Ready."
        )

        self.status_label.setObjectName("Muted")

        root.addWidget(self.status_label)

    # ==========================================
    # WORKFLOW SAFETY
    # ==========================================

    def is_workflow_running(self):

        if self.dashboard is None:
            return False

        engine = self.dashboard.engine

        return bool(
            engine and engine.is_running
        )

    def ensure_editing_allowed(self):

        if self.is_workflow_running():

            QMessageBox.warning(
                self,
                "Workflow Running",
                "Model configuration cannot be modified "
                "while a test workflow is running."
            )

            return False

        return True

    # ==========================================
    # MODEL REFRESH
    # ==========================================

    def refresh_models(self):

        try:

            self.models = self.model_service.discover_models()

            self.update_summary()
            self.populate_table()

            self.status_label.setText(
                f"{len(self.models)} model(s) loaded."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Model Management Error",
                str(error)
            )

    def update_summary(self):

        total = len(self.models)

        enabled = sum(
            1 for model in self.models
            if model["enabled"] is True
        )

        disabled = total - enabled

        draft = sum(
            1 for model in self.models
            if model["configuration_status"] == "DRAFT"
        )

        self.total_label.setText(
            f"Total Models: {total}"
        )

        self.enabled_label.setText(
            f"Enabled: {enabled}"
        )

        self.disabled_label.setText(
            f"Disabled: {disabled}"
        )

        self.draft_label.setText(
            f"Draft: {draft}"
        )

    # ==========================================
    # TABLE
    # ==========================================

    def populate_table(self):

        keyword = self.search_input.text().strip().lower()

        filtered = [
            model for model in self.models
            if (
                keyword in model["model_id"].lower()
                or keyword in model["model_name"].lower()
            )
        ]

        self.model_table.setRowCount(
            len(filtered)
        )

        for row, model in enumerate(filtered):

            values = [
                model["model_id"],
                model["model_name"],
                model["description"],
                "Enabled" if model["enabled"] else "Disabled",
                model["configuration_status"],
                (
                    "Approved"
                    if model["hardware_approved"]
                    else "Not Approved"
                )
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setFlags(
                    item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )

                self.model_table.setItem(
                    row,
                    column,
                    item
                )

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)

            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(
                lambda checked=False, m=model: self.edit_model(m)
            )

            toggle_button = QPushButton(
                "Disable" if model["enabled"] else "Enable"
            )

            toggle_button.clicked.connect(
                lambda checked=False, m=model: self.toggle_model(m)
            )

            delete_button = QPushButton("Delete")
            delete_button.setObjectName("DangerButton")

            delete_button.clicked.connect(
                lambda checked=False, m=model: self.delete_model(m)
            )

            action_layout.addWidget(edit_button)
            action_layout.addWidget(toggle_button)
            action_layout.addWidget(delete_button)

            self.model_table.setCellWidget(
                row,
                6,
                action_widget
            )

        self.model_table.resizeRowsToContents()

    def filter_models(self, text):

        self.populate_table()

    # ==========================================
    # ADD MODEL
    # ==========================================

    def add_model(self):

        if not self.ensure_editing_allowed():
            return

        dialog = ModelEditorDialog(
            self.model_service,
            parent=self
        )

        if not dialog.exec():
            return

        values = dialog.get_values()

        try:

            if not values["template_model_id"]:

                raise ValueError(
                    "Select a configuration template."
                )

            self.model_service.create_model(
                model_id=values["model_id"],
                model_name=values["model_name"],
                description=values["description"],
                template_model_id=values["template_model_id"]
            )

            QMessageBox.information(
                self,
                "Model Created",
                f'Model {values["model_id"]} created successfully.\n\n'
                "Configuration status: DRAFT\n"
                "Hardware approval: NOT APPROVED"
            )

            self.refresh_models()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Create Model Failed",
                str(error)
            )

    # ==========================================
    # EDIT MODEL
    # ==========================================

    def edit_model(self, model):

        if not self.ensure_editing_allowed():
            return

        dialog = ModelEditorDialog(
            self.model_service,
            model=model,
            parent=self
        )

        if not dialog.exec():
            return

        values = dialog.get_values()

        try:

            self.model_service.update_model(
                model_id=model["model_id"],
                model_name=values["model_name"],
                description=values["description"],
                enabled=model["enabled"]
            )

            QMessageBox.information(
                self,
                "Model Updated",
                f'Model {model["model_id"]} updated successfully.'
            )

            self.refresh_models()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Update Failed",
                str(error)
            )

    # ==========================================
    # ENABLE / DISABLE
    # ==========================================

    def toggle_model(self, model):

        if not self.ensure_editing_allowed():
            return

        new_state = not model["enabled"]

        action = "enable" if new_state else "disable"

        answer = QMessageBox.question(
            self,
            "Confirm Model Status",
            f'Are you sure you want to {action} '
            f'{model["model_id"]}?'
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:

            self.model_service.update_model(
                model_id=model["model_id"],
                model_name=model["model_name"],
                description=model["description"],
                enabled=new_state
            )

            self.refresh_models()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Update Failed",
                str(error)
            )

    # ==========================================
    # DELETE MODEL
    # ==========================================

    def delete_model(self, model):

        if not self.ensure_editing_allowed():
            return

        answer = QMessageBox.warning(
            self,
            "Delete Model",
            (
                f'Are you sure you want to delete '
                f'{model["model_id"]}?\n\n'
                "A backup will be created before deletion.\n"
                "This action cannot be undone from the application."
            ),
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:

            backup = self.model_service.delete_model(
                model["model_id"]
            )

            QMessageBox.information(
                self,
                "Model Deleted",
                (
                    f'Model {model["model_id"]} deleted successfully.\n\n'
                    f"Backup location:\n{backup}"
                )
            )

            self.refresh_models()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Delete Failed",
                str(error)
            )
