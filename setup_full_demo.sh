#!/bin/bash

# ===============================
# 一键初始化完整项目（PipelineRunner 版）
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
plugins:
  - path: "modules.signals.demo_signal.DemoSignal"
    enabled: true
    cfg:
      length: 100
      file: "cases/case1/input/demo.csv"

  - path: "modules.analysis.demo_overlay.DemoOverlay"
    enabled: true
    cfg:
      width: 640
      height: 480
      fps: 10
      length: 100
      output: "cases/case1/output/demo_video.avi"

  - path: "modules.quality.demo_check.DemoCheck"
    enabled: true
EOL

# ===============================
# 创建 utils 脚本
# ===============================
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
EOL

# pipeline_runner.py
cat > utils/pipeline_runner.py <<'EOL'
import sys
from pathlib import Path
import importlib
from utils.config_manager import ConfigManager
from utils.logger import setup_logger
from modules.datahub import DataHub

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class PipelineRunner:
    def __init__(self, case_cfg_path="cases/case1/case.yaml"):
        self.cfg = ConfigManager(case_cfg=case_cfg_path)
        self.case_name = Path(case_cfg_path).parent.name
        self.logger = setup_logger(self.cfg, case_dir=f"{self.case_name}_demo")
        self.hub = DataHub()
        self.plugins = []

    def load_plugins(self):
        plugin_list = self.cfg.get("plugins", [])
        for plugin_info in plugin_list:
            path = plugin_info.get("path")
            enabled = plugin_info.get("enabled", True)
            cfg = plugin_info.get("cfg", {})
            if not enabled:
                self.logger.info(f"[PipelineRunner] Plugin {path} is disabled, skip")
                continue
            try:
                mod_path, cls_name = path.rsplit(".", 1)
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                instance = cls()
                self.plugins.append({"instance": instance, "cfg": cfg, "name": cls_name})
                self.logger.info(f"[PipelineRunner] Loaded plugin {path}")
            except Exception as e:
                self.logger.error(f"[PipelineRunner] Failed to load plugin {path}: {e}")

    def run_all(self):
        for plugin in self.plugins:
            inst = plugin["instance"]
            cfg = plugin["cfg"]
            self.logger.info(f"[PipelineRunner] Running plugin {plugin['name']}")
            if hasattr(inst, "load"):
                inst.load(cfg.get("file", None), cfg, self.logger)
                self.hub.add_signal(plugin['name'], inst)
            elif hasattr(inst, "run"):
                inst.run(self.hub, cfg, self.logger)

    def run_plugin(self, plugin_name):
        for plugin in self.plugins:
            if plugin["name"] == plugin_name:
                inst = plugin["instance"]
                cfg = plugin["cfg"]
                self.logger.info(f"[PipelineRunner] Running plugin {plugin_name} independently")
                if hasattr(inst, "load"):
                    inst.load(cfg.get("file", None), cfg, self.logger)
                    self.hub.add_signal(plugin_name, inst)
                elif hasattr(inst, "run"):
                    inst.run(self.hub, cfg, self.logger)
                return
        self.logger.warning(f"[PipelineRunner] Plugin {plugin_name} not found")
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
# 创建插件示例
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

# demo signal
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

# demo overlay
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
        signal = datahub.get("DemoSignal")
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

# demo check
cat > modules/quality/demo_check.py <<'EOL'
from .base_check import BaseCheck

class DemoCheck(BaseCheck):
    default_cfg = {}
    def run(self, datahub, cfg, logger):
        logger.info("[DemoCheck] Running demo quality check")
EOL

# ===============================
# demo_run.py
# ===============================
cat > demo_run.py <<'EOL'
from utils.pipeline_runner import PipelineRunner
import sys

if __name__ == "__main__":
    case_cfg = sys.argv[1] if len(sys.argv) > 1 else "cases/case1/case.yaml"
    runner = PipelineRunner(case_cfg)
    runner.load_plugins()
    runner.run_all()
EOL

# ===============================
# 空输入文件
# ===============================
touch cases/case1/input/demo.csv

# ===============================
# README
# ===============================
cat > README.md <<EOL
# 视频回叠系统 Demo

## 目录结构

- modules/: 插件目录 (signals, analysis, quality)
- utils/: 工具类和 PipelineRunner
- config/: 全局和 case 配置
- cases/: 输入输出案例
- logs/: 日志目录

## 使用方法

1. 初始化项目：

\`\`\`bash
bash setup_full_demo.sh
\`\`\`

2. 运行 demo：

\`\`\`bash
python3 demo_run.py
\`\`\`

- 输出视频：cases/case1/output/demo_video.avi  
- 日志：logs/case1_demo/pipeline.log
EOL

echo "=== 初始化完成，执行 python3 demo_run.py 可以生成 demo 视频 ==="

#!/bin/bash

echo "=== 生成 requirements.txt ==="
cat > requirements.txt <<EOL
numpy
opencv-python
pyyaml
EOL

echo "=== 生成 .gitignore ==="
cat > .gitignore <<EOL
# Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Logs
logs/

# Output video
cases/*/output/

# Virtual environment
venv/
env/
EOL

echo "=== requirements.txt 和 .gitignore 生成完成 ==="
