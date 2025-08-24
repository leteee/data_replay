import cv2
import os
from pathlib import Path
from modules.base_plugin import BasePlugin

print("cv2 path:", cv2.__file__)
print("cv2 version:", getattr(cv2, "__version__", "no version"))
print("Has imread:", hasattr(cv2, "imread"))

class VideoCreator(BasePlugin):
    """
    A plugin that creates a video from a sequence of images.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.input_dir = self.config.get('input_dir')
        self.output_path_str = self.config.get('output_path')
        self.fps = self.config.get('fps', 10)

    def run(self, context: dict) -> dict:
        super().run(context)

        if not self.input_dir or not self.output_path_str:
            self.logger.error("'input_dir' and 'output_path' must be provided in the config.")
            return context

        input_path = Path(self.input_dir)
        if not input_path.is_absolute():
            input_path = self.case_path / input_path

        output_video_path = Path(self.output_path_str)
        if not output_video_path.is_absolute():
            output_video_path = self.case_path / output_video_path

        # Cleanup existing video file
        if output_video_path.exists():
            self.logger.info(f"Cleaning up existing video file: {output_video_path}")
            output_video_path.unlink()

        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        image_files = sorted([f for f in input_path.glob('*.png')], key=lambda f: int(f.stem.split('_')[-1]))

        if not image_files:
            self.logger.warning(f"No PNG images found in {input_path}, skipping video creation.")
            return context

        self.logger.info(f"Found {len(image_files)} images in {input_path}.")

        # Read the first image to get the dimensions
        frame = cv2.imread(str(image_files[0]))
        height, width, layers = frame.shape

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        video = cv2.VideoWriter(str(output_video_path), fourcc, self.fps, (width, height))

        for image_file in image_files:
            video.write(cv2.imread(str(image_file)))

        video.release()
        self.logger.info(f"Successfully created video: {output_video_path}")

        return context