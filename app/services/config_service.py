
import json
import shutil

from datetime import datetime
from pathlib import Path


class ConfigService:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.config_root = (
            self.project_root / "config"
        )

        self.backup_root = (
            self.config_root / "backups"
        )

    # --------------------------------------------------
    # PATH SAFETY
    # --------------------------------------------------

    def get_config_path(self, relative_path):

        path = (
            self.config_root / relative_path
        ).resolve()

        if not path.is_relative_to(
            self.config_root.resolve()
        ):

            raise ValueError(
                "Configuration path is outside config directory."
            )

        return path

    # --------------------------------------------------
    # JSON READER
    # --------------------------------------------------

    def read_config(self, relative_path):

        path = self.get_config_path(relative_path)

        if not path.is_file():

            raise FileNotFoundError(path)

        return path.read_text(
            encoding="utf-8"
        )

    def load_json(self, relative_path):

        return json.loads(
            self.read_config(relative_path)
        )

    # --------------------------------------------------
    # BACKUP
    # --------------------------------------------------

    def backup_file(self, relative_path):

        source = self.get_config_path(
            relative_path
        )

        if not source.is_file():

            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        backup_path = (
            self.backup_root
            / relative_path
        )

        backup_path = backup_path.with_name(
            f"{backup_path.stem}_{timestamp}"
            f"{backup_path.suffix}"
        )

        backup_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source,
            backup_path
        )

        return backup_path

    # --------------------------------------------------
    # JSON WRITER
    # --------------------------------------------------

    def save_json(
        self,
        relative_path,
        data,
        create_backup=True
    ):

        if not isinstance(data, (dict, list)):

            raise ValueError(
                "JSON root must be an object or array."
            )

        path = self.get_config_path(
            relative_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if create_backup and path.is_file():

            self.backup_file(
                relative_path
            )

        content = json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

        temporary_path = path.with_name(
            f"{path.name}.tmp"
        )

        try:

            temporary_path.write_text(
                content,
                encoding="utf-8"
            )

            temporary_path.replace(path)

        except Exception:

            if temporary_path.exists():
                temporary_path.unlink()

            raise

    def save_config(self, relative_path, content):

        parsed = json.loads(content)

        self.save_json(
            relative_path,
            parsed
        )

    # --------------------------------------------------
    # VALIDATION / FORMATTING
    # --------------------------------------------------

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
