
from modules.base_plugin import BasePlugin
from utils.logger import get_logger
from pathlib import Path
import json

logger = get_logger(__name__)

class DemoCheck(BasePlugin):
    def __init__(self, config):
        self.config = config
        self.rules = {} # To store rules from the input file

    def _load_rules_from_file(self, case_path):
        """Loads quality check rules from the file specified in the config."""
        rules_file_path_str = self.config.get("input_rules_file")
        if not rules_file_path_str:
            logger.info("配置中未指定 input_rules_file，跳过加载外部规则。")
            return

        # Construct the absolute path relative to the case directory
        absolute_rules_path = Path(case_path) / rules_file_path_str
        logger.info(f"正在从 {absolute_rules_path} 加载规则文件...")

        if absolute_rules_path.exists():
            with open(absolute_rules_path, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
                logger.info(f"成功加载规则: {self.rules}")
        else:
            logger.warning(f"规则文件不存在: {absolute_rules_path}")

    def run(self, data_hub):
        """Performs a demo quality check based on configuration and external rules."""
        logger.info(f"Running DemoCheck with config: {self.config}")

        # Load external rules using the case_path from the data_hub context
        case_path = data_hub.get("context", {}).get("case_path")
        if case_path:
            self._load_rules_from_file(case_path)
        else:
            logger.error("data_hub中缺少 case_path 上下文信息！")

        # This plugin will use the dataframe helper
        df = self.load_dataframe(data_hub.get('data'))

        # Use values from config, potentially overridden by loaded rules
        check_column = self.rules.get('column', self.config.get('column'))
        max_value = self.rules.get('max_value', self.config.get('max_value', 100))
        
        issues = 0
        if check_column and not df.empty and check_column in df.columns:
            issues = df[df[check_column] > max_value].shape[0]
            logger.info(f"根据规则，发现 {issues} 行在列 '{check_column}' 的值超过了 {max_value}.")
        else:
            logger.warning(f"列 '{check_column}' 未在配置或规则中指定，或在DataFrame中不存在。")

        # Store results in the data_hub
        results = {
            f"demo_check_{check_column}_issues": issues
        }
        data_hub.setdefault('results', {}).update(results)

        # This check doesn't modify the DataFrame, so we return it as is.
        data_hub['data'] = df
        return data_hub
