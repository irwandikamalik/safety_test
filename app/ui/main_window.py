from pathlib import Path

from PySide6.QtGui import QIcon

from PySide6.QtCore import QTimer, QSize

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QMessageBox
)

from app.ui.dashboard import DashboardPage
from app.ui.configuration_page import ConfigurationPage
from app.ui.dialogs import OperatorDialog
from app.ui.history_page import HistoryPage
from app.ui.instrument_configuration_page import InstrumentConfigurationPage


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Industrial Safety Test Platform"
        )

        self.asset_root = (
            Path(__file__).resolve().parents[2] / "assets"
        )

        self.icon_root = self.asset_root / "icons"

        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)

        self.operator = None
        self.nav_buttons = []

        self.build_ui()
        self.show_operator_login()

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # SIDEBAR

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(225)

        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 20, 14, 16)

        brand = QLabel("INDUSTRIAL\nSAFETY TEST")
        brand.setObjectName("Brand")
        side_layout.addWidget(brand)

        version = QLabel("PLATFORM  |  WORKFLOW ENGINE")
        version.setStyleSheet(
            "color: #8295AD; font-size: 8pt;"
        )
        side_layout.addWidget(version)

        side_layout.addSpacing(25)

        caption = QLabel("WORKSPACE")
        caption.setObjectName("SidebarCaption")
        side_layout.addWidget(caption)

        self.create_nav_button(
            "Test Execution", 0, side_layout, "test-execution.svg"
        )

        self.create_nav_button(
            "Test History", 1, side_layout, "test-history.svg"
        )

        side_layout.addSpacing(15)

        caption = QLabel("CONFIGURATION")
        caption.setObjectName("SidebarCaption")
        side_layout.addWidget(caption)

        self.create_nav_button(
            "Model Configuration", 2, side_layout, "model-configuration.svg"
        )

        self.create_nav_button(
            "Serial Mapping", 3, side_layout, "serial-mapping.svg"
        )

        self.create_nav_button(
            "Sequence JSON", 4, side_layout, "workflow-editor.svg"
        )

        self.create_nav_button(
            "Instrument Configuration", 5, side_layout,
            "instrument-configuration.svg"
        )

        side_layout.addStretch()

        self.operator_side_label = QLabel(
            "Operator: Not logged in"
        )

        self.operator_side_label.setStyleSheet(
            "color: #BDC9D8; padding: 7px;"
        )

        self.operator_side_label.setWordWrap(True)

        side_layout.addWidget(
            self.operator_side_label
        )

        logout_button = QPushButton("Logout")

        logout_icon = self.icon_root / "logout.svg"

        if logout_icon.is_file():
            logout_button.setIcon(QIcon(str(logout_icon)))
            logout_button.setIconSize(QSize(20, 20))

        logout_button.clicked.connect(self.logout)

        logout_button.setStyleSheet("""
            background: #263A55;
            color: white;
            border: 1px solid #344B68;
            text-align: left;
            padding: 10px;
        """)

        side_layout.addWidget(logout_button)

        # MAIN CONTENT

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(58)

        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 0, 22, 0)

        self.page_heading = QLabel("Test Execution")

        self.page_heading.setStyleSheet(
            "font-weight: bold; font-size: 11pt;"
        )

        self.session_label = QLabel("Session: -")
        self.session_label.setObjectName("Muted")

        top_layout.addWidget(self.page_heading)
        top_layout.addStretch()
        top_layout.addWidget(self.session_label)

        right_layout.addWidget(topbar)

        # PAGE STACK

        self.stack = QStackedWidget()

        self.dashboard = DashboardPage()

        self.history_page = HistoryPage()


        # ==========================================
        # CONFIGURATION PAGES
        # ==========================================

        self.model_page = ConfigurationPage(
            "Model Configuration",
            [
                (
                    "Model",
                    "models/MODEL-A/model.json"
                ),
                (
                    "Parameters",
                    "models/MODEL-A/parameters.json"
                )
            ]
        )

        self.mapping_page = ConfigurationPage(
            "Serial Mapping Configuration",
            [
                (
                    "Serial Mapping",
                    "global/serial_model_mapping.json"
                )
            ]
        )

        self.sequence_page = ConfigurationPage(
            "Sequence Configuration",
            [
                (
                    "MODEL-A",
                    "models/MODEL-A/sequence.json"
                )
            ]
        )

        self.instrument_page = InstrumentConfigurationPage()

        pages = [
            self.dashboard,
            self.history_page,
            self.model_page,
            self.mapping_page,
            self.sequence_page,
            self.instrument_page
        ]

        for page in pages:
            self.stack.addWidget(page)

        right_layout.addWidget(self.stack, 1)

        main_layout.addWidget(sidebar)
        main_layout.addLayout(right_layout, 1)

        # STATUS BAR

        status = QStatusBar()

        status.showMessage(
            "Workflow Engine | Simulation Mode | No Hardware Connected"
        )

        self.setStatusBar(status)

    def create_nav_button(
        self,
        text,
        index,
        layout,
        icon_filename=None
    ):
        button = QPushButton(text)
        button.setObjectName("NavButton")
        button.setCheckable(True)

        if icon_filename:
            icon_path = self.icon_root / icon_filename

            if icon_path.is_file():
                button.setIcon(QIcon(str(icon_path)))
                button.setIconSize(QSize(20, 20))
            else:
                print(f"Icon not found: {icon_path}")

        button.clicked.connect(
            lambda checked=False, i=index: self.navigate(i)
        )

        layout.addWidget(button)
        self.nav_buttons.append(button)

    def navigate(self, index):

        if not self.operator:

            QMessageBox.warning(
                self,
                "Operator Required",
                "Please login first."
            )

            return

        self.stack.setCurrentIndex(index)

        if index == 1:
            self.history_page.refresh_history()

        titles = [
            "Test Execution",
            "Test History",
            "Model Configuration",
            "Serial Mapping Configuration",
            "Sequence Configuration",
            "Instrument Configuration"
        ]
        
        self.page_heading.setText(titles[index])

        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def show_operator_login(self):

        dialog = OperatorDialog(self)

        if dialog.exec():

            self.operator = dialog.operator

            self.dashboard.set_operator(
                self.operator
            )

            self.operator_side_label.setText(
                f'Operator: {self.operator["name"]}\n'
                f'ID: {self.operator["id"]}'
            )

            self.session_label.setText(
                f'{self.operator["name"]} - '
                f'{self.operator["id"]}'
            )

            QTimer.singleShot(
                0,
                self.dashboard.serial_input.setFocus
            )

        elif self.operator is None:

            self.close()

    def logout(self):

        engine = self.dashboard.engine

        if engine and engine.is_running:

            QMessageBox.warning(
                self,
                "Sequence Running",
                "Abort sequence before logout."
            )

            return

        answer = QMessageBox.question(
            self,
            "Logout",
            "End current operator session?",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.Yes:

            self.operator = None

            self.operator_side_label.setText(
                "Operator: Not logged in"
            )

            self.session_label.setText(
                "Session: -"
            )

            self.show_operator_login()
