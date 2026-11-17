
from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class InstrumentTestStep(BaseStep):

    step_type = "instrument_test"

    def execute(self, context):

        return StepOutcome(
            success=True,
            message="Instrument test started."
        )
