
APP_STYLE = """


/* ==========================================
   SEQUENCE CONFIGURATION
========================================== */

QGroupBox#SequenceModelGroup {
    background-color: white;
    color: #263449;
    border: 1px solid #E0E6ED;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: bold;
}

QGroupBox#SequenceModelGroup::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: #263449;
    background-color: #F3F5F8;
}

QComboBox#SequenceModelSelector {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 7px 10px;
    min-height: 22px;
}

QComboBox#SequenceModelSelector:hover {
    border: 1px solid #AABBCD;
}

QComboBox#SequenceModelSelector:focus {
    border: 1px solid #287FC0;
}

QComboBox#SequenceModelSelector::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid #CCD5E0;
    background-color: #F6F8FB;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox#SequenceModelSelector QAbstractItemView {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    selection-background-color: #1769AA;
    selection-color: white;
    outline: none;
    padding: 4px;
}

QComboBox#SequenceModelSelector QAbstractItemView::item {
    min-height: 30px;
    padding: 5px 8px;
}

QComboBox#SequenceModelSelector QAbstractItemView::item:hover {
    background-color: #E8EDF3;
    color: #263449;
}

/* ==========================================
   GLOBAL
========================================== */

QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #263449;
}

QMainWindow {
    background: #F3F5F8;
}

/* ==========================================
   SIDEBAR
========================================== */

QFrame#Sidebar {
    background-color: #17263B;
    border: none;
}

QFrame#Sidebar QWidget {
    background-color: transparent;
}

QLabel#Brand {
    color: white;
    background: transparent;
    font-size: 16pt;
    font-weight: bold;
}

QLabel#SidebarCaption {
    color: #91A2B9;
    background: transparent;
    font-size: 8pt;
    font-weight: bold;
}

QPushButton#NavButton {
    background: transparent;
    color: #C7D2E1;
    border: none;
    text-align: left;
    padding: 11px;
    border-radius: 6px;
}

QPushButton#NavButton:hover {
    background: #263A55;
    color: white;
}

QPushButton#NavButton:checked {
    background: #245B91;
    color: white;
    font-weight: bold;
}

/* ==========================================
   TOP BAR
========================================== */

QFrame#TopBar {
    background-color: white;
    border: none;
    border-bottom: 1px solid #DFE5EC;
}

QFrame#TopBar QWidget {
    background-color: transparent;
}

QLabel#PageTitle {
    font-size: 17pt;
    font-weight: bold;
    color: #1D2B40;
    background: transparent;
}

QLabel#Muted {
    color: #738197;
    background: transparent;
}

/* ==========================================
   CONTENT PANEL
========================================== */

QFrame#Panel {
    background: white;
    border: 1px solid #E0E6ED;
    border-radius: 9px;
}

/* ==========================================
   BUTTONS
========================================== */

QPushButton {
    background: #E8EDF3;
    color: #26374D;
    border: 1px solid #D6DEE8;
    border-radius: 6px;
    padding: 8px 13px;
}

QPushButton:hover {
    background: #DCE6F0;
}

QPushButton#PrimaryButton {
    background: #1769AA;
    color: white;
    border: none;
    font-weight: bold;
}

QPushButton#SuccessButton {
    background: #16805D;
    color: white;
    border: none;
    font-weight: bold;
}

QPushButton#DangerButton {
    background: #B93838;
    color: white;
    border: none;
    font-weight: bold;
}

/* ==========================================
   INPUT
========================================== */

QLineEdit {
    background: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 9px;
}

QLineEdit:focus {
    border: 1px solid #287FC0;
}

/* ==========================================
   TERMINAL / JSON EDITOR
========================================== */

QTextEdit, QPlainTextEdit {
    background: #101A27;
    color: #D6E1EE;
    border: 1px solid #26374D;
    border-radius: 7px;
    padding: 10px;
    font-family: Consolas;
    font-size: 9pt;
}

/* ==========================================
   TABLE
========================================== */

QTableWidget {
    background: white;
    alternate-background-color: #F6F8FB;
    color: #263449;
    border: 1px solid #E0E6ED;
    gridline-color: #EDF0F4;
}

QHeaderView::section {
    background: #EDF2F7;
    color: #263449;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* ==========================================
   PROGRESS
========================================== */

QProgressBar {
    background: #E7EDF3;
    border: none;
    border-radius: 5px;
    height: 10px;
}

QProgressBar::chunk {
    background: #16805D;
    border-radius: 5px;
}

/* ==========================================
   TABS
========================================== */

QTabWidget::pane {
    border: 1px solid #DFE5EC;
    background: white;
}

QTabBar::tab {
    background: #E8EDF3;
    color: #263449;
    padding: 9px 16px;
}

QTabBar::tab:selected {
    background: #1769AA;
    color: white;
}


/* ==========================================
   INSTRUMENT CONFIGURATION PAGE
========================================== */

QScrollArea#InstrumentConfigurationScrollArea {
    background-color: #F3F5F8;
    border: none;
}

QWidget#InstrumentConfigurationContent {
    background-color: #F3F5F8;
}

QWidget#InstrumentConfigurationContent QGroupBox {
    background-color: white;
    color: #263449;
    border: 1px solid #E0E6ED;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: bold;
}

QWidget#InstrumentConfigurationContent QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: #263449;
    background-color: #F3F5F8;
}

QWidget#InstrumentConfigurationContent QLineEdit,
QWidget#InstrumentConfigurationContent QComboBox,
QWidget#InstrumentConfigurationContent QSpinBox {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 7px;
    min-height: 20px;
}

QWidget#InstrumentConfigurationContent QLineEdit:focus,
QWidget#InstrumentConfigurationContent QComboBox:focus,
QWidget#InstrumentConfigurationContent QSpinBox:focus {
    border: 1px solid #287FC0;
}

QWidget#InstrumentConfigurationContent QComboBox QAbstractItemView {
    background-color: white;
    color: #263449;
    selection-background-color: #1769AA;
    selection-color: white;
    border: 1px solid #CCD5E0;
}

QWidget#InstrumentConfigurationContent QCheckBox {
    background-color: transparent;
    color: #263449;
    spacing: 8px;
    padding: 5px;
}

QWidget#InstrumentConfigurationContent QTableWidget {
    background-color: white;
    alternate-background-color: #F6F8FB;
    color: #263449;
    border: 1px solid #E0E6ED;
    gridline-color: #EDF0F4;
    selection-background-color: #DCEAF7;
    selection-color: #263449;
}

QWidget#InstrumentConfigurationContent QHeaderView::section {
    background-color: #EDF2F7;
    color: #263449;
    padding: 8px;
    border: none;
    font-weight: bold;
}

QWidget#InstrumentConfigurationContent QTabWidget::pane {
    background-color: white;
    border: 1px solid #DFE5EC;
}

QWidget#InstrumentConfigurationContent QTabBar::tab {
    background-color: #E8EDF3;
    color: #263449;
    padding: 9px 16px;
}

QWidget#InstrumentConfigurationContent QTabBar::tab:selected {
    background-color: #1769AA;
    color: white;
}

/* ==========================================
   MODEL MANAGEMENT
========================================== */

QDialog QTextEdit#ModelDescriptionInput {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 9px;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QDialog QTextEdit#ModelDescriptionInput:focus {
    border: 1px solid #287FC0;
}

QDialog QComboBox#ModelTemplateSelector {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 7px;
    min-height: 20px;
}

QDialog QComboBox#ModelTemplateSelector:focus {
    border: 1px solid #287FC0;
}

QDialog QComboBox#ModelTemplateSelector QAbstractItemView {
    background-color: white;
    color: #263449;
    selection-background-color: #1769AA;
    selection-color: white;
    border: 1px solid #CCD5E0;
    outline: none;
}

/* ==========================================
   STATUS BAR
========================================== */

QStatusBar {
    background: white;
    color: #68788D;
}

QStatusBar QLabel {
    background: transparent;
}

/* ==========================================
   DIALOG WINDOWS
========================================== */

QDialog {
    background-color: #F3F5F8;
    color: #263449;
}

QDialog QWidget {
    color: #263449;
}

QDialog QLabel {
    background-color: transparent;
    color: #263449;
}

QDialog QLineEdit {
    background-color: white;
    color: #263449;
    border: 1px solid #CCD5E0;
    border-radius: 6px;
    padding: 9px;
}

QDialog QPushButton {
    background-color: #E8EDF3;
    color: #26374D;
    border: 1px solid #D6DEE8;
    border-radius: 6px;
    padding: 8px 13px;
}

QDialog QPushButton:hover {
    background-color: #DCE6F0;
}

QDialog QPushButton#PrimaryButton {
    background-color: #1769AA;
    color: white;
    border: none;
}

QDialog QPushButton#SuccessButton {
    background-color: #16805D;
    color: white;
    border: none;
}

QDialog QPushButton#DangerButton {
    background-color: #B93838;
    color: white;
    border: none;
}
"""
