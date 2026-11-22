
import csv
import json

from pathlib import Path


class CSVStorage:

    FIELDS = [
        "test_id",
        "timestamp",
        "model_id",
        "model_name",
        "sequence_id",
        "application_mode",
        "operator_id",
        "operator_name",
        "serial_number",
        "judgment",
        "result_json"
    ]

    def __init__(self, file_path):

        self.file_path = Path(file_path)

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def _check_duplicate(self, test_id):

        if not self.file_path.exists():
            return

        with self.file_path.open(
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                if row.get("test_id") == test_id:
                    raise ValueError(
                        f"Duplicate test ID: {test_id}"
                    )

    def save_result(self, result_record):

        system = result_record["system"]
        operator = result_record["operator"]
        product = result_record["product"]
        result = result_record["result"]

        test_id = system["test_id"]

        self._check_duplicate(test_id)

        file_exists = self.file_path.exists()
        write_header = (
            not file_exists
            or self.file_path.stat().st_size == 0
        )

        with self.file_path.open(
            "a",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=self.FIELDS
            )

            if write_header:
                writer.writeheader()

            writer.writerow({
                "test_id": test_id,
                "timestamp": system["timestamp"],
                "model_id": system["model_id"],
                "model_name": system["model_name"],
                "sequence_id": system["sequence_id"],
                "application_mode": system["application_mode"],
                "operator_id": operator.get("id"),
                "operator_name": operator.get("name"),
                "serial_number": product.get("serial_number"),
                "judgment": result["judgment"],
                "result_json": json.dumps(
                    result_record,
                    ensure_ascii=False,
                    allow_nan=False
                )
            })

            file.flush()

        return test_id
