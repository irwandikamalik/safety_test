
from pathlib import Path

from app.storage.sqlite_storage import SQLiteStorage
from app.storage.csv_storage import CSVStorage
from app.storage.json_storage import JSONStorage
from app.storage.txt_storage import TXTStorage
from app.storage.result_validator import ResultValidator


class StorageManager:

    SUPPORTED_TYPES = {
        "sqlite",
        "csv",
        "json",
        "txt"
    }

    def __init__(self, configuration=None):

        self.configuration = dict(configuration or {})
        self.storage = None

        self.initialize()

    def initialize(self):

        storage_type = str(
            self.configuration.get("type", "sqlite")
        ).lower()

        if storage_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported storage type: {storage_type}"
            )

        if storage_type == "sqlite":

            database_path = self._resolve_path(
                self.configuration.get(
                    "path",
                    "data/test_results_v2.db"
                )
            )

            self.storage = SQLiteStorage(
                database_path=database_path,
                table_name=self.configuration.get(
                    "table",
                    "test_results"
                )
            )

        elif storage_type == "csv":

            file_path = self._resolve_path(
                self.configuration.get(
                    "path",
                    "data/test_results.csv"
                )
            )

            self.storage = CSVStorage(file_path)

        elif storage_type == "json":

            file_path = self._resolve_path(
                self.configuration.get(
                    "path",
                    "data/test_results.json"
                )
            )

            self.storage = JSONStorage(file_path)

        elif storage_type == "txt":

            file_path = self._resolve_path(
                self.configuration.get(
                    "path",
                    "data/test_results.txt"
                )
            )

            self.storage = TXTStorage(file_path)

    @staticmethod
    def _resolve_path(path):

        if not isinstance(path, str) or not path.strip():
            raise ValueError("Storage path is required.")

        relative_path = Path(path)

        if relative_path.is_absolute():
            raise ValueError(
                "Absolute storage paths are not allowed."
            )

        project_root = Path(__file__).resolve().parents[2]

        resolved_path = (
            project_root / relative_path
        ).resolve()

        try:
            resolved_path.relative_to(project_root.resolve())

        except ValueError:
            raise ValueError(
                "Storage path cannot escape the application directory."
            )

        return resolved_path

    def save_result(self, result_record):

        if self.storage is None:
            raise RuntimeError(
                "Storage adapter is not initialized."
            )

        validated_record = ResultValidator.validate(
            result_record
        )

        return self.storage.save_result(
            validated_record
        )