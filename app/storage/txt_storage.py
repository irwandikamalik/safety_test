
import json

from pathlib import Path


class TXTStorage:

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
            encoding="utf-8"
        ) as file:

            for line in file:

                if line.strip() == f"TEST ID: {test_id}":
                    raise ValueError(
                        f"Duplicate test ID: {test_id}"
                    )

    def save_result(self, result_record):

        test_id = result_record["system"]["test_id"]

        self._check_duplicate(test_id)

        content = json.dumps(
            result_record,
            ensure_ascii=False,
            indent=4,
            allow_nan=False
        )

        with self.file_path.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write("=" * 70 + "\n")
            file.write(f"TEST ID: {test_id}\n")
            file.write("=" * 70 + "\n")
            file.write(content)
            file.write("\n\n")

            file.flush()

        return test_id
