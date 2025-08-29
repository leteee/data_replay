import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
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

            img = Image.new('RGB', (1920, 1080), color='black')
            draw = ImageDraw.Draw(img)

            # --- Dynamic Camera Logic ---
            zoom_factor = self.config.get("zoom_factor", 2.5)
            cam_world_x, cam_world_y = row['true_x'], row['true_y']
            viewport_width, viewport_height = img.size

            def world_to_camera(world_x, world_y):
                relative_x = (world_x - cam_world_x) * zoom_factor
                relative_y = (world_y - cam_world_y) * zoom_factor
                cam_x = relative_x + viewport_width / 2
                cam_y = relative_y + viewport_height / 2
                return cam_x, cam_y

            # --- Draw Grid ---
            grid_spacing = 50.0
            grid_color = (50, 50, 50)
            text_color = (128, 128, 128)
            world_top_left_x = cam_world_x - (viewport_width / 2.0) / zoom_factor
            world_top_left_y = cam_world_y - (viewport_height / 2.0) / zoom_factor
            world_bottom_right_x = cam_world_x + (viewport_width / 2.0) / zoom_factor
            world_bottom_right_y = cam_world_y + (viewport_height / 2.0) / zoom_factor

            start_grid_x = world_top_left_x - (world_top_left_x % grid_spacing)
            start_grid_y = world_top_left_y - (world_top_left_y % grid_spacing)

            for x in np.arange(float(start_grid_x), float(world_bottom_right_x), float(grid_spacing)):
                line_start_cam = world_to_camera(x, world_top_left_y)
                line_end_cam = world_to_camera(x, world_bottom_right_y)
                draw.line([line_start_cam, line_end_cam], fill=grid_color)
                text_pos_cam = (line_start_cam[0] + 5, viewport_height - 20)
                draw.text(text_pos_cam, f"{x:.0f}m", fill=text_color)

            for y in np.arange(float(start_grid_y), float(world_bottom_right_y), float(grid_spacing)):
                line_start_cam = world_to_camera(world_top_left_x, y)
                line_end_cam = world_to_camera(world_bottom_right_x, y)
                draw.line([line_start_cam, line_end_cam], fill=grid_color)
                text_pos_cam = (10, line_start_cam[1] + 5)
                draw.text(text_pos_cam, f"{y:.0f}m", fill=text_color)

            # --- Draw Data Points ---
            radius = self.config.get("circle_radius_px", 15)
            width = self.config.get("circle_width_px", 3)

            # Draw ground truth (green circle)
            gx_cam, gy_cam = world_to_camera(row['true_x'], row['true_y'])
            draw.ellipse([(gx_cam - radius, gy_cam - radius), (gx_cam + radius, gy_cam + radius)], outline='#28a745', width=width)

            # Draw predicted position (red circle)
            px_cam, py_cam = world_to_camera(row['predicted_x'], row['predicted_y'])
            draw.ellipse([(px_cam - radius, py_cam - radius), (px_cam + radius, py_cam + radius)], outline='#dc3545', width=width)

            # --- Add Info Display ---
            try:
                font = ImageFont.truetype("consola.ttf", 18)
            except IOError:
                font = ImageFont.load_default()

            # Ground Truth Info
            true_ts_str = row['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            true_yaw_deg = np.rad2deg(row.get('true_yaw_rad', 0.0))
            true_speed = row.get('true_speed', 0.0)
            gt_text = f"""--- Ground Truth ---
Time:  {true_ts_str}
Speed: {true_speed:6.2f} m/s
Yaw:   {true_yaw_deg:6.1f}°"""
            draw.text((20, 30), gt_text, fill='#28a745', font=font)

            # Predicted Info
            predicted_yaw = row.get('predicted_yaw_rad', 0.0)
            pred_yaw_deg = np.rad2deg(predicted_yaw)
            pred_speed = row.get('predicted_speed', 0.0)
            pred_text = f"""--- Predicted ---
Time:  {true_ts_str}
Speed: {pred_speed:6.2f} m/s
Yaw:   {pred_yaw_deg:6.1f}°"""
            draw.text((20, 130), pred_text, fill='#dc3545', font=font)

            # --- Save Frame ---
            output_frame_path = output_dir / Path(row['image_path']).name
            img.save(output_frame_path)

        self.logger.info(f"Finished rendering frames to {output_dir}")