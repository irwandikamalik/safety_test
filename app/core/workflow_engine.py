
from PySide6.QtCore import QObject, Signal, QTimer

from app.core.workflow_context import WorkflowContext
from app.core.step_registry import StepRegistry

from app.workflows.base_step import StepOutcome
from app.workflows.instrument_test_step import InstrumentTestStep
from app.workflows.instrument_measurement_step import InstrumentMeasurementStep

from app.instruments.instrument_manager import InstrumentManager
from app.instruments.measurement_worker import MeasurementWorker
from app.instruments.ac_volt_confirmation_worker import (
    ACVoltConfirmationWorker
)

from app.database.database_manager import DatabaseManager
from app.services.logging_service import LoggingService


class WorkflowEngine(QObject):

    log_message = Signal(str, str)

    step_started = Signal(int, int, str)
    step_finished = Signal(int, str)

    interaction_requested = Signal(dict)

    finished = Signal()
    failed = Signal(str)
    aborted = Signal(str)

    measurement_sample = Signal(dict, int, float, bool)
    measurement_completed = Signal(dict)
    measurement_failed = Signal(str)

    ac_volt_status_changed = Signal(str)
    ac_volt_configuration_ready = Signal(dict)
    ac_volt_sample_received = Signal(dict, int, float, bool)
    ac_volt_evaluation_passed = Signal(dict)
    ac_volt_completed = Signal(dict)
    ac_volt_failed = Signal(str)

    def __init__(
        self,
        model_configuration,
        operator,
        parent=None,
        initial_data=None
    ):

        super().__init__(parent)

        self.model_configuration = model_configuration

        self.model = model_configuration["model"]
        self.sequence_configuration = model_configuration["sequence"]
        self.parameter_configuration = model_configuration["parameters"]
        self.application_configuration = model_configuration["application"]
        self.instrument_catalog = model_configuration["instrument_catalog"]

        self.application_mode = (
            self.application_configuration.get(
                "application_mode",
                "SIMULATION"
            )
        )

        initial_data = dict(initial_data or {})

        initial_data.update({
            "model_id": self.model.get("model_id"),
            "model_name": self.model.get("model_name"),
            "sequence_id": self.sequence_configuration.get("sequence_id"),
            "application_mode": self.application_mode
        })

        self.context = WorkflowContext(
            operator,
            initial_data
        )

        self.registry = StepRegistry()

        self.instrument_manager = InstrumentManager(
            model_configuration["instruments"],
            self.instrument_catalog,
            self.application_configuration
        )

        self.database = DatabaseManager()
        self.logger = LoggingService()

        self.steps = self.sequence_configuration.get("steps", [])

        self.index = 0
        self.current_step = None
        self.current_configuration = None

        self.running = False
        self.waiting = False

        self.measurement_workers = []

        self.ac_volt_worker = None
        self.ac_volt_abort_requested = False

        self.stop_after_interaction = False
        self.result_saved = False

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.execute_next)

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
            self.failed.emit("Sequence has no steps.")
            return

        self.index = 0
        self.running = True
        self.waiting = False

        self.result_saved = False
        self.stop_after_interaction = False
        self.ac_volt_abort_requested = False

        self.log(
            "SYSTEM",
            f"Workflow started in {self.application_mode} mode."
        )

        self.timer.start(0)

    def log(self, category, message):

        self.log_message.emit(category, message)

        self.logger.info(
            f"[{category}] {message}"
        )

    # ==========================================
    # RESULT MANAGEMENT
    # ==========================================

    def store_measurement_result(self, step_id, result):

        measurements = self.context.get("measurements", {})

        measurements[step_id] = result

        self.context.set("measurements", measurements)

    def update_judgment(self, step_id, judgment):

        test_judgments = self.context.get(
            "test_judgments",
            {}
        )

        test_judgments[step_id] = judgment

        self.context.set(
            "test_judgments",
            test_judgments
        )

        normalized = [
            str(value).upper()
            for value in test_judgments.values()
        ]

        if any(value in ("FAIL", "NG") for value in normalized):
            overall = "FAIL"

        elif normalized and all(value == "PASS" for value in normalized):
            overall = "PASS"

        else:
            overall = None

        self.context.set("judgment", overall)

        return overall

    def save_result(self, judgment=None):

        if self.result_saved:
            return

        if judgment is not None:
            self.context.set("judgment", judgment)

        self.database.save_result(
            self.context.as_dict()
        )

        self.result_saved = True

        self.log(
            "DATABASE",
            "Test result saved."
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
                f"Skipping disabled step: {configuration.get('name')}"
            )

            self.index += 1
            self.timer.start(0)
            return

        try:

            self.current_configuration = configuration

            self.current_step = self.registry.create(configuration)

            self.stop_after_interaction = False

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

            if isinstance(self.current_step, InstrumentTestStep):

                outcome = self.execute_instrument_test()

            elif isinstance(self.current_step, InstrumentMeasurementStep):

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

        test_parameter_groups = (
            self.parameter_configuration.get(
                "test_parameters",
                {}
            )
        )

        parameter_group = {
            "acw": "acw",
            "ecac": "ecac",
            "ecdc": "ecdc"
        }.get(function)

        if parameter_group is None:
            raise ValueError(
                f"Unsupported instrument test function: {function}"
            )

        test_parameters = dict(
            self.parameter_configuration.get("limits", {})
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

        step_parameters = parameters.get(
            "test_parameters",
            {}
        )

        if not isinstance(step_parameters, dict):
            raise ValueError(
                "Step test_parameters must be an object."
            )

        test_parameters.update(step_parameters)

        self.log(
            "INSTRUMENT",
            f"{self.application_mode}: connecting {instrument_id}"
        )

        connected = False

        try:

            connected = self.instrument_manager.connect(instrument_id)

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
                self.instrument_manager.disconnect(instrument_id)

        if not isinstance(result, dict):
            raise TypeError(
                "Instrument test result must be a dictionary."
            )

        if (
            result.get("simulation") is not True
            and self.application_mode == "SIMULATION"
        ):
            raise RuntimeError(
                "Simulation mode received a non-simulation result."
            )

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        judgment = str(
            result.get("judgment", "")
        ).upper()

        if judgment not in ("PASS", "FAIL", "NG"):
            raise ValueError(
                f"Invalid instrument test judgment: {judgment}"
            )

        self.store_measurement_result(step_id, result)

        overall_judgment = self.update_judgment(
            step_id,
            judgment
        )

        self.log(
            "MEASUREMENT",
            f"{function}: {judgment}"
        )

        self.log(
            "JUDGMENT",
            f"Overall judgment: {overall_judgment}"
        )

        if judgment in ("FAIL", "NG"):
            self.stop_after_interaction = True

        return StepOutcome(
            success=True,
            message=f"{function} test completed: {judgment}.",
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

        parameters = self.current_configuration.get(
            "parameters",
            {}
        )

        instrument_id = parameters.get("instrument")

        if not instrument_id:
            raise ValueError("Instrument ID is required.")

        duration_s = float(parameters.get("duration_s", 10))
        sample_interval_s = float(
            parameters.get("sample_interval_s", 1)
        )

        measurement_ids = parameters.get("measurements")

        if duration_s <= 0 or sample_interval_s <= 0:
            raise ValueError(
                "Measurement duration and sample interval "
                "must be greater than zero."
            )

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

        QTimer.singleShot(0, worker.start)

        self.interaction_requested.emit({
            "type": "live_measurement",
            "instrument": instrument_id,
            "duration_s": duration_s,
            "sample_interval_s": sample_interval_s
        })

    def on_instrument_measurement_completed(self, result):

        if not self.running:
            return

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        self.store_measurement_result(step_id, result)

        measured_values = result.get("measurements", {})

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
                message=f"Measurement completed: {result.get('instrument')}",
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
    # AC VOLT CONFIRMATION
    # ==========================================

    def start_ac_volt_confirmation(self, parameters):

        if not self.running or not self.waiting:
            return

        if self.ac_volt_worker is not None:
            raise RuntimeError(
                "AC Volt Confirmation worker is already active."
            )

        parameters = dict(parameters or {})

        power_supply_id = parameters.get("power_supply")
        power_meter_id = parameters.get("power_meter")

        if not power_supply_id or not power_meter_id:
            raise ValueError(
                "AC Volt Confirmation instrument IDs are missing."
            )

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
                    "Hardware AC Volt Confirmation is blocked. "
                    "Test configuration has not been approved."
                )

        test_parameters = (
            self.parameter_configuration
            .get("test_parameters", {})
            .get("ac_volt_confirmation", {})
        )

        power_supply_parameters = test_parameters.get(
            "power_supply",
            {}
        )

        duration_s = float(
            test_parameters.get("evaluation_duration_s", 10)
        )

        sample_interval_s = float(
            test_parameters.get("sample_interval_s", 1)
        )

        voltage_min_V = float(
            test_parameters["lower"]
        )

        voltage_max_V = float(
            test_parameters["upper"]
        )


        measurement_ids = parameters.get(
            "measurements",
            ["voltage", "current"]
        )

        worker = ACVoltConfirmationWorker(
            instrument_manager=self.instrument_manager,
            power_supply_id=power_supply_id,
            power_meter_id=power_meter_id,
            power_supply_parameters=power_supply_parameters,
            evaluation_duration_s=duration_s,
            sample_interval_s=sample_interval_s,
            voltage_min_V=voltage_min_V,
            voltage_max_V=voltage_max_V,
            measurement_ids=measurement_ids
        )

        self.ac_volt_worker = worker
        self.ac_volt_abort_requested = False

        worker.status_changed.connect(
            self.ac_volt_status_changed.emit
        )

        worker.configuration_ready.connect(
            self.ac_volt_configuration_ready.emit
        )

        worker.sample_received.connect(
            self.ac_volt_sample_received.emit
        )

        worker.evaluation_passed.connect(
            self.on_ac_volt_evaluation_passed
        )

        worker.completed.connect(
            self.on_ac_volt_completed
        )

        worker.failed.connect(
            self.on_ac_volt_failed
        )

        worker.finished.connect(
            lambda w=worker: self.cleanup_ac_volt_worker(w)
        )

        self.log(
            "INSTRUMENT",
            "Starting AC Volt Confirmation."
        )

        QTimer.singleShot(0, worker.start)

    def approve_ac_volt_output(self):

        if self.ac_volt_worker is None:
            return

        self.ac_volt_worker.approve_output()

    def confirm_ac_volt_pass(self):

        if self.ac_volt_worker is None:
            return

        self.ac_volt_worker.confirm_pass()

    def cancel_ac_volt_confirmation(self):

        if self.ac_volt_worker is None:
            return

        self.ac_volt_abort_requested = True

        self.log(
            "ABORT",
            "AC Volt Confirmation cancellation requested. "
            "Waiting for safe shutdown."
        )

        self.ac_volt_worker.request_stop()

    def on_ac_volt_evaluation_passed(self, result):

        self.log(
            "JUDGMENT",
            "AC Volt Confirmation evaluation: PASS. "
            "PCR500M output remains ON until operator confirmation."
        )

        self.ac_volt_evaluation_passed.emit(result)

    def on_ac_volt_completed(self, result):

        if not self.running:
            return

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        self.store_measurement_result(step_id, result)

        judgment = str(
            result.get("judgment", "")
        ).upper()

        if judgment not in ("PASS", "FAIL", "NG"):
            self.fail(
                f"Invalid AC Volt Confirmation judgment: {judgment}"
            )
            return

        overall_judgment = self.update_judgment(
            step_id,
            judgment
        )

        self.log(
            "MEASUREMENT",
            f"AC Volt Confirmation: {judgment}"
        )

        self.ac_volt_completed.emit(result)

        if judgment in ("FAIL", "NG"):

            self.log(
                "JUDGMENT",
                "AC Volt Confirmation NG. Workflow stopped."
            )

            try:
                self.save_result("FAIL")
            except Exception as error:
                self.fail(
                    f"NG result database save failed: {error}"
                )
                return

            self.fail(
                "AC Volt Confirmation NG. "
                "Input voltage is outside the configured limits."
            )
            return

        self.waiting = False

        self.finish_current_step(
            StepOutcome(
                success=True,
                message="AC Volt Confirmation PASS.",
                data=result
            )
        )

    def on_ac_volt_failed(self, message):

        self.ac_volt_failed.emit(message)

        if self.ac_volt_abort_requested:

            self.timer.stop()
            self.running = False
            self.waiting = False

            self.log(
                "ABORT",
                "AC Volt Confirmation cancelled. "
                "Worker safe shutdown has completed."
            )

            self.aborted.emit(
                "Workflow aborted by operator."
            )

            return

        self.fail(
            f"AC Volt Confirmation error: {message}"
        )

    def cleanup_ac_volt_worker(self, worker):

        if self.ac_volt_worker is worker:
            self.ac_volt_worker = None

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

            if self.stop_after_interaction:

                try:
                    self.save_result("FAIL")
                except Exception as error:
                    self.fail(
                        f"NG result database save failed: {error}"
                    )
                    return

                self.fail(
                    "Instrument test NG. Workflow stopped."
                )
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

            judgment = self.context.get("judgment")

            if judgment is None:
                judgment = "PASS"

            self.save_result(judgment)

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

        # AC Volt Confirmation must finish safe shutdown first.
        if self.ac_volt_worker is not None:

            self.cancel_ac_volt_confirmation()
            return

        self.running = False
        self.waiting = False

        for worker in self.measurement_workers:
            worker.request_stop()

        self.log(
            "ABORT",
            "Workflow aborted by operator."
        )

        self.aborted.emit(
            "Workflow aborted by operator."
        )
