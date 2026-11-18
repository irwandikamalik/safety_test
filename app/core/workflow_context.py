
class WorkflowContext:

    def __init__(self, operator=None, initial_data=None):

        self.data = {
            # Operator
            "operator": operator or {},

            # Product information
            "model_id": None,
            "model_name": None,
            "serial_number": "",
            "door_top": "",
            "door_bottom": "",

            # Workflow information
            "sequence_id": None,
            "application_mode": "SIMULATION",

            # Test information
            "approval": False,
            "measurements": {},
            "judgment": None,
        }

        if isinstance(initial_data, dict):
            self.data.update(initial_data)

    def set(self, key, value):

        self.data[key] = value

    def get(self, key, default=None):

        return self.data.get(key, default)

    def as_dict(self):

        return dict(self.data)
