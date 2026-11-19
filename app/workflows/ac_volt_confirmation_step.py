
from app.workflows.base_step import BaseStep, StepOutcome


class ACVoltConfirmationStep(BaseStep):

    step_type = "ac_volt_confirmation"

    def execute(self, context):

        parameters = self.configuration.get(
            "parameters",
            {}
        )

        power_supply = parameters.get("power_supply")
        power_meter = parameters.get("power_meter")

        if not power_supply:
            return StepOutcome(
                success=False,
                message="AC Volt Confirmation power_supply is missing."
            )

        if not power_meter:
            return StepOutcome(
                success=False,
                message="AC Volt Confirmation power_meter is missing."
            )

        return StepOutcome(
            success=True,
            message="AC Volt Confirmation requested.",
            interaction={
                "type": "ac_volt_confirmation",
                "step_id": self.configuration.get("id"),
                "name": self.configuration.get(
                    "name",
                    "AC Volt Confirmation"
                ),
                "parameters": parameters
            }
        )
