
import csv
import io
import time

import pyvisa

from app.instruments.base_instrument import BaseInstrument


class KikusuiTOS9302Instrument(BaseInstrument):

    # STAT:OPER:TEST:COND? bit masks
    TEST_STATUS_PASS = 1
    TEST_STATUS_L_FAIL = 2
    TEST_STATUS_U_FAIL = 4

    TEST_STATUS_RISE = 16
    TEST_STATUS_TESTING = 32
    TEST_STATUS_FALL = 64
    TEST_STATUS_DISCHARGE = 128

    TEST_STATUS_READY = 256
    TEST_STATUS_IDLE = 512
    TEST_STATUS_STOP = 1024
    TEST_STATUS_PROTECT = 2048

    ACTIVE_TEST_MASK = (
        TEST_STATUS_RISE
        | TEST_STATUS_TESTING
        | TEST_STATUS_FALL
        | TEST_STATUS_DISCHARGE
    )

    JUDGMENT_MASK = (
        TEST_STATUS_PASS
        | TEST_STATUS_L_FAIL
        | TEST_STATUS_U_FAIL
    )

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

        self.last_test_result = None

    # ==================================================
    # CONNECTION
    # ==================================================

    def connect(self):

        if self.connected:
            return True

        resource = self.connection_config.get("resource")

        if not resource:
            raise ValueError(
                "Kikusui TOS9302 VISA resource is not configured."
            )

        backend = self.connection_config.get(
            "backend", ""
        ).strip()

        try:

            if backend:
                self.resource_manager = pyvisa.ResourceManager(
                    backend
                )
            else:
                self.resource_manager = pyvisa.ResourceManager()

            self.instrument = (
                self.resource_manager.open_resource(resource)
            )

            self.instrument.timeout = int(
                self.connection_config.get(
                    "timeout", 10000
                )
            )

            self.instrument.read_termination = (
                self.connection_config.get(
                    "read_termination", "\n"
                )
            )

            self.instrument.write_termination = (
                self.connection_config.get(
                    "write_termination", "\n"
                )
            )

            self.connected = True

            # Verify communication immediately.
            self.identify()

            return True

        except Exception:

            self.disconnect()
            raise


    def disconnect(self):

        if self.connected and self.instrument is not None:

            test_status = int(
                self._query("STAT:OPER:TEST:COND?")
            )

            operation_status = int(
                self._query("STAT:OPER:COND?")
            )

            test_active = bool(
                test_status & self.ACTIVE_TEST_MASK
            )

            high_voltage_active = bool(
                operation_status & 512
            )

            if test_active or high_voltage_active:
                self._abort_test()

        instrument = self.instrument
        resource_manager = self.resource_manager

        try:
            if instrument is not None:
                instrument.close()

        finally:
            self.instrument = None
            self.resource_manager = None
            self.connected = False

            if resource_manager is not None:
                resource_manager.close()


    def identify(self):

        self._require_connection()

        command = self.command_config.get(
            "identify", "*IDN?"
        )

        return self._query(command)

    # ==================================================
    # SCPI COMMUNICATION
    # ==================================================

    def _write(self, command):

        self._require_connection()

        self.instrument.write(command)

    def _query(self, command):

        self._require_connection()

        response = self.instrument.query(command)

        return response.strip()

    def _query_float(self, command):

        response = self._query(command)

        try:
            return float(response)

        except ValueError as exc:
            raise ValueError(
                f"Invalid numeric response for {command}: "
                f"{response}"
            ) from exc

    def _format_number(self, value, parameter_name):

        try:
            number = float(value)

        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid parameter: {parameter_name}"
            ) from exc

        if number < 0:
            raise ValueError(
                f"{parameter_name} cannot be negative."
            )

        return f"{number:g}"

    def _require_connection(self):

        if (
            not self.connected
            or self.instrument is None
        ):
            raise RuntimeError(
                "Kikusui TOS9302 is not connected."
            )

    # ==================================================
    # TEST CONFIGURATION
    # ==================================================

    def _configure_acw(self, parameters):

        test_voltage = self._format_number(
            parameters["test_voltage_V"],
            "test_voltage_V"
        )

        limit_voltage = self._format_number(
            parameters["limit_voltage_V"],
            "limit_voltage_V"
        )

        frequency = self._format_number(
            parameters["frequency_Hz"],
            "frequency_Hz"
        )

        upper_current = self._format_number(
            parameters["upper_mA"],
            "upper_mA"
        )

        test_time = self._format_number(
            parameters["test_time_s"],
            "test_time_s"
        )

        rise_time = self._format_number(
            parameters["rise_time_s"],
            "rise_time_s"
        )

        # Set instrument mode.
        self._write("FUNC ACW")

        # AC Hipot parameters.
        self._write(f"ACW:VOLT {test_voltage}")
        self._write(f"ACW:VOLT:PROT {limit_voltage}")
        self._write(f"ACW:VOLT:FREQ {frequency}HZ")

        self._write(f"SENS:ACW:JUDG {upper_current}MA")

        self._write("ACW:VOLT:TIM:STAT ON")
        self._write(f"ACW:VOLT:TIM {test_time}")

        self._write(f"ACW:VOLT:SWE:TIM {rise_time}")

        # Lower current limit.
        if "lower_mA" in parameters:

            lower_current = self._format_number(
                parameters["lower_mA"],
                "lower_mA"
            )

            self._write(
                "SENS:ACW:JUDG:LOW:STAT ON"
            )

            self._write(
                f"SENS:ACW:JUDG:LOW {lower_current}MA"
            )

        else:
            self._write(
                "SENS:ACW:JUDG:LOW:STAT OFF"
            )

        # Fall time.
        fall_time = parameters.get("fall_time_s")

        if fall_time is not None:

            fall_time = self._format_number(
                fall_time,
                "fall_time_s"
            )

            self._write(
                "ACW:VOLT:SWE:FALL:TIM:STAT ON"
            )

            self._write(
                f"ACW:VOLT:SWE:FALL:TIM {fall_time}"
            )

        else:
            self._write(
                "ACW:VOLT:SWE:FALL:TIM:STAT OFF"
            )

    def _configure_ec(self, function, parameters):

        test_current = self._format_number(
            parameters["test_current_A"],
            "test_current_A"
        )

        limit_current = self._format_number(
            parameters["limit_current_A"],
            "limit_current_A"
        )

        test_time = self._format_number(
            parameters["test_time_s"],
            "test_time_s"
        )

        rise_time = self._format_number(
            parameters["rise_time_s"],
            "rise_time_s"
        )

        judge_type = str(
            parameters.get("judge_type", "resistance")
        ).strip().upper()

        if judge_type not in ("RESISTANCE", "CURRENT"):
            raise ValueError(
                "judge_type must be 'resistance' or 'current'."
            )

        judge_command_type = (
            "RES" if judge_type == "RESISTANCE" else "CURR"
        )

        if function == "ecac":

            self._write("FUNC EC")

            mode = "AC"
            current_command = "EC:AC:CURR"
            protection_command = "EC:AC:CURR:PROT"
            time_command = "EC:AC:CURR:TIM"
            time_status_command = "EC:AC:CURR:TIM:STAT"
            rise_command = "EC:AC:CURR:SWE:TIM"
            fall_status_command = (
                "EC:AC:CURR:SWE:FALL:TIM:STAT"
            )
            fall_command = "EC:AC:CURR:SWE:FALL:TIM"

        elif function == "ecdc":

            self._write("FUNC ECDC")

            mode = "DC"
            current_command = "EC:DC:CURR"
            protection_command = "EC:DC:CURR:PROT"
            time_command = "EC:DC:CURR:TIM"
            time_status_command = "EC:DC:CURR:TIM:STAT"
            rise_command = "EC:DC:CURR:SWE:TIM"
            fall_status_command = (
                "EC:DC:CURR:SWE:FALL:TIM:STAT"
            )
            fall_command = "EC:DC:CURR:SWE:FALL:TIM"

        else:
            raise ValueError(
                f"Unsupported Ground Bond function: {function}"
            )

        self._write(
            f"{current_command} {test_current}"
        )

        self._write(
            f"{protection_command} {limit_current}"
        )

        # AC frequency applies to ECAC.
        if mode == "AC":

            frequency = self._format_number(
                parameters["frequency_Hz"],
                "frequency_Hz"
            )

            self._write(
                f"EC:CURR:FREQ {frequency}"
            )

        # Judgment type.
        self._write(
            f"SENS:EC:{mode}:JUDG:TYPE "
            f"{judge_command_type}"
        )

        self._write(
            f"SENS:EC:{mode}:JUDG:STAT ON"
        )

        upper_limit = self._format_number(
            parameters["upper"],
            "upper"
        )

        if judge_type == "RESISTANCE":
            upper_unit = "OHM"
        else:
            upper_unit = "A"

        self._write(
            f"SENS:EC:{mode}:JUDG "
            f"{upper_limit}{upper_unit}"
        )

        # Lower judgment limit.
        if "lower" in parameters:

            lower_limit = self._format_number(
                parameters["lower"],
                "lower"
            )

            self._write(
                f"SENS:EC:{mode}:JUDG:LOW:STAT ON"
            )

            self._write(
                f"SENS:EC:{mode}:JUDG:LOW "
                f"{lower_limit}{upper_unit}"
            )

        else:

            self._write(
                f"SENS:EC:{mode}:JUDG:LOW:STAT OFF"
            )

        # Test duration.
        self._write(
            f"{time_status_command} ON"
        )

        self._write(
            f"{time_command} {test_time}"
        )

        # Current rise time.
        self._write(
            f"{rise_command} {rise_time}"
        )

        # Current fall time.
        fall_time = parameters.get("fall_time_s")

        if fall_time is not None:

            fall_time = self._format_number(
                fall_time,
                "fall_time_s"
            )

            self._write(
                f"{fall_status_command} ON"
            )

            self._write(
                f"{fall_command} {fall_time}"
            )

        else:

            self._write(
                f"{fall_status_command} OFF"
            )

    # ==================================================
    # TEST EXECUTION
    # ==================================================

    def execute_test(self, function, parameters):

        self._require_connection()

        if not isinstance(parameters, dict):
            raise ValueError(
                "Test parameters must be a dictionary."
            )

        function = str(function).strip().lower()

        if function not in ("acw", "ecac", "ecdc"):
            raise ValueError(
                f"Unsupported TOS9302 test function: {function}"
            )

        # Set remote mode.
        self._write("SYST:COMM:RLST REM")

        # Configure test according to its function.
        if function == "acw":
            self._configure_acw(parameters)

        else:
            self._configure_ec(function, parameters)

        # Clear previous event/error information.
        self._write("*CLS")

        # Configure test result format.
        self._write(
            "RES:FORM FUNC,VOLT,CURR,RES,ETIM,JUDG"
        )

        # Start test using immediate trigger.
        self._write("TRIG:TEST:SOUR IMM")
        self._write("INIT:TEST")

        try:

            status = self._wait_for_test_complete(
                parameters
            )

            raw_result = self._query("RES?")

            result = self._parse_test_result(
                raw_result
            )

            result["function"] = function
            result["status_register"] = status
            result["raw"] = raw_result
            result["simulation"] = False

            self.last_test_result = result

            return result

        except Exception:

            # Abort an active test if anything goes wrong.
            self._abort_test()

            raise

    def _wait_for_test_complete(self, parameters):

        test_time = float(
            parameters.get("test_time_s", 5.0)
        )

        rise_time = float(
            parameters.get("rise_time_s", 0.0)
        )

        fall_time = float(
            parameters.get("fall_time_s", 0.0) or 0.0
        )

        timeout = (
            test_time
            + rise_time
            + fall_time
            + 30.0
        )

        start_time = time.monotonic()

        saw_active_state = False

        while True:

            self._require_connection()

            status = int(
                self._query(
                    "STAT:OPER:TEST:COND?"
                )
            )

            if status & self.ACTIVE_TEST_MASK:
                saw_active_state = True

            judgment_available = bool(
                status & self.JUDGMENT_MASK
            )

            test_active = bool(
                status & self.ACTIVE_TEST_MASK
            )

            if (
                saw_active_state
                and not test_active
                and judgment_available
            ):
                return status

            if time.monotonic() - start_time > timeout:

                raise TimeoutError(
                    "TOS9302 test did not complete within "
                    f"{timeout:.1f} seconds. "
                    f"Last status register: {status}"
                )

            time.sleep(0.05)


    def _abort_test(self):

        self._require_connection()

        self._write("ABOR:TEST")

        timeout = 15.0
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:

            operation_status = int(
                self._query("STAT:OPER:COND?")
            )

            # Bit 9 = HVON (512).
            high_voltage_active = bool(
                operation_status & 512
            )

            if not high_voltage_active:
                return True

            time.sleep(0.1)

        raise RuntimeError(
            "TOS9302 abort was sent, but HVON OFF "
            "could not be verified. Keep the VISA "
            "connection open and inspect the instrument."
        )


    # ==================================================
    # RESULT PARSING
    # ==================================================

    def _parse_test_result(self, raw_result):

        try:

            fields = next(
                csv.reader(
                    io.StringIO(raw_result),
                    skipinitialspace=True
                )
            )

        except Exception as exc:

            raise ValueError(
                f"Cannot parse TOS9302 result: {raw_result}"
            ) from exc

        if len(fields) != 6:

            raise ValueError(
                "Unexpected TOS9302 result format. "
                f"Expected 6 fields, received {len(fields)}: "
                f"{raw_result}"
            )

        function = fields[0].strip().strip('"').upper()

        voltage = self._parse_optional_float(fields[1])
        current = self._parse_optional_float(fields[2])
        resistance = self._parse_optional_float(fields[3])
        test_time = self._parse_optional_float(fields[4])

        judgment = (
            fields[5].strip().strip('"').upper()
        )

        if judgment not in (
            "PASS",
            "U-FAIL",
            "L-FAIL",
            "PROT",
            "ABORT"
        ):
            raise ValueError(
                f"Unknown TOS9302 judgment: {judgment}"
            )

        return {
            "instrument": self.configuration.get(
                "name", "Kikusui TOS9302"
            ),
            "instrument_function": function,
            "voltage_V": voltage,
            "current_A": current,
            "resistance_ohm": resistance,
            "test_time_s": test_time,
            "judgment": judgment,
            "result": (
                "PASS" if judgment == "PASS" else "FAIL"
            )
        }

    def _parse_optional_float(self, value):

        value = value.strip().strip('"')

        if not value:
            return None

        try:
            return float(value)

        except ValueError:
            return None

    # ==================================================
    # MEASUREMENT READING
    # ==================================================

    def read_measurements(self, parameters=None):

        self._require_connection()

        if parameters is None:
            parameters = {}

        if not isinstance(parameters, dict):
            raise ValueError(
                "Measurement parameters must be a dictionary."
            )

        # MEAS? returns:
        # Current, Voltage, Resistance, Elapsed Test Time
        raw_response = self._query("MEAS?")

        try:

            fields = next(
                csv.reader(
                    io.StringIO(raw_response),
                    skipinitialspace=True
                )
            )

        except Exception as exc:

            raise ValueError(
                f"Cannot parse measurement response: "
                f"{raw_response}"
            ) from exc

        if len(fields) != 4:

            raise ValueError(
                "Unexpected TOS9302 measurement response. "
                f"Expected 4 values, received {len(fields)}: "
                f"{raw_response}"
            )

        values = {
            "current": {
                "value": self._parse_optional_float(fields[0]),
                "unit": "A"
            },
            "voltage": {
                "value": self._parse_optional_float(fields[1]),
                "unit": "V"
            },
            "resistance": {
                "value": self._parse_optional_float(fields[2]),
                "unit": "ohm"
            },
            "test_time": {
                "value": self._parse_optional_float(fields[3]),
                "unit": "s"
            }
        }

        requested = parameters.get(
            "measurements",
            list(values.keys())
        )

        if not isinstance(requested, list):
            raise ValueError(
                "measurements must be a list."
            )

        results = {}

        for measurement_id in requested:

            if measurement_id not in values:
                raise ValueError(
                    "Unsupported TOS9302 measurement: "
                    f"{measurement_id}"
                )

            results[measurement_id] = {
                **values[measurement_id],
                "raw": raw_response
            }

        return {
            "instrument": self.configuration.get(
                "name", "Kikusui TOS9302"
            ),
            "measurements": results,
            "simulation": False,
            "raw": raw_response
        }
