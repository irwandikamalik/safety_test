
import logging
from pathlib import Path


class LoggingService:

    def __init__(self):

        project_root = Path(__file__).resolve().parents[2]

        log_folder = project_root / "logs"
        log_folder.mkdir(parents=True, exist_ok=True)

        log_file = log_folder / "application.log"

        self.logger = logging.getLogger(
            "IndustrialSafetyTest"
        )

        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:

            handler = logging.FileHandler(
                log_file,
                encoding="utf-8"
            )

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s"
            )

            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)
