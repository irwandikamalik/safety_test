
from app.workflows.base_step import BaseStep, StepOutcome


class InstrumentMeasurementStep(BaseStep):

    step_type = "instrument_measurement"

    def execute(self, context):

        return StepOutcome(
            success=True,
            message="Instrument measurement completed."
        )
