
from app.workflows.base_step import BaseStep, StepOutcome


class SaveResultStep(BaseStep):

    step_type = "save_result"

    def execute(self, context):

        runtime = self.runtime

        if runtime is None:
            return StepOutcome(
                success=False,
                message="Workflow step runtime is missing."
            )

        result_path = self.parameters.get(
            "source",
            "result"
        )

        if not context.has(result_path):
            return StepOutcome(
                success=False,
                message=f"Result data not found: {result_path}"
            )

        result_record = context.get(result_path)

        if not isinstance(result_record, dict):
            return StepOutcome(
                success=False,
                message="Result record must be a dictionary."
            )

        try:

            record_id = runtime.save_result_record(
                result_record
            )

            context.set(
                "storage.record_id",
                record_id
            )

            context.set(
                "storage.status",
                "SAVED"
            )

            return StepOutcome(
                success=True,
                message=f"Result saved successfully. Record ID: {record_id}",
                data={
                    "record_id": record_id,
                    "status": "SAVED"
                }
            )

        except Exception as error:

            context.set(
                "storage.status",
                "FAILED"
            )

            return StepOutcome(
                success=False,
                message=f"Save result failed: {error}"
            )
