
from modules.base_plugin import BasePlugin
from pathlib import Path
import json
import pandas as pd # Ensure pandas is imported for DataFrame operations

class DemoCheck(BasePlugin):
    def __init__(self, config):
        super().__init__(config) # Call parent constructor to set self.config
        self.rules = {} # To store rules from the input file

    def _load_rules_from_file(self):
        """Loads quality check rules from the file specified in the config."""
        rules_file_path_str = self.config.get("input_rules_file")
        if not rules_file_path_str:
            self.logger.info("配置中未指定 input_rules_file，跳过加载外部规则。")
            return

        # Construct the absolute path relative to the case directory
        # case_path is now available via self.case_path property
        absolute_rules_path = self.case_path / rules_file_path_str
        self.logger.info(f"正在从 {absolute_rules_path} 加载规则文件...")

        if absolute_rules_path.exists():
            try:
                with open(absolute_rules_path, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
                    self.logger.info(f"成功加载规则: {self.rules}")
            except json.JSONDecodeError as e:
                self.logger.error(f"规则文件 {absolute_rules_path} JSON解析失败: {e}")
            except Exception as e:
                self.logger.error(f"加载规则文件 {absolute_rules_path} 失败: {e}")
        else:
            self.logger.warning(f"规则文件不存在: {absolute_rules_path}")

    def run(self, context):
        """
        Performs a demo quality check based on configuration and external rules.
        
        Args:
            context (dict): The context containing data, logger, etc.
        
        Returns:
            dict: The updated context.
        """
        super().run(context) # Call parent run to set self._context and self._logger

        self.logger.info(f"Running DemoCheck with config: {self.config}")

        # Load external rules using the case_path from the self.case_path property
        self._load_rules_from_file()

        # This plugin will use the dataframe helper
        # self.data property automatically loads data from context['data']
        df = self.load_dataframe(self.data)

        # Use values from config, potentially overridden by loaded rules
        check_column = self.rules.get('column', self.config.get('column'))
        max_value = self.rules.get('max_value', self.config.get('max_value', 100))
        min_value = self.rules.get('min_value', self.config.get('min_value', 0)) # Added min_value from rules
        
        issues = 0
        issues_max = 0
        issues_min = 0
        if check_column and not df.empty and check_column in df.columns:
            # Check for values exceeding max_value
            issues_max = df[df[check_column] > max_value].shape[0]
            # Check for values below min_value
            issues_min = df[df[check_column] < min_value].shape[0]
            issues = issues_max + issues_min

            self.logger.info(f"根据规则，发现 {issues_max} 行在列 '{check_column}' 的值超过了 {max_value}.")
            self.logger.info(f"根据规则，发现 {issues_min} 行在列 '{check_column}' 的值低于 {min_value}.")
            self.logger.info(f"总计 {issues} 行不符合质量要求。")
        else:
            self.logger.warning(f"列 '{check_column}' 未在配置或规则中指定，或在DataFrame中不存在。")

        # Store results in the context
        results = {
            f"demo_check_{check_column}_issues": issues,
            f"demo_check_{check_column}_issues_max": issues_max if check_column and check_column in df.columns else 0,
            f"demo_check_{check_column}_issues_min": issues_min if check_column and check_column in df.columns else 0
        }
        context.setdefault('results', {}).update(results)

        # This check doesn't modify the DataFrame, so we return it as is.
        context['data'] = df
        return context

if __name__ == "__main__":
    # This temporary path adjustment is needed because the project is not yet
    # installed as a package. It will be removed after refactoring to a src-layout.
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))

    from core.plugin_helper import run_plugin_standalone

    # With the new helper, this is all the code needed for standalone execution.
    # It just needs to identify itself.
    run_plugin_standalone(plugin_class=DemoCheck)
