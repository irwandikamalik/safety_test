
from app.workflows.input_step import InputStep
from app.workflows.validation_step import (
    ValidationStep,
    BarcodeValidationStep
)
from app.workflows.approval_step import ApprovalStep
from app.workflows.instrument_test_step import InstrumentTestStep
from app.workflows.instrument_measurement_step import (
    InstrumentMeasurementStep
)
from app.workflows.ac_volt_confirmation_step import (
    ACVoltConfirmationStep
)


class StepRegistry:

    def __init__(self):
        self._steps = {}

        self.register(InputStep)
        self.register(ValidationStep)
        self.register(BarcodeValidationStep)
        self.register(ApprovalStep)
        self.register(InstrumentTestStep)
        self.register(InstrumentMeasurementStep)
        self.register(ACVoltConfirmationStep)

    def register(self, step_class):

        self._steps[step_class.step_type] = step_class

    def create(self, configuration):

        step_type = configuration.get("type")

        step_class = self._steps.get(step_type)

        if step_class is None:
            raise ValueError(
                f"Unknown step type: {step_type}"
            )

        return step_class(configuration)

    def available_types(self):

        return list(self._steps.keys())
