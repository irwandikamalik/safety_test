import sys

from pathlib import Path


class AppPaths:

    @staticmethod
    def application_root():

        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path(__file__).resolve().parents[2]

    @staticmethod
    def config_dir():
        return AppPaths.application_root() / "config"

    @staticmethod
    def data_dir():
        return AppPaths.application_root() / "data"

    @staticmethod
    def logs_dir():
        return AppPaths.application_root() / "logs"