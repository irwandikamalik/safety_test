
class WorkflowContext:

    def __init__(self, operator=None):
        self.data = {
            "operator": operator or {},
            "serial_number": "",
            "door_top": "",
            "door_bottom": "",
            "approval": False,
            "measurements": {},
            "judgment": None,
        }

    def set(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def as_dict(self):
        return dict(self.data)
