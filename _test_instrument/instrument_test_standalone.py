"""
Standalone Instrument Communication Test
Instruments:
- Kikusui TOS9302 (AC Hipot)
- Kikusui PCR500M (AC power source)

SAFETY SCOPE
------------
This first-stage utility performs VISA resource discovery and *IDN? queries.
Its "dry run" only prints the proposed sequence. It DOES NOT:
- turn PCR500M output ON,
- configure PCR500M output voltage/frequency,
- start a TOS9302 hipot test,
- change interlock or protection settings.

Do not add output/test commands until the exact communication manuals,
instrument firmware, wiring, EUT setup, and safety interlocks are verified.
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import pyvisa
except ImportError:
    print("PyVISA belum terpasang.")
    print("Install dengan: python -m pip install pyvisa")
    sys.exit(1)


# ---------------------------------------------------------------------------
# USER CONFIGURATION
# ---------------------------------------------------------------------------

# Known TOS9302 USB VISA resource from the previous instrument setup.
TOS9302_RESOURCE = (
    "USB0::0x0B3E::0x104F::ZC001527::INSTR"
)

# PCR500M resource is intentionally left blank until discovered on this PC.
PCR500M_RESOURCE = ""

VISA_TIMEOUT_MS = 5000
WRITE_TERMINATION = "\n"
READ_TERMINATION = "\n"

LOG_DIRECTORY = Path("instrument_test_logs")


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIRECTORY / (
    f"instrument_test_{datetime.now():%Y%m%d_%H%M%S}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("instrument_test")


@dataclass
class InstrumentConnection:
    name: str
    resource_name: str
    idn: str
    instrument: object


class InstrumentTester:
    def __init__(self) -> None:
        self.resource_manager = pyvisa.ResourceManager()
        self.connections: dict[str, InstrumentConnection] = {}

    def list_resources(self) -> tuple[str, ...]:
        """List VISA resources visible to the current VISA backend."""
        resources = self.resource_manager.list_resources()
        logger.info("VISA resources found: %s", len(resources))

        if not resources:
            logger.warning("Tidak ada VISA resource yang terdeteksi.")
            return resources

        for index, resource in enumerate(resources, start=1):
            logger.info("%d. %s", index, resource)

        return resources

    def connect_and_identify(
        self,
        key: str,
        display_name: str,
        resource_name: str,
    ) -> Optional[InstrumentConnection]:
        """Open a VISA session and perform the read-only *IDN? query."""
        if not resource_name:
            logger.warning(
                "%s: resource belum ditentukan. Lewati koneksi.",
                display_name,
            )
            return None

        instrument = None

        try:
            logger.info("%s: membuka %s", display_name, resource_name)

            instrument = self.resource_manager.open_resource(
                resource_name
            )

            instrument.timeout = VISA_TIMEOUT_MS
            instrument.write_termination = WRITE_TERMINATION
            instrument.read_termination = READ_TERMINATION

            # The only command sent in this first-stage connection test.
            idn = instrument.query("*IDN?").strip()

            if not idn:
                raise RuntimeError("Instrumen tidak mengembalikan IDN.")

            connection = InstrumentConnection(
                name=display_name,
                resource_name=resource_name,
                idn=idn,
                instrument=instrument,
            )

            self.connections[key] = connection

            logger.info("%s: CONNECTED", display_name)
            logger.info("%s IDN: %s", display_name, idn)

            return connection

        except Exception as error:
            logger.exception(
                "%s: koneksi/identifikasi gagal: %s",
                display_name,
                error,
            )

            if instrument is not None:
                try:
                    instrument.close()
                except Exception:
                    pass

            return None

    def connect_known_instruments(self) -> None:
        logger.info("=" * 72)
        logger.info("CONNECT AND IDENTIFY")
        logger.info("=" * 72)

        self.connect_and_identify(
            key="tos9302",
            display_name="Kikusui TOS9302",
            resource_name=TOS9302_RESOURCE,
        )

        self.connect_and_identify(
            key="pcr500m",
            display_name="Kikusui PCR500M",
            resource_name=PCR500M_RESOURCE,
        )

    def dry_run_test_sequence(self) -> None:
        """
        Print the proposed test sequence without sending instrument commands.
        This is deliberately a non-actuating dry run.
        """
        logger.info("=" * 72)
        logger.info("DRY RUN - NO OUTPUT / NO HIPOT TEST")
        logger.info("=" * 72)

        required = ("pcr500m", "tos9302")
        missing = [
            key for key in required
            if key not in self.connections
        ]

        if missing:
            logger.warning(
                "Dry run belum lengkap. Instrumen belum terhubung: %s",
                ", ".join(missing),
            )
            logger.info(
                "Tetap menampilkan rencana tanpa mengirim perintah ke alat."
            )

        steps = [
            "1. Verifikasi identitas PCR500M dan TOS9302.",
            "2. Verifikasi kabel, terminal, grounding, EUT, dan interlock "
            "secara fisik oleh personel berwenang.",
            "3. Rencana sumber AC: 230 V RMS, 50 Hz (BELUM DIKIRIM).",
            "4. Verifikasi konfigurasi ACW TOS9302 dari prosedur/manual "
            "yang sesuai firmware (BELUM DIKIRIM).",
            "5. Jalankan AC Hipot hanya setelah seluruh permissive dan "
            "prosedur keselamatan diverifikasi (TIDAK DIJALANKAN).",
            "6. Catat hasil pengukuran dan judgment setelah test resmi.",
        ]

        for step in steps:
            logger.info("[DRY RUN] %s", step)

        logger.info(
            "Dry run selesai. Tidak ada output yang diaktifkan dan "
            "tidak ada pengujian tegangan tinggi yang dimulai."
        )

    def save_connection_report(self) -> Path:
        report_path = LOG_DIRECTORY / (
            f"connection_report_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )

        with report_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                ["timestamp", "instrument", "resource", "idn", "status"]
            )

            for key, display_name in (
                ("tos9302", "Kikusui TOS9302"),
                ("pcr500m", "Kikusui PCR500M"),
            ):
                connection = self.connections.get(key)

                if connection:
                    writer.writerow(
                        [
                            datetime.now().isoformat(timespec="seconds"),
                            display_name,
                            connection.resource_name,
                            connection.idn,
                            "CONNECTED",
                        ]
                    )
                else:
                    writer.writerow(
                        [
                            datetime.now().isoformat(timespec="seconds"),
                            display_name,
                            "",
                            "",
                            "NOT CONNECTED",
                        ]
                    )

        logger.info("Connection report saved: %s", report_path)
        return report_path

    def close(self) -> None:
        for key, connection in list(self.connections.items()):
            try:
                connection.instrument.close()
                logger.info("%s: VISA session closed.", connection.name)
            except Exception as error:
                logger.warning(
                    "%s: gagal menutup session: %s",
                    connection.name,
                    error,
                )

        self.connections.clear()

        try:
            self.resource_manager.close()
        except Exception:
            pass


def print_menu() -> None:
    print()
    print("=" * 64)
    print(" KIKUSUI STANDALONE INSTRUMENT TEST")
    print("=" * 64)
    print("1. Scan VISA resources")
    print("2. Connect and identify instruments")
    print("3. Dry run test sequence (no output, no hipot)")
    print("4. Save connection report")
    print("5. Exit")
    print("-" * 64)


def main() -> None:
    tester = None

    try:
        tester = InstrumentTester()

        while True:
            print_menu()
            choice = input("Pilih menu [1-5]: ").strip()

            if choice == "1":
                tester.list_resources()

            elif choice == "2":
                tester.connect_known_instruments()

            elif choice == "3":
                tester.dry_run_test_sequence()

            elif choice == "4":
                tester.save_connection_report()

            elif choice == "5":
                logger.info("Program ditutup oleh user.")
                break

            else:
                print("Pilihan tidak valid.")

            input("\nTekan Enter untuk kembali ke menu...")

    except KeyboardInterrupt:
        logger.info("Program dihentikan dengan Ctrl+C.")

    except Exception as error:
        logger.exception("Program error: %s", error)

    finally:
        if tester is not None:
            tester.close()


if __name__ == "__main__":
    main()
