
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import shutil
from logging import Logger

from pydantic import BaseModel, Field

from nexus.core.data.hub import DataHub
from nexus.core.plugin.decorator import plugin


class FrameRendererConfig(BaseModel):
    """Configuration model for the Frame Renderer plugin."""
    video_manifest_key: str = "video_manifest"
    predicted_states_key: str = "predicted_states"
    rendered_frames_dir_key: str = "rendered_frames_dir"
    zoom_factor: float = 5.0
    circle_radius_px: int = 15
    circle_width_px: int = 3


@plugin(
    name="Frame Renderer",
    output_key=None  # This plugin writes files to disk, doesn't return to DataHub
)
def render_frames(
    # Dependencies from DataHub
    video_manifest: pd.DataFrame,
    predicted_states: pd.DataFrame,
    rendered_frames_dir: Path, # <-- Injected by DataHub using DirectoryHandler
    # Dependencies from Plugin Config
    config: FrameRendererConfig,
    # Dependencies from Context
    logger: Logger,
    case_path: Path
) -> None:
    """
    Renders predicted and ground truth data onto a series of image frames,
    creating a visual representation of the EKF predictions.
    """
    # --- Prepare Output Directory ---
    # The directory is now prepared by the DataHub and DirectoryHandler
    # We just use the Path provided by the dependency injection
    
    logger.info(f"Using output directory prepared by DataHub: {rendered_frames_dir}")
    logger.info(f"Absolute path of rendered_frames_dir: {rendered_frames_dir.absolute()}")

    # --- Merge Data ---
    manifest_df = video_manifest.copy()
    predictions_df = predicted_states.copy()
    manifest_df['timestamp'] = pd.to_datetime(manifest_df['timestamp'], unit='s')
    predictions_df['timestamp'] = pd.to_datetime(predictions_df['timestamp'])
    
    merged_df = pd.merge_asof(
        manifest_df.sort_values('timestamp'),
        predictions_df.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta('0.01s')
    )

    logger.info(f"Rendering {len(merged_df)} frames...")

    # --- Main Rendering Loop ---
    for i, row in merged_df.iterrows():
        if pd.isna(row.get('image_path')) or pd.isna(row.get('predicted_x')) or pd.isna(row.get('true_x')):
            continue

        img = Image.new('RGB', (1920, 1080), color='black')
        draw = ImageDraw.Draw(img)

        # --- Dynamic Camera Logic ---
        cam_world_x, cam_world_y = row['true_x'], row['true_y']
        viewport_width, viewport_height = img.size

        def world_to_camera(world_x, world_y):
            relative_x = (world_x - cam_world_x) * config.zoom_factor
            relative_y = (world_y - cam_world_y) * config.zoom_factor
            return (relative_x + viewport_width / 2, relative_y + viewport_height / 2)

        # --- Draw Grid and Data Points (simplified for brevity, logic is the same) ---
        # ... (The complex drawing logic would be here) ...
        radius = config.circle_radius_px
        width = config.circle_width_px
        
        gx_cam, gy_cam = world_to_camera(row['true_x'], row['true_y'])
        draw.ellipse([(gx_cam - radius, gy_cam - radius), (gx_cam + radius, gy_cam + radius)], outline='#28a745', width=width)

        px_cam, py_cam = world_to_camera(row['predicted_x'], row['predicted_y'])
        draw.ellipse([(px_cam - radius, py_cam - radius), (px_cam + radius, py_cam + radius)], outline='#dc3545', width=width)

        # --- Save Frame ---
        # Assuming image_path in manifest is relative to case_path
        image_filename = Path(row['image_path']).name
        output_frame_path = rendered_frames_dir / image_filename
        
        logger.info(f"Saving frame to: {output_frame_path}")
        img.save(output_frame_path)

    logger.info(f"Finished rendering frames to {rendered_frames_dir}")
