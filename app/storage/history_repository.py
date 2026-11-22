
import json
import re
import sqlite3

from pathlib import Path
from contextlib import contextmanager
from urllib.parse import quote

from app.services.model_service import ModelService


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
            "data/test_results_v2.db"
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

        project_root = Path(__file__).resolve().parents[2]

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
            yield connection

        finally:
            connection.close()

    # ==========================================
    # FILTER OPTIONS
    # ==========================================

    def get_filter_options(self):

        table = self.table_name

        with self.managed_connection() as connection:

            model_rows = connection.execute(
                f"""
                SELECT DISTINCT model_id
                FROM "{table}"
                WHERE model_id IS NOT NULL
                  AND model_id != ''
                ORDER BY model_id
                """
            ).fetchall()

            judgment_rows = connection.execute(
                f"""
                SELECT DISTINCT judgment
                FROM "{table}"
                WHERE judgment IS NOT NULL
                  AND judgment != ''
                ORDER BY judgment
                """
            ).fetchall()

            return {
                "models": [
                    row["model_id"]
                    for row in model_rows
                ],
                "judgments": [
                    row["judgment"]
                    for row in judgment_rows
                ]
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

        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError(
                "Limit must be a positive integer."
            )

        conditions = []
        parameters = []

        if start_date:
            conditions.append(
                "date(timestamp) >= date(?)"
            )
            parameters.append(start_date)

        if end_date:
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

        query = f"""
            SELECT
                id,
                test_id,
                timestamp,
                model_id,
                model_name,
                sequence_id,
                application_mode,
                execution_status,
                operator_id,
                operator_name,
                serial_number,
                judgment
            FROM "{table}"
        """

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            ORDER BY id DESC
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

            row = connection.execute(
                f"""
                SELECT id, result_json
                FROM "{table}"
                WHERE id = ?
                """,
                (result_id,)
            ).fetchone()

            if row is None:
                return None

            try:
                result = json.loads(
                    row["result_json"]
                )

            except (json.JSONDecodeError, TypeError) as error:
                raise ValueError(
                    f"Invalid result JSON for record ID {result_id}."
                ) from error

            if not isinstance(result, dict):
                raise ValueError(
                    f"Result record ID {result_id} is not a JSON object."
                )

            # Preserve database ID for the History detail dialog.
            result["id"] = row["id"]

            return result
