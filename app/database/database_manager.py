
import sqlite3
import json

from pathlib import Path
from datetime import datetime


class DatabaseManager:

    def __init__(self, database_path=None):

        if database_path is None:

            project_root = Path(__file__).resolve().parents[2]

            database_path = (
                project_root / "data" / "safety_test.db"
            )

        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    def connect(self):

        connection = sqlite3.connect(
            str(self.database_path)
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ==========================================
    # DATABASE INITIALIZATION
    # ==========================================

    def initialize(self):

        with self.connect() as connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS test_results (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    timestamp TEXT NOT NULL,

                    operator_id TEXT,
                    operator_name TEXT,

                    serial_number TEXT,
                    door_top TEXT,
                    door_bottom TEXT,

                    judgment TEXT,

                    measurement_json TEXT,

                    simulation INTEGER DEFAULT 1
                )
            """)

            self.migrate_schema(connection)

    # ==========================================
    # SCHEMA MIGRATION
    # ==========================================

    def migrate_schema(self, connection):

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(test_results)"
            ).fetchall()
        }

        new_columns = {

            "model_id": "TEXT",

            "model_name": "TEXT",

            "sequence_id": "TEXT",

            "application_mode": "TEXT DEFAULT 'SIMULATION'",
        }

        for column_name, column_type in new_columns.items():

            if column_name in existing_columns:
                continue

            connection.execute(
                f"""
                ALTER TABLE test_results
                ADD COLUMN {column_name} {column_type}
                """
            )

    # ==========================================
    # SAVE TEST RESULT
    # ==========================================

    def save_result(self, context):

        operator = context.get(
            "operator",
            {}
        )

        measurements = context.get(
            "measurements",
            {}
        )

        application_mode = context.get(
            "application_mode",
            "SIMULATION"
        )

        if application_mode not in (
            "SIMULATION",
            "HARDWARE"
        ):
            raise ValueError(
                f"Invalid application mode: {application_mode}"
            )

        simulation = (
            1 if application_mode == "SIMULATION" else 0
        )

        measurement_json = json.dumps(
            measurements,
            ensure_ascii=False
        )

        with self.connect() as connection:

            cursor = connection.execute("""

                INSERT INTO test_results (

                    timestamp,

                    operator_id,
                    operator_name,

                    model_id,
                    model_name,
                    sequence_id,

                    serial_number,
                    door_top,
                    door_bottom,

                    judgment,

                    measurement_json,

                    simulation,
                    application_mode
                )

                VALUES (
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?,
                    ?,
                    ?, ?
                )

            """, (

                datetime.now().isoformat(
                    timespec="seconds"
                ),

                operator.get("id"),
                operator.get("name"),

                context.get("model_id"),
                context.get("model_name"),
                context.get("sequence_id"),

                context.get("serial_number"),
                context.get("door_top"),
                context.get("door_bottom"),

                context.get("judgment"),

                measurement_json,

                simulation,
                application_mode
            ))

            return cursor.lastrowid

    # ==========================================
    # READ TEST RESULT
    # ==========================================

    def get_result(self, result_id):

        with self.connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM test_results
                WHERE id = ?
                """,
                (result_id,)
            ).fetchone()

            if row is None:
                return None

            result = dict(row)

            try:

                result["measurement_json"] = json.loads(
                    result.get("measurement_json") or "{}"
                )

            except json.JSONDecodeError:

                result["measurement_json"] = {}

            return result

    # ==========================================
    # GET RECENT RESULTS
    # ==========================================

    def get_recent_results(self, limit=100):

        if not isinstance(limit, int) or limit < 1:
            raise ValueError(
                "Limit must be a positive integer."
            )

        with self.connect() as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM test_results
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

            results = []

            for row in rows:

                result = dict(row)

                try:

                    result["measurement_json"] = json.loads(
                        result.get("measurement_json") or "{}"
                    )

                except json.JSONDecodeError:

                    result["measurement_json"] = {}

                results.append(result)

            return results


    # ==========================================
    # GET FILTER OPTIONS
    # ==========================================

    def get_filter_options(self):

        with self.connect() as connection:

            model_rows = connection.execute("""
                SELECT DISTINCT model_id
                FROM test_results
                WHERE model_id IS NOT NULL
                  AND model_id != ''
                ORDER BY model_id
            """).fetchall()

            judgment_rows = connection.execute("""
                SELECT DISTINCT judgment
                FROM test_results
                WHERE judgment IS NOT NULL
                  AND judgment != ''
                ORDER BY judgment
            """).fetchall()

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
    # SEARCH TEST RESULTS
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

        if not isinstance(limit, int) or limit < 1:
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

            conditions.append(
                "model_id = ?"
            )

            parameters.append(model_id)

        if judgment:

            conditions.append(
                "judgment = ?"
            )

            parameters.append(judgment)

        if serial_number:

            conditions.append(
                "serial_number LIKE ?"
            )

            parameters.append(
                f"%{serial_number}%"
            )

        if application_mode:

            conditions.append(
                "application_mode = ?"
            )

            parameters.append(application_mode)

        query = """
            SELECT *
            FROM test_results
        """

        if conditions:

            query += " WHERE "

            query += " AND ".join(conditions)

        query += """
            ORDER BY id DESC
            LIMIT ?
        """

        parameters.append(limit)

        with self.connect() as connection:

            rows = connection.execute(
                query,
                parameters
            ).fetchall()

            results = []

            for row in rows:

                result = dict(row)

                try:

                    result["measurement_json"] = json.loads(
                        result.get("measurement_json") or "{}"
                    )

                except json.JSONDecodeError:

                    result["measurement_json"] = {}

                results.append(result)

            return results

