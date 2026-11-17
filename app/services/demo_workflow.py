from PySide6.QtCore import QObject, Signal, QTimer


class DemoWorkflow(QObject):

    log_message = Signal(str, str)
    step_changed = Signal(int, int, str)
    finished = Signal()

    def __init__(self, parent=None):

        super().__init__(parent)

        self.steps = [
            ("Input Serial Number", "INPUT"),
            ("Validate Serial Number", "VALIDATION"),
            ("Input Door Top Barcode", "INPUT"),
            ("Validate Door Top Barcode", "VALIDATION"),
            ("Input Door Bottom Barcode", "INPUT"),
            ("Validate Door Bottom Barcode", "VALIDATION"),
            ("Operator Safety Approval", "APPROVAL"),
            ("Connect Kikusui TOS9302", "INSTRUMENT"),
            ("AC Withstanding Test", "MEASUREMENT"),
            ("Display Measurement Result", "RESULT"),
            ("Sequence Completed", "DONE")
        ]

        self.index = 0

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.execute_next
        )

    def start(self):

        self.index = 0

        self.log_message.emit(
            "SYSTEM",
            "Starting demonstration sequence."
        )

        self.timer.start(900)

    def stop(self):

        self.timer.stop()

        self.log_message.emit(
            "ABORT",
            "Sequence aborted by operator."
        )

    def execute_next(self):

        if self.index >= len(self.steps):

            self.timer.stop()
            self.finished.emit()

            return

        name, category = self.steps[self.index]

        self.step_changed.emit(
            self.index + 1,
            len(self.steps),
            name
        )

        self.log_message.emit(
            category,
            name
        )

        self.index += 1