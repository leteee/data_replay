
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
from pathlib import Path
from modules.base_plugin import BasePlugin

class Plotter(BasePlugin):
    """
    A plugin that plots the actual vs. predicted vehicle positions and saves them as images.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.output_dir_str = self.config.get('output_dir', 'images')

    def run(self, context: dict) -> dict:
        super().run(context)

        output_dir = Path(self.output_dir_str)
        if not output_dir.is_absolute():
            output_dir = self.case_path / output_dir

        # Cleanup existing directory
        if output_dir.exists():
            self.logger.info(f"Cleaning up existing output directory: {output_dir}")
            shutil.rmtree(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)

        df = self.data
        if df.empty:
            self.logger.warning("Input data is empty, skipping plotting.")
            return context

        self.logger.info(f"Generating plots for {len(df)} data points...")

        for i, row in df.iterrows():
            plt.figure(figsize=(10, 10))
            
            # Plot the entire actual trajectory up to the current point
            plt.plot(df['x_actual'][:i+1], df['y_actual'][:i+1], 'b-', label='Actual Trajectory')
            # Plot the entire predicted trajectory up to the current point
            plt.plot(df['predicted_x'][:i+1], df['predicted_y'][:i+1], 'g--', label='Predicted Trajectory')

            # Plot current actual and predicted points
            plt.plot(row['x_actual'], row['y_actual'], 'bo', markersize=8, label='Current Actual Position')
            plt.plot(row['predicted_x'], row['predicted_y'], 'gs', markersize=8, label='Current Predicted Position')

            # Set plot limits and labels
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

            # Save the plot to a file
            output_path = output_dir / f"frame_{i:04d}.png"
            plt.savefig(output_path)
            plt.close()

        self.logger.info(f"Successfully generated {len(df)} plot images in {output_dir}")
        return context
