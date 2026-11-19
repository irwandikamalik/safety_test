
import logging
from datetime import datetime
from pathlib import Path

import pyvisa

from pyvisa.constants import (
    Parity,
    StopBits,
    ControlFlow
)


# ============================================================
# CONFIGURATION
# ============================================================

INSTRUMENT_NAME = "Kikusui PCR500M"

VISA_RESOURCE = "ASRL6::INSTR"

VISA_TIMEOUT = 5000

BAUD_RATE = 19200
DATA_BITS = 8
SERIAL_PARITY = Parity.none
STOP_BITS = StopBits.one

VOLTAGE_RANGE_V = 270
OUTPUT_VOLTAGE_V = 230.0
OUTPUT_FREQUENCY_HZ = 50.0

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / (
    f"pcr500m_{datetime.now():%Y%m%d_%H%M%S}.log"
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ============================================================
# PCR500M TESTER
# ============================================================

class PCR500MTester:

    def __init__(self):

        self.rm = None
        self.instrument = None
        self.identity = None

        self.output_enabled = False

    # --------------------------------------------------------
    # INITIALIZE AND CONNECT
    # --------------------------------------------------------

    def connect(self):

        try:

            print("\nConnecting to PCR500M...")

            self.rm = pyvisa.ResourceManager()

            self.instrument = self.rm.open_resource(
                VISA_RESOURCE
            )

            # RS232C CONFIGURATION
            self.instrument.baud_rate = BAUD_RATE
            self.instrument.data_bits = DATA_BITS
            self.instrument.parity = SERIAL_PARITY
            self.instrument.stop_bits = STOP_BITS

            self.instrument.flow_control = (
                ControlFlow.xon_xoff
            )

            # PCR-M SERIAL TERMINATION:
            # Receive: LF
            # Transmit: CR/LF

            self.instrument.read_termination = "\n"
            self.instrument.write_termination = "\r\n"

            self.instrument.timeout = VISA_TIMEOUT

            logger.info(
                f"Connected to {VISA_RESOURCE}"
            )

            print("Connection successful.")

            return True

        except Exception as error:

            logger.exception(
                f"Connection failed: {error}"
            )

            self.disconnect()

            return False

    # --------------------------------------------------------
    # SCPI WRITE
    # --------------------------------------------------------

    def write_command(self, command):

        if self.instrument is None:

            raise RuntimeError(
                "Instrument not connected."
            )

        logger.info(
            f"WRITE: {command}"
        )

        self.instrument.write(command)

    # --------------------------------------------------------
    # SCPI QUERY
    # --------------------------------------------------------

    def query_command(self, command):

        if self.instrument is None:

            raise RuntimeError(
                "Instrument not connected."
            )

        logger.info(
            f"QUERY: {command}"
        )

        response = self.instrument.query(
            command
        ).strip()

        logger.info(
            f"RESPONSE: {response}"
        )

        return response

    # --------------------------------------------------------
    # IDENTIFICATION
    # --------------------------------------------------------

    def identify(self):

        try:

            self.identity = self.query_command(
                "*IDN?"
            )

            print("\nINSTRUMENT IDENTIFICATION")
            print("=" * 55)

            print(self.identity)

            if "PCR500M" not in self.identity.upper():

                raise RuntimeError(
                    "Connected instrument is not identified "
                    "as PCR500M."
                )

            logger.info(
                f"Instrument identified: {self.identity}"
            )

            return True

        except Exception as error:

            logger.exception(
                f"Identification failed: {error}"
            )

            return False

    # --------------------------------------------------------
    # CHECK OUTPUT STATUS
    # --------------------------------------------------------

    def is_output_on(self):

        response = self.query_command(
            "OUTP?"
        ).upper()

        return response in (
            "1",
            "1.0",
            "ON"
        )

    # --------------------------------------------------------
    # TURN OUTPUT OFF
    # --------------------------------------------------------

    def output_off(self):

        if self.instrument is None:
            return False

        try:

            self.write_command(
                "OUTP OFF"
            )

            self.output_enabled = False

            status = self.is_output_on()

            if status:

                raise RuntimeError(
                    "PCR500M output is still ON."
                )

            print("PCR500M output is OFF.")

            logger.info(
                "Output OFF verified."
            )

            return True

        except Exception as error:

            logger.exception(
                f"Output OFF failed: {error}"
            )

            return False

    # --------------------------------------------------------
    # VALIDATE CONFIGURATION
    # --------------------------------------------------------

    def validate_configuration(self):

        if VOLTAGE_RANGE_V != 270:

            raise ValueError(
                "Voltage range must be 270 V."
            )

        if not 0 < OUTPUT_VOLTAGE_V <= 275:

            raise ValueError(
                "Invalid output voltage for 270 V range."
            )

        if not 40 <= OUTPUT_FREQUENCY_HZ <= 500:

            raise ValueError(
                "Frequency must be between 40 and 500 Hz."
            )

        print("\nTARGET CONFIGURATION")
        print("=" * 55)

        print(f"Instrument    : {INSTRUMENT_NAME}")
        print("Output Mode   : AC")
        print(f"Voltage Range : {VOLTAGE_RANGE_V} V")
        print(f"Output Voltage: {OUTPUT_VOLTAGE_V} V")
        print(f"Frequency     : {OUTPUT_FREQUENCY_HZ} Hz")

        logger.info(
            "Target configuration validated."
        )

        return True

    # --------------------------------------------------------
    # CONFIGURE PCR500M
    # --------------------------------------------------------

    def configure(self):

        print("\nCONFIGURING PCR500M")
        print("=" * 55)

        # Output must be OFF before changing range/mode.

        if not self.output_off():

            raise RuntimeError(
                "Cannot configure while output OFF "
                "has not been verified."
            )

        # AC MODE

        self.write_command(
            "OUTP:COUP AC"
        )

        # VOLTAGE RANGE

        self.write_command(
            f"VOLT:RANG {VOLTAGE_RANGE_V}"
        )

        # OUTPUT VOLTAGE

        self.write_command(
            f"VOLT {OUTPUT_VOLTAGE_V}"
        )

        # OUTPUT FREQUENCY

        self.write_command(
            f"FREQ {OUTPUT_FREQUENCY_HZ}"
        )

        print("Configuration commands sent.")

        logger.info(
            "PCR500M configuration completed."
        )

    # --------------------------------------------------------
    # READ CONFIGURATION
    # --------------------------------------------------------

    def read_configuration(self):

        print("\nREADING PCR500M CONFIGURATION")
        print("=" * 55)

        commands = {
            "Output Status": "OUTP?",
            "Output Mode": "OUTP:COUP?",
            "Voltage Range": "VOLT:RANG?",
            "Output Voltage": "VOLT?",
            "Frequency": "FREQ?"
        }

        results = {}

        for label, command in commands.items():

            response = self.query_command(
                command
            )

            results[label] = response

            print(
                f"{label:<20}: {response}"
            )

        return results

    # --------------------------------------------------------
    # VERIFY CONFIGURATION
    # --------------------------------------------------------

    def verify_configuration(self):

        results = self.read_configuration()

        expected = {
            "Output Mode": "AC",
            "Voltage Range": 270.0,
            "Output Voltage": 230.0,
            "Frequency": 50.0
        }

        print("\nCONFIGURATION JUDGMENT")
        print("=" * 55)

        all_pass = True

        for label, target in expected.items():

            response = results.get(label)

            try:

                if label == "Output Mode":

                    passed = (
                        response.upper() == target
                    )

                else:

                    actual = float(response)

                    passed = abs(
                        actual - target
                    ) < 0.01

            except (ValueError, TypeError):

                passed = False

            status = (
                "PASS" if passed else "FAIL"
            )

            print(
                f"{label:<20}: {status}"
            )

            if not passed:
                all_pass = False

        print("=" * 55)

        if all_pass:

            print("CONFIGURATION: PASS")

        else:

            print("CONFIGURATION: FAIL")

        return all_pass

    # --------------------------------------------------------
    # TURN OUTPUT ON
    # --------------------------------------------------------

    def output_on(self):

        print("\nACTIVATING PCR500M OUTPUT")
        print("=" * 55)

        # Check configuration again before output ON.

        if not self.verify_configuration():

            raise RuntimeError(
                "Configuration verification failed. "
                "Output will not be activated."
            )

        confirmation = input(
            "\nWARNING: 230 VAC will be present at output.\n"
            "Ensure the load, wiring, grounding and "
            "test area are safe.\n\n"
            "Type ENABLE 230VAC to continue: "
        ).strip()

        if confirmation != "ENABLE 230VAC":

            print("Output activation cancelled.")

            return False

        self.write_command(
            "OUTP ON"
        )

        self.output_enabled = True

        # Verify output state

        if not self.is_output_on():

            self.output_enabled = False

            raise RuntimeError(
                "PCR500M output failed to turn ON."
            )

        print("\nPCR500M OUTPUT: ON")

        print(
            f"Voltage Setting : {OUTPUT_VOLTAGE_V} V"
        )

        print(
            f"Frequency Setting: {OUTPUT_FREQUENCY_HZ} Hz"
        )

        logger.info(
            "PCR500M output ON verified."
        )

        return True

    # --------------------------------------------------------
    # DISCONNECT
    # --------------------------------------------------------

    def disconnect(self):

        if self.instrument is not None:

            try:

                self.instrument.close()

                logger.info(
                    "Instrument disconnected."
                )

            except Exception as error:

                logger.error(str(error))

            finally:

                self.instrument = None

        if self.rm is not None:

            try:

                self.rm.close()

            except Exception:

                pass

            finally:

                self.rm = None


# ============================================================
# MAIN
# ============================================================

def main():

    tester = PCR500MTester()

    try:

        print("\n" + "=" * 60)
        print("          KIKUSUI PCR500M TEST PROGRAM")
        print("=" * 60)

        print(f"VISA Resource : {VISA_RESOURCE}")
        print(f"Baud Rate     : {BAUD_RATE}")

        # CONNECT

        if not tester.connect():
            return

        # IDENTIFY

        if not tester.identify():
            return

        # VALIDATE TARGET

        tester.validate_configuration()

        # SHOW CURRENT SETTINGS

        print("\nCURRENT INSTRUMENT SETTINGS")

        tester.read_configuration()

        # CONFIGURE

        confirmation = input(
            "\nType CONFIGURE to apply settings: "
        ).strip()

        if confirmation != "CONFIGURE":

            print("Configuration cancelled.")

            return

        tester.configure()

        # VERIFY

        if not tester.verify_configuration():

            raise RuntimeError(
                "Configuration verification failed."
            )

        # OUTPUT ON

        tester.output_on()

        print("\nPROGRAM FINISHED.")

        if tester.output_enabled:

            print(
                "PCR500M output remains ON."
            )

            print(
                "Use the OUTPUT OFF menu or front panel "
                "to switch it off when finished."
            )

            while True:

                choice = input(
                    "\nType OFF to turn output off, "
                    "or EXIT to close program: "
                ).strip().upper()

                if choice == "OFF":

                    tester.output_off()
                    break

                elif choice == "EXIT":

                    print(
                        "Closing communication. "
                        "Output state is not changed."
                    )

                    break

    except KeyboardInterrupt:

        print("\nProgram interrupted.")

        # Attempt output OFF on interruption.

        tester.output_off()

    except Exception as error:

        logger.exception(
            f"PCR500M error: {error}"
        )

        print(f"\nERROR: {error}")

        # Attempt output OFF after an error.

        tester.output_off()

    finally:

        tester.disconnect()

        print("\nProgram terminated.")


if __name__ == "__main__":

    main()
