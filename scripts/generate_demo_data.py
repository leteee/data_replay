import os
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import shutil

# --- Configuration ---
NUM_FRAMES = 2000
FPS = 50
LATENCY_MS = 200

IMAGE_SIZE = (800, 600)

CASE_DIR = "cases/demo"
RAW_DATA_DIR = os.path.join(CASE_DIR, "raw_data")
INTERMEDIATE_DIR = os.path.join(CASE_DIR, "intermediate")
OUTPUT_DIR = os.path.join(CASE_DIR, "output")
FRAMES_DIR = os.path.join(RAW_DATA_DIR, "frames")

LATENT_CSV_PATH = os.path.join(RAW_DATA_DIR, "latent_measurements.csv")
MANIFEST_CSV_PATH = os.path.join(RAW_DATA_DIR, "video_manifest.csv")

def clean_data():
    """Removes all generated data and output directories."""
    for dir_path in [RAW_DATA_DIR, INTERMEDIATE_DIR, OUTPUT_DIR]:
        if os.path.isdir(dir_path):
            print(f"Cleaning up directory: {dir_path}")
            shutil.rmtree(dir_path)
    print("Cleanup complete.")

def generate_data():
    """
    Cleans old data and generates new, more realistic mock vehicle data.
    """
    clean_data()
    print("--- Starting demo data generation ---")
    os.makedirs(FRAMES_DIR, exist_ok=True)
    print(f"Created directory: {FRAMES_DIR}")

    # --- Generate Dynamic Ground Truth Trajectory (Smoother S-Curve) ---
    dt_s = 1.0 / FPS
    timestamps_s = np.arange(0, NUM_FRAMES * dt_s, dt_s)

    # Smoother speed profile: accelerate, cruise, decelerate
    speed_profile = np.concatenate([
        np.linspace(10, 30, NUM_FRAMES // 3),
        np.full(NUM_FRAMES // 3, 30),
        np.linspace(30, 20, NUM_FRAMES - 2 * (NUM_FRAMES // 3))
    ])

    # Smoother steering profile: simulate a lane change
    steering_profile_deg = 15 * np.sin(np.linspace(0, 2 * np.pi, NUM_FRAMES))

    # Calculate trajectory from profiles
    initial_pos = np.array([50.0, 300.0])
    positions = [initial_pos]
    directions_rad = [np.deg2rad(-10)]

    for i in range(1, NUM_FRAMES):
        # CTRV model for ground truth generation
        v = speed_profile[i-1]
        yaw = directions_rad[-1]
        yaw_rate = np.deg2rad(steering_profile_deg[i-1]) * 0.5 # Relate steering to yaw rate

        px, py = positions[-1]
        
        if abs(yaw_rate) > 1e-5:
            next_px = px + (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt_s) - np.sin(yaw))
            next_py = py + (v / yaw_rate) * (-np.cos(yaw + yaw_rate * dt_s) + np.cos(yaw))
        else: # Straight line
            next_px = px + v * dt_s * np.cos(yaw)
            next_py = py + v * dt_s * np.sin(yaw)

        next_yaw = yaw + yaw_rate * dt_s

        positions.append(np.array([next_px, next_py]))
        directions_rad.append(next_yaw)

    positions_arr = np.array(positions)

    ground_truth_df = pd.DataFrame({
        'timestamp': timestamps_s,
        'true_x': positions_arr[:, 0],
        'true_y': positions_arr[:, 1],
        'true_speed': speed_profile,
        'true_steering_angle': steering_profile_deg
    })

    # --- Generate Video Frames & Manifest ---
    manifest_data = []
    for i, row in ground_truth_df.iterrows():
        img = Image.new('RGB', IMAGE_SIZE, color='black')
        
        frame_path_rel = os.path.join("raw_data", "frames", f"{i:04d}.png")
        img.save(os.path.join(CASE_DIR, frame_path_rel))
        
        manifest_data.append({
            'timestamp': row['timestamp'], 'image_path': frame_path_rel,
            'true_x': row['true_x'], 'true_y': row['true_y']
        })

    pd.DataFrame(manifest_data).to_csv(MANIFEST_CSV_PATH, index=False, float_format='%.3f')
    print(f"Generated {NUM_FRAMES} frames and video manifest: {MANIFEST_CSV_PATH}")

    # --- Generate Latent Measurement Data ---
    latency_steps = int(LATENCY_MS / (dt_s * 1000))
    latent_df = ground_truth_df.copy()
    for col in ['true_x', 'true_y', 'true_speed', 'true_steering_angle']:
        new_col = col.replace('true_', '')
        if new_col == 'x' or new_col == 'y': new_col = col # Keep true_x/y for renderer
        latent_df[new_col] = latent_df[col].shift(latency_steps)
    
    latent_df.rename(columns={'true_x': 'x', 'true_y': 'y', 'true_speed': 'vehicle_speed', 'true_steering_angle': 'steering_wheel_angle'}, inplace=True)
    latent_df.dropna(inplace=True)
    
    latent_measurements_df = latent_df[['timestamp', 'x', 'y', 'vehicle_speed', 'steering_wheel_angle']]

    # Add noise to measurements to make the simulation more realistic
    noise_std_dev = 2.5 # pixels
    latent_measurements_df['x'] += np.random.normal(0, noise_std_dev, len(latent_measurements_df))
    latent_measurements_df['y'] += np.random.normal(0, noise_std_dev, len(latent_measurements_df))
    print(f"Added measurement noise with std dev: {noise_std_dev}")

    latent_measurements_df.to_csv(LATENT_CSV_PATH, index=False, float_format='%.3f')
    print(f"Generated latent measurements: {LATENT_CSV_PATH}")
    print("--- Demo data generation complete! ---")

if __name__ == "__main__":
    generate_data()