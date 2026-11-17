
from app.instruments.simulation_instrument import (
    SimulationInstrument
)


class DriverRegistry:

    def __init__(self):

        self._drivers = {}

        # Register built-in simulation driver.
        self.register(
            "simulation",
            SimulationInstrument
        )

    def register(self, driver_id, driver_class):

        if not isinstance(driver_id, str) or not driver_id:
            raise ValueError(
                "Driver ID must be a non-empty string."
            )

        if not isinstance(driver_class, type):
            raise TypeError(
                "Driver class must be a class."
            )

        self._drivers[driver_id] = driver_class

    def get_driver(self, driver_id):

        driver_class = self._drivers.get(driver_id)

        if driver_class is None:
            raise ValueError(
                f"Driver is not registered: {driver_id}"
            )

        return driver_class

    def create(self, driver_id, configuration):

        driver_class = self.get_driver(driver_id)

        return driver_class(configuration)

    def available_drivers(self):

        return list(self._drivers.keys())
