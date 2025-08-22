import cv2
import numpy as np
from modules.base_plugin import BasePlugin
from utils.logger import get_logger

logger = get_logger(__name__)

class DemoOverlay(BasePlugin):
    # 移除 __init__ 方法，配置将从 data_hub 中获取

    def run(self, data_hub):
        """Overlays signal data onto an image based on configuration."""
        # 从 data_hub 中获取配置
        config = data_hub.get('config', {})
        logger.info(f"Running DemoOverlay with config: {config}")

        # 获取图像数据 (假设图像数据在 data_hub['image'])
        # 在实际流水线中，图像可能来自前一个插件或通过配置加载
        image_data = data_hub.get('image')
        if image_data is None:
            logger.warning("data_hub 中未找到图像数据，DemoOverlay 将跳过图像处理。")
            # 尝试从配置中加载默认图像 (如果存在)
            default_image_path = config.get('default_image')
            if default_image_path:
                case_path = data_hub.get("context", {}).get("case_path")
                if case_path:
                    abs_image_path = Path(case_path) / default_image_path
                    if abs_image_path.exists():
                        image_data = cv2.imread(str(abs_image_path))
                        logger.info(f"从 {abs_image_path} 加载了默认图像。")
                    else:
                        logger.error(f"默认图像文件不存在: {abs_image_path}")
                else:
                    logger.error("data_hub中缺少 case_path 上下文信息，无法加载默认图像！")

            if image_data is None:
                logger.error("DemoOverlay 无法获取图像数据，请确保前置插件提供了图像或配置了默认图像。")
                # 返回原始 data_hub，不进行处理
                return data_hub

        # 获取信号数据 (假设信号数据在 data_hub['signal_data'])
        signal_data = data_hub.get('signal_data', {})

        # 示例：在图像上绘制文本
        overlay_text = config.get('overlay_text', 'Processed Data')
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = config.get('font_scale', 1)
        font_thickness = config.get('font_thickness', 2)
        text_color = tuple(config.get('text_color', [0, 255, 0])) # Green by default
        text_position = tuple(config.get('text_position', [50, 50]))

        # 确保图像是可写的
        if image_data.dtype != np.uint8:
            image_data = image_data.astype(np.uint8)
        if len(image_data.shape) == 2:
            image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)

        # 绘制文本
        cv2.putText(image_data, overlay_text, text_position, font, font_scale, text_color, font_thickness, cv2.LINE_AA)

        # 更新 data_hub，将处理后的图像放回
        data_hub['image'] = image_data
        data_hub['overlay_applied'] = True

        # 返回更新后的 data_hub
        return data_hub