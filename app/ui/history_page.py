
import json

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QPlainTextEdit,
    QDialogButtonBox,
    QMessageBox
)

from app.database.database_manager import DatabaseManager


class HistoryPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.database = DatabaseManager()

        self.results = []

        self.build_ui()
        self.load_filter_options()
        self.refresh_history()

    # ==========================================
    # BUILD UI
    # ==========================================

    def build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # PAGE HEADER

        heading = QLabel("Test History")
        heading.setObjectName("PageTitle")

        subtitle = QLabel(
            "Browse and inspect previous product safety test results."
        )
        subtitle.setObjectName("Muted")

        root.addWidget(heading)
        root.addWidget(subtitle)

        # FILTER AREA

        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(12)
        filter_layout.setVerticalSpacing(8)

        # Serial number

        filter_layout.addWidget(
            QLabel("Serial Number"),
            0, 0
        )

        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText(
            "Search serial number..."
        )

        filter_layout.addWidget(
            self.serial_input,
            1, 0
        )

        # Model

        filter_layout.addWidget(
            QLabel("Model"),
            0, 1
        )

        self.model_combo = QComboBox()
        self.model_combo.addItem("All Models", "")

        filter_layout.addWidget(
            self.model_combo,
            1, 1
        )

        # Judgment

        filter_layout.addWidget(
            QLabel("Judgment"),
            0, 2
        )

        self.judgment_combo = QComboBox()
        self.judgment_combo.addItem("All Judgments", "")

        filter_layout.addWidget(
            self.judgment_combo,
            1, 2
        )

        # Application mode

        filter_layout.addWidget(
            QLabel("Application Mode"),
            0, 3
        )

        self.mode_combo = QComboBox()

        self.mode_combo.addItem("All Modes", "")
        self.mode_combo.addItem("SIMULATION", "SIMULATION")
        self.mode_combo.addItem("HARDWARE", "HARDWARE")

        filter_layout.addWidget(
            self.mode_combo,
            1, 3
        )

        # Date filter

        self.date_filter_checkbox = QCheckBox(
            "Enable date range"
        )

        filter_layout.addWidget(
            self.date_filter_checkbox,
            2, 0
        )

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(
            QDate.currentDate().addDays(-30)
        )

        filter_layout.addWidget(
            self.start_date,
            2, 1
        )

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(
            QDate.currentDate()
        )

        filter_layout.addWidget(
            self.end_date,
            2, 2
        )

        root.addLayout(filter_layout)

        # ACTION BUTTONS

        button_layout = QHBoxLayout()

        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("PrimaryButton")

        self.refresh_button = QPushButton("Refresh")
        self.clear_button = QPushButton("Clear Filters")
        self.detail_button = QPushButton("View Details")

        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        button_layout.addWidget(self.detail_button)

        root.addLayout(button_layout)

        # RESULT INFORMATION

        self.result_label = QLabel("0 records")
        self.result_label.setObjectName("Muted")

        root.addWidget(self.result_label)

        # RESULT TABLE

        self.table = QTableWidget()

        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Timestamp",
            "Serial Number",
            "Model",
            "Operator",
            "Judgment",
            "Mode",
            "Sequence"
        ])

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)

        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.Stretch
        )

        root.addWidget(self.table, 1)

        # SIGNALS

        self.search_button.clicked.connect(
            self.search_history
        )

        self.refresh_button.clicked.connect(
            self.refresh_history
        )

        self.clear_button.clicked.connect(
            self.clear_filters
        )

        self.detail_button.clicked.connect(
            self.show_selected_detail
        )

        self.table.doubleClicked.connect(
            self.show_selected_detail
        )

        self.serial_input.returnPressed.connect(
            self.search_history
        )

        self.date_filter_checkbox.toggled.connect(
            self.update_date_filter_state
        )

        self.update_date_filter_state(
            self.date_filter_checkbox.isChecked()
        )

    # ==========================================
    # FILTER OPTIONS
    # ==========================================

    def load_filter_options(self):

        options = self.database.get_filter_options()

        self.model_combo.clear()
        self.model_combo.addItem("All Models", "")

        for model_id in options["models"]:

            self.model_combo.addItem(
                model_id,
                model_id
            )

        self.judgment_combo.clear()
        self.judgment_combo.addItem(
            "All Judgments",
            ""
        )

        for judgment in options["judgments"]:

            self.judgment_combo.addItem(
                judgment,
                judgment
            )

    # ==========================================
    # DATE FILTER STATE
    # ==========================================

    def update_date_filter_state(self, enabled):

        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)

    # ==========================================
    # SEARCH HISTORY
    # ==========================================

    def search_history(self):

        start_date = None
        end_date = None

        if self.date_filter_checkbox.isChecked():

            start_date = (
                self.start_date.date().toString("yyyy-MM-dd")
            )

            end_date = (
                self.end_date.date().toString("yyyy-MM-dd")
            )

            if self.start_date.date() > self.end_date.date():

                QMessageBox.warning(
                    self,
                    "Invalid Date Range",
                    "Start date cannot be later than end date."
                )

                return

        model_id = self.model_combo.currentData()
        judgment = self.judgment_combo.currentData()
        application_mode = self.mode_combo.currentData()

        serial_number = (
            self.serial_input.text().strip()
        )

        try:

            results = self.database.search_results(
                start_date=start_date,
                end_date=end_date,
                model_id=model_id,
                judgment=judgment,
                serial_number=serial_number,
                application_mode=application_mode,
                limit=500
            )

            if application_mode:

                results = [
                    result
                    for result in results
                    if result.get("application_mode")
                    == application_mode
                ]

            self.results = results

            self.populate_table()

        except Exception as error:

            QMessageBox.critical(
                self,
                "History Error",
                str(error)
            )

    # ==========================================
    # REFRESH
    # ==========================================

    def refresh_history(self):

        self.load_filter_options()
        self.search_history()

    # ==========================================
    # CLEAR FILTERS
    # ==========================================

    def clear_filters(self):

        self.serial_input.clear()

        self.model_combo.setCurrentIndex(0)
        self.judgment_combo.setCurrentIndex(0)
        self.mode_combo.setCurrentIndex(0)

        self.date_filter_checkbox.setChecked(False)

        self.start_date.setDate(
            QDate.currentDate().addDays(-30)
        )

        self.end_date.setDate(
            QDate.currentDate()
        )

        self.refresh_history()

    # ==========================================
    # POPULATE TABLE
    # ==========================================

    def populate_table(self):

        self.table.setRowCount(0)

        for result in self.results:

            row = self.table.rowCount()

            self.table.insertRow(row)

            model_name = (
                result.get("model_name")
                or result.get("model_id")
                or "-"
            )

            operator_name = (
                result.get("operator_name")
                or result.get("operator_id")
                or "-"
            )

            values = [

                result.get("id"),

                result.get("timestamp"),

                result.get("serial_number"),

                model_name,

                operator_name,

                result.get("judgment"),

                result.get("application_mode"),

                result.get("sequence_id")
            ]

            for column, value in enumerate(values):

                display_value = (
                    str(value)
                    if value not in (None, "")
                    else "-"
                )

                item = QTableWidgetItem(display_value)

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                self.table.setItem(
                    row,
                    column,
                    item
                )

            judgment_item = self.table.item(row, 5)

            if judgment_item:

                if judgment_item.text().upper() == "PASS":

                    judgment_item.setForeground(
                        Qt.darkGreen
                    )

                elif judgment_item.text().upper() in (
                    "FAIL",
                    "NG"
                ):

                    judgment_item.setForeground(
                        Qt.red
                    )

        self.result_label.setText(
            f"{len(self.results)} records found "
            "(maximum 500)"
        )

    # ==========================================
    # SELECTED RESULT
    # ==========================================

    def get_selected_result(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.information(
                self,
                "Select Record",
                "Please select a test record first."
            )

            return None

        result_id_item = self.table.item(row, 0)

        if result_id_item is None:
            return None

        result_id = int(
            result_id_item.text()
        )

        return self.database.get_result(result_id)

    # ==========================================
    # RESULT DETAIL
    # ==========================================

    def show_selected_detail(self):

        result = self.get_selected_result()

        if result is None:
            return

        dialog = QDialog(self)

        dialog.setWindowTitle(
            f"Test Result Detail - ID {result['id']}"
        )

        dialog.resize(750, 650)

        layout = QVBoxLayout(dialog)

        heading = QLabel(
            f"TEST RESULT #{result['id']}"
        )

        heading.setObjectName("PageTitle")

        layout.addWidget(heading)

        detail_editor = QPlainTextEdit()

        detail_editor.setReadOnly(True)

        detail_editor.setLineWrapMode(
            QPlainTextEdit.NoWrap
        )

        detail_editor.setPlainText(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )

        layout.addWidget(detail_editor, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Close
        )

        buttons.rejected.connect(
            dialog.reject
        )

        buttons.accepted.connect(
            dialog.accept
        )

        layout.addWidget(buttons)

        dialog.exec()
