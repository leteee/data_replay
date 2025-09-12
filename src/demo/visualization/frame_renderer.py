
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from pathlib import Path
from logging import Logger
from typing import Annotated

from pydantic import BaseModel

from nexus.core.plugin.decorator import plugin
from nexus.core.plugin.typing import DataSource
from nexus.core.context import PluginContext


class FrameRendererConfig(BaseModel):
    """Configuration model for the Frame Renderer plugin."""
    # Needed to allow DataFrame and Path fields
    model_config = {"arbitrary_types_allowed": True}
    
    # --- Data Dependencies ---
    video_manifest: Annotated[
        pd.DataFrame,
        DataSource(name="video_manifest")
    ]
    predicted_states: Annotated[
        pd.DataFrame,
        DataSource(name="predicted_states")
    ]
    rendered_frames_dir: Annotated[
        Path,
        DataSource(name="rendered_frames", handler_args={"name": "dir"})
    ]

    # --- Algorithm Parameters ---
    zoom_factor: float = 5.0
    circle_radius_px: int = 15
    circle_width_px: int = 3


@plugin(
    name="Frame Renderer",
    default_config=FrameRendererConfig
)
def render_frames(context: PluginContext) -> None:
    """
    Renders predicted and ground truth data onto a series of image frames,
    creating a visual representation of the EKF predictions.
    """
    config = context.config
    logger = context.logger
    
    logger.info(f"Using output directory: {config.rendered_frames_dir}")

    # --- Merge Data ---
    manifest_df = config.video_manifest.copy()
    predictions_df = config.predicted_states.copy()
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

        # --- Draw Grid and Data Points ---
        radius = config.circle_radius_px
        width = config.circle_width_px
        
        gx_cam, gy_cam = world_to_camera(row['true_x'], row['true_y'])
        draw.ellipse([(gx_cam - radius, gy_cam - radius), (gx_cam + radius, gy_cam + radius)], outline='#28a745', width=width)

        px_cam, py_cam = world_to_camera(row['predicted_x'], row['predicted_y'])
        draw.ellipse([(px_cam - radius, py_cam - radius), (px_cam + radius, py_cam + radius)], outline='#dc3545', width=width)

        # --- Save Frame ---
        image_filename = Path(row['image_path']).name
        output_frame_path = config.rendered_frames_dir / image_filename
        
        img.save(output_frame_path)

    logger.info(f"Finished rendering frames to {config.rendered_frames_dir}")
