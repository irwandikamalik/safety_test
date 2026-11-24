
import threading
import time
import math

from PySide6.QtCore import QThread, Signal
from copy import deepcopy


class ACVoltConfirmationWorker(QThread):

    status_changed = Signal(str)

    configuration_ready = Signal(dict)

    sample_received = Signal(
        dict,
        int,
        float,
        bool,
        str
    )

    evaluation_passed = Signal(dict)

    completed = Signal(dict)

    failed = Signal(str)

    def __init__(
        self,
        instrument_manager,
        power_supply_id,
        power_meter_id,
        power_supply_parameters,
        evaluation_duration_s,
        sample_interval_s,
        voltage_min_V,
        voltage_max_V,
        measurement_ids=None,
        parent=None
    ):

        super().__init__(parent)

        self.instrument_manager = instrument_manager

        self.power_supply_id = power_supply_id
        self.power_meter_id = power_meter_id

        self.power_supply_parameters = (
            power_supply_parameters
        )

        self.evaluation_duration_s = float(
            evaluation_duration_s
        )

        self.sample_interval_s = float(
            sample_interval_s
        )

        self.voltage_min_V = float(
            voltage_min_V
        )

        self.voltage_max_V = float(
            voltage_max_V
        )

        self.measurement_ids = [
            "voltage",
            "current",
            "voltage_frequency",
            "active_power"
        ]
        
        self.approval_event = threading.Event()
        self.pass_confirmation_event = threading.Event()
        self.stop_event = threading.Event()

        self.power_supply_connected = False
        self.power_meter_connected = False

        self.output_activated = False
        self.shutdown_attempted = False

        self.final_result = None

        self.output_off_verified = False
        self.shutdown_success = False
        self.shutdown_error = None
        self.error_message = None

    # ==================================================
    # OPERATOR CONTROL
    # ==================================================

    def approve_output(self):

        self.approval_event.set()

    def confirm_pass(self):

        self.pass_confirmation_event.set()

    def request_stop(self):

        self.stop_event.set()

        # Release any pending wait.
        self.approval_event.set()
        self.pass_confirmation_event.set()

    # ==================================================
    # MAIN WORKER
    # ==================================================

    def run(self):

        try:

            self._validate_parameters()

            self.status_changed.emit(
                "Connecting PCR500M..."
            )

            self.instrument_manager.connect(
                self.power_supply_id
            )

            self.power_supply_connected = True

            self.status_changed.emit(
                "Connecting WT310E..."
            )

            self.instrument_manager.connect(
                self.power_meter_id
            )

            self.power_meter_connected = True

            if self._is_stopping():
                raise RuntimeError(
                    "AC Volt Confirmation was cancelled."
                )


            # ------------------------------------------
            # CONFIGURATION CHECK
            # ------------------------------------------

            self.status_changed.emit(
                "Checking PCR500M configuration..."
            )

            is_simulation = (
                self.instrument_manager.application_mode
                == "SIMULATION"
            )

            configuration = None

            # Read current configuration.
            try:

                configuration = (
                    self.instrument_manager
                    .read_instrument_configuration(
                        self.power_supply_id
                    )
                )

            except RuntimeError as error:

                # Only initialize an unconfigured simulation.
                if (
                    is_simulation
                    and "has not been configured" in str(error)
                ):

                    self.status_changed.emit(
                        "Initializing PCR500M simulation..."
                    )

                    self.instrument_manager.configure_instrument(
                        self.power_supply_id,
                        self.power_supply_parameters
                    )

                    configuration = (
                        self.instrument_manager
                        .read_instrument_configuration(
                            self.power_supply_id
                        )
                    )

                else:
                    raise

            # ------------------------------------------
            # CHECK OUTPUT SAFETY
            # ------------------------------------------

            output_status = str(
                configuration.get("output_status", "")
            ).strip().upper()

            if output_status not in ("OFF", "0", "FALSE"):

                raise RuntimeError(
                    "PCR500M output is ON or its status "
                    "cannot be verified. Configuration blocked."
                )

            # ------------------------------------------
            # APPLY CONFIGURATION IF REQUIRED
            # ------------------------------------------

            if not self._configuration_matches(configuration):

                self.status_changed.emit(
                    "Applying PCR500M configuration..."
                )

                self.instrument_manager.configure_instrument(
                    self.power_supply_id,
                    self.power_supply_parameters
                )

                configuration = (
                    self.instrument_manager
                    .read_instrument_configuration(
                        self.power_supply_id
                    )
                )

            # ------------------------------------------
            # VERIFY FINAL CONFIGURATION
            # ------------------------------------------

            output_status = str(
                configuration.get("output_status", "")
            ).strip().upper()

            if output_status not in ("OFF", "0", "FALSE"):

                raise RuntimeError(
                    "PCR500M output is not confirmed OFF "
                    "after configuration."
                )

            if not self._configuration_matches(configuration):

                raise RuntimeError(
                    "PCR500M configuration verification failed."
                )

            self.configuration_ready.emit(
                configuration
            )


            # ------------------------------------------
            # WAIT FOR OPERATOR APPROVAL
            # ------------------------------------------

            self.status_changed.emit(
                "Waiting for operator safety approval..."
            )

            while not self.approval_event.wait(0.1):

                if self._is_stopping():
                    raise RuntimeError(
                        "AC Volt Confirmation was cancelled."
                    )

            if self._is_stopping():
                raise RuntimeError(
                    "AC Volt Confirmation was cancelled."
                )

            # ------------------------------------------
            # ACTIVATE PCR500M
            # ------------------------------------------

            self.status_changed.emit(
                "Activating PCR500M output..."
            )

            self.output_activated = True

            self.instrument_manager.output_on(
                self.power_supply_id,
                safety_approved=True
            )

            self.status_changed.emit(
                "AC Volt Confirmation is running..."
            )

            # ------------------------------------------
            # 10 SECOND EVALUATION
            # ------------------------------------------

            evaluation_result = (
                self._run_evaluation()
            )

            if evaluation_result["judgment"] == "FAIL":

                self.final_result = evaluation_result

                self._shutdown_instruments()

                self.completed.emit(
                    evaluation_result
                )

                return

            # ------------------------------------------
            # PASS - KEEP OUTPUT ON
            # ------------------------------------------

            self.status_changed.emit(
                "PASS - Waiting for operator confirmation."
            )

            self.evaluation_passed.emit(
                evaluation_result
            )

            self._wait_for_pass_confirmation(
                evaluation_result
            )

            if self._is_stopping():
                raise RuntimeError(
                    "AC Volt Confirmation was cancelled."
                )

            # ------------------------------------------
            # OPERATOR PRESSED OK
            # ------------------------------------------

            self.status_changed.emit(
                "Operator confirmed PASS. Turning output OFF..."
            )

            self._shutdown_instruments()

            self.final_result = evaluation_result

            self.completed.emit(
                evaluation_result
            )

        except Exception as error:
            shutdown_error = None

            if not self.shutdown_attempted:
                shutdown_error = self._safe_shutdown()
            else:
                shutdown_error = self.shutdown_error

            message = str(error)

            if shutdown_error:
                message += (
                    "\n\nSAFE SHUTDOWN FAILURE: "
                    + shutdown_error
                )

            self.error_message = message
            self.failed.emit(message)

    # ==================================================
    # VALIDATION
    # ==================================================

    def _validate_parameters(self):

        if self.evaluation_duration_s <= 0:
            raise ValueError(
                "Evaluation duration must be greater than zero."
            )

        if self.sample_interval_s <= 0:
            raise ValueError(
                "Sample interval must be greater than zero."
            )

        if self.voltage_min_V >= self.voltage_max_V:
            raise ValueError(
                "Invalid AC voltage limits."
            )

        if not self.measurement_ids:
            raise ValueError(
                "No WT310E measurements selected."
            )

    def _is_stopping(self):

        return self.stop_event.is_set()

    # ==================================================
    # CONFIGURATION VERIFICATION
    # ==================================================

    def _configuration_matches(self, actual):

        if not isinstance(actual, dict):
            return False

        expected = self.power_supply_parameters

        try:

            if str(
                actual.get("output_mode", "")
            ).upper() != "AC":
                return False

            if str(
                actual.get("output_status", "")
            ).upper() != "OFF":
                return False

            if not self._number_matches(
                actual.get("voltage_range_V"),
                expected.get("voltage_range_V")
            ):
                return False

            if not self._number_matches(
                actual.get("output_voltage_V"),
                expected.get("output_voltage_V")
            ):
                return False

            if not self._number_matches(
                actual.get("frequency_Hz"),
                expected.get("frequency_Hz")
            ):
                return False

            return True

        except (TypeError, ValueError):
            return False

    @staticmethod
    def _number_matches(actual, expected):

        if actual is None or expected is None:
            return False

        return abs(
            float(actual) - float(expected)
        ) <= 0.01

    # ==================================================
    # WT310E MEASUREMENT
    # ==================================================

    def _read_power_meter(self, timeout=5.0, retry_interval=0.2):

        start_time = time.monotonic()

        last_invalid = {}

        while time.monotonic() - start_time < timeout:

            if self._is_stopping() or self.isInterruptionRequested():
                raise RuntimeError(
                    "AC Volt Confirmation interrupted while waiting "
                    "for valid WT310E measurements."
                )

            result = self.instrument_manager.read_measurements(
                self.power_meter_id,
                self.measurement_ids
            )

            measurements = (
                result.get("measurements", {})
                if isinstance(result, dict)
                else {}
            )

            invalid_measurements = {}

            # Validate every requested measurement.
            for measurement_id in self.measurement_ids:

                measurement = measurements.get(measurement_id)

                if not isinstance(measurement, dict):

                    invalid_measurements[measurement_id] = (
                        "Measurement unavailable"
                    )

                    continue

                raw_value = measurement.get("value")

                try:
                    numeric_value = float(raw_value)

                except (TypeError, ValueError):

                    invalid_measurements[measurement_id] = (
                        f"Invalid value: {raw_value!r}"
                    )

                    continue

                if not math.isfinite(numeric_value):

                    invalid_measurements[measurement_id] = (
                        f"Non-finite value: {raw_value!r}, "
                        f"raw={measurement.get('raw')!r}"
                    )

            # Accept the sample only when every measurement is valid.
            if not invalid_measurements:

                voltage = float(
                    measurements["voltage"]["value"]
                )

                return result, voltage

            last_invalid = invalid_measurements

            # Wait before retrying. Also allow cancellation.
            if self.stop_event.wait(retry_interval):
                raise RuntimeError(
                    "AC Volt Confirmation was cancelled while waiting "
                    "for valid WT310E measurements."
                )

        raise RuntimeError(
            "WT310E measurement timeout: "
            f"not all measurements became valid after {timeout:.1f} seconds. "
            f"Invalid measurements: {last_invalid}"
        )


    def _run_evaluation(self):

        start_time = time.monotonic()

        sample_number = 0
        evaluation_samples = []

        while True:

            if self._is_stopping():
                raise RuntimeError(
                    "AC Volt Confirmation was cancelled."
                )

            elapsed = time.monotonic() - start_time

            if elapsed >= self.evaluation_duration_s:
                break

            result, voltage = self._read_power_meter()

            elapsed = time.monotonic() - start_time

            sample_number += 1

            measurements = deepcopy(
                result.get("measurements", {})
            )

            simulation = bool(
                result.get("simulation", False)
            )

            sample_record = {
                "sample_number": sample_number,
                "elapsed_s": elapsed,
                "measurements": measurements,
                "simulation": simulation
            }

            evaluation_samples.append(sample_record)

            self.sample_received.emit(
                result,
                sample_number,
                elapsed,
                simulation,
                "evaluation"
            )

            remaining = (
                self.evaluation_duration_s
                - (time.monotonic() - start_time)
            )

            if remaining > 0:

                if self.stop_event.wait(
                    min(self.sample_interval_s, remaining)
                ):
                    raise RuntimeError(
                        "AC Volt Confirmation was cancelled."
                    )

        if not evaluation_samples:
            raise RuntimeError(
                "No WT310E measurement was collected."
            )

        # ==============================================
        # FINAL SAMPLE
        # ==============================================

        final_sample = deepcopy(
            evaluation_samples[-1]
        )

        final_measurements = final_sample["measurements"]

        voltage_data = final_measurements.get("voltage")

        if not isinstance(voltage_data, dict):
            raise RuntimeError(
                "Final WT310E voltage measurement is unavailable."
            )

        final_voltage = float(
            voltage_data.get("value")
        )

        if not math.isfinite(final_voltage):
            raise RuntimeError(
                "Final WT310E voltage is not finite."
            )

        passed = (
            self.voltage_min_V
            <= final_voltage
            <= self.voltage_max_V
        )

        judgment = "PASS" if passed else "FAIL"

        return {
            "test": "ac_volt_confirmation",
            "judgment": judgment,

            # Final reading used for judgment.
            "measured_voltage_V": final_voltage,
            "final_sample": final_sample,

            # Complete 10-second evaluation history.
            "evaluation_samples": evaluation_samples,

            # Statistical information.
            "average_voltage_V": (
                sum(
                    float(
                        sample["measurements"]["voltage"]["value"]
                    )
                    for sample in evaluation_samples
                ) / len(evaluation_samples)
            ),

            "minimum_voltage_V": min(
                float(
                    sample["measurements"]["voltage"]["value"]
                )
                for sample in evaluation_samples
            ),

            "maximum_voltage_V": max(
                float(
                    sample["measurements"]["voltage"]["value"]
                )
                for sample in evaluation_samples
            ),

            "voltage_min_V": self.voltage_min_V,
            "voltage_max_V": self.voltage_max_V,

            "sample_count": len(evaluation_samples),

            "elapsed_s": (
                time.monotonic() - start_time
            ),

            "simulation": (
                self.instrument_manager.application_mode
                == "SIMULATION"
            )
        }

    # ==================================================
    # PASS LIVE MONITORING
    # ==================================================

    def _wait_for_pass_confirmation(
        self,
        evaluation_result
    ):

        sample_number = evaluation_result["sample_count"]

        start_time = time.monotonic()

        while not self._is_stopping():

            if self.pass_confirmation_event.is_set():
                return

            result, _ = self._read_power_meter()

            sample_number += 1

            elapsed = (
                self.evaluation_duration_s
                + time.monotonic() - start_time
            )

            self.sample_received.emit(
                result,
                sample_number,
                elapsed,
                bool(result.get("simulation", False)),
                "post_pass_monitoring"
            )

            if self.pass_confirmation_event.wait(
                self.sample_interval_s
            ):
                return

        raise RuntimeError(
            "AC Volt Confirmation was cancelled."
        )

    # ==================================================
    # SAFE SHUTDOWN
    # ==================================================

    def _shutdown_instruments(self):

        if self.shutdown_attempted:
            raise RuntimeError(
                "PCR500M shutdown was already attempted. "
                "Manual safety recovery is required."
            )

        self.shutdown_attempted = True

        errors = []
        output_off_confirmed = False

        # ==========================================
        # PCR500M OUTPUT OFF
        # ==========================================

        if self.power_supply_connected:

            try:
                self.status_changed.emit(
                    "Verifying PCR500M output OFF..."
                )

                result = self.instrument_manager.output_off(
                    self.power_supply_id
                )

                if result is not True:
                    raise RuntimeError(
                        "PCR500M output OFF was not confirmed."
                    )

                output_off_confirmed = True
                self.output_off_verified = True
                self.output_activated = False

                self.status_changed.emit(
                    "PCR500M output OFF verified."
                )

            except Exception as error:
                errors.append(
                    f"PCR500M Output OFF failed: {error}"
                )

        else:
            errors.append(
                "CRITICAL: PCR500M output OFF cannot be verified "
                "because PCR500M is not connected."
            )

        # ==========================================
        # WT310E DISCONNECT
        # ==========================================

        if self.power_meter_connected:

            try:
                self.instrument_manager.disconnect(
                    self.power_meter_id
                )

                self.power_meter_connected = False

            except Exception as error:
                errors.append(
                    f"WT310E disconnect failed: {error}"
                )

        # ==========================================
        # PCR500M DISCONNECT
        # HANYA JIKA OUTPUT OFF TERVERIFIKASI
        # ==========================================

        if self.power_supply_connected and output_off_confirmed:

            try:
                self.instrument_manager.disconnect(
                    self.power_supply_id
                )

                self.power_supply_connected = False

            except Exception as error:
                errors.append(
                    f"PCR500M disconnect failed: {error}"
                )

        elif self.power_supply_connected:

            errors.append(
                "CRITICAL: PCR500M communication retained. "
                "Output OFF could not be verified. "
                "Check PCR500M front panel immediately."
            )

        # ==========================================
        # FINAL SHUTDOWN STATUS
        # ==========================================

        self.shutdown_success = (
            output_off_confirmed and not errors
        )

        self.shutdown_error = (
            " | ".join(errors) if errors else None
        )

        if not self.shutdown_success:
            raise RuntimeError(
                self.shutdown_error
                or "PCR500M safe shutdown was not verified."
            )

        self.status_changed.emit(
            "Instrument shutdown completed."
        )

    def _safe_shutdown(self):

        try:

            self._shutdown_instruments()

            return None

        except Exception as error:

            return str(error)
