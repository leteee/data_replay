
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from pathlib import Path
import shutil
from modules.base_plugin import BasePlugin
from core.data_hub import DataHub

class FrameRenderer(BasePlugin):
    """
    A plugin that renders predicted data onto video frames.
    """

    def run(self, data_hub: DataHub):
        super().run(data_hub)

        # --- Get Inputs from Config & DataHub ---
        manifest_name, predictions_name = self.config.get("inputs", [None, None])
        if not manifest_name or not predictions_name:
            self.logger.error("FrameRenderer requires two inputs: video_manifest and predicted_states.")
            return

        try:
            manifest_df = data_hub.get(manifest_name)
            predictions_df = data_hub.get(predictions_name)
        except KeyError as e:
            self.logger.error(f"Could not retrieve data from DataHub: {e}")
            return

        # --- Prepare Output Directory ---
        output_dir = self.case_path / self.config.get('output_dir', 'rendered_frames')
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        self.logger.info(f"Created output directory: {output_dir}")

        # --- Merge Data ---
        manifest_df['timestamp'] = pd.to_datetime(manifest_df['timestamp'], unit='s')
        predictions_df['timestamp'] = pd.to_datetime(predictions_df['timestamp'], unit='s')
        merged_df = pd.merge_asof(manifest_df.sort_values('timestamp'),
                                  predictions_df.sort_values('timestamp'),
                                  on='timestamp', direction='nearest', tolerance=pd.Timedelta('0.01s'))

        self.logger.info(f"Rendering {len(merged_df)} frames with dynamic camera...")

        # --- Main Rendering Loop ---
        for i, row in merged_df.iterrows():
            if pd.isna(row['image_path']) or pd.isna(row['predicted_x']) or pd.isna(row['true_x']):
                continue

            img = Image.new('RGB', (800, 600), color='black')
            draw = ImageDraw.Draw(img)

            # --- Dynamic Camera Logic ---
            # 1. Define camera center (focused on the ground truth)
            cam_world_x, cam_world_y = row['true_x'], row['true_y']
            viewport_width, viewport_height = img.size

            # 2. Function to transform world coordinates to camera (pixel) coordinates
            def world_to_camera(world_x, world_y):
                cam_x = world_x - cam_world_x + viewport_width / 2
                cam_y = world_y - cam_world_y + viewport_height / 2
                return cam_x, cam_y

            # 3. Draw dynamic grid and coordinates
            grid_spacing = 50.0
            grid_color = (50, 50, 50)
            text_color = (128, 128, 128)

            world_top_left_x = cam_world_x - (viewport_width / 2.0)
            world_top_left_y = cam_world_y - (viewport_height / 2.0)
            start_grid_x = world_top_left_x - (world_top_left_x % grid_spacing)
            start_grid_y = world_top_left_y - (world_top_left_y % grid_spacing)

            # Draw vertical grid lines and X coordinates
            for x in np.arange(float(start_grid_x), float(start_grid_x + viewport_width + grid_spacing), float(grid_spacing)):
                line_start_cam = world_to_camera(x, world_top_left_y)
                line_end_cam = world_to_camera(x, world_top_left_y + viewport_height)
                draw.line([line_start_cam, line_end_cam], fill=grid_color)
                # Add text label at the bottom
                text_pos_cam = (line_start_cam[0] + 5, viewport_height - 20)
                draw.text(text_pos_cam, f"{x:.0f}m", fill=text_color)

            # Draw horizontal grid lines and Y coordinates
            for y in np.arange(float(start_grid_y), float(start_grid_y + viewport_height + grid_spacing), float(grid_spacing)):
                line_start_cam = world_to_camera(world_top_left_x, y)
                line_end_cam = world_to_camera(world_top_left_x + viewport_width, y)
                draw.line([line_start_cam, line_end_cam], fill=grid_color)
                # Add text label on the left
                text_pos_cam = (10, line_start_cam[1] + 5)
                draw.text(text_pos_cam, f"{y:.0f}m", fill=text_color)

            # --- Draw Data Points ---
            radius = 8
            # Draw ground truth (green circle) - it will always be in the center
            gx_cam, gy_cam = world_to_camera(row['true_x'], row['true_y'])
            draw.ellipse([(gx_cam - radius, gy_cam - radius), (gx_cam + radius, gy_cam + radius)], fill='green', outline='green')

            # Draw predicted position (red circle)
            px_cam, py_cam = world_to_camera(row['predicted_x'], row['predicted_y'])
            draw.ellipse([(px_cam - radius, py_cam - radius), (px_cam + radius, py_cam + radius)], fill='red', outline='red')

            # --- Add Legend ---
            draw.text((10, 10), "Green: Ground Truth", fill="green")
            draw.text((10, 30), "Red: Predicted", fill="red")

            # --- Save Frame ---
            output_frame_path = output_dir / Path(row['image_path']).name
            img.save(output_frame_path)

        self.logger.info(f"Finished rendering frames to {output_dir}")
