class WorkflowStepRuntime:
    def __init__(
        self,
        instrument_manager,
        application_mode,
        parameter_configuration,
        store_measurement_result,
        update_judgment,
        log,
        request_stop_after_interaction,
        save_result_record
    ):
        self.instrument_manager = instrument_manager
        self.application_mode = application_mode
        self.parameter_configuration = parameter_configuration

        self.store_measurement_result = store_measurement_result
        self.update_judgment = update_judgment
        self.log = log
        self.request_stop_after_interaction = request_stop_after_interaction

        self.save_result_record = save_result_record