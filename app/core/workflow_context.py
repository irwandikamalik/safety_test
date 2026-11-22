from copy import deepcopy


class WorkflowContext:

    def __init__(self, operator=None, initial_data=None):

        self.data = {
            "operator": operator or {},

            "model_id": None,
            "model_name": None,
            "serial_number": "",

            "door_top": "",
            "door_bottom": "",

            "sequence_id": None,
            "application_mode": "SIMULATION",

            "approval": False,
            "measurements": {},
            "judgment": None
        }

        if isinstance(initial_data, dict):
            self.data.update(
                deepcopy(initial_data)
            )

    # ==========================================
    # INTERNAL PATH HANDLING
    # ==========================================

    @staticmethod
    def _split_path(key):

        if not isinstance(key, str) or not key:
            raise ValueError(
                "Context key must be a non-empty string."
            )

        return key.split(".")

    # ==========================================
    # SET DATA
    # ==========================================

    def set(self, key, value):

        parts = self._split_path(key)

        target = self.data

        for part in parts[:-1]:

            if part not in target:
                target[part] = {}

            if not isinstance(target[part], dict):
                raise ValueError(
                    f"Cannot create nested context path: {key}"
                )

            target = target[part]

        target[parts[-1]] = value

    # ==========================================
    # GET DATA
    # ==========================================

    def get(self, key, default=None):

        parts = self._split_path(key)

        target = self.data

        for part in parts:

            if not isinstance(target, dict):
                return default

            if part not in target:
                return default

            target = target[part]

        return target

    # ==========================================
    # CHECK DATA
    # ==========================================

    def has(self, key):

        marker = object()

        return self.get(key, marker) is not marker

    # ==========================================
    # REMOVE DATA
    # ==========================================

    def remove(self, key):

        parts = self._split_path(key)

        target = self.data

        for part in parts[:-1]:

            target = target.get(part)

            if not isinstance(target, dict):
                return False

        return target.pop(parts[-1], None) is not None

    # ==========================================
    # EXPORT DATA
    # ==========================================

    def as_dict(self):
        return deepcopy(self.data)