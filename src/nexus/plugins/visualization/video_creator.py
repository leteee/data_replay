
import cv2
import os
from pathlib import Path
from logging import Logger

from pydantic import BaseModel, Field

from nexus.core.plugin_decorator import plugin


class VideoCreatorConfig(BaseModel):
    """Configuration model for the Video Creator plugin."""
    input_dir: str = Field(
        default="intermediate/rendered_frames",
        description="Directory containing the input image frames, relative to the case path."
    )
    output_file: str = Field(
        default="output/replay_video.mp4",
        description="Path for the output video file, relative to the case path."
    )
    fps: int = Field(
        default=10,
        description="Frames per second for the output video."
    )


@plugin(
    name="Video Creator",
    output_key=None  # This plugin writes a file to disk
)
def create_video(
    # Dependencies from Plugin Config
    config: VideoCreatorConfig,
    # Dependencies from Context
    logger: Logger,
    case_path: Path
) -> None:
    """
    Creates a video from a sequence of image frames.
    """
    input_dir_path = case_path / config.input_dir
    output_video_path = case_path / config.output_file

    if not input_dir_path.exists() or not input_dir_path.is_dir():
        logger.error(f"Input directory does not exist: {input_dir_path}")
        return

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
