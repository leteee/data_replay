
import cv2
import os
from pathlib import Path
from logging import Logger

from pydantic import BaseModel, Field

from nexus.core.plugin.decorator import plugin
from typing import Dict, Any


class VideoCreatorConfig(BaseModel):
    """Configuration model for the Video Creator plugin."""
    data_sources: Dict[str, Any] = {
        "rendered_frames_dir": {
            "handler": "dir",
            "path": "intermediate/rendered_frames"
        },
        "replay_video": {
            "handler": "file",
            "path": "output/replay_video.mp4"
        }
    }
    fps: int = Field(
        default=10,
        description="Frames per second for the output video."
    )


@plugin(
    name="Video Creator",
    default_config=VideoCreatorConfig
)
def create_video(
    # Dependencies from DataHub
    rendered_frames_dir: Path, # <-- Injected by DataHub using DirectoryHandler
    # Dependencies from Plugin Config
    config: VideoCreatorConfig,
    # Dependencies from Context
    logger: Logger,
    case_path: Path
) -> Path:
    """
    Creates a video from a sequence of image frames.
    """
    input_dir_path = rendered_frames_dir
    output_video_path = case_path / config.data_sources["replay_video"]["path"]

    if not input_dir_path.exists() or not input_dir_path.is_dir():
        logger.error(f"Input directory does not exist: {input_dir_path}")
        return None

    image_files = sorted(
        [f for f in input_dir_path.glob('*.png')],
        # Sort by frame number, assuming format like 'frame_0001.png'
        key=lambda f: int(f.stem.split('_')[-1]) if f.stem.split('_')[-1].isdigit() else -1
    )

    if not image_files:
        logger.warning(f"No PNG images found in {input_dir_path}, skipping video creation.")
        return

    logger.info(f"Found {len(image_files)} images in {input_dir_path}.")

    # Clean up existing video file
    if output_video_path.exists():
        logger.info(f"Cleaning up existing video file: {output_video_path}")
        output_video_path.unlink()
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    # Process first image to get dimensions
    first_image_path = str(image_files[0])
    frame = cv2.imread(first_image_path)
    if frame is None:
        logger.error(f"Could not read the first image: {first_image_path}")
        return
    height, width, _ = frame.shape

    # Create video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(str(output_video_path), fourcc, config.fps, (width, height))

    for image_file in image_files:
        video.write(cv2.imread(str(image_file)))

    video.release()
    logger.info(f"Successfully created video: {output_video_path}")
    return output_video_path
