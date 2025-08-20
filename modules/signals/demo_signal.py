import csv
import numpy as np
from .base import BaseSignal

class DemoSignal(BaseSignal):
    default_cfg = {"length": 100}
    def load(self, file_path, cfg, logger):
        length = cfg.get("length", self.default_cfg["length"])
        logger.info(f"[DemoSignal] Generating {length} rows of demo data to {file_path}")
        self.data = [{"time": i, "value": np.sin(i/10)} for i in range(length)]
        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["time","value"])
            writer.writeheader()
            for row in self.data:
                writer.writerow(row)

    def get_data(self, start=None, end=None):
        return self.data
