
from app.instruments.driver_registry import DriverRegistry


class InstrumentManager:

    def __init__(
        self,
        model_configuration,
        instrument_catalog,
        application_configuration
    ):

        self.model_configuration = model_configuration
        self.instrument_catalog = instrument_catalog
        self.application_configuration = application_configuration

        self.registry = DriverRegistry()
        self.instruments = {}

        self.application_mode = (
            application_configuration.get(
                "application_mode",
                "SIMULATION"
            )
        )

        self._validate_application_mode()

        self._load_instruments()

    # ==========================================
    # APPLICATION MODE
    # ==========================================

    def _validate_application_mode(self):

        if self.application_mode not in (
            "SIMULATION",
            "HARDWARE"
        ):
            raise ValueError(
                f"Invalid application mode: {self.application_mode}"
            )

        if (
            self.application_mode == "HARDWARE"
            and self.application_configuration.get(
                "allow_hardware_mode"
            ) is not True
        ):
            raise RuntimeError(
                "Hardware mode is disabled by application policy."
            )

    # ==========================================
    # INSTRUMENT CONFIGURATION
    # ==========================================

    def _load_instruments(self):

        model_instruments = self.model_configuration.get(
            "instruments",
            {}
        )

        catalog_instruments = self.instrument_catalog.get(
            "instruments",
            {}
        )

        if not isinstance(model_instruments, dict):
            raise ValueError(
                "Model instruments configuration must be an object."
            )

        if not isinstance(catalog_instruments, dict):
            raise ValueError(
                "Instrument catalog must be an object."
            )

        for instrument_id, model_config in model_instruments.items():

            if not isinstance(model_config, dict):
                raise ValueError(
                    f"Invalid model instrument configuration: {instrument_id}"
                )

            if model_config.get("enabled") is not True:
                continue

            catalog_id = model_config.get("catalog_id")

            if not catalog_id:
                raise ValueError(
                    f"Missing catalog_id for instrument: {instrument_id}"
                )

            catalog_config = catalog_instruments.get(catalog_id)

            if catalog_config is None:
                raise ValueError(
                    f"Instrument catalog entry not found: {catalog_id}"
                )

            driver_configuration = (
                self._merge_configuration(
                    catalog_config,
                    model_config
                )
            )

            if self.application_mode == "SIMULATION":

                # Simulation mode always uses the simulation driver.
                driver_id = "simulation"

            else:

                # Hardware driver must be explicitly registered.
                driver_id = catalog_config.get("driver")

                if not driver_id:
                    raise ValueError(
                        f"No driver defined for: {catalog_id}"
                    )

            instrument = self.registry.create(
                driver_id,
                driver_configuration
            )

            self.instruments[instrument_id] = instrument

    # ==========================================
    # CONFIGURATION MERGING
    # ==========================================

    @staticmethod
    def _merge_configuration(
        catalog_config,
        model_config
    ):

        merged = dict(catalog_config)

        catalog_connection = catalog_config.get(
            "connection",
            {}
        )

        overrides = model_config.get(
            "overrides",
            {}
        )

        if not isinstance(overrides, dict):
            raise ValueError(
                "Instrument overrides must be an object."
            )

        connection_overrides = overrides.get(
            "connection",
            {}
        )

        if not isinstance(connection_overrides, dict):
            raise ValueError(
                "Connection overrides must be an object."
            )

        merged["connection"] = {
            **catalog_connection,
            **connection_overrides
        }

        # Apply other model-specific overrides.
        for key, value in overrides.items():

            if key == "connection":
                continue

            merged[key] = value

        merged["catalog_id"] = model_config.get(
            "catalog_id"
        )

        return merged

    # ==========================================
    # INSTRUMENT ACCESS
    # ==========================================

    def get_instrument(self, instrument_id):

        instrument = self.instruments.get(
            instrument_id
        )

        if instrument is None:
            raise ValueError(
                f"Instrument not found or disabled: {instrument_id}"
            )

        return instrument

    def connect(self, instrument_id):

        instrument = self.get_instrument(
            instrument_id
        )

        return instrument.connect()

    def disconnect(self, instrument_id):

        instrument = self.get_instrument(
            instrument_id
        )

        instrument.disconnect()

    def execute_test(
        self,
        instrument_id,
        function,
        parameters
    ):

        instrument = self.get_instrument(
            instrument_id
        )

        return instrument.execute_test(
            function,
            parameters
        )

    def available_instruments(self):

        return list(self.instruments.keys())
