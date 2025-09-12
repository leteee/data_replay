
import cv2
from pathlib import Path
from logging import Logger
from typing import Annotated, Optional

from pydantic import BaseModel, Field

from nexus.core.plugin.decorator import plugin
from nexus.core.plugin.typing import DataSource, DataSink
from nexus.core.context import PluginContext


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
def create_video(context: PluginContext) -> None:
    """
    Creates a video from a sequence of image frames.
    """
    config = context.config
    logger = context.logger
    
    input_dir_path = config.rendered_frames_dir
    output_video_path = context.output_path

    if not output_video_path:
        logger.error("Output path not provided in the context for this plugin run.")
        return

    # Ensure input_dir_path is a Path object and exists
    if not isinstance(input_dir_path, Path) or not input_dir_path.exists() or not input_dir_path.is_dir():
        logger.error(f"Input directory does not exist or is not a directory: {input_dir_path}")
        return

    image_files = sorted(
        [f for f in input_dir_path.glob('*.png')],
        key=lambda f: int(f.stem.split('_')[-1]) if f.stem.split('_')[-1].isdigit() else -1
    )

    if not image_files:
        logger.warning(f"No PNG images found in {input_dir_path}, skipping video creation.")
        return

    logger.info(f"Found {len(image_files)} images in {input_dir_path}.")

    # Ensure the output directory exists
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Clean up existing video file if it exists
    if output_video_path.exists():
        output_video_path.unlink()

    first_image_path = str(image_files[0])
    frame = cv2.imread(first_image_path)
    if frame is None:
        logger.error(f"Could not read the first image: {first_image_path}")
        return
    height, width, _ = frame.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(str(output_video_path), fourcc, config.fps, (width, height))

    for image_file in image_files:
        video.write(cv2.imread(str(image_file)))

    video.release()
    logger.info(f"Successfully created video: {output_video_path}")
    return
