
import pyvisa


def main():

    print("=" * 60)
    print("INSTRUMENT VISA RESOURCE SCANNER")
    print("=" * 60)

    resource_manager = None

    try:

        resource_manager = pyvisa.ResourceManager()

        print("\nVISA Backend:")
        print(resource_manager.visalib)

        print("\nScanning VISA resources...")

        resources = resource_manager.list_resources()

        if not resources:

            print("\nNo VISA resources detected.")

        else:

            print(f"\nFound {len(resources)} resource(s):\n")

            for index, resource in enumerate(resources, start=1):

                print(f"{index}. {resource}")

        print("\nScan completed.")

    except Exception as error:

        print("\nVISA ERROR:")
        print(type(error).__name__)
        print(error)

    finally:

        if resource_manager is not None:
            resource_manager.close()


if __name__ == "__main__":
    main()
