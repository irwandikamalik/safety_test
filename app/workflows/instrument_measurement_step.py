
from app.workflows.base_step import BaseStep, StepOutcome


class InstrumentMeasurementStep(BaseStep):

    step_type = "instrument_measurement"

    def execute(self, context):

        parameters = self.parameters

        instrument_id = parameters.get("instrument")

        if not instrument_id:
            return StepOutcome(
                success=False,
                message="Instrument ID is required."
            )

        try:
            duration_s = float(
                parameters.get("duration_s", 10)
            )

            sample_interval_s = float(
                parameters.get("sample_interval_s", 1)
            )

        except (TypeError, ValueError):
            return StepOutcome(
                success=False,
                message=(
                    "Measurement duration and sample interval "
                    "must be numeric."
                )
            )

        if duration_s <= 0:
            return StepOutcome(
                success=False,
                message="Measurement duration must be greater than zero."
            )

        if sample_interval_s <= 0:
            return StepOutcome(
                success=False,
                message="Sample interval must be greater than zero."
            )

        measurements = parameters.get("measurements")

        if measurements is not None:
            if not isinstance(measurements, list):
                return StepOutcome(
                    success=False,
                    message="Measurements must be a list."
                )

            if not measurements:
                return StepOutcome(
                    success=False,
                    message="Measurements list cannot be empty."
                )

        return StepOutcome(
            success=True,
            message="Live measurement requested.",
            interaction={
                "type": "live_measurement",
                "step_id": self.step_id,
                "instrument": instrument_id,
                "duration_s": duration_s,
                "sample_interval_s": sample_interval_s,
                "measurements": measurements
            }
        )
