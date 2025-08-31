import cv2
import os
from pathlib import Path
from ..base_plugin import BasePlugin
from ...core.data_hub import DataHub

class VideoCreator(BasePlugin):
    """
    A plugin that creates a video from a sequence of images.
    """

    def run(self, data_hub: DataHub):
        super().run(data_hub)

        # Get inputs and outputs from config
        input_names = self.config.get('inputs', [])
        output_names = self.config.get('outputs', [])
        fps = self.config.get('fps', 10)

        # Get input directory from data source
        if not input_names:
            self.logger.error("Input data source must be provided in the config.")
            return
            
        input_data_name = input_names[0]
        try:
            # For directory handler, get returns the directory path
            input_dir_path = data_hub.get(input_data_name)
            if not input_dir_path:
                self.logger.warning(f"Input directory not found for data source: {input_data_name}")
                return
                
            # Check if directory exists
            if not input_dir_path.exists():
                self.logger.warning(f"Input directory does not exist: {input_dir_path}")
                return
                
            # Get list of PNG files in the directory
            image_files = sorted([f for f in input_dir_path.glob('*.png')], key=lambda f: int(f.stem.split('_')[-1]))
            if not image_files:
                self.logger.warning(f"No PNG images found in {input_dir_path}, skipping video creation.")
                return
                
            self.logger.info(f"Found {len(image_files)} images from data source: {input_data_name}")
        except Exception as e:
            self.logger.error(f"Could not load input directory from data source '{input_data_name}': {e}")
            return

        # Get output path from data source
        if not output_names:
            self.logger.error("Output data source must be provided in the config.")
            return
            
        output_data_name = output_names[0]
        output_video_path = data_hub.get_path(output_data_name)
        if not output_video_path:
            self.logger.error(f"Could not get output path for data source: {output_data_name}")
            return

        # Clean up existing video file
        if output_video_path.exists():
            self.logger.info(f"Cleaning up existing video file: {output_video_path}")
            output_video_path.unlink()

        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        # Process first image to get dimensions
        first_image_file = image_files[0]
        frame = cv2.imread(str(first_image_file))
        if frame is None:
            self.logger.error(f"Could not read the first image: {first_image_file}")
            return
            
        height, width, layers = frame.shape

        # Create video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        video = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

        for image_file in image_files:
            video.write(cv2.imread(str(image_file)))

        video.release()
        self.logger.info(f"Successfully created video: {output_video_path}")