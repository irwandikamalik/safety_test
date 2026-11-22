from PySide6.QtCore import QObject, Signal, QTimer, Slot

from app.core.workflow_context import WorkflowContext
from app.core.step_registry import StepRegistry
from app.core.workflow_step_runtime import WorkflowStepRuntime

from app.workflows.base_step import StepOutcome
from app.workflows.build_result_step import BuildResultStep

from app.instruments.instrument_manager import InstrumentManager
from app.instruments.measurement_worker import MeasurementWorker
from app.instruments.ac_volt_confirmation_worker import (
    ACVoltConfirmationWorker
)

from app.services.logging_service import LoggingService
from app.storage.storage_manager import StorageManager


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

        self.step_runtime = WorkflowStepRuntime(
            instrument_manager=self.instrument_manager,
            application_mode=self.application_mode,
            parameter_configuration=self.parameter_configuration,
            store_measurement_result=self.store_measurement_result,
            update_judgment=self.update_judgment,
            log=self.log,
            request_stop_after_interaction=self.request_stop_after_interaction,
            save_result_record=self.save_result_record,
        )

        self.logger = LoggingService()
        
        storage_configuration = self.application_configuration.get(
            "storage",
            {
                "type": "sqlite",
                "path": "data/test_results_v2.db",
                "table": "test_results"
            }
        )

        self.storage_manager = StorageManager(
            storage_configuration
        )

        self.steps = self.sequence_configuration.get("steps", [])

        self.index = 0
        self.current_step = None
        self.current_configuration = None

        self.running = False
        self.waiting = False

        self.measurement_workers = []

        self.measurement_abort_requested = False
        self.measurement_pending_error = None
        self.measurement_finalization_started = False

        self.ac_volt_worker = None
        self.ac_volt_abort_requested = False
        self.ac_volt_pending_error = None

        self.stop_after_interaction = False
        self.result_saved = False

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.execute_next)

    @property
    def is_running(self):
        return self.running

    def request_stop_after_interaction(self):
        self.stop_after_interaction = True

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
        self.ac_volt_pending_error = None

        self.measurement_abort_requested = False
        self.measurement_pending_error = None
        self.measurement_finalization_started = False

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

    def save_result_record(self, result_record):

        if self.result_saved:
            raise RuntimeError(
                "A result record has already been saved."
            )

        record_id = self.storage_manager.save_result(
            result_record
        )

        self.result_saved = True

        self.context.set(
            "storage.record_id",
            record_id
        )

        self.context.set(
            "storage.status",
            "SAVED"
        )

        self.log(
            "STORAGE",
            f"Result record saved. ID: {record_id}"
        )

        return record_id

    def save_final_result(
        self,
        execution_status,
        reason=None,
        judgment=None
    ):

        if self.result_saved:
            return self.context.get("storage.record_id")

        build_configuration = next(
            (
                configuration
                for configuration in self.steps
                if configuration.get("type") == "build_result"
            ),
            {
                "id": "build_final_result",
                "type": "build_result",
                "name": "Build Final Result",
                "parameters": {}
            }
        )

        builder = self.registry.create(
            build_configuration
        )

        if judgment is not None:
            self.context.set("judgment", judgment)

        result_record = builder.build_result(
            self.context,
            execution_status=execution_status,
            reason=reason
        )

        return self.save_result_record(
            result_record
        )

    def finalize_abnormal_workflow(
        self,
        execution_status,
        reason
    ):

        if self.result_saved or self.measurement_finalization_started:
            return

        self.measurement_finalization_started = True

        self.timer.stop()

        self.running = False
        self.waiting = False

        try:

            self.save_final_result(
                execution_status=execution_status,
                reason=reason
            )

        except Exception as error:

            self.context.set(
                "storage.status",
                "FAILED"
            )

            failure_message = (
                f"{reason} | Result storage failed: {error}"
            )

            self.log(
                "ERROR",
                failure_message
            )

            self.failed.emit(failure_message)
            return

        if execution_status == "ABORTED":

            self.log(
                "ABORT",
                "Workflow aborted. Result record saved."
            )

            self.aborted.emit(reason)

        else:

            self.log(
                "ERROR",
                f"Workflow failed. Result record saved: {reason}"
            )

            self.failed.emit(reason)

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

            self.current_step = self.registry.create(
                configuration,
                runtime=self.step_runtime
            )

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

            outcome = self.current_step.execute(
                self.context
            )

            self.process_outcome(outcome)

        except Exception as error:

            self.fail(str(error))

    def on_instrument_measurement_completed(self, result):

        if not self.running:
            return

        step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
        )

        self.store_measurement_result(
            step_id,
            result
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

        self.waiting = False

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

        self.measurement_failed.emit(message)

        # Do not finalize here.
        # Wait until QThread.finished so cleanup is complete.
        self.log(
            "ERROR",
            f"Measurement worker reported an error: {message}"
        )

    def cleanup_measurement_worker(self, worker):

        worker_error = worker.error_message
        worker_cancelled = worker.cancelled
        partial_result = worker.partial_result

        if partial_result is not None and (
            worker_cancelled or worker_error
        ):

            step_id = getattr(
                worker,
                "workflow_step_id",
                None
            )

            if step_id:
                self.store_measurement_result(
                    step_id,
                    partial_result
                )

        if worker in self.measurement_workers:
            self.measurement_workers.remove(worker)

        worker.deleteLater()

        if worker_error:

            if self.measurement_pending_error is None:
                self.measurement_pending_error = worker_error

            for active_worker in self.measurement_workers:
                active_worker.request_stop()

        if self.measurement_workers:
            return

        if self.measurement_pending_error:

            self.finalize_abnormal_workflow(
                execution_status="ERROR",
                reason=self.measurement_pending_error
            )

        elif self.measurement_abort_requested:

            self.finalize_abnormal_workflow(
                execution_status="ABORTED",
                reason="Workflow aborted by operator."
            )

    def start_instrument_measurement(self, request):

        instrument_id = request.get("instrument")

        duration_s = float(
            request.get("duration_s", 10)
        )

        sample_interval_s = float(
            request.get("sample_interval_s", 1)
        )

        measurement_ids = request.get("measurements")

        if not instrument_id:
            raise ValueError(
                "Instrument ID is required."
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

        worker.workflow_step_id = self.current_configuration.get(
            "id",
            f"step_{self.index + 1}"
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
        self.ac_volt_pending_error = None

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
            self.on_ac_volt_worker_finished
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

        self.timer.stop()
        self.running = False
        self.waiting = False

        self.log(
            "ABORT",
            "AC Volt Confirmation cancellation requested. "
            "Waiting for safe shutdown."
        )

        self.ac_volt_worker.request_stop()

    @Slot(dict)
    def on_ac_volt_evaluation_passed(self, result):

        self.log(
            "JUDGMENT",
            "AC Volt Confirmation evaluation: PASS. "
            "PCR500M output remains ON until operator confirmation."
        )

        self.ac_volt_evaluation_passed.emit(result)

    @Slot(dict)
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

                self.save_final_result(
                    execution_status="COMPLETED",
                    judgment="FAIL",
                    reason=(
                        "AC Volt Confirmation NG. "
                        "Input voltage is outside the configured limits."
                    )
                )

            except Exception as error:

                self.fail(
                    f"AC Volt Confirmation result storage failed: {error}"
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


    @Slot(dict)
    def on_ac_volt_failed(self, message):

        self.ac_volt_pending_error = str(message)

        self.log(
            "ERROR",
            f"AC Volt Confirmation worker failed: {message}"
        )

        self.ac_volt_failed.emit(message)
    
    @Slot()
    def on_ac_volt_worker_finished(self):

        worker = self.ac_volt_worker

        if worker is None:
            return

        self.cleanup_ac_volt_worker(worker)

    def cleanup_ac_volt_worker(self, worker):

        shutdown_success = worker.shutdown_success
        output_off_verified = worker.output_off_verified
        shutdown_error = worker.shutdown_error

        worker_error = (
            self.ac_volt_pending_error
            or worker.error_message
        )

        if self.ac_volt_worker is worker:
            self.ac_volt_worker = None

        worker.deleteLater()

        # ==========================================
        # WORKER ERROR ATAU CANCELLATION
        # ==========================================

        if worker_error or self.ac_volt_abort_requested:

            # PCR500M output OFF tidak terverifikasi.
            if not output_off_verified:

                reason = (
                    "CRITICAL: AC Volt Confirmation ended, "
                    "but PCR500M output OFF could not be verified. "
                    "Check PCR500M front panel immediately."
                )

                if worker_error:
                    reason += f" Worker error: {worker_error}"

                if shutdown_error:
                    reason += f" Shutdown error: {shutdown_error}"

                self.finalize_abnormal_workflow(
                    execution_status="ERROR",
                    reason=reason
                )

                return

            # Output OFF terverifikasi, tetapi cleanup keseluruhan gagal.
            if not shutdown_success:

                reason = (
                    "PCR500M output OFF was verified, "
                    "but instrument cleanup was not completed successfully."
                )

                if worker_error:
                    reason += f" Worker error: {worker_error}"

                if shutdown_error:
                    reason += f" Shutdown error: {shutdown_error}"

                self.finalize_abnormal_workflow(
                    execution_status="ERROR",
                    reason=reason
                )

                return

            # Shutdown berhasil. Bedakan abort dan error.
            if self.ac_volt_abort_requested:

                self.finalize_abnormal_workflow(
                    execution_status="ABORTED",
                    reason="Workflow aborted by operator."
                )

                return

            self.finalize_abnormal_workflow(
                execution_status="ERROR",
                reason=(
                    f"AC Volt Confirmation failed: {worker_error}"
                )
            )

            return

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

            interaction = outcome.interaction

            self.waiting = True

            if interaction.get("type") == "live_measurement":

                self.start_instrument_measurement(
                    interaction
                )

            self.interaction_requested.emit(
                interaction
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

                self.stop_after_interaction = False

                try:

                    self.save_final_result(
                        execution_status="COMPLETED",
                        judgment="FAIL",
                        reason="Instrument test NG. Workflow stopped."
                    )

                except Exception as error:

                    self.fail(
                        f"Instrument test result storage failed: {error}"
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

        if not self.result_saved:

            self.fail(
                "Workflow reached completion without a saved result record."
            )
            return

        self.running = False
        self.waiting = False

        self.log(
            "DONE",
            "Workflow completed successfully."
        )

        self.finished.emit()

    # ==========================================
    # ERROR AND ABORT
    # ==========================================

    def fail(self, message):

        self.timer.stop()

        if self.result_saved:

            self.running = False
            self.waiting = False

            self.log("ERROR", message)
            self.failed.emit(message)
            return

        self.finalize_abnormal_workflow(
            execution_status="ERROR",
            reason=message
        )

    def stop(self):

        if not self.running:
            return

        self.timer.stop()

        # AC Volt Confirmation harus menyelesaikan
        # safe shutdown sebelum workflow difinalisasi.

        if self.ac_volt_worker is not None:

            self.cancel_ac_volt_confirmation()
            return

        # Live measurement worker harus menyelesaikan
        # cleanup WT310E sebelum workflow difinalisasi.

        if self.measurement_workers:

            self.measurement_abort_requested = True

            # Hentikan transisi workflow segera.
            # Worker tetap berjalan sampai cleanup selesai.

            self.running = False
            self.waiting = False

            self.log(
                "ABORT",
                "Measurement cancellation requested. "
                "Waiting for WT310E cleanup."
            )

            for worker in self.measurement_workers:
                worker.request_stop()

            return

        # Tidak ada worker aktif.
        # Workflow dapat langsung difinalisasi.

        self.finalize_abnormal_workflow(
            execution_status="ABORTED",
            reason="Workflow aborted by operator."
        )