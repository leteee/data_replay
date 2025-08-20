class BaseAnalysis:
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        raise NotImplementedError
