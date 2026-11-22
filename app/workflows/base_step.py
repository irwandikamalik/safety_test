from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepOutcome:

    success: bool = True
    message: str = ""
    interaction: dict | None = None
    data: dict = field(default_factory=dict)

    def __post_init__(self):

        if not isinstance(self.success, bool):
            raise TypeError(
                "StepOutcome.success must be a boolean."
            )

        if not isinstance(self.message, str):
            raise TypeError(
                "StepOutcome.message must be a string."
            )

        if self.interaction is not None:
            if not isinstance(self.interaction, dict):
                raise TypeError(
                    "StepOutcome.interaction must be a dictionary."
                )

        if not isinstance(self.data, dict):
            raise TypeError(
                "StepOutcome.data must be a dictionary."
            )


class BaseStep:

    step_type = None

    def __init__(self, configuration):

        if not isinstance(configuration, dict):
            raise TypeError(
                "Step configuration must be a dictionary."
            )

        if not self.step_type:
            raise ValueError(
                f"{type(self).__name__} has no step_type."
            )

        self.configuration = configuration
        self.runtime = None

        parameters = configuration.get("parameters", {})

        if not isinstance(parameters, dict):
            raise ValueError(
                f"Parameters of step '{self.step_type}' "
                "must be a dictionary."
            )

    def bind_runtime(self, runtime):
        self.runtime = runtime

    @property
    def step_id(self):
        return self.configuration.get("id")

    @property
    def name(self):
        return self.configuration.get(
            "name",
            self.step_type
        )

    @property
    def parameters(self):
        return self.configuration.get(
            "parameters",
            {}
        )

    def execute(self, context):
        raise NotImplementedError

    def complete(self, context, response):

        return StepOutcome(
            success=True,
            message="Step completed."
        )