
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
        manifest_name = self.config.get("inputs", [None])[0]
        predictions_name = self.config.get("inputs", [None])[1]

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
        output_dir_str = self.config.get('output_dir', 'rendered_frames')
        output_dir = Path(output_dir_str)
        if not output_dir.is_absolute():
            output_dir = self.case_path / output_dir

        if output_dir.exists():
            self.logger.info(f"Cleaning up existing output directory: {output_dir}")
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        self.logger.info(f"Created output directory: {output_dir}")

        # --- Merge and Render ---
        # Convert timestamp columns to datetime objects to use Timedelta tolerance
        manifest_df['timestamp'] = pd.to_datetime(manifest_df['timestamp'], unit='s')
        predictions_df['timestamp'] = pd.to_datetime(predictions_df['timestamp'], unit='s')

        # Merge based on the nearest timestamp, assuming they might not be exact
        merged_df = pd.merge_asof(manifest_df.sort_values('timestamp'),
                                  predictions_df.sort_values('timestamp'),
                                  on='timestamp',
                                  direction='nearest',
                                  tolerance=pd.Timedelta('0.01s'))

        self.logger.info(f"Rendering {len(merged_df)} frames...")

        for i, row in merged_df.iterrows():
            # Skip rows where data is missing
            if pd.isna(row['image_path']) or pd.isna(row['predicted_x']) or pd.isna(row['true_x']):
                continue

            # Load original image
            image_path = self.case_path / row['image_path']
            img = Image.open(image_path).convert('RGB')
            draw = ImageDraw.Draw(img)

            radius = 8 # Increase radius for better visibility

            # Draw ground truth position (e.g., a green circle)
            gx, gy = row['true_x'], row['true_y']
            draw.ellipse([(gx - radius, gy - radius), (gx + radius, gy + radius)], fill='green', outline='green')

            # Draw predicted position (e.g., a red circle)
            px, py = row['predicted_x'], row['predicted_y']
            draw.ellipse([(px - radius, py - radius), (px + radius, py + radius)], fill='red', outline='red')

            # Add a legend
            draw.text((10, 10), "Green: Ground Truth", fill="green")
            draw.text((10, 30), "Red: Predicted", fill="red")

            # Save rendered frame
            output_frame_path = output_dir / image_path.name
            img.save(output_frame_path)

        self.logger.info(f"Finished rendering frames to {output_dir}")
