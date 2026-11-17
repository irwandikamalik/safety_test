
import sqlite3
from pathlib import Path
from datetime import datetime


class DatabaseManager:

    def __init__(self, database_path=None):

        if database_path is None:
            project_root = Path(__file__).resolve().parents[2]
            database_path = project_root / "data" / "safety_test.db"

        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    def connect(self):
        connection = sqlite3.connect(
            str(self.database_path)
        )

        connection.row_factory = sqlite3.Row

        return connection

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

    def save_result(self, context):

        operator = context.get("operator", {})

        measurements = context.get(
            "measurements", {}
        )

        with self.connect() as connection:

            cursor = connection.execute("""
                INSERT INTO test_results (
                    timestamp,
                    operator_id,
                    operator_name,
                    serial_number,
                    door_top,
                    door_bottom,
                    judgment,
                    measurement_json,
                    simulation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(timespec="seconds"),
                operator.get("id"),
                operator.get("name"),
                context.get("serial_number"),
                context.get("door_top"),
                context.get("door_bottom"),
                context.get("judgment"),
                __import__("json").dumps(
                    measurements,
                    ensure_ascii=False
                ),
                1
            ))

            return cursor.lastrowid
