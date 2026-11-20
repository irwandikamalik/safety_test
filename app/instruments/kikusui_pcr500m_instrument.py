
import pyvisa

from pyvisa.constants import (
    Parity,
    StopBits,
    ControlFlow
)

from app.instruments.base_instrument import BaseInstrument


class KikusuiPCR500MInstrument(BaseInstrument):

    def __init__(self, configuration):

        self.configuration = configuration

        self.connection_config = configuration.get(
            "connection", {}
        )

        self.command_config = configuration.get(
            "commands", {}
        )

        self.resource_manager = None
        self.instrument = None
        self.connected = False

        self.output_off_verified = False

    # ==================================================
    # CONNECTION
    # ==================================================

    def connect(self):

        if self.connected:
            return True

        resource = self.connection_config.get("resource")

        if not resource:
            raise ValueError(
                "PCR500M VISA resource is not configured."
            )

        backend = self.connection_config.get(
            "backend", ""
        ).strip()

        if backend:
            self.resource_manager = pyvisa.ResourceManager(
                backend
            )
        else:
            self.resource_manager = pyvisa.ResourceManager()

        try:

            self.instrument = (
                self.resource_manager.open_resource(resource)
            )

            # Mark connected immediately after opening the resource.
            # This allows disconnect() to attempt output OFF if
            # serial configuration subsequently fails.
            self.connected = True
            self.output_off_verified = False

            self.instrument.baud_rate = int(
                self.connection_config.get(
                    "baud_rate", 19200
                )
            )

            self.instrument.data_bits = int(
                self.connection_config.get(
                    "data_bits", 8
                )
            )

            self.instrument.parity = Parity.none
            self.instrument.stop_bits = StopBits.one

            self.instrument.flow_control = (
                ControlFlow.xon_xoff
            )

            self.instrument.read_termination = (
                self.connection_config.get(
                    "read_termination", "\n"
                )
            )

            self.instrument.write_termination = (
                self.connection_config.get(
                    "write_termination", "\r\n"
                )
            )

            self.instrument.timeout = int(
                self.connection_config.get(
                    "timeout", 5000
                )
            )

            return True

        except Exception:

            try:
                self.disconnect()
            except Exception:
                pass

            raise

    def disconnect(self):

        if self.instrument is None:
            return True

        if not self.connected:
            raise RuntimeError(
                "PCR500M connection state is invalid."
            )

        # ==============================================
        # VERIFY OUTPUT OFF
        # ==============================================

        try:

            # Reuse the successful verification performed
            # by output_off() if it is still valid.
            if not self.output_off_verified:

                status = self._parse_output_status(
                    self._query("OUTP?")
                )

                if status == "ON":

                    self.output_off()

                elif status == "OFF":

                    self.output_off_verified = True

                else:

                    raise RuntimeError(
                        "PCR500M output status is unknown."
                    )

            if not self.output_off_verified:

                raise RuntimeError(
                    "PCR500M output OFF could not be verified."
                )

        except Exception as error:

            raise RuntimeError(
                "PCR500M disconnect aborted. "
                "Output OFF could not be verified. "
                f"Underlying error: {error}"
            ) from error

        # ==============================================
        # CLOSE AFTER VERIFIED OFF
        # ==============================================

        try:

            self.instrument.close()

            self.instrument = None
            self.connected = False
            self.output_off_verified = False

            if self.resource_manager is not None:

                self.resource_manager.close()
                self.resource_manager = None

            return True

        except Exception as error:

            raise RuntimeError(
                f"PCR500M VISA resource close failed: {error}"
            ) from error

    # ==================================================
    # IDENTIFICATION
    # ==================================================

    def identify(self):

        self._require_connection()

        command = self.command_config.get(
            "identify", "*IDN?"
        )

        identity = self._query(command)

        if "PCR500M" not in identity.upper():

            raise RuntimeError(
                "Connected instrument is not identified "
                "as Kikusui PCR500M."
            )

        return identity

    # ==================================================
    # CONFIGURATION
    # ==================================================

    def configure(self, parameters):

        self._require_connection()

        if not isinstance(parameters, dict):
            raise ValueError(
                "PCR500M configuration must be a dictionary."
            )

        voltage_range = float(
            parameters.get("voltage_range_V", 270)
        )

        output_voltage = float(
            parameters.get("output_voltage_V", 230.0)
        )

        frequency = float(
            parameters.get("frequency_Hz", 50.0)
        )

        if voltage_range != 270:
            raise ValueError(
                "PCR500M configuration currently supports "
                "the verified 270 V range only."
            )

        if not 0 < output_voltage <= 275:
            raise ValueError(
                "Output voltage must be greater than 0 "
                "and not exceed 275 V."
            )

        if not 40 <= frequency <= 500:
            raise ValueError(
                "Output frequency must be between 40 and 500 Hz."
            )

        try:

            # Output must be OFF before changing configuration.
            self.output_off()

            self._write("OUTP:COUP AC")
            self._write(
                f"VOLT:RANG {voltage_range:g}"
            )
            self._write(
                f"VOLT {output_voltage:g}"
            )
            self._write(
                f"FREQ {frequency:g}"
            )

            result = self.read_configuration()

            expected = {
                "output_mode": "AC",
                "voltage_range_V": voltage_range,
                "output_voltage_V": output_voltage,
                "frequency_Hz": frequency
            }

            checks = {
                "output_mode": (
                    result["output_mode"].upper()
                    == expected["output_mode"]
                )
            }

            for key in (
                "voltage_range_V",
                "output_voltage_V",
                "frequency_Hz"
            ):

                checks[key] = abs(
                    float(result[key]) - expected[key]
                ) < 0.01

            if not all(checks.values()):

                raise RuntimeError(
                    "PCR500M configuration verification failed: "
                    f"{checks}"
                )

            if result["output_status"] != "OFF":

                raise RuntimeError(
                    "PCR500M output unexpectedly turned ON "
                    "during configuration."
                )

            return {
                "instrument": "Kikusui PCR500M",
                **result,
                "verification": checks,
                "judgment": "PASS",
                "simulation": False
            }

        except Exception as error:

            try:
                self.output_off()

            except Exception as shutdown_error:

                raise RuntimeError(
                    f"PCR500M configuration failed: {error}. "
                    f"Output OFF verification also failed: "
                    f"{shutdown_error}"
                ) from error

            raise

    # ==================================================
    # READ CONFIGURATION
    # ==================================================

    def read_configuration(self):

        self._require_connection()

        commands = {
            "output_status": "OUTP?",
            "output_mode": "OUTP:COUP?",
            "voltage_range_V": "VOLT:RANG?",
            "output_voltage_V": "VOLT?",
            "frequency_Hz": "FREQ?"
        }

        raw = {}

        for key, command in commands.items():
            raw[key] = self._query(command)

        try:

            return {
                "output_status": self._parse_output_status(
                    raw["output_status"]
                ),
                "output_mode": raw["output_mode"].strip(),
                "voltage_range_V": float(
                    raw["voltage_range_V"]
                ),
                "output_voltage_V": float(
                    raw["output_voltage_V"]
                ),
                "frequency_Hz": float(
                    raw["frequency_Hz"]
                )
            }

        except (ValueError, TypeError) as error:

            raise RuntimeError(
                f"Invalid PCR500M configuration response: {raw}"
            ) from error

    # ==================================================
    # OUTPUT CONTROL
    # ==================================================

    def output_on(self, safety_approved=False):

        self._require_connection()

        if safety_approved is not True:

            raise PermissionError(
                "PCR500M output activation requires explicit "
                "safety approval."
            )

        try:
            self.output_off_verified = False

            # Verify actual configuration before activation.
            actual = self.read_configuration()

            if actual["output_status"] != "OFF":
                raise RuntimeError(
                    "PCR500M output must be OFF before activation."
                )

            expected = {
                "output_mode": "AC",
                "voltage_range_V": 270.0,
                "output_voltage_V": 230.0,
                "frequency_Hz": 50.0
            }

            if actual["output_mode"].upper() != "AC":
                raise RuntimeError(
                    "PCR500M output mode is not AC."
                )

            for key, target in expected.items():

                if key == "output_mode":
                    continue

                if abs(float(actual[key]) - target) >= 0.01:
                    raise RuntimeError(
                        f"PCR500M {key} mismatch. "
                        f"Expected {target}, got {actual[key]}."
                    )

            self._write("OUTP ON")

            status = self._parse_output_status(
                self._query("OUTP?")
            )

            if status != "ON":
                raise RuntimeError(
                    "PCR500M output ON could not be verified."
                )

            return {
                "output_status": status,
                "judgment": "PASS"
            }

        except Exception as error:

            try:
                self.output_off()

            except Exception as shutdown_error:

                raise RuntimeError(
                    f"PCR500M output activation failed: {error}. "
                    f"Output OFF also failed: {shutdown_error}"
                ) from error

            raise

    def output_off(self):

        self._require_connection()

        # Previous verification must not be reused
        # until a new OFF response is received.
        self.output_off_verified = False

        self._write("OUTP OFF")

        status = self._parse_output_status(
            self._query("OUTP?")
        )

        if status != "OFF":

            raise RuntimeError(
                "PCR500M output OFF could not be verified."
            )

        self.output_off_verified = True

        return True

    # ==================================================
    # SCPI HELPERS
    # ==================================================

    def _write(self, command):

        self._require_connection()
        self.instrument.write(command)

    def _query(self, command):

        self._require_connection()

        return self.instrument.query(
            command
        ).strip()

    @staticmethod
    def _parse_output_status(response):

        value = response.strip().upper()

        if value in ("1", "1.0", "ON"):
            return "ON"

        if value in ("0", "0.0", "OFF"):
            return "OFF"

        raise ValueError(
            f"Unknown PCR500M output status: {response}"
        )

    def _require_connection(self):

        if not self.connected or self.instrument is None:

            raise RuntimeError(
                "Kikusui PCR500M is not connected."
            )

    # ==================================================
    # UNSUPPORTED TEST OPERATIONS
    # ==================================================

    def execute_test(self, function, parameters):

        raise NotImplementedError(
            "PCR500M is an AC power source, "
            "not a safety test instrument."
        )

    def read_measurements(self, parameters):

        raise NotImplementedError(
            "PCR500M measurement catalog has not been implemented."
        )
