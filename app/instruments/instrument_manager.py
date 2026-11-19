
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

    def _load_instruments(self):

        model_instruments = self.model_configuration.get(
            "instruments", {}
        )

        catalog_instruments = self.instrument_catalog.get(
            "instruments", {}
        )

        if not isinstance(model_instruments, dict):
            raise ValueError(
                "Model instruments configuration must be an object."
            )

        if not isinstance(catalog_instruments, dict):
            raise ValueError(
                "Instrument catalog must be an object."
            )

        print("\n========== INSTRUMENT MANAGER DEBUG ==========")
        print("MODEL INSTRUMENTS:", list(model_instruments.keys()))
        print("CATALOG INSTRUMENTS:", list(catalog_instruments.keys()))
        print("APPLICATION MODE:", self.application_mode)
        print("==============================================\n")

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

            driver_configuration = self._merge_configuration(
                catalog_config,
                model_config
            )

            # ----------------------------------
            # DRIVER SELECTION
            # ----------------------------------

            if self.application_mode == "SIMULATION":

                driver_id = "simulation"

            else:

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

            print(
                f"LOADED INSTRUMENT: {instrument_id} "
                f"-> {type(instrument).__name__}"
            )

    @staticmethod
    def _merge_configuration(
        catalog_config,
        model_config
    ):

        merged = dict(catalog_config)

        catalog_connection = catalog_config.get(
            "connection", {}
        )

        overrides = model_config.get(
            "overrides", {}
        )

        if not isinstance(overrides, dict):
            raise ValueError(
                "Instrument overrides must be an object."
            )

        connection_overrides = overrides.get(
            "connection", {}
        )

        if not isinstance(connection_overrides, dict):
            raise ValueError(
                "Connection overrides must be an object."
            )

        merged["connection"] = {
            **catalog_connection,
            **connection_overrides
        }

        for key, value in overrides.items():

            if key == "connection":
                continue

            merged[key] = value

        merged["catalog_id"] = model_config.get(
            "catalog_id"
        )

        return merged

    def get_instrument(self, instrument_id):

        instrument = self.instruments.get(instrument_id)

        if instrument is None:
            raise ValueError(
                f"Instrument not found or disabled: {instrument_id}"
            )

        return instrument

    def connect(self, instrument_id):

        return self.get_instrument(
            instrument_id
        ).connect()

    def disconnect(self, instrument_id):

        self.get_instrument(
            instrument_id
        ).disconnect()

    def execute_test(
        self,
        instrument_id,
        function,
        parameters
    ):

        instrument = self.get_instrument(instrument_id)

        return instrument.execute_test(
            function,
            parameters
        )

    def read_measurements(
        self,
        instrument_id,
        measurement_ids=None
    ):

        instrument = self.get_instrument(instrument_id)

        instrument_configuration = instrument.configuration

        measurement_catalog = (
            instrument_configuration.get(
                "measurements", {}
            )
        )

        if not isinstance(measurement_catalog, dict):
            raise ValueError(
                "Instrument measurement catalog must be an object."
            )

        selected_ids = measurement_ids

        if selected_ids is None:
            selected_ids = instrument_configuration.get(
                "selected_measurements", []
            )

        if not selected_ids:
            raise ValueError(
                f"No measurements selected for {instrument_id}."
            )

        measurement_definitions = []

        for measurement_id in selected_ids:

            definition = measurement_catalog.get(
                measurement_id
            )

            if definition is None:
                raise ValueError(
                    f"Unknown measurement: {measurement_id}"
                )

            if not isinstance(definition, dict):
                raise ValueError(
                    f"Invalid measurement definition: {measurement_id}"
                )

            measurement_definitions.append({
                "id": measurement_id,
                **definition
            })

        parameters = {
            "measurements": measurement_definitions,
            "element": instrument_configuration.get(
                "element", 1
            ),
            "simulation_values": instrument_configuration.get(
                "simulation_values", {}
            )
        }

        return instrument.read_measurements(parameters)

    def configure_instrument(
        self,
        instrument_id,
        parameters
    ):

        instrument = self.get_instrument(
            instrument_id
        )

        configure_method = getattr(
            instrument,
            "configure",
            None
        )

        if not callable(configure_method):
            raise NotImplementedError(
                f"Configuration is not supported by: {instrument_id}"
            )

        return configure_method(parameters)


    def output_on(
        self,
        instrument_id,
        safety_approved=False
    ):

        instrument = self.get_instrument(
            instrument_id
        )

        output_on_method = getattr(
            instrument,
            "output_on",
            None
        )

        if not callable(output_on_method):
            raise NotImplementedError(
                f"Output ON is not supported by: {instrument_id}"
            )

        return output_on_method(
            safety_approved=safety_approved
        )

    def output_off(self, instrument_id):

        instrument = self.get_instrument(
            instrument_id
        )

        output_off_method = getattr(
            instrument,
            "output_off",
            None
        )

        if not callable(output_off_method):
            raise NotImplementedError(
                f"Output OFF is not supported by: {instrument_id}"
            )

        return output_off_method()


    def read_instrument_configuration(
        self,
        instrument_id
    ):

        instrument = self.get_instrument(
            instrument_id
        )

        read_method = getattr(
            instrument,
            "read_configuration",
            None
        )

        if not callable(read_method):
            raise NotImplementedError(
                f"Configuration reading is not supported by: {instrument_id}"
            )

        return read_method()

    def available_instruments(self):

        return list(self.instruments.keys())
