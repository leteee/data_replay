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

        input_dir_str = self.config.get('input_dir')
        output_path_str = self.config.get('output_path')
        fps = self.config.get('fps', 10)

        if not input_dir_str or not output_path_str:
            self.logger.error("'input_dir' and 'output_path' must be provided in the config.")
            return

        input_path = Path(input_dir_str)
        if not input_path.is_absolute():
            input_path = self.case_path / input_path

        output_video_path = Path(output_path_str)
        if not output_video_path.is_absolute():
            output_video_path = self.case_path / output_video_path

        if output_video_path.exists():
            self.logger.info(f"Cleaning up existing video file: {output_video_path}")
            output_video_path.unlink()

        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        image_files = sorted([f for f in input_path.glob('*.png')], key=lambda f: int(f.stem.split('_')[-1]))

        if not image_files:
            self.logger.warning(f"No PNG images found in {input_path}, skipping video creation.")
            return

        self.logger.info(f"Found {len(image_files)} images in {input_path}.")

        frame = cv2.imread(str(image_files[0]))
        if frame is None:
            self.logger.error(f"Could not read the first image: {image_files[0]}")
            return
            
        height, width, layers = frame.shape

        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        video = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

        for image_file in image_files:
            video.write(cv2.imread(str(image_file)))

        video.release()
        self.logger.info(f"Successfully created video: {output_video_path}")