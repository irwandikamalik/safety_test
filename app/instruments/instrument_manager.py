
from app.instruments.simulation_instrument import (
    SimulationInstrument
)


class InstrumentManager:

    def __init__(self, configuration):
        self.configuration = configuration
        self.instruments = {}

        for instrument_id, instrument_config in (
            configuration.get("instruments", {}).items()
        ):
            self.instruments[instrument_id] = (
                SimulationInstrument(instrument_config)
            )

    def get_instrument(self, instrument_id):

        instrument = self.instruments.get(instrument_id)

        if instrument is None:
            raise ValueError(
                f"Instrument not found: {instrument_id}"
            )

        return instrument

    def connect(self, instrument_id):

        instrument = self.get_instrument(instrument_id)

        return instrument.connect()

    def disconnect(self, instrument_id):

        instrument = self.get_instrument(instrument_id)

        instrument.disconnect()

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
