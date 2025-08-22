import pandas as pd
from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    所有插件的通用抽象基类（v2）。

    这个基类定义了一个更通用的插件结构。
    核心方法 `run` 直接接收和返回 data_hub 字典，
    使得插件可以处理DataFrame之外的任何数据类型（如图像、纯文本等）。

    对于处理表格数据的插件，提供了一个辅助方法 `load_dataframe` 
    来方便地将 data_hub['data'] 中地内容（内存对象或文件路径）转为DataFrame。
    """

    @abstractmethod
    def run(self, data_hub: dict) -> dict:
        """
        这是每个插件需要实现的核心处理逻辑。
        它接收完整的data_hub，执行其任务，并返回修改后的data_hub。

        Args:
            data_hub (dict): 包含所有上下文信息的完整数据总线。

        Returns:
            dict: 修改更新后的 data_hub。
        """
        plugin_name = self.__class__.__name__
        print(f"[{plugin_name}] a plugin should implement its own run method.")
        pass

    def load_dataframe(self, data_input) -> pd.DataFrame:
        """
        辅助方法：将输入统一加载为DataFrame。
        处理表格数据的插件应该在它们的 `run` 方法内部调用此方法。
        """
        if isinstance(data_input, pd.DataFrame):
            # 使用副本以避免副作用
            return data_input.copy()
        elif isinstance(data_input, str):
            # 这里可以根据文件扩展名支持更多格式
            if data_input.endswith('.parquet'):
                return pd.read_parquet(data_input)
            elif data_input.endswith('.csv'):
                return pd.read_csv(data_input)
            else:
                raise ValueError(f"不支持的文件类型: {data_input}")
        elif data_input is None:
            return pd.DataFrame()
        else:
            raise TypeError(f"不支持的数据输入类型: {type(data_input)}")