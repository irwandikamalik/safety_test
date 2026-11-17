
import json
import re

from pathlib import Path


class ModelService:

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

        self.project_root = Path(__file__).resolve().parents[2]

        self.config_root = (
            self.project_root / "config"
        )

        self.global_root = (
            self.config_root / "global"
        )

        self.models_root = (
            self.config_root / "models"
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

                model_file = (
                    directory / "model.json"
                )

                if not model_file.is_file():
                    continue

                model_config = self.read_json(
                    model_file
                )

                models.append({
                    "model_id": model_config.get(
                        "model_id",
                        model_id
                    ),
                    "model_name": model_config.get(
                        "model_name",
                        model_id
                    ),
                    "enabled": model_config.get(
                        "enabled",
                        False
                    ),
                })

            except (
                ValueError,
                OSError,
                json.JSONDecodeError
            ):
                continue

        return models

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

        errors = []

        try:

            configuration = self.load_model(
                model_id
            )

        except (
            ValueError,
            OSError,
            json.JSONDecodeError
        ) as error:

            return {
                "valid": False,
                "errors": [str(error)]
            }

        model = configuration["model"]
        sequence = configuration["sequence"]
        instruments = configuration["instruments"]
        parameters = configuration["parameters"]

        catalog = configuration[
            "instrument_catalog"
        ]

        # MODEL VALIDATION

        if model.get("model_id") != model_id:

            errors.append(
                "model.json: model_id does not match folder name."
            )

        if not model.get("model_name"):

            errors.append(
                "model.json: model_name is required."
            )

        if model.get("enabled") is not True:

            errors.append(
                "Model is disabled."
            )

        # SEQUENCE VALIDATION

        steps = sequence.get("steps")

        if not isinstance(steps, list) or not steps:

            errors.append(
                "sequence.json: steps must be a non-empty list."
            )

        else:

            step_ids = set()

            for index, step in enumerate(steps):

                prefix = f"Step {index + 1}"

                if not isinstance(step, dict):

                    errors.append(
                        f"{prefix}: configuration must be an object."
                    )

                    continue

                step_id = step.get("id")

                if not step_id:

                    errors.append(
                        f"{prefix}: id is required."
                    )

                elif step_id in step_ids:

                    errors.append(
                        f"{prefix}: duplicate step ID '{step_id}'."
                    )

                else:

                    step_ids.add(step_id)

                if step.get("enabled", True) is not True:
                    continue

                if step.get("type") != "instrument_test":
                    continue

                step_parameters = step.get(
                    "parameters", {}
                )

                instrument_id = step_parameters.get(
                    "instrument"
                )

                function = step_parameters.get(
                    "function"
                )

                if not instrument_id or not function:

                    errors.append(
                        f"{prefix}: instrument and function are required."
                    )

                    continue

                model_instrument = (
                    instruments.get(
                        "instruments", {}
                    ).get(instrument_id)
                )

                if model_instrument is None:

                    errors.append(
                        f"{prefix}: instrument '{instrument_id}' "
                        "is not mapped in model instruments.json."
                    )

                    continue

                if model_instrument.get("enabled") is not True:

                    errors.append(
                        f"{prefix}: instrument '{instrument_id}' "
                        "is disabled for this model."
                    )

                    continue

                catalog_id = model_instrument.get(
                    "catalog_id"
                )

                catalog_instrument = (
                    catalog.get(
                        "instruments", {}
                    ).get(catalog_id)
                )

                if catalog_instrument is None:

                    errors.append(
                        f"{prefix}: catalog instrument "
                        f"'{catalog_id}' does not exist."
                    )

                    continue

                supported_functions = (
                    catalog_instrument.get(
                        "supported_functions", []
                    )
                )

                if function not in supported_functions:

                    errors.append(
                        f"{prefix}: function '{function}' "
                        f"is not supported by '{catalog_id}'."
                    )

        # PARAMETER VALIDATION

        limits = parameters.get("limits")

        if not isinstance(limits, dict):

            errors.append(
                "parameters.json: limits must be an object."
            )

        # APPLICATION MODE VALIDATION

        application_mode = configuration[
            "application"
        ].get("application_mode")

        if application_mode not in (
            "SIMULATION",
            "HARDWARE"
        ):

            errors.append(
                "application.json: invalid application_mode."
            )

        if (
            application_mode == "HARDWARE"
            and configuration["application"].get(
                "allow_hardware_mode"
            ) is not True
        ):

            errors.append(
                "Hardware mode is not enabled by application policy."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
