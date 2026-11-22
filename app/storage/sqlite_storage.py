
import json
import re
import sqlite3

from pathlib import Path
from contextlib import contextmanager


class SQLiteStorage:

    def __init__(self, database_path, table_name="test_results"):

        self.database_path = Path(database_path)
        self.table_name = table_name

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
            raise ValueError("Invalid SQLite table name.")

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    def connect(self):

        connection = sqlite3.connect(
            str(self.database_path),
            timeout=10
        )

        connection.row_factory = sqlite3.Row

        return connection

    @contextmanager
    def _managed_connection(self):

        connection = self.connect()

        try:
            with connection:
                yield connection

        finally:
            connection.close()

    def initialize(self):

        table = self.table_name

        with self._managed_connection() as connection:

            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{table}" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    model_id TEXT,
                    model_name TEXT,
                    sequence_id TEXT,
                    application_mode TEXT,
                    execution_status TEXT NOT NULL DEFAULT 'COMPLETED',
                    operator_id TEXT,
                    operator_name TEXT,
                    serial_number TEXT,
                    judgment TEXT NOT NULL DEFAULT '',
                    result_json TEXT NOT NULL
                )
                """
            )

            # --------------------------------------
            # MIGRATE EXISTING TABLE
            # --------------------------------------

            existing_columns = {
                row["name"]
                for row in connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            }

            if "execution_status" not in existing_columns:

                connection.execute(
                    f"""
                    ALTER TABLE "{table}"
                    ADD COLUMN execution_status TEXT
                    NOT NULL DEFAULT 'COMPLETED'
                    """
                )

            if "judgment" not in existing_columns:

                connection.execute(
                    f"""
                    ALTER TABLE "{table}"
                    ADD COLUMN judgment TEXT
                    NOT NULL DEFAULT ''
                    """
                )

    def save_result(self, result_record):

        if not isinstance(result_record, dict):
            raise TypeError(
                "Result record must be a dictionary."
            )

        system = result_record.get("system", {})
        operator = result_record.get("operator", {})
        product = result_record.get("product", {})
        result = result_record.get("result", {})

        if not isinstance(system, dict):
            raise ValueError(
                "System data must be a dictionary."
            )

        if not isinstance(operator, dict):
            raise ValueError(
                "Operator data must be a dictionary."
            )

        if not isinstance(product, dict):
            raise ValueError(
                "Product data must be a dictionary."
            )

        if not isinstance(result, dict):
            raise ValueError(
                "Result data must be a dictionary."
            )

        test_id = system.get("test_id")
        timestamp = system.get("timestamp")

        if not test_id or not timestamp:
            raise ValueError(
                "Required result fields are missing."
            )

        execution_status = system.get(
            "execution_status",
            "COMPLETED"
        )

        judgment = result.get("judgment")

        serialized_result = json.dumps(
            result_record,
            ensure_ascii=False,
            allow_nan=False
        )

        table = self.table_name

        with self._managed_connection() as connection:

            connection.execute(
                f"""
                INSERT INTO "{table}" (
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
                    judgment,
                    result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_id,
                    timestamp,
                    system.get("model_id"),
                    system.get("model_name"),
                    system.get("sequence_id"),
                    system.get("application_mode"),
                    execution_status,
                    operator.get("id"),
                    operator.get("name"),
                    product.get("serial_number"),
                    judgment or "",
                    serialized_result
                )
            )

        return test_id
