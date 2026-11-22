
import csv
import json
import re
import sqlite3
import sys

from pathlib import Path

from app.workflows.base_step import (
    BaseStep,
    StepOutcome
)


class LoadDataStep(BaseStep):

    step_type = "load_data"

    SUPPORTED_SOURCES = {
        "csv",
        "txt",
        "json",
        "sqlite"
    }

    MAX_RECORDS = 10000

    # ==========================================
    # APPLICATION DIRECTORY
    # ==========================================

    @staticmethod
    def get_application_directory():

        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path(__file__).resolve().parents[2]

    # ==========================================
    # RESOLVE FILE PATH
    # ==========================================

    def resolve_file_path(self, file_path):

        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("Data file path is required.")

        relative_path = Path(file_path)

        if relative_path.is_absolute():
            raise ValueError(
                "Absolute file paths are not allowed."
            )

        base_directory = self.get_application_directory()

        resolved_path = (
            base_directory / relative_path
        ).resolve()

        try:
            resolved_path.relative_to(
                base_directory.resolve()
            )

        except ValueError:
            raise ValueError(
                "Data file path must stay inside the application directory."
            )

        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"Data file not found: {relative_path}"
            )

        return resolved_path

    # ==========================================
    # RECORD LIMIT
    # ==========================================

    def validate_record_count(self, rows):

        if len(rows) > self.MAX_RECORDS:
            raise ValueError(
                f"Data source exceeds maximum limit "
                f"of {self.MAX_RECORDS} records."
            )

        return rows

    # ==========================================
    # CSV / TXT LOADER
    # ==========================================

    def load_delimited_file(
        self,
        file_path,
        delimiter=",",
        has_header=True,
        fieldnames=None,
        encoding="utf-8-sig"
    ):

        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ValueError(
                "Delimiter must be exactly one character."
            )

        if not isinstance(has_header, bool):
            raise ValueError(
                "has_header must be a boolean."
            )

        if not has_header:
            if (
                not isinstance(fieldnames, list)
                or not fieldnames
                or not all(
                    isinstance(name, str) and name.strip()
                    for name in fieldnames
                )
                or len(set(fieldnames)) != len(fieldnames)
            ):
                raise ValueError(
                    "fieldnames must contain unique, non-empty column names "
                    "when has_header is false."
                )

        with file_path.open(
            mode="r",
            encoding=encoding,
            newline=""
        ) as file:

            if has_header:
                reader = csv.DictReader(
                    file,
                    delimiter=delimiter
                )

            else:
                reader = csv.DictReader(
                    file,
                    delimiter=delimiter,
                    fieldnames=fieldnames
                )

            if not reader.fieldnames:
                raise ValueError(
                    "Data file does not contain column headers."
                )

            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError(
                    "Data file contains duplicate column names."
                )

            rows = list(reader)

        return self.validate_record_count(rows)

    # ==========================================
    # JSON LOADER
    # ==========================================

    def load_json(self, file_path):

        with file_path.open(
            mode="r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            rows = data

        elif isinstance(data, dict) and isinstance(
            data.get("rows"), list
        ):
            rows = data["rows"]

        else:
            raise ValueError(
                "JSON data must be an array of objects "
                "or an object containing a 'rows' array."
            )

        if not all(
            isinstance(row, dict)
            for row in rows
        ):
            raise ValueError(
                "Every JSON record must be an object."
            )

        return self.validate_record_count(rows)

    # ==========================================
    # SQLITE IDENTIFIER VALIDATION
    # ==========================================

    @staticmethod
    def quote_identifier(identifier):

        if not isinstance(identifier, str):
            raise ValueError(
                "SQLite table and column names must be strings."
            )

        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            identifier
        ):
            raise ValueError(
                f"Invalid SQLite identifier: {identifier}"
            )

        return f'"{identifier}"'

    # ==========================================
    # SQLITE LOADER
    # ==========================================

    def load_sqlite(
        self,
        database_path,
        table,
        columns=None
    ):

        quoted_table = self.quote_identifier(table)

        if columns is not None:

            if (
                not isinstance(columns, list)
                or not columns
                or not all(
                    isinstance(column, str)
                    for column in columns
                )
                or len(set(columns)) != len(columns)
            ):
                raise ValueError(
                    "SQLite columns must be a non-empty list "
                    "of unique column names."
                )

        # Open external database in READ-ONLY mode.
        connection = sqlite3.connect(
            f"{database_path.as_uri()}?mode=ro",
            uri=True
        )

        connection.row_factory = sqlite3.Row

        try:

            table_exists = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (table,)
            ).fetchone()

            if table_exists is None:
                raise ValueError(
                    f"SQLite table not found: {table}"
                )

            schema = connection.execute(
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()

            available_columns = {
                row["name"]
                for row in schema
            }

            if not available_columns:
                raise ValueError(
                    f"SQLite table has no columns: {table}"
                )

            if columns is None:
                columns = [
                    row["name"]
                    for row in schema
                ]

            missing_columns = [
                column
                for column in columns
                if column not in available_columns
            ]

            if missing_columns:
                raise ValueError(
                    f"SQLite columns not found: {missing_columns}"
                )

            quoted_columns = ", ".join(
                self.quote_identifier(column)
                for column in columns
            )

            query = f"""
                SELECT {quoted_columns}
                FROM {quoted_table}
                LIMIT ?
            """

            rows = connection.execute(
                query,
                (self.MAX_RECORDS + 1,)
            ).fetchall()

            if len(rows) > self.MAX_RECORDS:
                raise ValueError(
                    f"SQLite data exceeds maximum limit "
                    f"of {self.MAX_RECORDS} records."
                )

            return [
                dict(row)
                for row in rows
            ]

        finally:
            connection.close()

    # ==========================================
    # EXECUTE
    # ==========================================

    def execute(self, context):

        parameters = self.parameters

        source = str(
            parameters.get("source", "")
        ).lower()

        output = parameters.get("output")

        if source not in self.SUPPORTED_SOURCES:
            return StepOutcome(
                success=False,
                message=f"Unsupported data source: {source}"
            )

        if not output:
            return StepOutcome(
                success=False,
                message="Load data output path is required."
            )

        try:

            if source in ("csv", "txt"):

                file_path = self.resolve_file_path(
                    parameters.get("file")
                )

                delimiter = parameters.get(
                    "delimiter",
                    "\t" if source == "txt" else ","
                )

                has_header = parameters.get(
                    "has_header",
                    True
                )

                rows = self.load_delimited_file(
                    file_path=file_path,
                    delimiter=delimiter,
                    has_header=has_header,
                    fieldnames=parameters.get("fieldnames"),
                    encoding=parameters.get(
                        "encoding",
                        "utf-8-sig"
                    )
                )

                source_name = file_path.name

            elif source == "json":

                file_path = self.resolve_file_path(
                    parameters.get("file")
                )

                rows = self.load_json(file_path)

                source_name = file_path.name

            else:

                database_path = self.resolve_file_path(
                    parameters.get("database")
                )

                rows = self.load_sqlite(
                    database_path=database_path,
                    table=parameters.get("table"),
                    columns=parameters.get("columns")
                )

                source_name = database_path.name

            context.set(output, rows)

            return StepOutcome(
                success=True,
                message=(
                    f"Loaded {len(rows)} records "
                    f"from {source_name}."
                ),
                data={
                    "source": source,
                    "output": output,
                    "record_count": len(rows),
                    "source_name": source_name
                }
            )

        except Exception as error:

            return StepOutcome(
                success=False,
                message=str(error)
            )
