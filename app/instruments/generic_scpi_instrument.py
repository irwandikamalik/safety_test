import re

import pyvisa

from app.instruments.base_instrument import BaseInstrument


class GenericSCPIInstrument(BaseInstrument):

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

    def connect(self):

        if self.connected:
            return True

        interface = self.connection_config.get(
            "interface", "USB"
        ).upper()

        resource = self.connection_config.get(
            "resource"
        )

        if not resource:
            raise ValueError(
                "SCPI resource is not configured."
            )

        timeout = int(
            self.connection_config.get(
                "timeout", 5000
            )
        )

        backend = self.connection_config.get(
            "backend", ""
        ).strip()

        if backend:
            self.resource_manager = (
                pyvisa.ResourceManager(backend)
            )
        else:
            self.resource_manager = (
                pyvisa.ResourceManager()
            )

        self.instrument = (
            self.resource_manager.open_resource(resource)
        )

        self.instrument.timeout = timeout

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

        return True

    def disconnect(self):

        try:
            if self.instrument is not None:
                self.instrument.close()

        finally:
            self.instrument = None
            self.connected = False

            if self.resource_manager is not None:
                self.resource_manager.close()

            self.resource_manager = None

    def identify(self):

        self._require_connection()

        command = self.command_config.get(
            "identify", "*IDN?"
        )

        return self.instrument.query(command).strip()

    def execute_test(self, function, parameters):

        raise NotImplementedError(
            "Generic SCPI driver is a measurement driver. "
            "It does not implement safety test execution."
        )

    def read_measurements(self, parameters):

        self._require_connection()

        measurements = parameters.get(
            "measurements", []
        )

        if not isinstance(measurements, list):
            raise ValueError(
                "Measurements must be a list."
            )

        results = {}

        configure_template = (
            self.command_config.get(
                "configure_item",
                ":NUMERIC:NORMAL:ITEM{item} {function},{element}"
            )
        )

        read_template = (
            self.command_config.get(
                "read_item",
                ":NUMERIC:NORMAL:VALUE? {item}"
            )
        )

        element = int(parameters.get("element", 1))

        for item_number, measurement in enumerate(
            measurements, start=1
        ):

            if not isinstance(measurement, dict):
                raise ValueError(
                    "Invalid measurement definition."
                )

            measurement_id = measurement.get("id")
            function = measurement.get("function")
            unit = measurement.get("unit", "")

            if not measurement_id or not function:
                raise ValueError(
                    "Measurement ID and function are required."
                )

            configure_command = (
                configure_template.format(
                    item=item_number,
                    function=function,
                    element=element
                )
            )

            self.instrument.write(
                configure_command
            )

            read_command = read_template.format(
                item=item_number
            )

            raw_value = self.instrument.query(
                read_command
            ).strip()

            value = self._parse_value(raw_value)

            results[measurement_id] = {
                "value": value,
                "unit": unit,
                "raw": raw_value
            }

        return {
            "instrument": self.configuration.get(
                "name", "Generic SCPI Instrument"
            ),
            "measurements": results,
            "simulation": False
        }

    def _parse_value(self, raw_value):

        value = raw_value.strip()

        try:
            return float(value)

        except ValueError:
            pass

        # Some instruments may return multiple values.
        # For example: 220.5,0.0
        parts = value.split(",")

        if parts:
            try:
                return float(parts[0].strip())
            except ValueError:
                pass

        raise ValueError(
            f"Invalid numeric response from instrument: {raw_value}"
        )

    def _require_connection(self):

        if not self.connected or self.instrument is None:
            raise RuntimeError(
                "Instrument is not connected."
            )