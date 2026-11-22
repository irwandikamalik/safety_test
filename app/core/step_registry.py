from app.workflows.base_step import BaseStep
from app.workflows.input_step import InputStep
from app.workflows.load_data_step import LoadDataStep
from app.workflows.validation_data_step import ValidationDataStep
from app.workflows.validation_step import (
    ValidationStep,
    BarcodeValidationStep
)
from app.workflows.approval_step import ApprovalStep
from app.workflows.instrument_test_step import InstrumentTestStep
from app.workflows.instrument_measurement_step import InstrumentMeasurementStep
from app.workflows.ac_volt_confirmation_step import ACVoltConfirmationStep
from app.workflows.build_result_step import BuildResultStep
from app.workflows.save_result_step import SaveResultStep


class StepRegistry:

    def __init__(self):

        self._steps = {}

        self.register(InputStep)
        self.register(LoadDataStep)
        self.register(ValidationDataStep)
        self.register(ValidationStep)
        self.register(BarcodeValidationStep)
        self.register(ApprovalStep)
        self.register(InstrumentTestStep)
        self.register(InstrumentMeasurementStep)
        self.register(ACVoltConfirmationStep)
        self.register(BuildResultStep)
        self.register(SaveResultStep)

    # ==========================================
    # REGISTER
    # ==========================================

    def register(self, step_class):

        if not isinstance(step_class, type):
            raise TypeError(
                "Step registration requires a class."
            )

        if not issubclass(step_class, BaseStep):
            raise TypeError(
                "Registered step must inherit from BaseStep."
            )

        step_type = step_class.step_type

        if not isinstance(step_type, str) or not step_type:
            raise ValueError(
                "Step class must define a valid step_type."
            )

        if step_type in self._steps:
            raise ValueError(
                f"Step type is already registered: {step_type}"
            )

        self._steps[step_type] = step_class

    # ==========================================
    # CREATE
    # ==========================================

    def create(self, configuration, runtime=None):
        step_type = configuration.get("type")

        step_class = self.get_step_class(step_type)

        if step_class is None:
            raise ValueError(
                f"Unregistered step type: {step_type}"
            )

        step = step_class(configuration)
        step.bind_runtime(runtime)

        return step

    # ==========================================
    # QUERY
    # ==========================================

    def available_types(self):

        return sorted(self._steps.keys())

    def is_registered(self, step_type):

        return step_type in self._steps

    def get_step_class(self, step_type):

        step_class = self._steps.get(step_type)

        if step_class is None:
            raise ValueError(
                f"Unknown step type: {step_type}"
            )

        return step_class