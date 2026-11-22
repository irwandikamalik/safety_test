
import threading
import time

from copy import deepcopy
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from app.instruments.instrument_manager import InstrumentManager


class MeasurementWorker(QThread):

    sample_received = Signal(dict, int, float, bool)
    measurement_completed = Signal(dict)
    measurement_failed = Signal(str)

    def __init__(
        self,
        model_instruments,
        instrument_catalog,
        application_configuration,
        instrument_id,
        duration_s,
        sample_interval_s,
        measurement_ids=None
    ):

        super().__init__()

        self.model_instruments = model_instruments
        self.instrument_catalog = instrument_catalog
        self.application_configuration = application_configuration

        self.instrument_id = instrument_id
        self.duration_s = float(duration_s)
        self.sample_interval_s = float(sample_interval_s)
        self.measurement_ids = measurement_ids

        self.stop_event = threading.Event()

        self.partial_result = None
        self.error_message = None
        self.cancelled = False

    def request_stop(self):

        self.stop_event.set()

    def _build_measurement_result(
        self,
        samples,
        last_result,
        started_at,
        partial
    ):

        if not samples or last_result is None:
            return None

        last_sample = samples[-1]

        elapsed = 0.0

        if started_at is not None:
            elapsed = time.monotonic() - started_at

        return {
            "instrument": last_result.get(
                "instrument",
                self.instrument_id
            ),
            "measurements": deepcopy(
                last_sample["measurements"]
            ),
            "samples": deepcopy(samples),
            "sample_count": len(samples),
            "duration_s": round(elapsed, 3),
            "sample_interval_s": self.sample_interval_s,
            "simulation": last_result.get(
                "simulation",
                False
            ),
            "partial": partial
        }

    def run(self):

        self.partial_result = None
        self.error_message = None
        self.cancelled = False

        if self.instrument_id != "wt310e":
            self.error_message = (
                "Live hardware measurement is restricted to WT310E."
            )
            self.measurement_failed.emit(self.error_message)
            return

        if self.duration_s <= 0:
            self.error_message = (
                "Measurement duration must be greater than zero."
            )
            self.measurement_failed.emit(self.error_message)
            return

        if self.sample_interval_s <= 0:
            self.error_message = (
                "Sample interval must be greater than zero."
            )
            self.measurement_failed.emit(self.error_message)
            return

        manager = None
        connected = False

        samples = []
        result = None
        final_result = None

        started_at = None

        try:

            if "instruments" in self.model_instruments:

                normalized_model_configuration = (
                    self.model_instruments
                )

            else:

                normalized_model_configuration = {
                    "instruments": self.model_instruments
                }

            manager = InstrumentManager(
                normalized_model_configuration,
                self.instrument_catalog,
                self.application_configuration
            )

            print("\n========== WORKER DEBUG ==========")
            print("REQUESTED ID:", repr(self.instrument_id))
            print("LOADED IDS:", list(manager.instruments.keys()))
            print("WT310E EXISTS:", "wt310e" in manager.instruments)
            print("=================================\n")

            connected = manager.connect(
                self.instrument_id
            )

            if connected is False:
                raise RuntimeError(
                    "Could not connect to physical WT310E."
                )

            instrument = manager.get_instrument(
                self.instrument_id
            )

            if manager.application_mode == "HARDWARE":

                identity = instrument.identify()

                if "WT310E" not in identity.upper():
                    raise RuntimeError(
                        "Unexpected instrument identity: "
                        f"{identity}"
                    )

                print(
                    f"WT310E: Physical instrument verified: {identity}"
                )

            else:

                print(
                    "WT310E: Running in simulation mode."
                )

            started_at = time.monotonic()
            next_sample_at = started_at

            while not self.stop_event.is_set():

                elapsed = time.monotonic() - started_at

                if elapsed >= self.duration_s:
                    break

                result = manager.read_measurements(
                    self.instrument_id,
                    measurement_ids=self.measurement_ids
                )

                elapsed = time.monotonic() - started_at

                sample_number = len(samples) + 1

                sample = {
                    "sample_number": sample_number,
                    "timestamp": datetime.now().isoformat(
                        timespec="milliseconds"
                    ),
                    "elapsed_s": round(elapsed, 3),
                    "measurements": result.get(
                        "measurements", {}
                    )
                }

                samples.append(sample)

                self.partial_result = (
                    self._build_measurement_result(
                        samples,
                        result,
                        started_at,
                        partial=True
                    )
                )

                self.sample_received.emit(
                    sample["measurements"],
                    sample_number,
                    sample["elapsed_s"],
                    result.get("simulation", False)
                )

                if elapsed >= self.duration_s:
                    break

                next_sample_at += self.sample_interval_s

                wait_time = max(
                    0,
                    next_sample_at - time.monotonic()
                )

                if self.stop_event.wait(wait_time):
                    break

            if not self.stop_event.is_set():

                if not samples:
                    raise RuntimeError(
                        "No measurement samples were received."
                    )

                final_result = (
                    self._build_measurement_result(
                        samples,
                        result,
                        started_at,
                        partial=False
                    )
                )

        except Exception as error:

            self.error_message = str(error)

        finally:

            if connected and manager is not None:

                try:

                    manager.disconnect(self.instrument_id)

                except Exception as error:

                    disconnect_error = (
                        f"Failed to disconnect WT310E: {error}"
                    )

                    if self.error_message:
                        self.error_message += (
                            f" | {disconnect_error}"
                        )
                    else:
                        self.error_message = disconnect_error

        self.cancelled = (
            self.stop_event.is_set()
            and self.error_message is None
        )

        if self.partial_result is not None:

            self.partial_result["cancelled"] = self.cancelled

            if started_at is not None:
                self.partial_result["duration_s"] = round(
                    time.monotonic() - started_at,
                    3
                )

        if self.error_message:

            self.measurement_failed.emit(
                self.error_message
            )
            return

        if self.cancelled:
            return

        if final_result is not None:

            self.measurement_completed.emit(
                final_result
            )
