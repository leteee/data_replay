import cv2
import numpy as np
from modules.base_plugin import BasePlugin
from pathlib import Path

class DemoOverlay(BasePlugin):
    def __init__(self, config):
        super().__init__(config) # Call parent constructor to set self.config

    def run(self, context):
        """Overlays signal data onto an image based on configuration."""
        super().run(context) # Call parent run to set self._context and self._logger

        self.logger.info(f"Running DemoOverlay with config: {self.config}")

        # 获取图像数据 (假设图像数据在 context['image'])
        # 在实际流水线中，图像可能来自前一个插件或通过配置加载
        image_data = context.get('image') # Access context directly
        if image_data is None:
            self.logger.warning("context 中未找到图像数据，DemoOverlay 将尝试从配置加载默认图像。")
            # 尝试从配置中加载默认图像 (如果存在)
            default_image_path = self.config.get('default_image')
            if default_image_path:
                # case_path is now available via self.case_path property
                abs_image_path = self.case_path / default_image_path
                if abs_image_path.exists():
                    image_data = cv2.imread(str(abs_image_path))
                    self.logger.info(f"从 {abs_image_path} 加载了默认图像。")
                else:
                    self.logger.error(f"默认图像文件不存在: {abs_image_path}")
            
            if image_data is None:
                self.logger.error("DemoOverlay 无法获取图像数据，请确保前置插件提供了图像或配置了默认图像。")
                # 返回原始 context，不进行处理
                return context

        # 获取信号数据 (假设信号数据在 context['signal_data'])
        signal_data = context.get('signal_data', {})

        # 示例：在图像上绘制文本
        overlay_text = self.config.get('overlay_text', 'Processed Data')
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.config.get('font_scale', 1)
        font_thickness = self.config.get('font_thickness', 2)
        text_color = tuple(self.config.get('text_color', [0, 255, 0])) # Green by default
        text_position = tuple(self.config.get('text_position', [50, 50]))

        # 确保图像是可写的
        if image_data.dtype != np.uint8:
            image_data = image_data.astype(np.uint8)
        if len(image_data.shape) == 2:
            image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)

        # 绘制文本
        cv2.putText(image_data, overlay_text, text_position, font, font_scale, text_color, font_thickness, cv2.LINE_AA)

        # 更新 context，将处理后的图像放回
        context['image'] = image_data
        context['overlay_applied'] = True

        # 返回更新后的 context
        return context