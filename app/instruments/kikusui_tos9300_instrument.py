
import pyvisa

from app.instruments.base_instrument import BaseInstrument


class KikusuiTOS9300Instrument(BaseInstrument):

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

        resource = self.connection_config.get("resource")

        if not resource:
            raise ValueError(
                "Kikusui VISA resource is not configured."
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

            self.instrument.timeout = int(
                self.connection_config.get(
                    "timeout", 5000
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

            return True

        except Exception:
            self.disconnect()
            raise

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
            "TOS9302 hardware test execution has not "
            "been implemented or safety-validated yet."
        )

    def read_measurements(self, parameters):

        raise NotImplementedError(
            "TOS9302 measurement reading is not implemented."
        )

    def _require_connection(self):

        if not self.connected or self.instrument is None:
            raise RuntimeError(
                "Kikusui TOS9302 is not connected."
            )
