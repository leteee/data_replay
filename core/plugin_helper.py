import argparse
import logging
import json
import pandas as pd
from pathlib import Path
import sys
import inspect

# To import from the parent directory (core), we adjust the path
# This will be cleaner after the src-layout refactor
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.config_manager import ConfigManager

def run_plugin_standalone(plugin_class):
    """
    通用的、符合项目设计原则的插件独立运行辅助函数。

    它通过 --case 参数获取案例上下文，然后完全复用 ConfigManager
    来加载配置，确保与流水线运行时的行为一致。

    Args:
        plugin_class: 要运行的插件类 (例如 DemoCheck).
    """
    parser = argparse.ArgumentParser(
        description=f"Standalone runner for {plugin_class.__name__}"
    )
    parser.add_argument(
        "--case",
        required=True,
        help="案例目录的路径 (e.g., 'cases/case1')"
    )
    args = parser.parse_args()

    # --- 1. 初始化环境 ---
    case_path = Path(args.case)
    # The project root is assumed to be the parent of the cases/ directory
    project_root_path = case_path.parent.parent
    plugin_file_path = inspect.getfile(plugin_class)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(f"{plugin_class.__name__}Standalone")

    # --- 2. 加载配置 (复用 ConfigManager) ---
    config_manager = ConfigManager(project_root=str(project_root_path))
    case_yaml_path = case_path / "case.yaml"
    
    if not case_yaml_path.exists():
        logger.error(f"案例配置文件不存在: {case_yaml_path}")
        sys.exit(1)

    with open(case_yaml_path, 'r', encoding='utf-8') as f:
        case_config = yaml.safe_load(f)

    # 在 case.yaml 的 pipeline 中找到本插件的配置
    case_override_config = {}
    for step in case_config.get("pipeline", []):
        if step.get("plugin") == plugin_class.__name__:
            case_override_config = step.get("config", {})
            logger.info(f"在 case.yaml 中找到 {plugin_class.__name__} 的特定配置")
            break
    
    # 使用 ConfigManager 获取最终合并的配置
    final_config = config_manager.get_plugin_config(
        plugin_module_path=plugin_file_path,
        case_config_override=case_override_config
    )
    # 将 case_path 注入 config，以便插件内部可以访问
    final_config['case_path'] = str(case_path)

    # --- 3. 加载初始数据 ---
    # 约定：初始数据在 case.yaml 的顶层 input_data_file 字段中定义
    initial_data_path_str = case_config.get("input_data_file")
    if not initial_data_path_str:
        logger.error(f"案例配置 {case_yaml_path} 中未定义初始数据源 'input_data_file'")
        sys.exit(1)

    initial_data_path = case_path / initial_data_path_str
    try:
        if not initial_data_path.exists():
            logger.error(f"初始数据文件不存在: {initial_data_path}")
            sys.exit(1)
        
        if initial_data_path.suffix == '.csv':
            df = pd.read_csv(initial_data_path)
        elif initial_data_path.suffix == '.parquet':
            df = pd.read_parquet(initial_data_path)
        else:
            logger.error(f"不支持的输入文件格式: {initial_data_path.suffix}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"加载初始数据文件失败: {e}")
        sys.exit(1)

    # --- 4. 构建 Context 并执行 ---
    context = {
        "data": df,
        "logger": logger,
        "results": {}
    }

    logger.info(f"--- Running {plugin_class.__name__} Standalone ---")
    logger.info(f"Final Config: {final_config}")
    
    plugin_instance = plugin_class(config=final_config)
    output_context = plugin_instance.run(context)

    # --- 5. 打印结果 ---
    logger.info("--- Standalone Run Finished ---")
    results = output_context.get("results", {})
    print("\n====== Plugin Results ======")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("============================")

# Need to import yaml for the helper function
import yaml
yaml