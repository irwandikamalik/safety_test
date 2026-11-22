
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from app.workflows.base_step import BaseStep, StepOutcome


class BuildResultStep(BaseStep):

    step_type = "build_result"

    VALID_EXECUTION_STATUSES = {
        "COMPLETED",
        "ERROR",
        "ABORTED"
    }

    VALID_JUDGMENTS = {
        "PASS",
        "FAIL",
        "NG"
    }

    REQUIRED_SYSTEM_FIELDS = {
        "test_id",
        "timestamp",
        "model_id",
        "model_name",
        "sequence_id",
        "application_mode",
        "execution_status"
    }

    def execute(self, context):

        try:

            result_record = self.build_result(
                context,
                execution_status="COMPLETED"
            )

            context.set("result", result_record)

            return StepOutcome(
                success=True,
                message="Test result structure created.",
                data=result_record
            )

        except Exception as error:

            return StepOutcome(
                success=False,
                message=f"Build result failed: {error}"
            )

    def build_result(
        self,
        context,
        execution_status="COMPLETED",
        judgment=None,
        reason=None
    ):

        execution_status = str(
            execution_status
        ).strip().upper()

        if execution_status not in self.VALID_EXECUTION_STATUSES:
            raise ValueError(
                f"Invalid execution status: {execution_status}"
            )

        operator = context.get("operator", {})

        if not isinstance(operator, dict):
            raise ValueError(
                "Operator data must be a dictionary."
            )

        measurements = context.get("measurements", {})

        if not isinstance(measurements, dict):
            raise ValueError(
                "Measurements data must be a dictionary."
            )

        test_judgments = context.get("test_judgments", {})

        if not isinstance(test_judgments, dict):
            raise ValueError(
                "Test judgments data must be a dictionary."
            )

        if judgment is None:

            judgment = context.get("judgment")

        if judgment is not None:

            judgment = str(judgment).strip().upper()

            if judgment not in self.VALID_JUDGMENTS:
                raise ValueError(
                    f"Invalid overall judgment: {judgment}"
                )

        if execution_status == "COMPLETED" and judgment is None:
            raise ValueError(
                "Completed workflow must have an overall judgment."
            )

        if execution_status in ("ERROR", "ABORTED"):
            judgment = None

        system_data = {
            "test_id": str(uuid4()),
            "timestamp": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "model_id": context.get("model_id"),
            "model_name": context.get("model_name"),
            "sequence_id": context.get("sequence_id"),
            "application_mode": context.get(
                "application_mode",
                "SIMULATION"
            ),
            "execution_status": execution_status
        }

        result_record = {
            "system": system_data,

            "operator": deepcopy(operator),

            "product": {
                "serial_number": context.get("serial_number", ""),
                "door_top": context.get("door_top", ""),
                "door_bottom": context.get("door_bottom", "")
            },

            "measurements": deepcopy(measurements),

            "test_judgments": deepcopy(test_judgments),

            "result": {
                "judgment": judgment
            },

            "custom": {}
        }

        if reason is not None:

            result_record["result"]["reason"] = str(reason)

        self._add_custom_fields(
            context,
            result_record
        )

        return result_record

    def _add_custom_fields(self, context, result_record):

        custom_fields = self.parameters.get(
            "custom_fields",
            {}
        )

        if not isinstance(custom_fields, dict):
            raise ValueError(
                "custom_fields must be a dictionary."
            )

        for field_name, source_path in custom_fields.items():

            if not isinstance(field_name, str) or not field_name:
                raise ValueError(
                    "Custom field name must be a non-empty string."
                )

            if not isinstance(source_path, str) or not source_path:
                raise ValueError(
                    f"Source path for custom field '{field_name}' is invalid."
                )

            if field_name in self.REQUIRED_SYSTEM_FIELDS:
                raise ValueError(
                    f"Cannot override required system field: {field_name}"
                )

            if not context.has(source_path):
                raise ValueError(
                    f"Custom field source does not exist: {source_path}"
                )

            result_record["custom"][field_name] = deepcopy(
                context.get(source_path)
            )
