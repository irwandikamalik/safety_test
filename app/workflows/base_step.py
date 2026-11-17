
class StepOutcome:

    def __init__(
        self,
        success=True,
        message="",
        interaction=None,
        data=None
    ):
        self.success = success
        self.message = message
        self.interaction = interaction
        self.data = data or {}


class BaseStep:

    step_type = None

    def __init__(self, configuration):
        self.configuration = configuration

    def execute(self, context):
        raise NotImplementedError

    def complete(self, context, response):
        return StepOutcome(
            success=True,
            message="Step completed."
        )
