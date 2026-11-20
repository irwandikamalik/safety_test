from app.services.config_service import ConfigService

config = ConfigService()
operators = config.load_operators()
applications = config.load_aplications()
instrument_catalog = config.load_instrument_catalog()
serial_model = config.serial_model()

print("\nOperators:", operators)
print("\nApplications:", applications)
print("\nInstrument Catalog:", instrument_catalog)
print("\nSerial Model:", serial_model)