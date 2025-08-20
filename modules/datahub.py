class DataHub:
    def __init__(self):
        self.signals = {}

    def add_signal(self, name, obj):
        self.signals[name] = obj

    def get(self, name):
        return self.signals.get(name, None)
