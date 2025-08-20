import cv2
import numpy as np
from .base_analysis import BaseAnalysis

class DemoOverlay(BaseAnalysis):
    default_cfg = {"width":640,"height":480,"fps":10,"length":100,"output":"cases/case1/output/demo_video.avi"}

    def run(self, datahub, cfg, logger):
        cfg = {**self.default_cfg, **cfg}
        logger.info(f"[DemoOverlay] Creating demo video {cfg['output']}")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(cfg["output"], fourcc, cfg["fps"], (cfg["width"], cfg["height"]))
        signal = datahub.get("DemoSignal")
        data = signal.get_data() if signal else []
        for i in range(cfg["length"]):
            frame = np.zeros((cfg["height"], cfg["width"],3), dtype=np.uint8)
            if i < len(data):
                val = int((data[i]["value"]+1)*127)
                cv2.putText(frame, f"Value:{val}", (50,50), cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
            out.write(frame)
        out.release()
