
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


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Industrial Safety Test Platform"
        )

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
            "Test Execution", 0, side_layout
        )

        side_layout.addSpacing(15)

        caption = QLabel("CONFIGURATION")
        caption.setObjectName("SidebarCaption")
        side_layout.addWidget(caption)

        self.create_nav_button(
            "Sequence JSON", 1, side_layout
        )

        self.create_nav_button(
            "Instruments JSON", 2, side_layout
        )

        self.create_nav_button(
            "Parameters JSON", 3, side_layout
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

        logout_button.setStyleSheet("""
            background: #263A55;
            color: white;
            border: 1px solid #344B68;
            text-align: left;
            padding: 10px;
        """)

        logout_button.clicked.connect(self.logout)
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

        self.sequence_page = ConfigurationPage(
            "Sequence Configuration",
            [
                (
                    "Safety Test",
                    "sequences/safety_test.json"
                )
            ]
        )

        self.instrument_page = ConfigurationPage(
            "Instrument Configuration",
            [
                (
                    "Instruments",
                    "instruments/instruments.json"
                )
            ]
        )

        self.parameter_page = ConfigurationPage(
            "Test Parameters",
            [
                (
                    "Model A",
                    "parameters/model_a.json"
                )
            ]
        )

        pages = [
            self.dashboard,
            self.sequence_page,
            self.instrument_page,
            self.parameter_page
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

    def create_nav_button(self, text, index, layout):

        button = QPushButton(text)
        button.setObjectName("NavButton")
        button.setCheckable(True)

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

        titles = [
            "Test Execution",
            "Sequence Configuration",
            "Instrument Configuration",
            "Test Parameters"
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

            self.navigate(0)

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
