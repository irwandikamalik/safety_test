
from PySide6.QtCore import QObject, Signal, QTimer

from app.core.workflow_context import WorkflowContext
from app.core.step_registry import StepRegistry

from app.workflows.base_step import StepOutcome
from app.workflows.instrument_test_step import InstrumentTestStep

from app.instruments.instrument_manager import InstrumentManager
from app.database.database_manager import DatabaseManager
from app.services.logging_service import LoggingService


class WorkflowEngine(QObject):

    log_message = Signal(str, str)

    step_started = Signal(int, int, str)
    step_finished = Signal(int, str)

    interaction_requested = Signal(dict)

    finished = Signal()
    failed = Signal(str)

    def __init__(
        self,
        sequence_configuration,
        instrument_configuration,
        parameter_configuration,
        operator,
        parent=None
    ):

        super().__init__(parent)

        self.sequence_configuration = sequence_configuration
        self.parameter_configuration = parameter_configuration

        self.context = WorkflowContext(operator)

        self.registry = StepRegistry()

        self.instrument_manager = InstrumentManager(
            instrument_configuration
        )

        self.database = DatabaseManager()
        self.logger = LoggingService()

        self.steps = sequence_configuration.get(
            "steps", []
        )

        self.index = 0
        self.current_step = None
        self.current_configuration = None

        self.running = False
        self.waiting = False

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)

        self.timer.timeout.connect(
            self.execute_next
        )

    @property
    def is_running(self):
        return self.running

    def start(self):

        if self.running:
            return

        if not self.steps:
            self.failed.emit("Sequence has no steps.")
            return

        self.index = 0
        self.running = True
        self.waiting = False

        self.log("SYSTEM", "Workflow started.")

        self.timer.start(0)

    def log(self, category, message):

        self.log_message.emit(category, message)

        self.logger.info(
            f"[{category}] {message}"
        )

    def execute_next(self):

        if not self.running:
            return

        if self.index >= len(self.steps):

            self.complete_workflow()
            return

        configuration = self.steps[self.index]

        if not configuration.get("enabled", True):

            self.log(
                "SYSTEM",
                f"Skipping disabled step: {configuration.get('name')}"
            )

            self.index += 1
            self.timer.start(0)

            return

        try:

            self.current_configuration = configuration

            self.current_step = self.registry.create(
                configuration
            )

            name = configuration.get(
                "name",
                configuration.get("id", "Unnamed Step")
            )

            self.step_started.emit(
                self.index + 1,
                len(self.steps),
                name
            )

            self.log("STEP", name)

            if isinstance(
                self.current_step,
                InstrumentTestStep
            ):

                outcome = self.execute_instrument_test()

            else:

                outcome = self.current_step.execute(
                    self.context
                )

            self.process_outcome(outcome)

        except Exception as error:

            self.fail(str(error))

    def execute_instrument_test(self):

        parameters = self.current_configuration.get(
            "parameters", {}
        )

        instrument_id = parameters.get("instrument")
        function = parameters.get("function")

        if not instrument_id or not function:
            raise ValueError(
                "Instrument ID or function is missing."
            )

        self.log(
            "INSTRUMENT",
            f"Simulation: connecting {instrument_id}"
        )

        self.instrument_manager.connect(instrument_id)

        try:

            model_limits = self.parameter_configuration.get(
                "limits", {}
            )

            test_parameters = dict(model_limits)

            test_parameters.update(
                parameters.get("test_parameters", {})
            )

            result = self.instrument_manager.execute_test(
                instrument_id,
                function,
                test_parameters
            )

        finally:

            self.instrument_manager.disconnect(
                instrument_id
            )

        self.context.set(
            "measurements",
            result
        )

        self.context.set(
            "judgment",
            result["judgment"]
        )

        self.log(
            "MEASUREMENT",
            f"Judgment: {result['judgment']}"
        )

        return StepOutcome(
            success=True,
            message="Simulation measurement completed.",
            interaction={
                "type": "measurement",
                "result": result
            },
            data=result
        )

    def process_outcome(self, outcome):

        if not isinstance(outcome, StepOutcome):
            raise TypeError(
                "Step must return StepOutcome."
            )

        if not outcome.success:
            self.fail(outcome.message)
            return

        if outcome.interaction:

            self.waiting = True

            self.interaction_requested.emit(
                outcome.interaction
            )

            return

        self.finish_current_step(outcome)

    def submit_interaction(self, response):

        if not self.running or not self.waiting:
            return

        try:

            outcome = self.current_step.complete(
                self.context,
                response
            )

            self.waiting = False

            if not outcome.success:
                self.fail(outcome.message)
                return

            self.finish_current_step(outcome)

        except Exception as error:

            self.fail(str(error))

    def finish_current_step(self, outcome):

        self.log(
            "SUCCESS",
            outcome.message
        )

        self.step_finished.emit(
            self.index + 1,
            outcome.message
        )

        self.index += 1

        self.timer.start(0)

    def complete_workflow(self):

        try:

            self.database.save_result(
                self.context.as_dict()
            )

            self.log(
                "DATABASE",
                "Test result saved."
            )

            self.running = False
            self.waiting = False

            self.log(
                "DONE",
                "Workflow completed successfully."
            )

            self.finished.emit()

        except Exception as error:

            self.fail(
                f"Database save failed: {error}"
            )

    def fail(self, message):

        self.timer.stop()

        self.running = False
        self.waiting = False

        self.log("ERROR", message)

        self.failed.emit(message)

    def stop(self):

        if not self.running:
            return

        self.timer.stop()

        self.running = False
        self.waiting = False

        self.log(
            "ABORT",
            "Workflow aborted by operator."
        )
