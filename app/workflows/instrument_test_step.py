
from app.workflows.base_step import BaseStep, StepOutcome


class InstrumentTestStep(BaseStep):

    step_type = "instrument_test"

    def execute(self, context):

        parameters = self.parameters

        instrument_id = parameters.get("instrument")
        function = parameters.get("function")

        if not instrument_id or not function:
            return StepOutcome(
                success=False,
                message="Instrument ID or function is missing."
            )

        if self.runtime is None:
            return StepOutcome(
                success=False,
                message="Workflow step runtime is missing."
            )

        self._instrument_id = instrument_id
        self._function = function
        self._parameters = parameters
        self._stage = None
        self._measurement_result = None

        # Other instrument tests retain their original flow.
        return self.execute_instrument_test()

    def execute_instrument_test(self):

        try:

            result = self._execute_test(
                self.runtime,
                self._instrument_id,
                self._function,
                self._parameters
            )

            judgment = str(
                result.get("judgment", "")
            ).upper()

            if judgment not in ("PASS", "FAIL", "NG"):
                raise ValueError(
                    f"Invalid instrument test judgment: {judgment}"
                )

            step_id = self.step_id or "step"

            self.runtime.store_measurement_result(
                step_id,
                result
            )

            overall_judgment = self.runtime.update_judgment(
                step_id,
                judgment
            )

            self.runtime.log(
                "MEASUREMENT",
                f"{self._function}: {judgment}"
            )

            self.runtime.log(
                "JUDGMENT",
                f"Overall judgment: {overall_judgment}"
            )

            if judgment in ("FAIL", "NG"):
                self.runtime.request_stop_after_interaction()

            self._measurement_result = result
            self._stage = "measurement"

            return StepOutcome(
                success=True,
                message=f"{self._function} test completed: {judgment}.",
                interaction={
                    "type": "tos9302",
                    "result": result
                },
                data=result
            )

        except Exception as error:

            return StepOutcome(
                success=False,
                message=str(error)
            )

    def complete(self, context, response):

        # Operator confirmed AC Hipot.
        if self._stage == "confirmation":

            if response.get("confirmed") is not True:
                return StepOutcome(
                    success=False,
                    message="AC Hipot confirmation was rejected."
                )

            # Execute TOS9302 only after confirmation.
            return self.execute_instrument_test()

        # Operator acknowledged measurement result.
        if (
            self._stage == "measurement"
            and response.get("continue") is True
        ):

            self._stage = None

            return StepOutcome(
                success=True,
                message="Instrument test result acknowledged.",
                data=self._measurement_result
            )

        return StepOutcome(
            success=False,
            message="Invalid instrument test interaction response."
        )

    @staticmethod
    def _execute_test(
        runtime,
        instrument_id,
        function,
        parameters
    ):

        application_mode = runtime.application_mode
        parameter_configuration = runtime.parameter_configuration
        instrument_manager = runtime.instrument_manager

        if application_mode == "HARDWARE":

            if (
                parameter_configuration.get(
                    "configuration_status"
                ) != "APPROVED"
                or parameter_configuration.get(
                    "hardware_approved"
                ) is not True
            ):
                raise RuntimeError(
                    "Hardware test is blocked. "
                    "Test configuration has not been approved."
                )

        parameter_groups = parameter_configuration.get(
            "test_parameters",
            {}
        )

        parameter_group = {
            "acw": "acw",
            "ecac": "ecac",
            "ecdc": "ecdc"
        }.get(function)

        if parameter_group is None:
            raise ValueError(
                f"Unsupported instrument test function: {function}"
            )

        test_parameters = dict(
            parameter_configuration.get(
                "limits",
                {}
            )
        )

        configured_parameters = parameter_groups.get(
            parameter_group,
            {}
        )

        if not isinstance(configured_parameters, dict):
            raise ValueError(
                f"Invalid test parameter group: {parameter_group}"
            )

        test_parameters.update(configured_parameters)

        step_parameters = parameters.get(
            "test_parameters",
            {}
        )

        if not isinstance(step_parameters, dict):
            raise ValueError(
                "Step test_parameters must be an object."
            )

        test_parameters.update(step_parameters)

        runtime.log(
            "INSTRUMENT",
            f"{application_mode}: connecting {instrument_id}"
        )

        connected = False

        try:

            connected = instrument_manager.connect(
                instrument_id
            )

            if connected is False:
                raise RuntimeError(
                    f"Could not connect instrument: {instrument_id}"
                )

            result = instrument_manager.execute_test(
                instrument_id,
                function,
                test_parameters
            )

        finally:

            if connected:
                instrument_manager.disconnect(
                    instrument_id
                )

        if not isinstance(result, dict):
            raise TypeError(
                "Instrument test result must be a dictionary."
            )

        if (
            result.get("simulation") is not True
            and application_mode == "SIMULATION"
        ):
            raise RuntimeError(
                "Simulation mode received a non-simulation result."
            )

        return result
