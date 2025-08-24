import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
from pathlib import Path
from modules.base_plugin import BasePlugin
from core.data_hub import DataHub

class Plotter(BasePlugin):
    """
    A plugin that plots the actual vs. predicted vehicle positions and saves them as images.
    """

    def run(self, data_hub: DataHub):
        super().run(data_hub)

        output_dir_str = self.config.get('output_dir', 'images')
        output_dir = Path(output_dir_str)
        if not output_dir.is_absolute():
            output_dir = self.case_path / output_dir

        if output_dir.exists():
            self.logger.info(f"Cleaning up existing output directory: {output_dir}")
            shutil.rmtree(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)

        input_name = self.config.get("inputs", [None])[0]
        if not input_name:
            self.logger.error("No input data name defined in config for Plotter.")
            return

        df = data_hub.get(input_name)
        if df.empty:
            self.logger.warning("Input data is empty, skipping plotting.")
            return

        self.logger.info(f"Generating plots for {len(df)} data points...")

        for i, row in df.iterrows():
            plt.figure(figsize=(10, 10))
            
            plt.plot(df['x_actual'][:i+1], df['y_actual'][:i+1], 'b-', label='Actual Trajectory')
            plt.plot(df['predicted_x'][:i+1], df['predicted_y'][:i+1], 'g--', label='Predicted Trajectory')

            plt.plot(row['x_actual'], row['y_actual'], 'bo', markersize=8, label='Current Actual Position')
            plt.plot(row['predicted_x'], row['predicted_y'], 'gs', markersize=8, label='Current Predicted Position')

            all_x = pd.concat([df['x_actual'], df['predicted_x']])
            all_y = pd.concat([df['y_actual'], df['predicted_y']])
            plt.xlim(all_x.min() - 10, all_x.max() + 10)
            plt.ylim(all_y.min() - 10, all_y.max() + 10)
            plt.xlabel("X Position (m)")
            plt.ylabel("Y Position (m)")
            plt.title(f"Vehicle Position at Timestamp {row['timestamp']:.2f}s")
            plt.legend()
            plt.grid(True)
            plt.gca().set_aspect('equal', adjustable='box')

            output_path = output_dir / f"frame_{i:04d}.png"
            plt.savefig(output_path)
            plt.close()

        self.logger.info(f"Successfully generated {len(df)} plot images in {output_dir}")
