#!/bin/bash

# ===============================
# 一键初始化完整项目并生成可跑 demo (含 __init__.py)
# ===============================

echo "=== 创建项目目录结构 ==="
mkdir -p modules/{signals,analysis,quality}
mkdir -p utils
mkdir -p config
mkdir -p cases/case1/{input,output}
mkdir -p logs

# 创建 __init__.py 确保模块可被导入
touch modules/__init__.py
touch modules/signals/__init__.py
touch modules/analysis/__init__.py
touch modules/quality/__init__.py
touch utils/__init__.py

# ===============================
# 创建全局配置文件
# ===============================
echo "=== 创建配置文件 ==="

# global.yaml
cat > config/global.yaml <<EOL
data_root: "./cases"
log_level: "INFO"
video_decoder: "opencv"
sync_method: "interpolation"
plugins_dir: "./modules"
EOL

# logging.yaml
cat > config/logging.yaml <<EOL
version: 1
formatters:
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: standard
    filename: logs/system.log

root:
  level: DEBUG
  handlers: [console, file]
EOL

# case.yaml
cat > cases/case1/case.yaml <<EOL
log_level: "DEBUG"
sync_method: "resample"
signals:
  demo:
    enabled: true
    file: ./cases/case1/input/demo.csv
analysis:
  demo_overlay:
    enabled: true
quality:
  demo_check:
    enabled: true
input_files:
  demo: ./cases/case1/input/demo.csv
EOL

# ===============================
# 创建 utils 脚本
# ===============================
echo "=== 创建 utils 脚本 ==="

# config_manager.py
cat > utils/config_manager.py <<'EOL'
import yaml
from pathlib import Path
from copy import deepcopy

def load_yaml(file_path):
    if not Path(file_path).exists():
        return {}
    with open(file_path, "r") as f:
        return yaml.safe_load(f) or {}

def deep_merge(dict1, dict2):
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result:
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

class ConfigManager:
    def __init__(self, global_cfg="config/global.yaml", case_cfg=None):
        self.config = load_yaml(global_cfg)
        if case_cfg:
            case_conf = load_yaml(case_cfg)
            self.config = deep_merge(self.config, case_conf)

    def get(self, key, default=None):
        return self.config.get(key, default)
EOL

# logger.py
cat > utils/logger.py <<'EOL'
import logging
import logging.config
import yaml
import os

def setup_logger(cfg, case_dir=None):
    with open("config/logging.yaml", "r") as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

    logger = logging.getLogger()
    if case_dir:
        os.makedirs(os.path.join("logs", case_dir), exist_ok=True)
        file_handler = logging.FileHandler(os.path.join("logs", case_dir, "pipeline.log"), mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(file_handler)
    return logger
EOL

# plugin_loader.py
cat > utils/plugin_loader.py <<'EOL'
import importlib
import logging
from pathlib import Path

class PluginLoader:
    def __init__(self, plugin_dir="modules"):
        self.plugin_dir = Path(plugin_dir)
        self.logger = logging.getLogger("PluginLoader")

    def load_module(self, module_type, module_name):
        module_path = f"modules.{module_type}.{module_name}"
        try:
            mod = importlib.import_module(module_path)
            self.logger.info(f"[PluginLoader] Loaded {module_type}.{module_name}")
            return mod
        except ModuleNotFoundError:
            self.logger.error(f"[PluginLoader] Module not found: {module_path}")
            return None
        except Exception as e:
            self.logger.error(f"[PluginLoader] Failed to load {module_path}: {e}")
            return None

    def list_plugins(self, module_type):
        folder = self.plugin_dir / module_type
        if not folder.exists():
            return []
        return [f.stem for f in folder.glob("*.py") if f.stem != "__init__"]
EOL

# ===============================
# 创建 DataHub
# ===============================
cat > modules/datahub.py <<'EOL'
class DataHub:
    def __init__(self):
        self.signals = {}

    def add_signal(self, name, obj):
        self.signals[name] = obj

    def get(self, name):
        return self.signals.get(name, None)
EOL

# ===============================
# 创建插件模板
# ===============================
# base signal
cat > modules/signals/base.py <<'EOL'
class BaseSignal:
    default_cfg = {}
    def load(self, file_path, cfg, logger):
        raise NotImplementedError

    def get_data(self, start=None, end=None):
        raise NotImplementedError
EOL

# demo signal: 生成模拟数据
cat > modules/signals/demo_signal.py <<'EOL'
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
EOL

# base analysis
cat > modules/analysis/base_analysis.py <<'EOL'
class BaseAnalysis:
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        raise NotImplementedError
EOL

# demo analysis: 回叠数据到黑色背景视频
cat > modules/analysis/demo_overlay.py <<'EOL'
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
        signal = datahub.get("demo")
        data = signal.get_data() if signal else []
        for i in range(cfg["length"]):
            frame = np.zeros((cfg["height"], cfg["width"],3), dtype=np.uint8)
            if i < len(data):
                val = int((data[i]["value"]+1)*127)
                cv2.putText(frame, f"Value:{val}", (50,50), cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
            out.write(frame)
        out.release()
EOL

# base quality
cat > modules/quality/base_check.py <<'EOL'
class BaseCheck:
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        raise NotImplementedError
EOL

# demo quality check
cat > modules/quality/demo_check.py <<'EOL'
from .base_check import BaseCheck

class DemoCheck(BaseCheck):
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        logger.info("[DemoCheck] Running demo quality check")
EOL

# ===============================
# 创建 demo_run.py
# ===============================
cat > demo_run.py <<'EOL'
from utils.config_manager import ConfigManager
from utils.logger import setup_logger
from utils.plugin_loader import PluginLoader
from modules.datahub import DataHub
from pathlib import Path

def run_demo(case_path="cases/case1/case.yaml"):
    cfg = ConfigManager(case_cfg=case_path)
    case_name = Path(case_path).parent.name
    logger = setup_logger(cfg, case_dir=f"{case_name}_demo")
    logger.info(f"[Demo] Start demo pipeline for {case_name}")

    hub = DataHub()
    loader = PluginLoader()

    # 加载 demo 信号插件
    mod = loader.load_module("signals", "demo_signal")
    signal_cfg = cfg.get("signals", {}).get("demo", {})
    if mod and signal_cfg.get("enabled", True):
        instance = mod.DemoSignal()
        instance.load("cases/case1/input/demo.csv", signal_cfg, logger)
        hub.add_signal("demo", instance)

    # 执行 demo 分析插件
    mod = loader.load_module("analysis", "demo_overlay")
    analysis_cfg = cfg.get("analysis", {}).get("demo_overlay", {})
    if mod and analysis_cfg.get("enabled", True):
        mod.DemoOverlay().run(hub, analysis_cfg, logger)

    # 执行 demo 质量检查插件
    mod = loader.load_module("quality", "demo_check")
    quality_cfg = cfg.get("quality", {}).get("demo_check", {})
    if mod and quality_cfg.get("enabled", True):
        mod.DemoCheck().run(hub, quality_cfg, logger)

    logger.info(f"[Demo] Demo pipeline finished for {case_name}")

if __name__ == "__main__":
    import sys
    case_path = sys.argv[1] if len(sys.argv) > 1 else "cases/case1/case.yaml"
    run_demo(case_path)
EOL

echo "=== 初始化完成，执行 demo_run.py 可以生成 demo 视频 ==="
