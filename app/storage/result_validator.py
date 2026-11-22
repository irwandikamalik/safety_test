
import json

from copy import deepcopy


class ResultValidator:

    REQUIRED_SYSTEM_FIELDS = (
        "test_id",
        "timestamp",
        "model_id",
        "model_name",
        "sequence_id",
        "application_mode",
    )

    VALID_JUDGMENTS = {
        "PASS",
        "FAIL",
        "NG",
    }

    VALID_APPLICATION_MODES = {
        "SIMULATION",
        "HARDWARE",
    }

    VALID_EXECUTION_STATUSES = {
        "COMPLETED",
        "ERROR",
        "ABORTED",
    }

    @classmethod
    def validate(cls, result_record):

        if not isinstance(result_record, dict):
            raise TypeError(
                "Result record must be a dictionary."
            )

        record = deepcopy(result_record)

        required_sections = (
            "system",
            "operator",
            "product",
            "result",
        )

        for section_name in required_sections:

            section = record.get(section_name)

            if not isinstance(section, dict):
                raise ValueError(
                    f"Section '{section_name}' must be a dictionary."
                )

        system = record["system"]
        result = record["result"]

        # ------------------------------------------
        # REQUIRED SYSTEM FIELDS
        # ------------------------------------------

        for field_name in cls.REQUIRED_SYSTEM_FIELDS:

            value = system.get(field_name)

            if value is None or str(value).strip() == "":
                raise ValueError(
                    f"Required system field is missing: {field_name}"
                )

        system["test_id"] = str(
            system["test_id"]
        ).strip()

        # ------------------------------------------
        # APPLICATION MODE
        # ------------------------------------------

        application_mode = str(
            system["application_mode"]
        ).upper()

        if application_mode not in cls.VALID_APPLICATION_MODES:
            raise ValueError(
                f"Invalid application mode: {application_mode}"
            )

        system["application_mode"] = application_mode

        # ------------------------------------------
        # EXECUTION STATUS
        # ------------------------------------------

        execution_status = str(
            system.get("execution_status", "COMPLETED")
        ).strip().upper()

        if execution_status not in cls.VALID_EXECUTION_STATUSES:
            raise ValueError(
                f"Invalid execution status: {execution_status}"
            )

        system["execution_status"] = execution_status

        # ------------------------------------------
        # JUDGMENT
        # ------------------------------------------

        judgment = result.get("judgment")

        if judgment is not None:
            judgment = str(judgment).strip().upper()

            if judgment not in cls.VALID_JUDGMENTS:
                raise ValueError(
                    f"Invalid judgment: {judgment}"
                )

        if execution_status == "COMPLETED" and judgment is None:
            raise ValueError(
                "Completed result must have a judgment."
            )

        if execution_status in ("ERROR", "ABORTED"):
            if judgment is not None and judgment not in cls.VALID_JUDGMENTS:
                raise ValueError(
                    f"Invalid judgment: {judgment}"
                )

        result["judgment"] = judgment

        # ------------------------------------------
        # OPTIONAL STRUCTURED SECTIONS
        # ------------------------------------------

        optional_sections = (
            "measurements",
            "test_judgments",
            "custom",
        )

        for section_name in optional_sections:

            if section_name in record:

                if not isinstance(record[section_name], dict):
                    raise ValueError(
                        f"Section '{section_name}' must be a dictionary."
                    )

        # ------------------------------------------
        # JSON COMPATIBILITY
        # ------------------------------------------

        try:

            json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
            )

        except (TypeError, ValueError) as error:

            raise ValueError(
                f"Result record contains unsupported data: {error}"
            ) from error

        return record
