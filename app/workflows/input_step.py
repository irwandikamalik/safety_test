from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class InputStep(BaseStep):

    step_type = "input"

    def execute(self, context):

        parameters = self.parameters

        field = parameters.get("field")

        if not field:
            return StepOutcome(
                success=False,
                message="Input field is not configured."
            )

        return StepOutcome(
            success=True,
            message="Waiting for operator input.",
            interaction={
                "type": "input",
                "title": self.name,
                "field": field,
                "label": parameters.get(
                    "label",
                    field.replace("_", " ").title()
                ),
                "placeholder": parameters.get(
                    "placeholder",
                    "Enter value"
                ),
                "required": parameters.get(
                    "required",
                    True
                )
            }
        )

    def complete(self, context, response):

        field = self.parameters["field"]

        value = str(
            response.get("value", "")
        ).strip()

        required = self.parameters.get(
            "required",
            True
        )

        if required and not value:
            return StepOutcome(
                success=False,
                message=f"{field} cannot be empty."
            )

        context.set(field, value)

        return StepOutcome(
            success=True,
            message=f"{field} received.",
            data={
                field: value
            }
        )