from app.instruments.base_instrument import BaseInstrument


class SimulationInstrument(BaseInstrument):

    _shared_configuration_states = {}

    def __init__(self, configuration):

        self.configuration = configuration
        self.connected = False
        self.configuration_state = {}

    def connect(self):

        self.connected = True
        return True


    def disconnect(self):

        catalog_id = self.configuration.get(
            "catalog_id", ""
        )

        if catalog_id == "kikusui_pcr500m":

            state_key = self._get_configuration_state_key()

            if state_key in self._shared_configuration_states:

                self.output_off()

        self.connected = False


    def execute_test(self, function, parameters):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        if not isinstance(parameters, dict):
            raise ValueError(
                "Test parameters must be a dictionary."
            )

        if function == "acw":
            return self._simulate_ac_hipot(parameters)

        if function == "ecac":
            return self._simulate_ground_bond(
                "ecac",
                parameters
            )

        if function == "ecdc":
            return self._simulate_ground_bond(
                "ecdc",
                parameters
            )

        raise ValueError(
            f"Unsupported simulation function: {function}"
        )

    # ==================================================
    # AC HIPOT TEST
    # ==================================================

    def _simulate_ac_hipot(self, parameters):

        voltage = float(
            parameters.get("test_voltage_V", 0)
        )

        voltage_limit = float(
            parameters.get("limit_voltage_V", voltage)
        )

        frequency = float(
            parameters.get("frequency_Hz", 50.0)
        )

        measured_current = float(
            parameters.get("simulation_current_mA", 0.42)
        )

        duration = float(
            parameters.get(
                "test_time_s",
                parameters.get("test_duration_s", 2.0)
            )
        )

        upper_current = float(
            parameters.get(
                "upper_mA",
                parameters.get(
                    "current_limit_mA",
                    parameters.get(
                        "withstand_current_max_mA",
                        5.0
                    )
                )
            )
        )

        lower_current = float(
            parameters.get("lower_mA", 0.0)
        )

        rise_time = float(
            parameters.get("rise_time_s", 0.0)
        )

        fall_time = float(
            parameters.get("fall_time_s", 0.0)
        )

        if (
            voltage <= 0
            or voltage_limit <= 0
            or frequency <= 0
            or duration <= 0
            or upper_current <= 0
            or lower_current < 0
            or rise_time < 0
            or fall_time < 0
        ):
            raise ValueError(
                "Invalid AC Hipot Test parameters."
            )

        if voltage > voltage_limit:
            raise ValueError(
                "Test voltage exceeds the configured voltage limit."
            )

        passed = (
            lower_current
            <= measured_current
            <= upper_current
        )

        return {
            "function": "acw",
            "test_voltage_V": voltage,
            "limit_voltage_V": voltage_limit,
            "frequency_Hz": frequency,
            "measured_current_mA": measured_current,
            "upper_current_mA": upper_current,
            "lower_current_mA": lower_current,
            "test_time_s": duration,
            "rise_time_s": rise_time,
            "fall_time_s": fall_time,
            "judgment": "PASS" if passed else "FAIL",
            "simulation": True
        }

    # ==================================================
    # GROUND BOND TEST (AC / DC)
    # ==================================================

    def _simulate_ground_bond(self, function, parameters):

        judge_type = parameters.get(
            "judge_type",
            "resistance"
        )

        if judge_type != "resistance":
            raise ValueError(
                f"Unsupported Ground Bond judge type: {judge_type}"
            )

        test_current = float(
            parameters.get("test_current_A", 0)
        )

        measured_resistance = float(
            parameters.get(
                "simulation_resistance_mOhm",
                80.0
            )
        )

        duration = float(
            parameters.get(
                "test_time_s",
                parameters.get("test_duration_s", 2.0)
            )
        )

        # Parameter "upper" dan "lower" pada konfigurasi
        # dinyatakan dalam Ohm.
        #
        # Hasil simulasi menggunakan mOhm.
        #
        # Contoh:
        # 0.2 Ohm = 200 mOhm

        if "upper" in parameters:

            upper_resistance = (
                float(parameters["upper"]) * 1000
            )

        else:

            upper_resistance = float(
                parameters.get(
                    "resistance_limit_mOhm",
                    100.0
                )
            )

        lower_resistance = float(
            parameters.get("lower", 0.0)
        ) * 1000

        rise_time = float(
            parameters.get("rise_time_s", 0.0)
        )

        fall_time = float(
            parameters.get("fall_time_s", 0.0)
        )

        frequency = parameters.get("frequency_Hz")

        if (
            test_current <= 0
            or duration <= 0
            or upper_resistance <= 0
            or lower_resistance < 0
            or rise_time < 0
            or fall_time < 0
        ):
            raise ValueError(
                "Invalid Ground Bond Test parameters."
            )

        passed = (
            lower_resistance
            <= measured_resistance
            <= upper_resistance
        )

        result = {
            "function": function,
            "judge_type": judge_type,
            "test_current_A": test_current,
            "measured_resistance_mOhm": measured_resistance,
            "lower_resistance_mOhm": lower_resistance,
            "upper_resistance_mOhm": upper_resistance,
            "test_time_s": duration,
            "rise_time_s": rise_time,
            "fall_time_s": fall_time,
            "judgment": "PASS" if passed else "FAIL",
            "simulation": True
        }

        if frequency is not None:
            result["frequency_Hz"] = float(frequency)

        return result

    def _get_configuration_state_key(self):

        connection = self.configuration.get(
            "connection", {}
        )

        resource = connection.get(
            "resource",
            connection.get("port", "default")
        )

        driver = self.configuration.get(
            "driver",
            "simulation"
        )

        name = self.configuration.get(
            "name",
            "Simulation Instrument"
        )

        return f"{driver}:{name}:{resource}"

    # ==================================================
    # SIMULATED AC POWER SUPPLY CONFIGURATION
    # ==================================================

    def configure(self, parameters):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        if not isinstance(parameters, dict):
            raise ValueError(
                "Configuration must be a dictionary."
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
                "Simulation currently supports 270 V range."
            )

        if not 0 < output_voltage <= 275:
            raise ValueError(
                "Invalid output voltage."
            )

        if not 40 <= frequency <= 500:
            raise ValueError(
                "Invalid output frequency."
            )

        self.configuration_state = {
            "instrument": self.configuration.get(
                "name",
                "Simulation Instrument"
            ),
            "output_mode": "AC",
            "output_status": "OFF",
            "voltage_range_V": voltage_range,
            "output_voltage_V": output_voltage,
            "frequency_Hz": frequency
        }

        state_key = self._get_configuration_state_key()

        self._save_configuration_state()

        return {
            **self.configuration_state,
            "verification": {
                "output_mode": True,
                "voltage_range_V": True,
                "output_voltage_V": True,
                "frequency_Hz": True
            },
            "judgment": "PASS",
            "simulation": True
        }

    def read_configuration(self):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        state_key = self._get_configuration_state_key()

        configuration_state = (
            SimulationInstrument._shared_configuration_states.get(
                state_key
            )
        )

        if not configuration_state:
            raise RuntimeError(
                "PCR500M simulation has not been configured."
            )

        self.configuration_state = configuration_state.copy()

        return {
            **self.configuration_state,
            "simulation": True
        }


    # ==================================================
    # SIMULATED OUTPUT CONTROL
    # ==================================================

    def _save_configuration_state(self):

        state_key = self._get_configuration_state_key()

        SimulationInstrument._shared_configuration_states[
            state_key
        ] = self.configuration_state.copy()

    def output_on(self, safety_approved=False):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        if safety_approved is not True:
            raise PermissionError(
                "PCR500M simulation output requires "
                "explicit safety approval."
            )

        actual = self.read_configuration()

        if actual["output_status"] != "OFF":
            raise RuntimeError(
                "PCR500M simulation output must be OFF "
                "before activation."
            )

        if actual["output_mode"].upper() != "AC":
            raise RuntimeError(
                "PCR500M simulation output mode is not AC."
            )

        voltage_range = float(
            actual["voltage_range_V"]
        )

        output_voltage = float(
            actual["output_voltage_V"]
        )

        frequency = float(
            actual["frequency_Hz"]
        )

        if voltage_range != 270:
            raise RuntimeError(
                "PCR500M simulation requires 270 V range."
            )

        if not 0 < output_voltage <= 275:
            raise RuntimeError(
                "Invalid simulated output voltage."
            )

        if not 40 <= frequency <= 500:
            raise RuntimeError(
                "Invalid simulated output frequency."
            )

        self.configuration_state["output_status"] = "ON"

        self._save_configuration_state()

        result = self.read_configuration()

        if result["output_status"] != "ON":
            self.output_off()

            raise RuntimeError(
                "PCR500M simulation output ON verification failed."
            )

        return {
            "output_status": "ON",
            "output_voltage_V": output_voltage,
            "frequency_Hz": frequency,
            "judgment": "PASS",
            "simulation": True
        }

    def output_off(self):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        state_key = self._get_configuration_state_key()

        if state_key not in self._shared_configuration_states:
            return True

        self.configuration_state = (
            self._shared_configuration_states[
                state_key
            ].copy()
        )

        self.configuration_state["output_status"] = "OFF"

        self._save_configuration_state()

        result = self.read_configuration()

        if result["output_status"] != "OFF":
            raise RuntimeError(
                "PCR500M simulation output OFF verification failed."
            )

        return True


    # ==================================================
    # LIVE MEASUREMENT SIMULATION
    # ==================================================

    def read_measurements(self, parameters):

        if not self.connected:
            raise RuntimeError(
                "Simulation instrument is not connected."
            )

        measurements = parameters.get(
            "measurements", []
        )

        simulation_values = parameters.get(
            "simulation_values", {}
        )

        results = {}

        default_values = {
            "voltage": 220.5,
            "current": 1.25,
            "active_power": 275.6,
            "current_frequency": 50.0,
            "voltage_frequency": 50.0
        }

        for measurement in measurements:

            measurement_id = measurement["id"]

            value = simulation_values.get(
                measurement_id,
                default_values.get(
                    measurement_id,
                    0.0
                )
            )

            results[measurement_id] = {
                "value": float(value),
                "unit": measurement.get("unit", "")
            }

        return {
            "instrument": self.configuration.get(
                "name",
                "Simulation Instrument"
            ),
            "measurements": results,
            "simulation": True
        }