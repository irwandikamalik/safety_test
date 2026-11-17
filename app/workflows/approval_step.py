
from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class ApprovalStep(BaseStep):

    step_type = "approval"

    def execute(self, context):

        parameters = self.configuration.get(
            "parameters", {}
        )

        return StepOutcome(
            success=True,
            message="Waiting for operator approval.",
            interaction={
                "type": "approval",
                "title": self.configuration.get(
                    "name", "Operator Approval"
                ),
                "message": parameters.get(
                    "message",
                    "Please verify safety preparation before continuing."
                )
            }
        )

    def complete(self, context, response):

        approved = response.get("approved", False)

        if not approved:
            return StepOutcome(
                success=False,
                message="Operator approval rejected."
            )

        context.set("approval", True)

        return StepOutcome(
            success=True,
            message="Operator approval accepted."
        )
