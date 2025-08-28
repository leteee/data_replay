import os
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import shutil
import ast
import importlib
import inspect
from pathlib import Path
import yaml

# --- Data Generation ---

# Configuration
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

    dt_s = 1.0 / FPS
    timestamps_s = np.arange(0, NUM_FRAMES * dt_s, dt_s)
    speed_profile = np.concatenate([
        np.linspace(10, 30, NUM_FRAMES // 3),
        np.full(NUM_FRAMES // 3, 30),
        np.linspace(30, 20, NUM_FRAMES - 2 * (NUM_FRAMES // 3))
    ])
    steering_profile_deg = 15 * np.sin(np.linspace(0, 2 * np.pi, NUM_FRAMES))

    initial_pos = np.array([50.0, 300.0])
    positions = [initial_pos]
    directions_rad = [np.deg2rad(-10)]

    for i in range(1, NUM_FRAMES):
        v = speed_profile[i-1]
        yaw = directions_rad[-1]
        yaw_rate = np.deg2rad(steering_profile_deg[i-1]) * 0.5
        px, py = positions[-1]
        if abs(yaw_rate) > 1e-5:
            next_px = px + (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt_s) - np.sin(yaw))
            next_py = py + (v / yaw_rate) * (-np.cos(yaw + yaw_rate * dt_s) + np.cos(yaw))
        else:
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

    latency_steps = int(LATENCY_MS / (dt_s * 1000))
    latent_df = ground_truth_df.copy()
    for col in ['true_x', 'true_y', 'true_speed', 'true_steering_angle']:
        new_col = col.replace('true_', '')
        if new_col == 'x' or new_col == 'y': new_col = col
        latent_df[new_col] = latent_df[col].shift(latency_steps)
    
    latent_df.rename(columns={'true_x': 'x', 'true_y': 'y', 'true_speed': 'vehicle_speed', 'true_steering_angle': 'steering_wheel_angle'}, inplace=True)
    latent_df.dropna(inplace=True)
    latent_measurements_df = latent_df[['timestamp', 'x', 'y', 'vehicle_speed', 'steering_wheel_angle']]

    noise_std_dev = 2.5
    latent_measurements_df['x'] += np.random.normal(0, noise_std_dev, len(latent_measurements_df))
    latent_measurements_df['y'] += np.random.normal(0, noise_std_dev, len(latent_measurements_df))
    print(f"Added measurement noise with std dev: {noise_std_dev}")

    latent_measurements_df.to_csv(LATENT_CSV_PATH, index=False, float_format='%.3f')
    print(f"Generated latent measurements: {LATENT_CSV_PATH}")
    print("--- Demo data generation complete! ---")


# --- Docs Generation ---

def get_plugin_info(plugin_py_file: Path, project_root: Path):
    """
    Extracts information about a plugin from its source file and YAML config.
    """
    module_path = str(plugin_py_file.relative_to(project_root)).replace('\\', '.').replace('/', '.')[:-3]
    
    with open(plugin_py_file, 'r', encoding='utf-8') as f:
        source = f.read()
        tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_plugin = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'BasePlugin':
                    is_plugin = True
                    break
            
            if is_plugin:
                class_name = node.name
                docstring = ast.get_docstring(node) or "No description provided."
                
                yaml_path = plugin_py_file.with_suffix('.yaml')
                params = []
                if yaml_path.exists():
                    with open(yaml_path, 'r', encoding='utf-8') as yf:
                        config_data = yaml.safe_load(yf)
                        yf.seek(0)
                        lines = yf.readlines()
                        param_comments = {}
                        for i, line in enumerate(lines):
                            if '#' in line and i > 0:
                                key_line = lines[i-1]
                                key = key_line.split(':')[0].strip()
                                comment = line.split('#', 1)[1].strip()
                                if key:
                                    param_comments[key] = comment

                        if config_data:
                            for key, value in config_data.items():
                                params.append({
                                    "name": key,
                                    "default": value,
                                    "description": param_comments.get(key, "No description.")
                                })

                return {
                    "name": class_name,
                    "description": docstring,
                    "parameters": params,
                    "module_path": module_path
                }
    return None

def generate_plugin_documentation():
    """
    Finds all plugins, extracts their info, and writes PLUGINS.md.
    """
    project_root = Path(__file__).parent.parent
    modules_dir = project_root / 'modules'
    output_file = project_root / 'PLUGINS.md'

    plugin_files = list(modules_dir.glob('**/*.py'))
    
    all_plugins_info = []
    for py_file in plugin_files:
        if py_file.name in ['__init__.py', 'base_plugin.py', 'datahub.py']:
            continue
        
        info = get_plugin_info(py_file, project_root)
        if info:
            all_plugins_info.append(info)

    all_plugins_info.sort(key=lambda x: x['name'])

    md_content = "# Plugin Reference\n\n"
    md_content += "This document provides a reference for all available plugins in the framework.\n\n"
    md_content += "It is auto-generated by `run.py generate-docs`. Do not edit it manually.\n\n"
    md_content += "---\n\n"

    for info in all_plugins_info:
        md_content += f"## {info['name']}\n\n"
        md_content += f"**Module:** `{info['module_path']}`\n\n"
        md_content += f"{info['description']}\n\n"
        
        if info['parameters']:
            md_content += "### Parameters\n\n"
            md_content += "| Name | Default Value | Description |\n"
            md_content += "|------|---------------|-------------|\n"
            for param in info['parameters']:
                md_content += f"| `{param['name']}` | `{param['default']}` | {param['description']} |\n"
        else:
            md_content += "This plugin has no configurable parameters.\n"
        
        md_content += "\n---\n\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Successfully generated plugin documentation at {output_file}")