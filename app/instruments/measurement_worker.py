
import threading
import time

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

    def request_stop(self):

        self.stop_event.set()

    def run(self):

        if self.instrument_id != "wt310e":
            self.measurement_failed.emit(
                "Live hardware measurement is restricted to WT310E."
            )
            return

        if self.duration_s <= 0:
            self.measurement_failed.emit(
                "Measurement duration must be greater than zero."
            )
            return

        if self.sample_interval_s <= 0:
            self.measurement_failed.emit(
                "Sample interval must be greater than zero."
            )
            return

        manager = None
        connected = False

        samples = []
        result = None
        final_result = None
        error_message = None

        try:

            # ModelService supplies the instrument mapping.
            # InstrumentManager expects an object containing
            # the "instruments" property.
            # Normalize model instrument configuration.
            if "instruments" in self.model_instruments:
                normalized_model_configuration = self.model_instruments
            else:
                normalized_model_configuration = {
                    "instruments": self.model_instruments
                }

            # Determine measurement source.
            measurement_source = self.application_configuration.get(
                "measurement_source",
                "SIMULATION"
            )

            if measurement_source not in ("SIMULATION", "HARDWARE"):
                raise ValueError(
                    f"Invalid measurement source: {measurement_source}"
                )

            hardware_measurement_ids = (
                {"wt310e"}
                if measurement_source == "HARDWARE"
                else set()
            )

            manager = InstrumentManager(
                normalized_model_configuration,
                self.instrument_catalog,
                self.application_configuration,
                hardware_measurement_ids=hardware_measurement_ids
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

            if (
                self.application_configuration.get(
                    "application_mode",
                    "SIMULATION"
                ) == "HARDWARE"
            ):
                identity = instrument.identify()

                if "WT310E" not in identity.upper():
                    raise RuntimeError(
                        f"Unexpected instrument identity: {identity}"
                    )
            else:
                print("WT310E: Running in simulation mode.")

            # Start measurement timer AFTER successful connection.
            started_at = time.monotonic()
            next_sample_at = started_at

            while not self.stop_event.is_set():

                elapsed = time.monotonic() - started_at

                if elapsed >= self.duration_s:
                    break

                # Read actual WT310E measurements.
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

            if self.stop_event.is_set():
                return

            if not samples:
                raise RuntimeError(
                    "No measurement samples were received."
                )

            last_sample = samples[-1]

            final_result = {
                "instrument": result.get(
                    "instrument",
                    self.instrument_id
                ),
                "measurements": last_sample["measurements"],
                "samples": samples,
                "sample_count": len(samples),
                "duration_s": round(
                    time.monotonic() - started_at, 3
                ),
                "sample_interval_s": self.sample_interval_s,
                "simulation": result.get("simulation", False)
            }

        except Exception as error:

            error_message = str(error)

        finally:

            if connected and manager is not None:

                try:
                    manager.disconnect(self.instrument_id)

                except Exception as error:

                    if error_message is None:
                        error_message = (
                            f"Failed to disconnect WT310E: {error}"
                        )

        # Send completion only after disconnect.
        if self.stop_event.is_set():
            return

        if error_message:
            self.measurement_failed.emit(error_message)
            return

        if final_result is not None:
            self.measurement_completed.emit(final_result)
