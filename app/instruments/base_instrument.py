
class BaseInstrument:

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def execute_test(self, function, parameters):
        raise NotImplementedError
