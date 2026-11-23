
import json
import re
import sqlite3

from pathlib import Path
from contextlib import contextmanager

from app.services.model_service import ModelService
from app.utils.app_paths import AppPaths


class HistoryRepository:

    def __init__(self, storage_configuration=None):

        if storage_configuration is None:
            application_configuration = (
                ModelService().load_application_config()
            )

            storage_configuration = (
                application_configuration.get("storage", {})
            )

        self.configuration = dict(storage_configuration)

        storage_type = str(
            self.configuration.get("type", "sqlite")
        ).lower()

        if storage_type != "sqlite":
            raise ValueError(
                "Test History currently supports SQLite storage only."
            )

        database_path = self.configuration.get(
            "path",
            "data/safety_test.db"
        )

        if (
            not isinstance(database_path, str)
            or not database_path.strip()
        ):
            raise ValueError("Invalid history database path.")

        relative_path = Path(database_path)

        if relative_path.is_absolute():
            raise ValueError(
                "Absolute storage paths are not allowed."
            )

        project_root = AppPaths.application_root()

        self.database_path = (
            project_root / relative_path
        ).resolve()

        try:
            self.database_path.relative_to(
                project_root.resolve()
            )
        except ValueError:
            raise ValueError(
                "Storage path cannot escape the application directory."
            )

        self.table_name = self.configuration.get(
            "table",
            "test_results"
        )

        if not isinstance(self.table_name, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            self.table_name
        ):
            raise ValueError("Invalid SQLite table name.")

        self.columns = set()

    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    def connect(self):

        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"History database not found: {self.database_path}"
            )

        database_uri = (
            self.database_path.as_uri()
            + "?mode=ro"
        )

        return sqlite3.connect(
            database_uri,
            uri=True,
            timeout=10
        )

    @contextmanager
    def managed_connection(self):

        connection = self.connect()
        connection.row_factory = sqlite3.Row

        try:
            self.columns = {
                row["name"]
                for row in connection.execute(
                    f'PRAGMA table_info("{self.table_name}")'
                ).fetchall()
            }

            if not self.columns:
                raise ValueError(
                    f"Table '{self.table_name}' does not exist "
                    "or has no columns."
                )

            yield connection

        finally:
            connection.close()

    # ==========================================
    # COLUMN HELPERS
    # ==========================================

    def get_column_expression(
        self,
        column,
        alias=None,
        fallback="NULL"
    ):

        if column not in self.columns:
            return f"{fallback} AS {column}"

        prefix = f'"{alias}".' if alias else ""

        return f'{prefix}"{column}" AS "{column}"'

    # ==========================================
    # FILTER OPTIONS
    # ==========================================

    def get_filter_options(self):

        table = self.table_name

        with self.managed_connection() as connection:

            models = []
            judgments = []

            if "model_id" in self.columns:

                rows = connection.execute(
                    f"""
                    SELECT DISTINCT model_id
                    FROM "{table}"
                    WHERE model_id IS NOT NULL
                      AND model_id != ''
                    ORDER BY model_id
                    """
                ).fetchall()

                models = [
                    row["model_id"]
                    for row in rows
                ]

            if "judgment" in self.columns:

                rows = connection.execute(
                    f"""
                    SELECT DISTINCT judgment
                    FROM "{table}"
                    WHERE judgment IS NOT NULL
                      AND judgment != ''
                    ORDER BY judgment
                    """
                ).fetchall()

                judgments = [
                    row["judgment"]
                    for row in rows
                ]

            return {
                "models": models,
                "judgments": judgments
            }

    # ==========================================
    # SEARCH RESULTS
    # ==========================================

    def search_results(
        self,
        start_date=None,
        end_date=None,
        model_id=None,
        judgment=None,
        serial_number=None,
        application_mode=None,
        limit=500
    ):

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "Limit must be a positive integer."
            )

        conditions = []
        parameters = []

        if start_date:
            if "timestamp" not in self.columns:
                raise ValueError(
                    "Database does not contain timestamp column."
                )

            conditions.append(
                "date(timestamp) >= date(?)"
            )
            parameters.append(start_date)

        if end_date:
            if "timestamp" not in self.columns:
                raise ValueError(
                    "Database does not contain timestamp column."
                )

            conditions.append(
                "date(timestamp) <= date(?)"
            )
            parameters.append(end_date)

        if model_id:
            conditions.append("model_id = ?")
            parameters.append(model_id)

        if judgment:
            conditions.append("judgment = ?")
            parameters.append(judgment)

        if serial_number:
            conditions.append("serial_number LIKE ?")
            parameters.append(f"%{serial_number}%")

        if application_mode:
            conditions.append("application_mode = ?")
            parameters.append(application_mode)

        table = self.table_name

        selected_columns = [
            self.get_column_expression("id"),
            self.get_column_expression("test_id"),
            self.get_column_expression("timestamp"),
            self.get_column_expression("model_id"),
            self.get_column_expression("model_name"),
            self.get_column_expression("sequence_id"),
            self.get_column_expression("application_mode"),
            self.get_column_expression("execution_status"),
            self.get_column_expression("operator_id"),
            self.get_column_expression("operator_name"),
            self.get_column_expression("serial_number"),
            self.get_column_expression("door_top"),
            self.get_column_expression("door_bottom"),
            self.get_column_expression("judgment"),
        ]

        query = f"""
            SELECT
                {", ".join(selected_columns)}
            FROM "{table}"
        """

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        order_column = (
            "id" if "id" in self.columns else "timestamp"
        )

        query += f"""
            ORDER BY "{order_column}" DESC
            LIMIT ?
        """

        parameters.append(limit)

        with self.managed_connection() as connection:

            rows = connection.execute(
                query,
                parameters
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================
    # GET RESULT DETAIL
    # ==========================================

    def get_result(self, result_id):

        table = self.table_name

        with self.managed_connection() as connection:

            if "id" not in self.columns:
                raise ValueError(
                    "Database does not contain id column."
                )

            json_column = None

            if "result_json" in self.columns:
                json_column = "result_json"

            elif "measurement_json" in self.columns:
                json_column = "measurement_json"

            if json_column is None:
                raise ValueError(
                    "Database does not contain result_json "
                    "or measurement_json."
                )

            row = connection.execute(
                f"""
                SELECT id, "{json_column}" AS result_data
                FROM "{table}"
                WHERE id = ?
                """,
                (result_id,)
            ).fetchone()

            if row is None:
                return None

            try:
                result = json.loads(
                    row["result_data"]
                )

            except (json.JSONDecodeError, TypeError) as error:
                raise ValueError(
                    f"Invalid result JSON for record ID {result_id}."
                ) from error

            if not isinstance(result, dict):
                raise ValueError(
                    f"Result record ID {result_id} "
                    "is not a JSON object."
                )

            result["id"] = row["id"]

            # Include legacy barcode fields in detail.
            if "door_top" in self.columns:
                result["door_top"] = None

            if "door_bottom" in self.columns:
                result["door_bottom"] = None

            metadata = connection.execute(
                f"""
                SELECT *
                FROM "{table}"
                WHERE id = ?
                """,
                (result_id,)
            ).fetchone()

            if metadata:
                for field in (
                    "timestamp",
                    "operator_id",
                    "operator_name",
                    "serial_number",
                    "door_top",
                    "door_bottom",
                    "model_id",
                    "model_name",
                    "sequence_id",
                    "application_mode",
                    "execution_status",
                    "judgment",
                ):
                    if field in self.columns:
                        result[field] = metadata[field]

            return result
    