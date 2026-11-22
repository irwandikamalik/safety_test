
import json

from pathlib import Path


class JSONStorage:

    def __init__(self, file_path):

        self.file_path = Path(file_path)

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def _check_duplicate(self, records, test_id):

        for item in records:

            if not isinstance(item, dict):
                continue

            system = item.get("system")

            if not isinstance(system, dict):
                continue

            if system.get("test_id") == test_id:
                raise ValueError(
                    f"Duplicate test ID: {test_id}"
                )

    def save_result(self, result_record):

        records = []

        if self.file_path.exists():

            try:
                with self.file_path.open(
                    "r",
                    encoding="utf-8"
                ) as file:

                    records = json.load(file)

            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Existing JSON storage is invalid: {error}"
                ) from error

            if not isinstance(records, list):
                raise ValueError(
                    "JSON storage root must be an array."
                )

        test_id = result_record["system"]["test_id"]

        self._check_duplicate(
            records,
            test_id
        )

        records.append(result_record)

        temporary_path = self.file_path.with_suffix(
            self.file_path.suffix + ".tmp"
        )

        try:

            with temporary_path.open(
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    records,
                    file,
                    ensure_ascii=False,
                    indent=4,
                    allow_nan=False
                )

                file.flush()

            temporary_path.replace(self.file_path)

        finally:

            if temporary_path.exists():
                temporary_path.unlink()

        return test_id
