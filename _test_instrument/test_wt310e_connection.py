
import pyvisa

def main():

    resource_manager = None

    try:
        resource_manager = pyvisa.ResourceManager()

        print("Available VISA resources:")
        resources = resource_manager.list_resources()

        for resource in resources:
            print(" -", resource)

        if not resources:
            print("\nNo VISA instrument detected.")
            return

        # Select the WT310E resource from the list.
        resource = input(
            "\nEnter WT310E VISA Resource: "
        ).strip()

        instrument = resource_manager.open_resource(resource)

        try:
            instrument.timeout = 5000
            instrument.read_termination = "\n"
            instrument.write_termination = "\n"

            print("\nQuerying instrument...")

            identity = instrument.query("*IDN?").strip()

            print("\nInstrument identification:")
            print(identity)

        finally:
            instrument.close()

    except Exception as error:
        print("\nCONNECTION ERROR:")
        print(type(error).__name__, error)

    finally:
        if resource_manager is not None:
            resource_manager.close()


if __name__ == "__main__":
    main()
