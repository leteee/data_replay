class BaseSignal:
    default_cfg = {}
    def load(self, file_path, cfg, logger):
        raise NotImplementedError

    def get_data(self, start=None, end=None):
        raise NotImplementedError
