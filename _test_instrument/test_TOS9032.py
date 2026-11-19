
import logging
import time
from datetime import datetime
from pathlib import Path

import pyvisa


# ============================================================
# CONFIGURATION
# ============================================================

INSTRUMENT_NAME = "Kikusui TOS9302"

VISA_RESOURCE = (
    "USB0::0x0B3E::0x104F::ZC001527::INSTR"
)

VISA_TIMEOUT = 15000

TEST_VOLTAGE_V = 1400.0
TEST_FREQUENCY_HZ = 50.0

TEST_TIME_S = 3.0
RISE_TIME_S = 1.0
FALL_TIME_S = 1.0

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / (
    f"tos9302_acw_{datetime.now():%Y%m%d_%H%M%S}.log"
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
# TOS9302 ACW TESTER
# ============================================================

class TOS9302ACW:

    def __init__(self):

        self.rm = None
        self.instrument = None

        self.identity = None

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    def connect(self):

        try:

            logger.info("Initializing VISA...")

            self.rm = pyvisa.ResourceManager()

            logger.info(
                f"Connecting to {VISA_RESOURCE}"
            )

            self.instrument = self.rm.open_resource(
                VISA_RESOURCE
            )

            self.instrument.timeout = VISA_TIMEOUT

            self.instrument.read_termination = "\n"
            self.instrument.write_termination = "\n"

            logger.info("Connection successful.")

            return True

        except Exception as error:

            logger.error(
                f"Connection failed: {error}"
            )

            return False

    # --------------------------------------------------------
    # IDENTIFICATION
    # --------------------------------------------------------

    def identify(self):

        try:

            self.identity = (
                self.instrument.query("*IDN?").strip()
            )

            print("\nInstrument Identification")
            print("=" * 50)

            print(self.identity)

            logger.info(
                f"Instrument ID: {self.identity}"
            )

            if "TOS9302" not in self.identity.upper():

                raise RuntimeError(
                    "Connected instrument is not TOS9302."
                )

            return True

        except Exception as error:

            logger.error(
                f"Identification failed: {error}"
            )

            return False

    # --------------------------------------------------------
    # SCPI WRITE
    # --------------------------------------------------------

    def write_command(self, command):

        logger.info(f"SCPI WRITE: {command}")

        self.instrument.write(command)

    # --------------------------------------------------------
    # SCPI QUERY
    # --------------------------------------------------------

    def query_command(self, command):

        logger.info(f"SCPI QUERY: {command}")

        response = self.instrument.query(command).strip()

        logger.info(f"SCPI RESPONSE: {response}")

        return response

    # --------------------------------------------------------
    # CHECK INSTRUMENT ERROR
    # --------------------------------------------------------

    def check_error(self):

        response = self.query_command("SYST:ERR?")

        print(f"Instrument Error: {response}")

        return response

    # --------------------------------------------------------
    # CONFIGURE ACW
    # --------------------------------------------------------

    def configure_acw(self, upper_current_mA):

        print("\nCONFIGURING ACW")
        print("=" * 50)

        # Set remote mode
        self.write_command(
            "SYST:COMM:RLST REM"
        )

        # Select ACW mode
        self.write_command(
            "FUNC ACW"
        )

        # Test voltage
        self.write_command(
            f"ACW:VOLT {TEST_VOLTAGE_V}V"
        )

        # Frequency
        self.write_command(
            f"ACW:VOLT:FREQ {TEST_FREQUENCY_HZ}HZ"
        )

        # Test time enable
        self.write_command(
            "ACW:VOLT:TIM:STAT ON"
        )

        # Test time
        self.write_command(
            f"ACW:VOLT:TIM {TEST_TIME_S}S"
        )

        # Rise time
        self.write_command(
            f"ACW:VOLT:SWE:TIM {RISE_TIME_S}S"
        )

        # Fall time enable
        self.write_command(
            "ACW:VOLT:SWE:FALL:TIM:STAT ON"
        )

        # Fall time
        self.write_command(
            f"ACW:VOLT:SWE:FALL:TIM {FALL_TIME_S}S"
        )

        # Upper current limit
        self.write_command(
            f"SENS:ACW:JUDG {upper_current_mA}MA"
        )

        # Lower current judgment disabled
        self.write_command(
            "SENS:ACW:JUDG:LOW:STAT OFF"
        )

        print("\nACW configuration sent.")

        self.check_error()

    # --------------------------------------------------------
    # VERIFY ACW CONFIGURATION
    # --------------------------------------------------------

    def verify_acw(self):

        print("\nVERIFYING ACW CONFIGURATION")
        print("=" * 50)

        commands = [
            "FUNC?",
            "ACW:VOLT?",
            "ACW:VOLT:FREQ?",
            "ACW:VOLT:TIM:STAT?",
            "ACW:VOLT:TIM?",
            "ACW:VOLT:SWE:TIM?",
            "ACW:VOLT:SWE:FALL:TIM:STAT?",
            "ACW:VOLT:SWE:FALL:TIM?",
            "SENS:ACW:JUDG?",
            "SENS:ACW:JUDG:LOW:STAT?"
        ]

        for command in commands:

            response = self.query_command(command)

            print(
                f"{command:<40} : {response}"
            )

    # --------------------------------------------------------
    # START ACW TEST
    # --------------------------------------------------------

    def start_test(self):

        print("\nSTARTING ACW TEST")
        print("=" * 50)

        # Reset test trigger subsystem
        self.write_command(
            "ABOR:TEST"
        )

        # Select immediate trigger
        self.write_command(
            "TRIG:TEST:SOUR IMM"
        )

        # Start ACW test
        self.write_command(
            "INIT:TEST"
        )

        logger.info(
            "ACW test started."
        )

        print("ACW test command sent.")

    # --------------------------------------------------------
    # WAIT FOR TEST COMPLETION
    # --------------------------------------------------------

    def wait_test_complete(self):

        print("\nWaiting for test completion...")

        response = self.query_command("*OPC?")

        logger.info(
            f"Operation complete response: {response}"
        )

        print("Test operation completed.")

    # --------------------------------------------------------
    # READ RESULT
    # --------------------------------------------------------

    def read_result(self):

        print("\nREADING ACW RESULT")
        print("=" * 50)

        self.write_command(
            "RES:FORM FUNC,VOLT,CURR,ETIM,JUDG"
        )

        result = self.query_command(
            "RES?"
        )

        print("\nACW RESULT")
        print("=" * 50)

        print(result)

        logger.info(
            f"ACW RESULT: {result}"
        )

        return result

    # --------------------------------------------------------
    # STOP TEST
    # --------------------------------------------------------

    def stop_test(self):

        if self.instrument is None:
            return

        try:

            self.write_command(
                "ABOR:TEST"
            )

            logger.warning(
                "ACW test aborted."
            )

        except Exception as error:

            logger.error(
                f"Stop test failed: {error}"
            )

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

            self.rm.close()
            self.rm = None


# ============================================================
# MAIN
# ============================================================

def main():

    tester = TOS9302ACW()

    try:

        print("\n" + "=" * 55)
        print("       KIKUSUI TOS9302 - ACW TEST")
        print("=" * 55)

        print(f"Voltage    : {TEST_VOLTAGE_V} V AC")
        print(f"Frequency  : {TEST_FREQUENCY_HZ} Hz")
        print(f"Test Time  : {TEST_TIME_S} seconds")
        print(f"Rise Time  : {RISE_TIME_S} seconds")
        print(f"Fall Time  : {FALL_TIME_S} seconds")

        # Connect
        if not tester.connect():
            return

        # Identify
        if not tester.identify():
            return

        # Ask upper current limit
        upper_current_mA = float(
            input(
                "\nEnter approved upper current limit (mA): "
            )
        )

        if upper_current_mA <= 0:
            raise ValueError(
                "Upper current limit must be greater than zero."
            )

        # Safety confirmation
        print("\nSAFETY CHECK")
        print("=" * 50)

        print("1. EUT is correctly connected.")
        print("2. HV test leads are properly installed.")
        print("3. Test area is isolated.")
        print("4. Protective grounding is verified.")
        print("5. TOS9302 interlock and emergency stop are ready.")
        print("6. Upper current limit is approved.")

        confirmation = input(
            "\nType START 1400V to configure and execute ACW: "
        ).strip()

        if confirmation != "START 1400V":

            print("Test cancelled by operator.")

            return

        # Configure
        tester.configure_acw(
            upper_current_mA
        )

        # Verify
        tester.verify_acw()

        # Final confirmation
        confirmation = input(
            "\nVerify settings and safety. "
            "Type RUN ACW to apply high voltage: "
        ).strip()

        if confirmation != "RUN ACW":

            print("Test cancelled.")

            return

        # Execute
        tester.start_test()

        # Wait
        tester.wait_test_complete()

        # Result
        tester.read_result()

        print("\nACW TEST FINISHED.")

    except KeyboardInterrupt:

        print("\nKeyboard interrupt detected.")

        tester.stop_test()

    except Exception as error:

        logger.exception(
            f"ACW test error: {error}"
        )

        print(f"\nERROR: {error}")

        tester.stop_test()

    finally:

        tester.disconnect()

        print("\nProgram terminated.")


if __name__ == "__main__":

    main()
