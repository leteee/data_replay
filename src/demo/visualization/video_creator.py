
import cv2
from pathlib import Path
from logging import Logger
from typing import Annotated, Optional

from pydantic import BaseModel, Field

from nexus.core.plugin.decorator import plugin
from nexus.core.plugin.typing import DataSource, DataSink


class VideoCreatorConfig(BaseModel):
    """Configuration model for the Video Creator plugin."""
    # Needed to allow Path fields
    model_config = {"arbitrary_types_allowed": True}
    
    # --- Data Dependencies ---
    rendered_frames_dir: Annotated[
        Path,
        DataSource(name="rendered_frames", handler_args={"name": "dir"})
    ]
    replay_video: Optional[Annotated[
        Path,
        DataSink(name="replay_video", handler_args={"name": "file", "must_exist": True})
    ]] = None

    # --- Algorithm Parameters ---
    fps: int = Field(
        default=10,
        description="Frames per second for the output video."
    )


@plugin(
    name="Video Creator",
    default_config=VideoCreatorConfig
)
def create_video(config: VideoCreatorConfig, logger: Logger) -> None:
    """
    Creates a video from a sequence of image frames.
    """
    input_dir_path = config.rendered_frames_dir
    # 使用硬编码的输出路径，符合DataSink的定义
    output_video_path = Path("output/replay_video.mp4")

    # Ensure input_dir_path is a Path object and exists
    if not isinstance(input_dir_path, Path) or not input_dir_path.exists() or not input_dir_path.is_dir():
        logger.error(f"Input directory does not exist or is not a directory: {input_dir_path}")
        return None

    image_files = sorted(
        [f for f in input_dir_path.glob('*.png')],
        key=lambda f: int(f.stem.split('_')[-1]) if f.stem.split('_')[-1].isdigit() else -1
    )

    if not image_files:
        logger.warning(f"No PNG images found in {input_dir_path}, skipping video creation.")
        return None

    logger.info(f"Found {len(image_files)} images in {input_dir_path}.")

    # 构建完整的输出路径
    full_output_path = input_dir_path.parent.parent / output_video_path
    
    # 确保输出目录存在
    full_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Clean up existing video file if it exists
    if full_output_path.exists():
        full_output_path.unlink()

    first_image_path = str(image_files[0])
    frame = cv2.imread(first_image_path)
    if frame is None:
        logger.error(f"Could not read the first image: {first_image_path}")
        return None
    height, width, _ = frame.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(str(full_output_path), fourcc, config.fps, (width, height))

    for image_file in image_files:
        video.write(cv2.imread(str(image_file)))

    video.release()
    logger.info(f"Successfully created video: {full_output_path}")
    return None
