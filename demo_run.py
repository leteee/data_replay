from utils.config_manager import ConfigManager
from utils.logger import setup_logger
from utils.plugin_loader import PluginLoader
from modules.datahub import DataHub
from pathlib import Path
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
