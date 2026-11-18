
from app.instruments.base_instrument import BaseInstrument


class SimulationInstrument(BaseInstrument):

    def __init__(self, configuration):

        self.configuration = configuration
        self.connected = False

    def connect(self):

        self.connected = True
        return True

    def disconnect(self):

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

        if function == "ac_withstanding":
            return self._simulate_ac_hipot(parameters)

        if function == "ground_bond":
            return self._simulate_ground_bond(parameters)

        raise ValueError(
            f"Unsupported simulation function: {function}"
        )

    def _simulate_ac_hipot(self, parameters):

        voltage = float(
            parameters.get("test_voltage_V", 1500.0)
        )

        measured_current = float(
            parameters.get("simulation_current_mA", 0.42)
        )

        duration = float(
            parameters.get("test_duration_s", 2.0)
        )

        current_limit = float(
            parameters.get(
                "current_limit_mA",
                parameters.get(
                    "withstand_current_max_mA",
                    5.0
                )
            )
        )

        if voltage <= 0 or duration <= 0 or current_limit <= 0:
            raise ValueError(
                "Invalid AC Hipot Test parameters."
            )

        passed = measured_current <= current_limit

        return {
            "function": "ac_withstanding",
            "test_voltage_V": voltage,
            "measured_current_mA": measured_current,
            "test_duration_s": duration,
            "current_limit_mA": current_limit,
            "judgment": "PASS" if passed else "FAIL",
            "simulation": True
        }

    def _simulate_ground_bond(self, parameters):

        test_current = float(
            parameters.get("test_current_A", 25.0)
        )

        measured_resistance = float(
            parameters.get(
                "simulation_resistance_mOhm",
                80.0
            )
        )

        duration = float(
            parameters.get("test_duration_s", 2.0)
        )

        resistance_limit = float(
            parameters.get(
                "resistance_limit_mOhm",
                100.0
            )
        )

        if (
            test_current <= 0
            or duration <= 0
            or resistance_limit <= 0
        ):
            raise ValueError(
                "Invalid Ground Bond Test parameters."
            )

        passed = measured_resistance <= resistance_limit

        return {
            "function": "ground_bond",
            "test_current_A": test_current,
            "measured_resistance_mOhm": measured_resistance,
            "test_duration_s": duration,
            "resistance_limit_mOhm": resistance_limit,
            "judgment": "PASS" if passed else "FAIL",
            "simulation": True
        }

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
                    measurement_id, 0.0
                )
            )

            results[measurement_id] = {
                "value": float(value),
                "unit": measurement.get("unit", "")
            }

        return {
            "instrument": self.configuration.get(
                "name", "Simulation Instrument"
            ),
            "measurements": results,
            "simulation": True
        }
