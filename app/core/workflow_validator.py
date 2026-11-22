
import re
from pathlib import Path

from app.core.step_registry import StepRegistry


class WorkflowValidator:
    """
    Static preflight validator for model workflow configuration.

    This validator must not:
    - Create instrument drivers.
    - Connect to instruments.
    - Initialize storage adapters.
    - Execute workflow steps.
    - Modify configuration files or databases.
    """

    SUPPORTED_STORAGE_TYPES = {
        "sqlite",
        "csv",
        "json",
        "txt",
    }

    SUPPORTED_APPLICATION_MODES = {
        "SIMULATION",
        "HARDWARE",
    }

    SUPPORTED_DATA_SOURCES = {
        "csv",
        "txt",
        "json",
        "sqlite",
    }

    VALIDATION_OPERATORS = {
        "equals",
        "not_equals",
        "contains",
        "starts_with",
        "ends_with",
    }

    IDENTIFIER_PATTERN = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    STEP_SCHEMAS = {
        "input": {
            "required": {
                "field": str,
            },
            "optional": {
                "label": str,
                "placeholder": str,
                "required": bool,
            },
        },

        "validate_serial": {
            "required": {
                "source": str,
            },
            "optional": {
                "min_length": int,
                "max_length": int,
                "pattern": str,
            },
        },

        "validate_barcode": {
            "required": {
                "source": str,
            },
            "optional": {
                "min_length": int,
                "max_length": int,
                "pattern": str,
            },
        },

        "approval": {
            "required": {},
            "optional": {
                "message": str,
            },
        },

        "instrument_test": {
            "required": {
                "instrument": str,
                "function": str,
            },
            "optional": {
                "test_parameters": dict,
            },
        },

        "instrument_measurement": {
            "required": {
                "instrument": str,
            },
            "optional": {
                "duration_s": (int, float),
                "sample_interval_s": (int, float),
                "measurements": list,
            },
        },

        "ac_volt_confirmation": {
            "required": {
                "power_supply": str,
                "power_meter": str,
            },
            "optional": {
                "measurements": list,
            },
        },

        "load_data": {
            "required": {
                "source": str,
                "output": str,
            },
            "optional": {
                "file": str,
                "database": str,
                "table": str,
                "delimiter": str,
                "has_header": bool,
                "fieldnames": list,
                "columns": list,
            },
        },

        "validation_data": {
            "required": {
                "reference": str,
            },
            "optional": {
                "conditions": list,
                "condition_mode": str,
                "case_sensitive": bool,
                "source": str,
                "reference_column": str,
                "operator": str,
                "value": object,
                "output": str,
            },
        },

        "build_result": {
            "required": {},
            "optional": {
                "custom_fields": dict,
            },
        },

        "save_result": {
            "required": {},
            "optional": {
                "source": str,
            },
        },
    }

    def __init__(self):

        self.registry = StepRegistry()
        self.errors = []

    # ==================================================
    # PUBLIC VALIDATION
    # ==================================================

    def validate(
        self,
        configuration,
        expected_model_id=None
    ):

        self.errors = []

        if not isinstance(configuration, dict):

            return self._result([
                "Model configuration must be an object."
            ])

        required_roots = (
            "model",
            "sequence",
            "instruments",
            "parameters",
            "application",
            "instrument_catalog",
        )

        for key in required_roots:

            if key not in configuration:

                self.errors.append(
                    f"Configuration is missing '{key}'."
                )

            elif not isinstance(configuration[key], dict):

                self.errors.append(
                    f"Configuration '{key}' must be an object."
                )

        if self.errors:
            return self._result()

        self._validate_model(
            configuration["model"],
            expected_model_id
        )

        self._validate_application(
            configuration["application"]
        )

        self._validate_parameters(
            configuration["parameters"]
        )

        self._validate_instrument_configuration(
            configuration["instruments"],
            configuration["instrument_catalog"],
            configuration["application"]
        )

        self._validate_sequence(
            configuration["sequence"],
            configuration["instruments"],
            configuration["instrument_catalog"]
        )

        self._validate_storage(
            configuration["application"]
        )

        return self._result()

    # ==================================================
    # RESULT
    # ==================================================

    def _result(self, additional_errors=None):

        errors = list(self.errors)

        if additional_errors:
            errors.extend(additional_errors)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    # ==================================================
    # MODEL
    # ==================================================

    def _validate_model(
        self,
        model,
        expected_model_id
    ):

        model_id = model.get("model_id")

        if not isinstance(model_id, str) or not model_id.strip():

            self.errors.append(
                "model.json: model_id is required."
            )

        elif (
            expected_model_id is not None
            and model_id != expected_model_id
        ):

            self.errors.append(
                "model.json: model_id does not match folder name."
            )

        model_name = model.get("model_name")

        if not isinstance(model_name, str) or not model_name.strip():

            self.errors.append(
                "model.json: model_name is required."
            )

        if model.get("enabled") is not True:

            self.errors.append(
                "Model is disabled."
            )

    # ==================================================
    # APPLICATION
    # ==================================================

    def _validate_application(self, application):

        mode = application.get(
            "application_mode"
        )

        if (
            not isinstance(mode, str)
            or mode not in self.SUPPORTED_APPLICATION_MODES
        ):

            self.errors.append(
                "application.json: invalid application_mode."
            )

        if (
            mode == "HARDWARE"
            and application.get("allow_hardware_mode") is not True
        ):

            self.errors.append(
                "Hardware mode is not enabled by application policy."
            )

        allow_hardware = application.get(
            "allow_hardware_mode"
        )

        if not isinstance(allow_hardware, bool):

            self.errors.append(
                "application.json: allow_hardware_mode must be boolean."
            )

    # ==================================================
    # PARAMETERS
    # ==================================================

    def _validate_parameters(self, parameters):

        test_parameters = parameters.get(
            "test_parameters"
        )

        if not isinstance(test_parameters, dict):

            self.errors.append(
                "parameters.json: test_parameters must be an object."
            )

        model_id = parameters.get("model_id")

        if model_id is not None and not isinstance(model_id, str):

            self.errors.append(
                "parameters.json: model_id must be a string."
            )

        hardware_approved = parameters.get(
            "hardware_approved"
        )

        if (
            hardware_approved is not None
            and not isinstance(hardware_approved, bool)
        ):

            self.errors.append(
                "parameters.json: hardware_approved must be boolean."
            )

    # ==================================================
    # SEQUENCE
    # ==================================================

    def _validate_sequence(
        self,
        sequence,
        model_instruments,
        instrument_catalog
    ):

        sequence_id = sequence.get("sequence_id")

        if not isinstance(sequence_id, str) or not sequence_id.strip():

            self.errors.append(
                "sequence.json: sequence_id is required."
            )

        steps = sequence.get("steps")

        if not isinstance(steps, list) or not steps:

            self.errors.append(
                "sequence.json: steps must be a non-empty list."
            )

            return

        step_ids = set()

        for index, step in enumerate(steps):

            prefix = f"Step {index + 1}"

            if not isinstance(step, dict):

                self.errors.append(
                    f"{prefix}: configuration must be an object."
                )

                continue

            self._validate_step_id(
                step,
                prefix,
                step_ids
            )

            if not self._validate_step_enabled(
                step,
                prefix
            ):

                continue

            step_type = step.get("type")

            if not isinstance(step_type, str) or not step_type:

                self.errors.append(
                    f"{prefix}: type is required."
                )

                continue

            if not self.registry.is_registered(step_type):

                self.errors.append(
                    f"{prefix}: unregistered step type '{step_type}'."
                )

                continue

            parameters = step.get(
                "parameters",
                {}
            )

            if not isinstance(parameters, dict):

                self.errors.append(
                    f"{prefix}: parameters must be an object."
                )

                continue

            self._validate_step_parameters(
                step_type,
                parameters,
                prefix
            )

            self._validate_step_instruments(
                step_type,
                parameters,
                model_instruments,
                instrument_catalog,
                prefix
            )
        self._validate_sequence_dependencies(steps)

    # ==================================================
    # SEQUENCE DEPENDENCIES
    # ==================================================

    def _validate_sequence_dependencies(self, steps):

        # Data yang tersedia sejak WorkflowContext dibuat.
        available_paths = {
            "operator",
            "model_id",
            "model_name",
            "serial_number",
            "door_top",
            "door_bottom",
            "sequence_id",
            "application_mode",
            "approval",
            "measurements",
            "judgment",
        }

        judgment_available = False

        def is_path_available(path):

            if not isinstance(path, str) or not path.strip():
                return False

            path = path.strip()

            # Exact path exists.
            if path in available_paths:
                return True

            # A child path can exist only when explicitly registered
            # or when it is part of an already registered output.
            return False

        def register_output(path, prefix):

            if not isinstance(path, str) or not path.strip():

                self.errors.append(
                    f"{prefix}: output path must be a non-empty string."
                )

                return

            available_paths.add(path.strip())

        for index, step in enumerate(steps):

            if not isinstance(step, dict):
                continue

            if step.get("enabled", True) is not True:
                continue

            step_type = step.get("type")
            parameters = step.get("parameters", {})

            if not isinstance(parameters, dict):
                continue

            prefix = f"Step {index + 1}"

            # ------------------------------------------
            # VALIDATE SERIAL / BARCODE
            # ------------------------------------------

            if step_type in (
                "validate_serial",
                "validate_barcode",
            ):

                source = parameters.get("source")

                if (
                    isinstance(source, str)
                    and source.strip()
                    and not is_path_available(source)
                ):

                    self.errors.append(
                        f"{prefix}: source '{source}' is not available. "
                        "Provide it through the initial context or an "
                        "earlier workflow step."
                    )

            # ------------------------------------------
            # INPUT
            # ------------------------------------------

            elif step_type == "input":

                field = parameters.get("field")

                register_output(field, prefix)

            # ------------------------------------------
            # LOAD DATA
            # ------------------------------------------

            elif step_type == "load_data":

                output = parameters.get("output")

                register_output(output, prefix)
            
            # ------------------------------------------
            # VALIDATION DATA
            # ------------------------------------------

            elif step_type == "validation_data":

                reference = parameters.get("reference")

                if (
                    isinstance(reference, str)
                    and reference.strip()
                    and not is_path_available(reference)
                ):

                    self.errors.append(
                        f"{prefix}: reference '{reference}' is not "
                        "available. Load or create it before this step."
                    )

                conditions = parameters.get("conditions")

                if isinstance(conditions, list):

                    for condition_index, condition in enumerate(conditions):

                        if not isinstance(condition, dict):
                            continue

                        source = condition.get("source")

                        if source is None:
                            continue

                        if (
                            isinstance(source, str)
                            and source.strip()
                            and not is_path_available(source)
                        ):

                            self.errors.append(
                                f"{prefix}: condition "
                                f"{condition_index + 1} source '{source}' "
                                "is not available before this step."
                            )

                elif conditions is None:

                    # Backward compatibility:
                    # validation_data menggunakan parameter source
                    # jika conditions tidak diberikan.
                    source = parameters.get("source")

                    if (
                        isinstance(source, str)
                        and source.strip()
                        and not is_path_available(source)
                    ):

                        self.errors.append(
                            f"{prefix}: source '{source}' is not "
                            "available before this step."
                        )

                output = parameters.get(
                    "output",
                    "validation.result"
                )

                register_output(output, prefix)

                # Register known nested output fields.
                if isinstance(output, str) and output.strip():

                    validation_output_fields = [
                        "valid",
                        "reference",
                        "condition_mode",
                        "matched_index",
                        "matched_record",
                        "condition_results",
                        "evaluated_records",
                    ]

                    for field in validation_output_fields:

                        available_paths.add(
                            f"{output.strip()}.{field}"
                        )


            # ------------------------------------------
            # INSTRUMENT MEASUREMENT
            # ------------------------------------------

            elif step_type == "instrument_measurement":

                step_id = step.get("id")

                if step_id:
                    register_output(
                        f"measurements.{step_id}",
                        prefix
                    )

            # ------------------------------------------
            # INSTRUMENT TEST
            # ------------------------------------------

            elif step_type == "instrument_test":

                step_id = step.get("id")

                if step_id:
                    register_output(
                        f"measurements.{step_id}",
                        prefix
                    )

                    register_output(
                        f"test_judgments.{step_id}",
                        prefix
                    )

                judgment_available = True

            # ------------------------------------------
            # AC VOLT CONFIRMATION
            # ------------------------------------------

            elif step_type == "ac_volt_confirmation":

                step_id = step.get("id")

                if step_id:
                    register_output(
                        f"measurements.{step_id}",
                        prefix
                    )

                    register_output(
                        f"test_judgments.{step_id}",
                        prefix
                    )

                judgment_available = True

            # ------------------------------------------
            # BUILD RESULT
            # ------------------------------------------

            elif step_type == "build_result":

                if not judgment_available:

                    self.errors.append(
                        f"{prefix}: build_result requires a preceding "
                        "judgment-producing step, such as instrument_test "
                        "or ac_volt_confirmation."
                    )

                custom_fields = parameters.get(
                    "custom_fields",
                    {}
                )

                if isinstance(custom_fields, dict):

                    for field_name, source_path in custom_fields.items():

                        if not isinstance(field_name, str) or not field_name.strip():

                            self.errors.append(
                                f"{prefix}: custom field name must be "
                                "a non-empty string."
                            )

                            continue

                        if not isinstance(source_path, str) or not source_path.strip():

                            self.errors.append(
                                f"{prefix}: source path for custom field "
                                f"'{field_name}' must be a non-empty string."
                            )

                            continue

                        if not is_path_available(source_path):

                            self.errors.append(
                                f"{prefix}: custom field '{field_name}' "
                                f"references unavailable source '{source_path}'."
                            )

                register_output("result", prefix)

            # ------------------------------------------
            # SAVE RESULT
            # ------------------------------------------

            elif step_type == "save_result":

                source = parameters.get("source", "result")

                if (
                    isinstance(source, str)
                    and source.strip()
                    and not is_path_available(source)
                ):

                    self.errors.append(
                        f"{prefix}: result source '{source}' is not "
                        "available. A preceding step must produce it."
                    )

    def _validate_step_id(
        self,
        step,
        prefix,
        step_ids
    ):

        step_id = step.get("id")

        if not isinstance(step_id, str) or not step_id.strip():

            self.errors.append(
                f"{prefix}: id is required."
            )

            return

        if step_id in step_ids:

            self.errors.append(
                f"{prefix}: duplicate step ID '{step_id}'."
            )

        else:

            step_ids.add(step_id)

    def _validate_step_enabled(self, step, prefix):

        enabled = step.get("enabled", True)

        if not isinstance(enabled, bool):

            self.errors.append(
                f"{prefix}: enabled must be boolean."
            )

            return False

        return enabled

    # ==================================================
    # STEP PARAMETERS
    # ==================================================

    def _validate_step_parameters(
        self,
        step_type,
        parameters,
        prefix
    ):

        schema = self.STEP_SCHEMAS.get(step_type)

        if schema is None:
            return

        for key, expected_type in schema["required"].items():

            if key not in parameters:

                self.errors.append(
                    f"{prefix}: parameter '{key}' is required."
                )

                continue

            self._validate_parameter_type(
                parameters[key],
                expected_type,
                f"{prefix}: parameter '{key}'"
            )

        for key, expected_type in schema["optional"].items():

            if key not in parameters:
                continue

            self._validate_parameter_type(
                parameters[key],
                expected_type,
                f"{prefix}: parameter '{key}'"
            )

        self._validate_step_specific_rules(
            step_type,
            parameters,
            prefix
        )

    def _validate_parameter_type(
        self,
        value,
        expected_type,
        label
    ):

        if expected_type is object:
            return

        if expected_type is int:

            valid = (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        elif expected_type == (int, float):

            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        else:

            valid = isinstance(value, expected_type)

        if not valid:

            if isinstance(expected_type, tuple):

                expected_name = " or ".join(
                    item.__name__
                    for item in expected_type
                )

            else:

                expected_name = expected_type.__name__

            self.errors.append(
                f"{label} must be {expected_name}."
            )

    def _validate_step_specific_rules(
        self,
        step_type,
        parameters,
        prefix
    ):

        if step_type in (
            "validate_serial",
            "validate_barcode"
        ):

            minimum = parameters.get("min_length")
            maximum = parameters.get("max_length")
            pattern = parameters.get("pattern")

            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and minimum < 0
            ):

                self.errors.append(
                    f"{prefix}: min_length cannot be negative."
                )

            if (
                isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and maximum < 0
            ):

                self.errors.append(
                    f"{prefix}: max_length cannot be negative."
                )

            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and minimum > maximum
            ):

                self.errors.append(
                    f"{prefix}: min_length cannot exceed max_length."
                )

            if isinstance(pattern, str):

                try:
                    re.compile(pattern)

                except re.error as error:

                    self.errors.append(
                        f"{prefix}: invalid regular expression: {error}."
                    )

        elif step_type == "instrument_measurement":

            for key, default in (
                ("duration_s", 10),
                ("sample_interval_s", 1),
            ):

                value = parameters.get(key, default)

                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or value <= 0
                ):

                    self.errors.append(
                        f"{prefix}: {key} must be greater than zero."
                    )

            measurements = parameters.get("measurements")

            if measurements is not None:

                self._validate_string_list(
                    measurements,
                    f"{prefix}: measurements",
                    require_non_empty=True
                )

        elif step_type == "load_data":

            source = parameters.get("source")

            if (
                not isinstance(source, str)
                or source not in self.SUPPORTED_DATA_SOURCES
            ):

                self.errors.append(
                    f"{prefix}: unsupported data source '{source}'."
                )

            if source in ("csv", "txt", "json"):

                file_path = parameters.get("file")

                if (
                    not isinstance(file_path, str)
                    or not file_path.strip()
                ):

                    self.errors.append(
                        f"{prefix}: file is required for {source}."
                    )

            if source == "sqlite":

                for key in ("database", "table"):

                    value = parameters.get(key)

                    if (
                        not isinstance(value, str)
                        or not value.strip()
                    ):

                        self.errors.append(
                            f"{prefix}: {key} is required for sqlite."
                        )

                table = parameters.get("table")

                if isinstance(table, str):

                    if not self.IDENTIFIER_PATTERN.fullmatch(table):

                        self.errors.append(
                            f"{prefix}: invalid SQLite table identifier."
                        )

            delimiter = parameters.get("delimiter")

            if (
                delimiter is not None
                and (
                    not isinstance(delimiter, str)
                    or len(delimiter) != 1
                )
            ):

                self.errors.append(
                    f"{prefix}: delimiter must contain exactly one character."
                )

            has_header = parameters.get(
                "has_header",
                True
            )

            if not isinstance(has_header, bool):

                self.errors.append(
                    f"{prefix}: has_header must be boolean."
                )

            if has_header is False:

                fieldnames = parameters.get("fieldnames")

                self._validate_string_list(
                    fieldnames,
                    f"{prefix}: fieldnames",
                    require_non_empty=True,
                    unique=True
                )

            columns = parameters.get("columns")

            if columns is not None:

                self._validate_string_list(
                    columns,
                    f"{prefix}: columns",
                    require_non_empty=True,
                    unique=True
                )

        elif step_type == "validation_data":

            mode = parameters.get(
                "condition_mode",
                "all"
            )

            if mode not in ("all", "any"):

                self.errors.append(
                    f"{prefix}: condition_mode must be 'all' or 'any'."
                )

            conditions = parameters.get("conditions")

            if conditions is not None:

                if not isinstance(conditions, list) or not conditions:

                    self.errors.append(
                        f"{prefix}: conditions must be a non-empty list."
                    )

                else:

                    for index, condition in enumerate(conditions):

                        condition_prefix = (
                            f"{prefix}: condition {index + 1}"
                        )

                        if not isinstance(condition, dict):

                            self.errors.append(
                                f"{condition_prefix} must be an object."
                            )

                            continue

                        reference_column = condition.get(
                            "reference_column"
                        )

                        if (
                            not isinstance(reference_column, str)
                            or not reference_column.strip()
                        ):

                            self.errors.append(
                                f"{condition_prefix}: reference_column is required."
                            )

                        has_source = (
                            isinstance(condition.get("source"), str)
                            and bool(condition["source"].strip())
                        )

                        has_value = "value" in condition

                        if not has_source and not has_value:

                            self.errors.append(
                                f"{condition_prefix}: source or value is required."
                            )

                        operator = condition.get(
                            "operator",
                            "equals"
                        )

                        if (
                            not isinstance(operator, str)
                            or operator not in self.VALIDATION_OPERATORS
                        ):

                            self.errors.append(
                                f"{condition_prefix}: unsupported operator '{operator}'."
                            )

        elif step_type == "save_result":

            source = parameters.get(
                "source",
                "result"
            )

            if not isinstance(source, str) or not source.strip():

                self.errors.append(
                    f"{prefix}: source must be a non-empty string."
                )

    def _validate_string_list(
        self,
        values,
        label,
        require_non_empty=False,
        unique=False
    ):

        if not isinstance(values, list):

            self.errors.append(
                f"{label} must be a list."
            )

            return

        if require_non_empty and not values:

            self.errors.append(
                f"{label} cannot be empty."
            )

        for value in values:

            if not isinstance(value, str) or not value.strip():

                self.errors.append(
                    f"{label} must contain non-empty strings."
                )

                break

        if (
            unique
            and all(isinstance(value, str) for value in values)
            and len(values) != len(set(values))
        ):

            self.errors.append(
                f"{label} must not contain duplicates."
            )

    # ==================================================
    # INSTRUMENT REFERENCES
    # ==================================================

    def _validate_step_instruments(
        self,
        step_type,
        parameters,
        model_instruments,
        instrument_catalog,
        prefix
    ):

        if step_type == "instrument_test":

            self._validate_instrument_reference(
                parameters.get("instrument"),
                "function",
                parameters.get("function"),
                model_instruments,
                instrument_catalog,
                prefix
            )

        elif step_type == "instrument_measurement":

            self._validate_instrument_reference(
                parameters.get("instrument"),
                "measurements",
                parameters.get("measurements"),
                model_instruments,
                instrument_catalog,
                prefix
            )

        elif step_type == "ac_volt_confirmation":

            self._validate_instrument_reference(
                parameters.get("power_supply"),
                "function",
                "ac_supply_configuration",
                model_instruments,
                instrument_catalog,
                prefix
            )

            self._validate_instrument_reference(
                parameters.get("power_meter"),
                "measurements",
                parameters.get("measurements"),
                model_instruments,
                instrument_catalog,
                prefix
            )

    def _validate_instrument_reference(
        self,
        instrument_id,
        capability_type,
        requested_capability,
        model_instruments,
        instrument_catalog,
        prefix
    ):

        model_mapping = model_instruments.get(
            "instruments"
        )

        catalog_mapping = instrument_catalog.get(
            "instruments"
        )

        if not isinstance(model_mapping, dict):

            self.errors.append(
                "instruments.json: instruments must be an object."
            )

            return

        if not isinstance(catalog_mapping, dict):

            self.errors.append(
                "instrument_catalog.json: instruments must be an object."
            )

            return

        if (
            not isinstance(instrument_id, str)
            or not instrument_id.strip()
        ):

            self.errors.append(
                f"{prefix}: instrument reference is required."
            )

            return

        model_instrument = model_mapping.get(
            instrument_id
        )

        if not isinstance(model_instrument, dict):

            self.errors.append(
                f"{prefix}: instrument '{instrument_id}' "
                "is not mapped in model instruments.json."
            )

            return

        if model_instrument.get("enabled") is not True:

            self.errors.append(
                f"{prefix}: instrument '{instrument_id}' "
                "is disabled for this model."
            )

            return

        catalog_id = model_instrument.get(
            "catalog_id"
        )

        if not isinstance(catalog_id, str) or not catalog_id.strip():

            self.errors.append(
                f"{prefix}: catalog_id is missing for '{instrument_id}'."
            )

            return

        catalog_instrument = catalog_mapping.get(
            catalog_id
        )

        if not isinstance(catalog_instrument, dict):

            self.errors.append(
                f"{prefix}: catalog instrument '{catalog_id}' does not exist."
            )

            return

        if not isinstance(
            catalog_instrument.get("driver"),
            str
        ) or not catalog_instrument["driver"].strip():

            self.errors.append(
                f"{prefix}: driver is missing for '{catalog_id}'."
            )

        connection = catalog_instrument.get(
            "connection",
            {}
        )

        if not isinstance(connection, dict):

            self.errors.append(
                f"{prefix}: connection configuration for "
                f"'{catalog_id}' must be an object."
            )

        overrides = model_instrument.get(
            "overrides",
            {}
        )

        if not isinstance(overrides, dict):

            self.errors.append(
                f"{prefix}: overrides for '{instrument_id}' must be an object."
            )

            return

        if capability_type == "function":

            supported = catalog_instrument.get(
                "supported_functions",
                []
            )

            if not isinstance(supported, list):

                self.errors.append(
                    f"{prefix}: supported_functions for "
                    f"'{catalog_id}' must be a list."
                )

                return

            if requested_capability not in supported:

                self.errors.append(
                    f"{prefix}: function '{requested_capability}' "
                    f"is not supported by '{catalog_id}'."
                )

                return

            selected = overrides.get("selected_functions")

            if selected is not None:

                if not isinstance(selected, list):

                    self.errors.append(
                        f"{prefix}: selected_functions for "
                        f"'{instrument_id}' must be a list."
                    )

                elif requested_capability not in selected:

                    self.errors.append(
                        f"{prefix}: function '{requested_capability}' "
                        f"is not selected for '{instrument_id}'."
                    )

        elif capability_type == "measurements":

            if requested_capability is None:
                return

            supported = catalog_instrument.get("measurements")

            # Catalog dapat menggunakan dictionary:
            # {
            #     "voltage": {"function": "U", ...},
            #     "current": {"function": "I", ...}
            # }
            #
            # Atau list:
            # ["voltage", "current"]

            if isinstance(supported, dict):
                supported_measurements = set(supported.keys())

            elif isinstance(supported, list):
                supported_measurements = set(supported)

            else:
                self.errors.append(
                    f"{prefix}: measurements for "
                    f"'{catalog_id}' must be a dictionary or list."
                )
                return

            # Normalisasi requested capability
            if isinstance(requested_capability, list):
                requested_measurements = requested_capability
            else:
                requested_measurements = [requested_capability]

            for measurement in requested_measurements:

                if not isinstance(measurement, str):
                    self.errors.append(
                        f"{prefix}: measurement name must be a string."
                    )
                    continue

                if measurement not in supported_measurements:
                    self.errors.append(
                        f"{prefix}: measurement '{measurement}' "
                        f"is not supported by '{catalog_id}'."
                    )

            # Validasi selected_measurements dari model configuration
            selected = overrides.get("selected_measurements")

            if selected is not None:

                if not isinstance(selected, list):

                    self.errors.append(
                        f"{prefix}: selected_measurements for "
                        f"'{instrument_id}' must be a list."
                    )

                else:

                    for measurement in requested_measurements:

                        if (
                            isinstance(measurement, str)
                            and measurement not in selected
                        ):
                            self.errors.append(
                                f"{prefix}: measurement '{measurement}' "
                                f"is not selected for '{instrument_id}'."
                            )

    # ==================================================
    # INSTRUMENT CONFIGURATION
    # ==================================================

    def _validate_instrument_configuration(
        self,
        model_instruments,
        instrument_catalog,
        application
    ):

        model_mapping = model_instruments.get(
            "instruments"
        )

        catalog_mapping = instrument_catalog.get(
            "instruments"
        )

        if not isinstance(model_mapping, dict):

            self.errors.append(
                "instruments.json: instruments must be an object."
            )

        if not isinstance(catalog_mapping, dict):

            self.errors.append(
                "instrument_catalog.json: instruments must be an object."
            )

        if not isinstance(model_mapping, dict):
            return

        for instrument_id, configuration in model_mapping.items():

            if not isinstance(configuration, dict):

                self.errors.append(
                    f"instruments.json: '{instrument_id}' must be an object."
                )

                continue

            enabled = configuration.get("enabled")

            if not isinstance(enabled, bool):

                self.errors.append(
                    f"instruments.json: '{instrument_id}' "
                    "enabled must be boolean."
                )

            overrides = configuration.get(
                "overrides",
                {}
            )

            if not isinstance(overrides, dict):

                self.errors.append(
                    f"instruments.json: '{instrument_id}' "
                    "overrides must be an object."
                )

        if not isinstance(catalog_mapping, dict):
            return

        for catalog_id, configuration in catalog_mapping.items():

            if not isinstance(configuration, dict):

                self.errors.append(
                    f"instrument_catalog.json: '{catalog_id}' "
                    "must be an object."
                )

                continue

            if (
                application.get("application_mode") == "HARDWARE"
                and configuration.get("driver") is None
            ):

                self.errors.append(
                    f"instrument_catalog.json: driver is required "
                    f"for HARDWARE instrument '{catalog_id}'."
                )

    # ==================================================
    # STORAGE
    # ==================================================

    def _validate_storage(self, application):

        storage = application.get(
            "storage",
            {
                "type": "sqlite",
                "path": "data/test_results_v2.db",
                "table": "test_results",
            }
        )

        if not isinstance(storage, dict):

            self.errors.append(
                "application.json: storage must be an object."
            )

            return

        storage_type = str(
            storage.get("type", "sqlite")
        ).lower()

        if storage_type not in self.SUPPORTED_STORAGE_TYPES:

            self.errors.append(
                f"Unsupported storage type: {storage_type}."
            )

            return

        path = storage.get(
            "path",
            (
                "data/test_results_v2.db"
                if storage_type == "sqlite"
                else f"data/test_results.{storage_type}"
            )
        )

        if not isinstance(path, str) or not path.strip():

            self.errors.append(
                "Storage path is required."
            )

        else:

            relative_path = Path(path)

            if relative_path.is_absolute():

                self.errors.append(
                    "Storage absolute paths are not allowed."
                )

            else:

                project_root = (
                    Path(__file__).resolve().parents[2]
                )

                resolved_path = (
                    project_root / relative_path
                ).resolve()

                try:

                    resolved_path.relative_to(
                        project_root.resolve()
                    )

                except ValueError:

                    self.errors.append(
                        "Storage path cannot escape the application directory."
                    )

        if storage_type == "sqlite":

            table = storage.get(
                "table",
                "test_results"
            )

            if (
                not isinstance(table, str)
                or not self.IDENTIFIER_PATTERN.fullmatch(table)
            ):

                self.errors.append(
                    "Storage SQLite table name is invalid."
                )
