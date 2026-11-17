
import re

from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class ValidationStep(BaseStep):

    step_type = "validate_serial"

    def execute(self, context):

        return self.validate(context)

    def validate(self, context):

        parameters = self.configuration.get(
            "parameters", {}
        )

        source = parameters.get("source")

        value = context.get(source, "")

        if not value:
            return StepOutcome(
                success=False,
                message=f"No data found for {source}."
            )

        minimum = parameters.get("min_length")
        maximum = parameters.get("max_length")
        pattern = parameters.get("pattern")

        if minimum is not None and len(value) < minimum:
            return StepOutcome(
                success=False,
                message=f"{source} is too short."
            )

        if maximum is not None and len(value) > maximum:
            return StepOutcome(
                success=False,
                message=f"{source} is too long."
            )

        if pattern and not re.fullmatch(pattern, value):
            return StepOutcome(
                success=False,
                message=f"{source} format is invalid."
            )

        return StepOutcome(
            success=True,
            message=f"{source} validation passed."
        )


class BarcodeValidationStep(ValidationStep):

    step_type = "validate_barcode"
