import shutil

from datetime import datetime

import json
import re

from pathlib import Path

from app.core.workflow_validator import WorkflowValidator
from app.utils.app_paths import AppPaths


class ModelService:

    MODEL_METADATA_FIELDS = (
        "model_name",
        "description",
        "enabled",
    )

    REQUIRED_FILES = (
        "model.json",
        "sequence.json",
        "instruments.json",
        "parameters.json",
    )

    MODEL_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9_-]+$"
    )

    def __init__(self):

        self.project_root = AppPaths.application_root()

        self.config_root = (
            self.project_root / "config"
        )

        self.global_root = (
            self.config_root / "global"
        )

        self.models_root = (
            self.config_root / "models"
        )

        self.backup_root = (
            self.config_root / "backups" / "models"
        )

    # --------------------------------------------------
    # PATH SAFETY
    # --------------------------------------------------

    def get_model_directory(self, model_id):

        if not isinstance(model_id, str):
            raise ValueError("Model ID must be a string.")

        if not self.MODEL_ID_PATTERN.fullmatch(model_id):
            raise ValueError(
                f"Invalid model ID: {model_id}"
            )

        model_directory = (
            self.models_root / model_id
        ).resolve()

        models_root = self.models_root.resolve()

        if not model_directory.is_relative_to(models_root):
            raise ValueError(
                "Model directory is outside the models folder."
            )

        return model_directory

    # --------------------------------------------------
    # JSON READER
    # --------------------------------------------------

    def read_json(self, path):

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Configuration path is not a file: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    # --------------------------------------------------
    # GLOBAL CONFIGURATION
    # --------------------------------------------------

    def load_application_config(self):

        return self.read_json(
            self.global_root / "application.json"
        )

    def load_instrument_catalog(self):

        return self.read_json(
            self.global_root / "instrument_catalog.json"
        )


    # --------------------------------------------------
    # SERIAL MAPPING CONFIGURATION
    # --------------------------------------------------

    @staticmethod
    def empty_serial_mapping():
        return {
            "start_suffix": None,
            "end_suffix": None,
            "expected_value": "",
            "min_length": None,
            "max_length": None,
            "exact_length": None,
            "enabled": False,
        }

    def normalize_serial_model_mapping(self, configuration):

        if not isinstance(configuration, dict):
            raise ValueError(
                "Serial mapping configuration must be an object."
            )

        # New format.
        if isinstance(configuration.get("models"), dict):
            return configuration

        # Legacy format migration.
        rules = configuration.get("rules")

        if not isinstance(rules, list):
            raise ValueError(
                "Serial mapping must contain a 'models' object."
            )

        models = {}

        for rule in rules:

            if not isinstance(rule, dict):
                raise ValueError(
                    "Invalid legacy serial mapping rule."
                )

            model_id = rule.get("model_id")

            if not isinstance(model_id, str) or not model_id:
                raise ValueError(
                    "Legacy mapping contains an invalid model_id."
                )

            if model_id in models:
                raise ValueError(
                    f"Cannot automatically migrate legacy mapping: "
                    f"multiple rules reference {model_id}. "
                    "Resolve these rules manually first."
                )

            models[model_id] = {
                "start_suffix": rule.get("start_suffix"),
                "end_suffix": rule.get("end_suffix"),
                "expected_value": rule.get("expected_value", ""),
                "min_length": rule.get("min_length"),
                "max_length": rule.get("max_length"),
                "exact_length": rule.get("exact_length"),
                "enabled": rule.get("enabled", False),
            }

        return {"models": models}

    def load_serial_model_mapping(self):

        mapping_file = (
            self.global_root / "serial_model_mapping.json"
        )

        configuration = self.read_json(mapping_file)

        configuration = self.normalize_serial_model_mapping(
            configuration
        )

        self.validate_serial_model_mapping(configuration)

        return configuration["models"]

    def validate_serial_model_mapping(self, configuration):

        configuration = self.normalize_serial_model_mapping(
            configuration
        )

        models = configuration["models"]

        if not isinstance(models, dict):
            raise ValueError(
                "Serial mapping models must be an object."
            )

        for model_id, mapping in models.items():

            if (
                not isinstance(model_id, str)
                or not self.MODEL_ID_PATTERN.fullmatch(model_id)
            ):
                raise ValueError(
                    f"Invalid model_id: {model_id}"
                )

            if not isinstance(mapping, dict):
                raise ValueError(
                    f"{model_id}: mapping must be an object."
                )

            enabled = mapping.get("enabled")

            if not isinstance(enabled, bool):
                raise ValueError(
                    f"{model_id}: enabled must be boolean."
                )

            start = mapping.get("start_suffix")
            end = mapping.get("end_suffix")
            expected = mapping.get("expected_value", "")

            min_length = mapping.get("min_length")
            max_length = mapping.get("max_length")
            exact_length = mapping.get("exact_length")

            # Disabled and incomplete mappings are allowed.
            if not enabled:
                continue

            # Enabled mappings must be complete.
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
            ):
                raise ValueError(
                    f"{model_id}: start_suffix and end_suffix "
                    "must be integers when mapping is enabled."
                )

            if start < 1 or end < start:
                raise ValueError(
                    f"{model_id}: invalid character positions."
                )

            if not isinstance(expected, str) or not expected.strip():
                raise ValueError(
                    f"{model_id}: expected_value is required."
                )

            if len(expected.strip()) != end - start + 1:
                raise ValueError(
                    f"{model_id}: expected_value length must equal "
                    "end_suffix - start_suffix + 1."
                )

            length_values = {
                "min_length": min_length,
                "max_length": max_length,
                "exact_length": exact_length,
            }

            for field, value in length_values.items():

                if value is None:
                    continue

                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 1
                ):
                    raise ValueError(
                        f"{model_id}: {field} must be "
                        "a positive integer."
                    )

            if exact_length is not None:

                if min_length is not None or max_length is not None:
                    raise ValueError(
                        f"{model_id}: exact_length cannot be combined "
                        "with min_length or max_length."
                    )

                if exact_length < end:
                    raise ValueError(
                        f"{model_id}: exact_length cannot be "
                        "smaller than end_suffix."
                    )

            else:

                if (
                    min_length is not None
                    and max_length is not None
                    and min_length > max_length
                ):
                    raise ValueError(
                        f"{model_id}: min_length cannot exceed "
                        "max_length."
                    )

                if min_length is not None and min_length < end:
                    raise ValueError(
                        f"{model_id}: min_length cannot be "
                        "smaller than end_suffix."
                    )

                if max_length is not None and max_length < end:
                    raise ValueError(
                        f"{model_id}: max_length cannot be "
                        "smaller than end_suffix."
                    )

        return True

    def resolve_model_by_serial(self, serial_number):

        if not isinstance(serial_number, str):
            raise ValueError(
                "Serial number must be a string."
            )

        serial_number = serial_number.strip().upper()

        if not serial_number:
            raise ValueError(
                "Serial number cannot be empty."
            )

        configuration = self.normalize_serial_model_mapping(
            self.read_json(
                self.global_root / "serial_model_mapping.json"
            )
        )

        self.validate_serial_model_mapping(configuration)

        serial_length = len(serial_number)
        matched_models = []

        for model_id, mapping in configuration["models"].items():

            if mapping["enabled"] is not True:
                continue

            start = mapping["start_suffix"]
            end = mapping["end_suffix"]
            expected = mapping["expected_value"]

            min_length = mapping.get("min_length")
            max_length = mapping.get("max_length")
            exact_length = mapping.get("exact_length")

            if exact_length is not None:

                if serial_length != exact_length:
                    continue

            else:

                if (
                    min_length is not None
                    and serial_length < min_length
                ):
                    continue

                if (
                    max_length is not None
                    and serial_length > max_length
                ):
                    continue

            actual_value = serial_number[start - 1:end]

            if len(actual_value) != end - start + 1:
                continue

            if actual_value == expected.strip().upper():

                matched_models.append({
                    "model_id": model_id,
                    "start_suffix": start,
                    "end_suffix": end,
                    "expected_value": expected.upper(),
                    "matched_value": actual_value,
                    "serial_length": serial_length,
                })

        if not matched_models:
            raise ValueError(
                "No model mapping found for serial number: "
                f"{serial_number}"
            )

        if len(matched_models) > 1:

            model_ids = ", ".join(
                item["model_id"]
                for item in matched_models
            )

            raise ValueError(
                "Ambiguous serial number mapping. "
                f"Multiple models matched: {model_ids}"
            )

        return {
            "serial_number": serial_number,
            **matched_models[0],
        }


    def resolve_model_by_serial(self, serial_number):

        if not isinstance(serial_number, str):
            raise ValueError(
                "Serial number must be a string."
            )

        serial_number = serial_number.strip().upper()

        if not serial_number:
            raise ValueError(
                "Serial number cannot be empty."
            )

        mapping_file = (
            self.global_root / "serial_model_mapping.json"
        )

        configuration = self.read_json(mapping_file)

        self.validate_serial_model_mapping(configuration)

        rules = configuration["rules"]
        serial_length = len(serial_number)

        matched_rules = []

        for rule in rules:

            if rule["enabled"] is not True:
                continue

            rule_id = rule["rule_id"]
            start = rule["start_suffix"]
            end = rule["end_suffix"]
            expected = rule["expected_value"]
            model_id = rule["model_id"]

            min_length = rule.get("min_length")
            max_length = rule.get("max_length")
            exact_length = rule.get("exact_length")

            # Check total serial number length.
            if exact_length is not None:

                if serial_length != exact_length:
                    continue

            else:

                if (
                    min_length is not None
                    and serial_length < min_length
                ):
                    continue

                if (
                    max_length is not None
                    and serial_length > max_length
                ):
                    continue

            # Character positions are 1-based and inclusive.
            actual_value = serial_number[start - 1:end]

            if len(actual_value) != end - start + 1:
                continue

            if actual_value == expected.strip().upper():

                matched_rules.append({
                    "rule_id": rule_id,
                    "model_id": model_id,
                    "start_suffix": start,
                    "end_suffix": end,
                    "expected_value": expected.upper(),
                    "matched_value": actual_value,
                    "serial_length": serial_length
                })

        if not matched_rules:

            raise ValueError(
                f"No model mapping found for serial number: "
                f"{serial_number}"
            )

        if len(matched_rules) > 1:

            rule_ids = ", ".join(
                rule["rule_id"]
                for rule in matched_rules
            )

            raise ValueError(
                "Ambiguous serial number mapping. "
                f"Multiple rules matched: {rule_ids}"
            )

        result = matched_rules[0]

        return {
            "serial_number": serial_number,
            **result
        }

    # --------------------------------------------------
    # MODEL DISCOVERY
    # --------------------------------------------------

    def discover_models(self):

        self.models_root.mkdir(
            parents=True,
            exist_ok=True
        )

        models = []

        for directory in sorted(
            self.models_root.iterdir()
        ):

            if not directory.is_dir():
                continue

            model_id = directory.name

            try:

                self.get_model_directory(model_id)

                model_file = directory / "model.json"

                if not model_file.is_file():
                    continue

                model_config = self.read_json(model_file)

                if not isinstance(model_config, dict):
                    continue

                parameters_path = directory / "parameters.json"

                parameters = {}

                if parameters_path.is_file():
                    parameters = self.read_json(parameters_path)

                    if not isinstance(parameters, dict):
                        parameters = {}

                models.append({
                    "model_id": model_config.get(
                        "model_id",
                        model_id
                    ),
                    "model_name": model_config.get(
                        "model_name",
                        model_id
                    ),
                    "description": model_config.get(
                        "description",
                        ""
                    ),
                    "enabled": model_config.get(
                        "enabled",
                        False
                    ),
                    "configuration_status": model_config.get(
                        "configuration_status",
                        parameters.get(
                            "configuration_status",
                            "NOT SET"
                        )
                    ),
                    "hardware_approved": parameters.get(
                        "hardware_approved",
                        False
                    )
                })

            except (
                ValueError,
                OSError,
                json.JSONDecodeError
            ):
                continue

        return models

    # --------------------------------------------------
    # MODEL BACKUP
    # --------------------------------------------------

    def backup_model(self, model_id):

        source = self.get_model_directory(
            model_id
        )

        if not source.is_dir():

            raise FileNotFoundError(
                f"Model not found: {model_id}"
            )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        backup_directory = (
            self.backup_root
            / f"{model_id}_{timestamp}"
        )

        backup_directory.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copytree(
            source,
            backup_directory
        )

        return backup_directory

    # --------------------------------------------------
    # MODEL METADATA VALIDATION
    # --------------------------------------------------

    def validate_model_metadata(
        self,
        model_name,
        description,
        enabled
    ):

        errors = []

        if (
            not isinstance(model_name, str)
            or not model_name.strip()
        ):

            errors.append(
                "Model Name is required."
            )

        if not isinstance(description, str):

            errors.append(
                "Description must be a string."
            )

        if not isinstance(enabled, bool):

            errors.append(
                "Enabled must be a boolean."
            )

        return errors

    # --------------------------------------------------
    # CREATE MODEL
    # --------------------------------------------------

    def create_model(
        self,
        model_id,
        model_name,
        description="",
        template_model_id="MODEL-A"
    ):

        if not isinstance(model_id, str):

            raise ValueError(
                "Model ID must be a string."
            )

        model_id = model_id.strip().upper()

        target_directory = self.get_model_directory(
            model_id
        )

        errors = self.validate_model_metadata(
            model_name,
            description,
            True
        )

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        if target_directory.exists():

            raise FileExistsError(
                f"Model already exists: {model_id}"
            )

        if model_id == template_model_id:

            raise ValueError(
                "New Model ID cannot be the template Model ID."
            )

        template_directory = self.get_model_directory(
            template_model_id
        )

        if not template_directory.is_dir():

            raise FileNotFoundError(
                f"Template model not found: {template_model_id}"
            )

        # Verify all required files before copying.
        for filename in self.REQUIRED_FILES:

            file_path = (
                template_directory / filename
            )

            if not file_path.is_file():

                raise FileNotFoundError(
                    f"Template is missing {filename}."
                )

            content = self.read_json(file_path)

            if not isinstance(content, dict):

                raise ValueError(
                    f"Template {filename} must contain a JSON object."
                )

        target_directory.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        try:

            shutil.copytree(
                template_directory,
                target_directory
            )

            model_config = self.read_json(
                target_directory / "model.json"
            )

            model_config.update({
                "model_id": model_id,
                "model_name": model_name.strip(),
                "description": description.strip(),
                "enabled": True,
                "version": 1
            })

            # New model starts as a draft.
            model_config["configuration_status"] = "DRAFT"

            self.write_model_json(
                target_directory / "model.json",
                model_config
            )

            parameters_path = (
                target_directory / "parameters.json"
            )

            parameters = self.read_json(
                parameters_path
            )

            parameters["model_id"] = model_id

            # New model must always start as DRAFT.
            parameters["configuration_status"] = "DRAFT"
            parameters["hardware_approved"] = False

            self.write_model_json(
                parameters_path,
                parameters
            )

            return model_id

        except Exception:

            if target_directory.exists():

                shutil.rmtree(
                    target_directory
                )

            raise

    # --------------------------------------------------
    # MODEL JSON WRITER
    # --------------------------------------------------

    def write_model_json(self, path, data):

        path = Path(path)

        temporary_path = path.with_name(
            f"{path.name}.tmp"
        )

        try:

            temporary_path.write_text(
                json.dumps(
                    data,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            temporary_path.replace(path)

        except Exception:

            if temporary_path.exists():
                temporary_path.unlink()

            raise

    # --------------------------------------------------
    # UPDATE MODEL METADATA
    # --------------------------------------------------

    def update_model(
        self,
        model_id,
        model_name,
        description,
        enabled
    ):

        errors = self.validate_model_metadata(
            model_name,
            description,
            enabled
        )

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        model_directory = self.get_model_directory(
            model_id
        )

        model_file = (
            model_directory / "model.json"
        )

        if not model_file.is_file():

            raise FileNotFoundError(
                f"Model not found: {model_id}"
            )

        model_config = self.read_json(
            model_file
        )

        if model_config.get("model_id") != model_id:

            raise ValueError(
                "Model ID does not match its directory."
            )

        self.backup_model(model_id)

        model_config.update({
            "model_name": model_name.strip(),
            "description": description.strip(),
            "enabled": enabled
        })

        self.write_model_json(
            model_file,
            model_config
        )

    # --------------------------------------------------
    # SERIAL MAPPING DEPENDENCY
    # --------------------------------------------------


    def get_model_mapping_references(self, model_id):

        mappings = self.load_serial_model_mapping()

        if model_id in mappings:
            return [f"Serial Mapping ({model_id})"]

        return []


    # --------------------------------------------------
    # DELETE MODEL
    # --------------------------------------------------

    def delete_model(self, model_id):

        model_directory = self.get_model_directory(
            model_id
        )

        if not model_directory.is_dir():

            raise FileNotFoundError(
                f"Model not found: {model_id}"
            )

        references = self.get_model_mapping_references(
            model_id
        )

        if references:

            raise ValueError(
                "Cannot delete model because it is used "
                "by Serial Mapping:\n"
                + ", ".join(references)
            )

        backup_directory = self.backup_model(
            model_id
        )

        try:

            shutil.rmtree(
                model_directory
            )

        except Exception:

            raise RuntimeError(
                "Model deletion failed. "
                f"Backup is available at: {backup_directory}"
            )


    # --------------------------------------------------
    # LOAD MODEL CONFIGURATION
    # --------------------------------------------------

    def load_model(self, model_id):

        model_directory = self.get_model_directory(
            model_id
        )

        configuration = {}

        for filename in self.REQUIRED_FILES:

            file_path = model_directory / filename

            configuration[filename.replace(
                ".json", ""
            )] = self.read_json(file_path)

        configuration["model_directory"] = (
            str(model_directory)
        )

        configuration["application"] = (
            self.load_application_config()
        )

        configuration["instrument_catalog"] = (
            self.load_instrument_catalog()
        )

        return configuration


    # --------------------------------------------------
    # MODEL VALIDATION
    # --------------------------------------------------

    def validate_model(self, model_id):

        try:

            configuration = self.load_model(
                model_id
            )

            validator = WorkflowValidator()

            return validator.validate(
                configuration,
                expected_model_id=model_id
            )

        except (
            ValueError,
            OSError,
            TypeError,
            KeyError,
            json.JSONDecodeError
        ) as error:

            return {
                "valid": False,
                "errors": [str(error)]
            }
