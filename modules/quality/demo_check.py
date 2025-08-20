from .base_check import BaseCheck

class DemoCheck(BaseCheck):
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        logger.info("[DemoCheck] Running demo quality check")
