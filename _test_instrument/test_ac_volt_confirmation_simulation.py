import sys
import time
import threading

from pathlib import Path

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


def main():

    print("\n" + "=" * 65)
    print("AC VOLT CONFIRMATION - SIMULATION TEST")
    print("=" * 65)

    config_service = ConfigService()

    # ==============================================
    # LOAD CONFIGURATION
    # ==============================================

    model_instruments = config_service.load_json(
        "models/MODEL-A/instruments.json"
    )

    instrument_catalog = config_service.load_json(
        "global/instrument_catalog.json"
    )

    application_configuration = config_service.load_json(
        "global/application.json"
    )

    model_parameters = config_service.load_json(
        "models/MODEL-A/parameters.json"
    )

    # Simulation only.
    application_configuration["application_mode"] = "SIMULATION"
    application_configuration["allow_hardware_mode"] = False

    limits = model_parameters["limits"]

    voltage_min = float(
        limits["input_voltage_min_V"]
    )

    voltage_max = float(
        limits["input_voltage_max_V"]
    )

    duration_s = 10
    sample_interval_s = 1

    pcr_id = "kikusui_pcr500m"
    wt_id = "wt310e"

    model_instruments["instruments"]["wt310e"]["overrides"][
        "simulation_values"
    ] = {
        "voltage": 220.5,
        "current": 1.25,
        "active_power": 275.625,
        "current_frequency": 50.0,
        "voltage_frequency": 50.0
    }

    manager = InstrumentManager(
        model_instruments,
        instrument_catalog,
        application_configuration
    )

    pcr_connected = False
    wt_connected = False

    output_enabled = False

    try:

        # ==========================================
        # 1. CONNECT BOTH INSTRUMENTS
        # ==========================================

        print("\n[1] CONNECT INSTRUMENTS")

        manager.connect(pcr_id)
        pcr_connected = True

        manager.connect(wt_id)
        wt_connected = True

        print_result(
            "PCR500M connected",
            True
        )

        print_result(
            "WT310E connected",
            True
        )

        # ==========================================
        # 2. CONFIGURE PCR500M
        # ==========================================

        print("\n[2] CONFIGURE PCR500M")

        target_configuration = {
            "voltage_range_V": 270,
            "output_voltage_V": 230.0,
            "frequency_Hz": 50.0
        }

        configuration_result = manager.configure_instrument(
            pcr_id,
            target_configuration
        )

        print("Configuration:", configuration_result)

        if configuration_result.get("judgment") != "PASS":
            raise RuntimeError(
                "PCR500M configuration failed."
            )

        # ==========================================
        # 3. VERIFY CONFIGURATION
        # ==========================================

        print("\n[3] VERIFY PCR500M CONFIGURATION")

        actual_configuration = (
            manager.read_instrument_configuration(pcr_id)
        )

        print("Actual configuration:", actual_configuration)

        configuration_valid = (
            actual_configuration["output_mode"] == "AC"
            and actual_configuration["output_status"] == "OFF"
            and float(actual_configuration["voltage_range_V"]) == 270
            and abs(
                float(actual_configuration["output_voltage_V"]) - 230.0
            ) < 0.01
            and abs(
                float(actual_configuration["frequency_Hz"]) - 50.0
            ) < 0.01
        )

        print_result(
            "PCR500M configuration verification",
            configuration_valid
        )

        if not configuration_valid:
            raise RuntimeError(
                "PCR500M configuration does not match target."
            )

        # ==========================================
        # 4. WT310E INITIAL MEASUREMENT
        # ==========================================

        print("\n[4] WT310E INITIAL MEASUREMENT")

        initial_measurement = manager.read_measurements(
            wt_id
        )

        print("Initial measurement:", initial_measurement)

        # ==========================================
        # 5. OPERATOR APPROVAL
        # ==========================================

        print("\n[5] OUTPUT ACTIVATION")

        print("Target output: 230 VAC / 50 Hz")
        print("Voltage range: 220 - 240 VAC")

        approval = input(
            "\nType ENABLE 230VAC to activate simulation: "
        ).strip()

        if approval != "ENABLE 230VAC":
            raise RuntimeError(
                "Operator did not approve output activation."
            )

        output_result = manager.output_on(
            pcr_id,
            safety_approved=True
        )

        output_enabled = True

        print("Output result:", output_result)

        print_result(
            "PCR500M output ON",
            output_result.get("output_status") == "ON"
        )

        # ==========================================
        # 6. LIVE WT310E MEASUREMENT
        # ==========================================

        print("\n[6] AC VOLT EVALUATION")
        print(
            f"Evaluation duration: {duration_s} seconds"
        )
        print(
            f"Sample interval: {sample_interval_s} second"
        )

        print(
            f"Voltage limits: {voltage_min} - {voltage_max} V"
        )

        samples = []

        start_time = time.monotonic()
        next_sample_time = start_time

        all_samples_pass = True

        while True:

            elapsed = time.monotonic() - start_time

            if elapsed >= duration_s:
                break

            measurement = manager.read_measurements(
                wt_id
            )

            values = measurement["measurements"]

            voltage = values["voltage"]["value"]
            current = values["current"]["value"]
            power = values["active_power"]["value"]
            frequency = values["voltage_frequency"]["value"]

            sample_pass = (
                voltage_min <= voltage <= voltage_max
            )

            if not sample_pass:
                all_samples_pass = False

            sample = {
                "elapsed_s": round(elapsed, 2),
                "voltage_V": voltage,
                "current_A": current,
                "active_power_W": power,
                "frequency_Hz": frequency,
                "judgment": (
                    "PASS" if sample_pass else "FAIL"
                )
            }

            samples.append(sample)

            print(
                f"[{elapsed:05.2f}s] "
                f"Voltage={voltage:.2f} V | "
                f"Current={current:.3f} A | "
                f"Power={power:.2f} W | "
                f"Frequency={frequency:.2f} Hz | "
                f"{sample['judgment']}"
            )

            if not sample_pass:
                print("\nVoltage outside MODEL-A limits.")

                break

            next_sample_time += sample_interval_s

            wait_time = (
                next_sample_time - time.monotonic()
            )

            if wait_time > 0:
                time.sleep(wait_time)

        # ==========================================
        # 7. FINAL EVALUATION
        # ==========================================

        print("\n[7] FINAL EVALUATION")

        actual_duration = time.monotonic() - start_time

        judgment = (
            "PASS"
            if (
                all_samples_pass
                and len(samples) > 0
                and actual_duration >= duration_s
            )
            else "FAIL"
        )

        print("Sample count:", len(samples))
        print("Actual duration:", round(actual_duration, 2), "s")
        print("Final judgment:", judgment)

        # ==========================================
        # 8. OUTPUT STATE AFTER EVALUATION
        # ==========================================

        actual_configuration = (
            manager.read_instrument_configuration(pcr_id)
        )

        remains_on = (
            actual_configuration["output_status"] == "ON"
        )

        print_result(
            "PCR500M remains ON after evaluation",
            remains_on
        )

        if judgment == "FAIL":

            print("\nNG: PCR500M output will be turned OFF.")

            manager.output_off(pcr_id)
            output_enabled = False

            raise RuntimeError(
                "AC Volt Confirmation NG."
            )

        # ==========================================
        # 9. PASS CONFIRMATION
        # ==========================================

        print("\n" + "=" * 65)
        print("AC VOLT CONFIRMATION: PASS")
        print("=" * 65)

        print("PCR500M output is still ON.")
        print("WT310E will continue live measurement.")
        print("Press ENTER to simulate PASS popup OK.")

        operator_confirmed = threading.Event()

        def wait_for_operator():

            input()

            operator_confirmed.set()

        confirmation_thread = threading.Thread(
            target=wait_for_operator,
            daemon=True
        )

        confirmation_thread.start()

        post_pass_samples = 0

        print("\nPOST-PASS LIVE MONITORING")

        while not operator_confirmed.is_set():

            # Continue reading WT310E.
            measurement = manager.read_measurements(
                wt_id
            )

            values = measurement["measurements"]

            voltage = values["voltage"]["value"]
            current = values["current"]["value"]
            power = values["active_power"]["value"]
            frequency = values["voltage_frequency"]["value"]

            post_pass_samples += 1

            # Verify PCR500M output remains ON.
            actual_configuration = (
                manager.read_instrument_configuration(pcr_id)
            )

            output_is_on = (
                actual_configuration["output_status"] == "ON"
            )

            print(
                f"[POST-PASS #{post_pass_samples}] "
                f"Voltage={voltage:.2f} V | "
                f"Current={current:.3f} A | "
                f"Power={power:.2f} W | "
                f"Frequency={frequency:.2f} Hz | "
                f"PCR OUTPUT={'ON' if output_is_on else 'OFF'}"
            )

            if not output_is_on:
                raise RuntimeError(
                    "PCR500M output unexpectedly turned OFF "
                    "during PASS confirmation."
                )

            # Wait before next live measurement.
            operator_confirmed.wait(
                sample_interval_s
            )

        print("\nOperator confirmed PASS popup OK.")

        print(
            "Post-PASS live sample count:",
            post_pass_samples
        )

        # ==========================================
        # 10. OPERATOR CONFIRMED OK
        # ==========================================

        print("\n[10] OPERATOR CONFIRMED PASS")

        manager.output_off(pcr_id)
        output_enabled = False

        actual_configuration = (
            manager.read_instrument_configuration(pcr_id)
        )

        print_result(
            "PCR500M output OFF after confirmation",
            actual_configuration["output_status"] == "OFF"
        )

        # ==========================================
        # 10. OPERATOR CONFIRMED OK
        # ==========================================

        print("\n[10] OPERATOR CONFIRMED PASS")

        manager.output_off(pcr_id)
        output_enabled = False

        actual_configuration = (
            manager.read_instrument_configuration(pcr_id)
        )

        print_result(
            "PCR500M output OFF after confirmation",
            actual_configuration["output_status"] == "OFF"
        )

    except Exception as error:

        print("\nAC VOLT CONFIRMATION ERROR")
        print(
            f"{type(error).__name__}: {error}"
        )

    finally:

        print("\n[CLEANUP]")

        if pcr_connected and output_enabled:

            try:
                manager.output_off(pcr_id)
                print_result(
                    "Safety output OFF",
                    True
                )

            except Exception as error:
                print(
                    "CRITICAL: Failed to turn output OFF:",
                    error
                )

        if wt_connected:

            try:
                manager.disconnect(wt_id)
                print_result(
                    "WT310E disconnected",
                    True
                )

            except Exception as error:
                print(
                    "WT310E disconnect error:",
                    error
                )

        if pcr_connected:

            try:
                manager.disconnect(pcr_id)
                print_result(
                    "PCR500M disconnected",
                    True
                )

            except Exception as error:
                print(
                    "PCR500M disconnect error:",
                    error
                )

    print("\n" + "=" * 65)
    print("AC VOLT CONFIRMATION SIMULATION FINISHED")
    print("=" * 65)


if __name__ == "__main__":
    main()
