from app.workflows.instrument_measurement_step import (
    InstrumentMeasurementStep
)

from PySide6.QtCore import QObject, Signal, QTimer

from app.core.workflow_context import WorkflowContext
from app.core.step_registry import StepRegistry

from app.workflows.base_step import StepOutcome
from app.workflows.instrument_test_step import InstrumentTestStep

from app.instruments.instrument_manager import InstrumentManager
from app.database.database_manager import DatabaseManager
from app.services.logging_service import LoggingService
from app.instruments.measurement_worker import MeasurementWorker


class WorkflowEngine(QObject):

    log_message = Signal(str, str)

    step_started = Signal(int, int, str)
    step_finished = Signal(int, str)

    interaction_requested = Signal(dict)

    finished = Signal()
    failed = Signal(str)

    measurement_sample = Signal(dict, int, float, bool)
    measurement_completed = Signal(dict)
    measurement_failed = Signal(str)


    def __init__(
        self,
        model_configuration,
        operator,
        parent=None,
        initial_data=None
    ):

        super().__init__(parent)

        self.model_configuration = model_configuration

        # --------------------------------------
        # MODEL CONFIGURATION
        # --------------------------------------

        self.model = model_configuration["model"]

        self.sequence_configuration = (
            model_configuration["sequence"]
        )

        self.parameter_configuration = (
            model_configuration["parameters"]
        )

        self.application_configuration = (
            model_configuration["application"]
        )

        self.instrument_catalog = (
            model_configuration["instrument_catalog"]
        )

        self.application_mode = (
            self.application_configuration.get(
                "application_mode",
                "SIMULATION"
            )
        )

        # --------------------------------------
        # WORKFLOW CONTEXT
        # --------------------------------------

        initial_data = dict(initial_data or {})

        initial_data.update({
            "model_id": self.model.get("model_id"),
            "model_name": self.model.get("model_name"),
            "sequence_id": (
                self.sequence_configuration.get("sequence_id")
            ),
            "application_mode": self.application_mode,
        })

        self.context = WorkflowContext(
            operator,
            initial_data
        )

        # --------------------------------------
        # REGISTRIES AND SERVICES
        # --------------------------------------

        self.registry = StepRegistry()

        self.instrument_manager = InstrumentManager(
            model_configuration["instruments"],
            self.instrument_catalog,
            self.application_configuration
        )

        self.database = DatabaseManager()
        self.logger = LoggingService()

        # --------------------------------------
        # SEQUENCE
        # --------------------------------------

        self.steps = self.sequence_configuration.get(
            "steps",
            []
        )

        self.index = 0
        self.current_step = None
        self.current_configuration = None

        self.running = False
        self.waiting = False
        self.measurement_workers = []

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)

        self.timer.timeout.connect(
            self.execute_next
        )

    @property
    def is_running(self):

        return self.running

    # ==========================================
    # WORKFLOW CONTROL
    # ==========================================

    def start(self):

        if self.running:
            return

        if not self.steps:
            self.failed.emit(
                "Sequence has no steps."
            )
            return

        self.index = 0
        self.running = True
        self.waiting = False

        self.log(
            "SYSTEM",
            f"Workflow started in {self.application_mode} mode."
        )

        self.timer.start(0)

    def log(self, category, message):

        self.log_message.emit(
            category,
            message
        )

        self.logger.info(
            f"[{category}] {message}"
        )

    # ==========================================
    # STEP EXECUTION
    # ==========================================

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
                f"Skipping disabled step: "
                f"{configuration.get('name')}"
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

            elif isinstance(
                self.current_step,
                InstrumentMeasurementStep
            ):

                self.execute_instrument_measurement()
                return

            else:
                outcome = self.current_step.execute(
                    self.context
                )

            self.process_outcome(outcome)

        except Exception as error:

            self.fail(str(error))

    # ==========================================
    # INSTRUMENT TEST EXECUTION
    # ==========================================


    def execute_instrument_test(self):

        parameters = self.current_configuration.get(
            "parameters",
            {}
        )

        instrument_id = parameters.get("instrument")
        function = parameters.get("function")

        if not instrument_id or not function:
            raise ValueError(
                "Instrument ID or function is missing."
            )

        # --------------------------------------
        # HARDWARE SAFETY VALIDATION
        # --------------------------------------

        if self.application_mode == "HARDWARE":

            if (
                self.parameter_configuration.get(
                    "configuration_status"
                ) != "APPROVED"
                or self.parameter_configuration.get(
                    "hardware_approved"
                ) is not True
            ):
                raise RuntimeError(
                    "Hardware test is blocked. "
                    "Test configuration has not been approved."
                )

        # --------------------------------------
        # LOAD MODEL TEST PARAMETERS
        # --------------------------------------

        test_parameter_groups = (
            self.parameter_configuration.get(
                "test_parameters",
                {}
            )
        )

        function_groups = {
            "acw": "acw",
            "ecac": "ecac",
            "ecdc": "ecdc"
        }

        parameter_group = function_groups.get(function)

        if parameter_group is None:
            raise ValueError(
                f"Unsupported instrument test function: {function}"
            )

        test_parameters = dict(
            self.parameter_configuration.get(
                "limits",
                {}
            )
        )

        configured_parameters = test_parameter_groups.get(
            parameter_group,
            {}
        )

        if not isinstance(configured_parameters, dict):
            raise ValueError(
                f"Invalid test parameter group: {parameter_group}"
            )

        test_parameters.update(configured_parameters)

        # Allow explicit step-level overrides.
        step_parameters = parameters.get(
            "test_parameters",
            {}
        )

        if not isinstance(step_parameters, dict):
            raise ValueError(
                "Step test_parameters must be an object."
            )

        test_parameters.update(step_parameters)

        # --------------------------------------
        # CONNECT AND EXECUTE
        # --------------------------------------

        self.log(
            "INSTRUMENT",
            f"{self.application_mode}: connecting "
            f"{instrument_id}"
        )

        connected = False

        try:

            connected = self.instrument_manager.connect(
                instrument_id
            )

            if connected is False:
                raise RuntimeError(
                    f"Could not connect instrument: {instrument_id}"
                )

            result = self.instrument_manager.execute_test(
                instrument_id,
                function,
                test_parameters
            )

        finally:

            if connected:
                self.instrument_manager.disconnect(
                    instrument_id
                )

        if not isinstance(result, dict):
            raise TypeError(
                "Instrument test result must be a dictionary."
            )

        if result.get("simulation") is not True:
            if self.application_mode == "SIMULATION":
                raise RuntimeError(
                    "Simulation mode received a non-simulation result."
                )

        # --------------------------------------
        # STORE INDIVIDUAL TEST RESULT
        # --------------------------------------

        measurements = self.context.get(
            "measurements",
            {}
        )

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        measurements[step_id] = result

        self.context.set(
            "measurements",
            measurements
        )

        # --------------------------------------
        # AGGREGATE TEST JUDGMENT
        # --------------------------------------

        test_judgments = self.context.get(
            "test_judgments",
            {}
        )

        test_judgments[step_id] = result.get(
            "judgment"
        )

        self.context.set(
            "test_judgments",
            test_judgments
        )

        judgments = list(test_judgments.values())

        if "FAIL" in judgments:
            overall_judgment = "FAIL"

        elif judgments and all(
            judgment == "PASS"
            for judgment in judgments
        ):
            overall_judgment = "PASS"

        else:
            overall_judgment = None

        self.context.set(
            "judgment",
            overall_judgment
        )

        self.log(
            "MEASUREMENT",
            f"{function}: {result.get('judgment')}"
        )

        self.log(
            "JUDGMENT",
            f"Overall judgment: {overall_judgment}"
        )

        return StepOutcome(
            success=True,
            message=f"{function} test completed.",
            interaction={
                "type": "measurement",
                "result": result
            },
            data=result
        )

    # ==========================================
    # INSTRUMENT MEASUREMENT EXECUTION
    # ==========================================

    def execute_instrument_measurement(self):

        parameters = self.current_configuration.get("parameters", {})

        instrument_id = parameters.get("instrument")

        if not instrument_id:
            raise ValueError("Instrument ID is required.")

        duration_s = float(parameters.get("duration_s", 10))
        sample_interval_s = float(parameters.get("sample_interval_s", 1))

        measurement_ids = parameters.get("measurements")

        if duration_s <= 0:
            raise ValueError("Measurement duration must be greater than zero.")

        if sample_interval_s <= 0:
            raise ValueError("Sample interval must be greater than zero.")

        self.log(
            "INFO",
            f"Starting live measurement: {instrument_id}"
        )

        worker = MeasurementWorker(
            model_instruments=self.model_configuration["instruments"],
            instrument_catalog=self.instrument_catalog,
            application_configuration=self.application_configuration,
            instrument_id=instrument_id,
            duration_s=duration_s,
            sample_interval_s=sample_interval_s,
            measurement_ids=measurement_ids
        )

        self.measurement_workers.append(worker)

        # Connect worker signals.
        worker.sample_received.connect(
            self.measurement_sample.emit
        )

        worker.measurement_completed.connect(
            self.on_instrument_measurement_completed
        )

        worker.measurement_failed.connect(
            self.on_instrument_measurement_failed
        )

        worker.finished.connect(
            lambda w=worker: self.cleanup_measurement_worker(w)
        )

        # Start worker first, before opening the modal dialog.
        QTimer.singleShot(0, worker.start)

        # Then request Dashboard to open the live measurement dialog.
        self.interaction_requested.emit({
            "type": "live_measurement",
            "instrument": instrument_id,
            "duration_s": duration_s,
            "sample_interval_s": sample_interval_s
        })


    def on_instrument_measurement_completed(self, result):

        if not self.running:
            return

        measurements = self.context.get(
            "measurements",
            {}
        )

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        measurements[step_id] = result

        self.context.set(
            "measurements",
            measurements
        )

        measured_values = result.get(
            "measurements",
            {}
        )

        for measurement_id, measurement in measured_values.items():

            self.log(
                "MEASUREMENT",
                f"{measurement_id}: "
                f"{measurement.get('value')} "
                f"{measurement.get('unit', '')}"
            )

        self.log(
            "INSTRUMENT",
            f"Measurement completed. "
            f"Samples: {result.get('sample_count', 0)}"
        )

        self.measurement_completed.emit(result)

        self.finish_current_step(
            StepOutcome(
                success=True,
                message=(
                    f"Measurement completed: "
                    f"{result.get('instrument')}"
                ),
                data=result
            )
        )


    def on_instrument_measurement_failed(self, message):

        if not self.running:
            return

        self.measurement_failed.emit(message)
        self.fail(message)


    def cleanup_measurement_worker(self, worker):

        if worker in self.measurement_workers:
            self.measurement_workers.remove(worker)

        worker.deleteLater()
        
    # ==========================================
    # INTERACTION HANDLING
    # ==========================================

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

    # ==========================================
    # STEP COMPLETION
    # ==========================================

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

    # ==========================================
    # WORKFLOW COMPLETION
    # ==========================================

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

    # ==========================================
    # ERROR AND ABORT
    # ==========================================

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

        # Request background measurement workers to stop.
        for worker in self.measurement_workers:
            worker.request_stop()

        self.log(
            "ABORT",
            "Workflow aborted by operator."
        )