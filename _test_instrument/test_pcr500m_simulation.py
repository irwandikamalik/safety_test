import sys
from pathlib import Path

# Add project root to Python module search path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.config_service import ConfigService
from app.instruments.instrument_manager import InstrumentManager


def print_result(name, passed, detail=""):

    status = "PASS" if passed else "FAIL"

    print(
        f"[{status}] {name}"
        + (f" - {detail}" if detail else "")
    )


def expect_exception(function, expected_exception):

    try:
        function()

    except expected_exception:
        return True

    except Exception as error:
        print(
            f"Unexpected exception: {type(error).__name__}: {error}"
        )
        return False

    return False


def main():

    print("\n" + "=" * 60)
    print("PCR500M SIMULATION TEST")
    print("=" * 60)

    config_service = ConfigService()

    # ==============================================
    # LOAD CONFIGURATION
    # ==============================================

    model_configuration = config_service.load_json(
        "models/MODEL-A/instruments.json"
    )

    instrument_catalog = config_service.load_json(
        "global/instrument_catalog.json"
    )

    application_configuration = config_service.load_json(
        "global/application.json"
    )

    # Force simulation mode for this test only.
    application_configuration["application_mode"] = "SIMULATION"
    application_configuration["allow_hardware_mode"] = False

    print("\nAPPLICATION MODE: SIMULATION")

    # ==============================================
    # CREATE INSTRUMENT MANAGER
    # ==============================================

    manager = InstrumentManager(
        model_configuration,
        instrument_catalog,
        application_configuration
    )

    instrument_id = "kikusui_pcr500m"

    connected = False

    try:

        # ==========================================
        # TEST 1: CONNECT
        # ==========================================

        manager.connect(instrument_id)
        connected = True

        print_result(
            "Connect PCR500M",
            True
        )

        # ==========================================
        # TEST 2: READ BEFORE CONFIGURATION
        # ==========================================

        read_before_config = expect_exception(
            lambda: manager.read_instrument_configuration(
                instrument_id
            ),
            RuntimeError
        )

        print_result(
            "Read before configuration",
            read_before_config,
            "Expected RuntimeError"
        )

        # ==========================================
        # TEST 3: CONFIGURE
        # ==========================================

        target_configuration = {
            "voltage_range_V": 270,
            "output_voltage_V": 230.0,
            "frequency_Hz": 50.0
        }

        configuration_result = manager.configure_instrument(
            instrument_id,
            target_configuration
        )

        print_result(
            "Configure PCR500M",
            configuration_result.get("judgment") == "PASS"
        )

        print(
            "Configuration:",
            configuration_result
        )

        # ==========================================
        # TEST 4: VERIFY OUTPUT OFF
        # ==========================================

        actual = manager.read_instrument_configuration(
            instrument_id
        )

        output_off_initial = (
            actual["output_status"] == "OFF"
        )

        print_result(
            "Initial output OFF",
            output_off_initial
        )

        # ==========================================
        # TEST 5: REJECT WITHOUT APPROVAL
        # ==========================================

        rejected = expect_exception(
            lambda: manager.output_on(
                instrument_id,
                safety_approved=False
            ),
            PermissionError
        )

        print_result(
            "Reject output ON without approval",
            rejected
        )

        # ==========================================
        # TEST 6: OUTPUT ON WITH APPROVAL
        # ==========================================

        output_on_result = manager.output_on(
            instrument_id,
            safety_approved=True
        )

        print(
            "Output ON result:",
            output_on_result
        )

        actual = manager.read_instrument_configuration(
            instrument_id
        )

        output_on_verified = (
            actual["output_status"] == "ON"
        )

        print_result(
            "Output ON verification",
            output_on_verified
        )

        # ==========================================
        # TEST 7: OUTPUT REMAINS ON
        # ==========================================

        actual_again = manager.read_instrument_configuration(
            instrument_id
        )

        remains_on = (
            actual_again["output_status"] == "ON"
        )

        print_result(
            "Output remains ON",
            remains_on
        )

        # ==========================================
        # TEST 8: OUTPUT OFF
        # ==========================================

        manager.output_off(instrument_id)

        actual = manager.read_instrument_configuration(
            instrument_id
        )

        output_off_verified = (
            actual["output_status"] == "OFF"
        )

        print_result(
            "Output OFF verification",
            output_off_verified
        )

        # ==========================================
        # TEST 9: DISCONNECT
        # ==========================================

        manager.disconnect(instrument_id)
        connected = False

        print_result(
            "Disconnect PCR500M",
            True
        )

        # ==========================================
        # TEST 10: RECONNECT AND VERIFY STATE
        # ==========================================

        manager.connect(instrument_id)
        connected = True

        actual = manager.read_instrument_configuration(
            instrument_id
        )

        disconnected_state_safe = (
            actual["output_status"] == "OFF"
        )

        print_result(
            "Output OFF after reconnect",
            disconnected_state_safe
        )

    except Exception as error:

        print("\nSIMULATION TEST ERROR")
        print(
            f"{type(error).__name__}: {error}"
        )

    finally:

        if connected:

            try:
                manager.output_off(instrument_id)

            except Exception as error:
                print(
                    "WARNING: Output OFF failed:",
                    error
                )

            try:
                manager.disconnect(instrument_id)

            except Exception as error:
                print(
                    "WARNING: Disconnect failed:",
                    error
                )

    print("\n" + "=" * 60)
    print("PCR500M SIMULATION TEST FINISHED")
    print("=" * 60)


if __name__ == "__main__":
    main()
