
from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class ValidationDataStep(BaseStep):

    step_type = "validation_data"

    SUPPORTED_OPERATORS = {
        "equals",
        "not_equals",
        "contains",
        "starts_with",
        "ends_with"
    }

    @staticmethod
    def normalize(value, case_sensitive=True):
        value = str(value).strip()

        if not case_sensitive:
            value = value.casefold()

        return value

    def compare(self, actual, expected, operator, case_sensitive):
        if actual is None:
            return False

        actual_value = self.normalize(
            actual,
            case_sensitive
        )

        expected_value = self.normalize(
            expected,
            case_sensitive
        )

        if operator == "equals":
            return actual_value == expected_value

        if operator == "not_equals":
            return actual_value != expected_value

        if operator == "contains":
            return expected_value in actual_value

        if operator == "starts_with":
            return actual_value.startswith(expected_value)

        if operator == "ends_with":
            return actual_value.endswith(expected_value)

        raise ValueError(
            f"Unsupported validation operator: {operator}"
        )

    def build_conditions(self, context, parameters):

        conditions = parameters.get("conditions")

        # Backward compatibility:
        # Configuration lama hanya menggunakan source
        # dan reference_column.

        if conditions is None:
            source = parameters.get("source")
            reference_column = parameters.get(
                "reference_column"
            )

            if not source or not reference_column:
                raise ValueError(
                    "Validation source and reference_column are required."
                )

            conditions = [
                {
                    "source": source,
                    "reference_column": reference_column,
                    "operator": "equals"
                }
            ]

        if not isinstance(conditions, list) or not conditions:
            raise ValueError(
                "Validation conditions must be a non-empty list."
            )

        prepared = []

        for index, condition in enumerate(conditions):

            if not isinstance(condition, dict):
                raise ValueError(
                    f"Condition {index} must be an object."
                )

            source = condition.get("source")
            reference_column = condition.get(
                "reference_column"
            )

            if not reference_column:
                raise ValueError(
                    f"Condition {index} has no reference_column."
                )

            if source:
                expected = context.get(source)

                if expected is None:
                    raise ValueError(
                        f"No context data found at '{source}'."
                    )

            elif "value" in condition:
                expected = condition["value"]

            else:
                raise ValueError(
                    f"Condition {index} requires source or value."
                )

            operator = condition.get(
                "operator",
                "equals"
            )

            if operator not in self.SUPPORTED_OPERATORS:
                raise ValueError(
                    f"Unsupported validation operator: {operator}"
                )

            prepared.append({
                "source": source,
                "reference_column": reference_column,
                "operator": operator,
                "expected": expected
            })

        return prepared

    def execute(self, context):

        parameters = self.parameters

        reference = parameters.get("reference")

        output = parameters.get(
            "output",
            "validation.result"
        )

        mode = parameters.get(
            "condition_mode",
            "all"
        )

        case_sensitive = parameters.get(
            "case_sensitive",
            True
        )

        if mode not in ("all", "any"):
            return StepOutcome(
                success=False,
                message="Condition mode must be 'all' or 'any'."
            )

        reference_rows = context.get(reference)

        if not isinstance(reference_rows, list):
            return StepOutcome(
                success=False,
                message=f"Reference data '{reference}' is not a list."
            )

        try:
            conditions = self.build_conditions(
                context,
                parameters
            )

            best_candidate = None
            best_score = -1
            matched_record = None
            matched_index = None
            matched_results = None

            for row_index, record in enumerate(reference_rows):

                if not isinstance(record, dict):
                    continue

                condition_results = []

                for condition in conditions:

                    actual = record.get(
                        condition["reference_column"]
                    )

                    passed = self.compare(
                        actual=actual,
                        expected=condition["expected"],
                        operator=condition["operator"],
                        case_sensitive=case_sensitive
                    )

                    condition_results.append({
                        "source": condition["source"],
                        "reference_column": condition[
                            "reference_column"
                        ],
                        "operator": condition["operator"],
                        "expected": condition["expected"],
                        "actual": actual,
                        "passed": passed
                    })

                passed_count = sum(
                    result["passed"]
                    for result in condition_results
                )

                if passed_count > best_score:
                    best_score = passed_count
                    best_candidate = condition_results

                if mode == "all":
                    is_valid = all(
                        result["passed"]
                        for result in condition_results
                    )
                else:
                    is_valid = any(
                        result["passed"]
                        for result in condition_results
                    )

                if is_valid:
                    matched_record = record
                    matched_index = row_index
                    matched_results = condition_results
                    break

            is_valid = matched_record is not None

            result = {
                "valid": is_valid,
                "reference": reference,
                "condition_mode": mode,
                "matched_index": matched_index,
                "matched_record": matched_record,
                "condition_results": (
                    matched_results
                    if is_valid
                    else best_candidate
                ),
                "evaluated_records": len(reference_rows)
            }

            context.set(output, result)

            if not is_valid:
                return StepOutcome(
                    success=False,
                    message="Reference validation failed.",
                    data=result
                )

            return StepOutcome(
                success=True,
                message="Reference validation passed.",
                data=result
            )

        except Exception as error:
            return StepOutcome(
                success=False,
                message=str(error)
            )
