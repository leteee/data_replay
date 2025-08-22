import pandas as pd
from abc import ABC, abstractmethod
import logging # Import logging module
from pathlib import Path # Import Path for case_path property

class BasePlugin(ABC):
    """
    所有插件的通用抽象基类。
    它定义了插件的通用接口，并提供辅助方法来访问数据、配置和日志。
    """
    def __init__(self, config: dict):
        """
        插件的配置通过 __init__ 传入。
        """
        self.config = config
        self._logger = None # Will be set by the run method via context
        self._context = None # Will be set by the run method

    @property
    def logger(self) -> logging.Logger:
        """
        便捷访问当前插件的日志记录器。
        """
        if self._logger is None:
            # Fallback if not set by runner (e.g., during standalone testing without full context setup)
            self._logger = logging.getLogger(self.__class__.__name__)
            self._logger.warning(f"插件 {self.__class__.__name__} 的logger未通过context注入，使用默认logger。")
        return self._logger

    @property
    def data(self) -> pd.DataFrame:
        """
        便捷访问当前流水线的主数据载荷。
        """
        if self._context is None or 'data' not in self._context:
            self.logger.warning(f"插件 {self.__class__.__name__} 尝试访问data，但context中无数据。返回空DataFrame。")
            return pd.DataFrame()
        # data is now directly at context['data']
        return self._context['data']

    @property
    def case_path(self) -> Path:
        """
        便捷访问当前Case的根目录路径。
        """
        path_str = self.config.get('case_path')
        if not path_str:
            self.logger.warning(f"插件 {self.__class__.__name__} 尝试访问case_path，但config中未找到。返回当前工作目录。")
            return Path.cwd()
        return Path(path_str)

    @abstractmethod
    def run(self, context: dict) -> dict:
        """
        这是每个插件需要实现的核心处理逻辑。
        它接收完整的context，执行其任务，并返回修改后的context。

        Args:
            context (dict): 包含所有上下文信息的完整数据总线。

        Returns:
            dict: 修改更新后的 context。
        """
        self._context = context # Store context for property access
        self._logger = context.get('logger', None) # Get logger from context

        self.logger.info(f"[{self.__class__.__name__}] 开始执行...")
        # Plugin specific logic will go here
        # This abstract method must be implemented by subclasses
        pass

    def load_dataframe(self, data_input) -> pd.DataFrame:
        """
        辅助方法：将输入统一加载为DataFrame。
        处理表格数据的插件应该在它们的 `run` 方法内部调用此方法。
        """
        # data_input is now directly context['data']
        if isinstance(data_input, pd.DataFrame):
            self.logger.debug(f"[{self.__class__.__name__}] 正在处理内存中的DataFrame...")
            return data_input.copy() # 使用副本以避免副作用
        elif isinstance(data_input, str):
            self.logger.debug(f"[{self.__class__.__name__}] 正在从路径 {data_input} 读取文件...")
            # 这里可以根据文件扩展名支持更多格式
            try:
                if data_input.endswith('.parquet'):
                    return pd.read_parquet(data_input)
                elif data_input.endswith('.csv'):
                    return pd.read_csv(data_input)
                else:
                    self.logger.error(f"不支持的文件类型: {data_input}")
                    raise ValueError(f"不支持的文件类型: {data_input}")
            except Exception as e:
                self.logger.error(f"从文件 {data_input} 加载DataFrame失败: {e}")
                raise
        elif data_input is None:
            self.logger.debug(f"[{self.__class__.__name__}] 未接收到输入数据，将创建空的DataFrame。")
            return pd.DataFrame()
        else:
            self.logger.error(f"不支持的数据输入类型: {type(data_input)}")
            raise TypeError(f"不支持的数据输入类型: {type(data_input)}")
