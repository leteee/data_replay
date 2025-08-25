
import os
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw

# --- Configuration ---
NUM_FRAMES = 100
IMAGE_SIZE = (640, 480)
VEHICLE_SIZE = (50, 30)
OUTPUT_DIR = "cases/demo/raw_data"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
CSV_PATH = os.path.join(OUTPUT_DIR, "position.csv")

def generate_data():
    """
    Generates mock vehicle trajectory data (CSV) and corresponding video frames (images).
    """
    # --- Create output directories ---
    os.makedirs(FRAMES_DIR, exist_ok=True)
    print(f"Created directory: {FRAMES_DIR}")

    # --- Generate Trajectory Data ---
    # Simple linear trajectory from left to right
    timestamps = np.linspace(0, 10, NUM_FRAMES)
    start_x = 50
    end_x = IMAGE_SIZE[0] - 50 - VEHICLE_SIZE[0]
    x_coords = np.linspace(start_x, end_x, NUM_FRAMES)
    y_coord = IMAGE_SIZE[1] / 2

    df = pd.DataFrame({
        'timestamp': timestamps,
        'x': x_coords,
        'y': np.full(NUM_FRAMES, y_coord)
    })

    df.to_csv(CSV_PATH, index=False)
    print(f"Generated position data: {CSV_PATH}")

    # --- Generate Video Frames ---
    for i, row in df.iterrows():
        img = Image.new('RGB', IMAGE_SIZE, color = 'black')
        draw = ImageDraw.Draw(img)

        # Vehicle position
        x, y = row['x'], row['y']
        top_left = (x, y - VEHICLE_SIZE[1] / 2)
        bottom_right = (x + VEHICLE_SIZE[0], y + VEHICLE_SIZE[1] / 2)

        # Draw vehicle
        draw.rectangle([top_left, bottom_right], fill='white')

        # Save frame
        frame_path = os.path.join(FRAMES_DIR, f"{i:04d}.png")
        img.save(frame_path)

    print(f"Generated {NUM_FRAMES} frames in {FRAMES_DIR}")

if __name__ == "__main__":
    generate_data()
    print("--- Demo data generation complete! ---")

