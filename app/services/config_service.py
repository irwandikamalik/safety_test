
import json
from pathlib import Path


class ConfigService:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.config_root = self.project_root / "config"

    def read_config(self, relative_path):

        path = self.config_root / relative_path

        if not path.exists():
            raise FileNotFoundError(path)

        return path.read_text(encoding="utf-8")

    def load_json(self, relative_path):

        content = self.read_config(relative_path)

        return json.loads(content)

    def save_config(self, relative_path, content):

        parsed = json.loads(content)

        path = self.config_root / relative_path

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            json.dumps(
                parsed,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def validate_json(self, content):

        try:
            json.loads(content)

            return True, "JSON syntax valid."

        except json.JSONDecodeError as error:

            return False, (
                f"Line {error.lineno}, "
                f"Column {error.colno}: {error.msg}"
            )

    def format_json(self, content):

        parsed = json.loads(content)

        return json.dumps(
            parsed,
            indent=4,
            ensure_ascii=False
        )
