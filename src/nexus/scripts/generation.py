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
NUM_FRAMES = 500
FPS = 30
LATENCY_MS = 200
IMAGE_SIZE = (1920, 1080)
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
    timestamps_s = np.linspace(0, (NUM_FRAMES - 1) * dt_s, NUM_FRAMES)
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
        'true_steering_angle': steering_profile_deg,
        'true_yaw_rad': directions_rad
    })

    manifest_data = []
    for i, row in ground_truth_df.iterrows():
        img = Image.new('RGB', IMAGE_SIZE, color='black')
        frame_path_rel = os.path.join("raw_data", "frames", f"{i:04d}.png")
        img.save(os.path.join(CASE_DIR, frame_path_rel))
        manifest_data.append({
            'timestamp': row['timestamp'], 'image_path': frame_path_rel,
            'true_x': row['true_x'], 'true_y': row['true_y'],
            'true_yaw_rad': row['true_yaw_rad'],
            'true_speed': row['true_speed']
        })

    pd.DataFrame(manifest_data).to_csv(MANIFEST_CSV_PATH, index=False, float_format='%.3f')
    print(f"Generated {NUM_FRAMES} frames and video manifest: {MANIFEST_CSV_PATH}")

    # --- Create Latent Data by Shifting Ground Truth ---
    latency_steps = int(LATENCY_MS / (dt_s * 1000))
    
    latent_measurements_df = pd.DataFrame()
    
    latent_measurements_df['timestamp'] = ground_truth_df['timestamp']
    latent_measurements_df['x'] = ground_truth_df['true_x'].shift(latency_steps)
    latent_measurements_df['y'] = ground_truth_df['true_y'].shift(latency_steps)
    latent_measurements_df['vehicle_speed'] = ground_truth_df['true_speed'].shift(latency_steps)
    latent_measurements_df['steering_wheel_angle'] = ground_truth_df['true_steering_angle'].shift(latency_steps)
    latent_measurements_df['yaw'] = ground_truth_df['true_yaw_rad'].shift(latency_steps)
    
    latent_measurements_df.dropna(inplace=True)
    
    # Add noise to the valid data by creating explicitly indexed Series
    noise_std_dev = 2.5
    
    noise_x = pd.Series(np.random.normal(0, noise_std_dev, len(latent_measurements_df)), index=latent_measurements_df.index)
    latent_measurements_df['x'] += noise_x

    noise_y = pd.Series(np.random.normal(0, noise_std_dev, len(latent_measurements_df)), index=latent_measurements_df.index)
    latent_measurements_df['y'] += noise_y

    noise_yaw = pd.Series(np.random.normal(0, np.deg2rad(1.0), len(latent_measurements_df)), index=latent_measurements_df.index)
    latent_measurements_df['yaw'] += noise_yaw

    print(f"Added measurement noise with std dev: {noise_std_dev}")

    latent_measurements_df.to_csv(LATENT_CSV_PATH, index=False, float_format='%.3f')
    print(f"Generated latent measurements: {LATENT_CSV_PATH}")
    print("--- Demo data generation complete! ---")
    
    # Copy the template case.yaml file to the demo case directory
    project_root = Path(__file__).parent.parent.parent.parent
    template_path = project_root / "templates" / "demo_case.yaml"
    case_yaml_path = Path(CASE_DIR) / "case.yaml"
    
    if template_path.exists():
        import shutil
        shutil.copy(template_path, case_yaml_path)
        print(f"Copied template to: {case_yaml_path}")
    else:
        print(f"Template file not found: {template_path}")


# --- Docs Generation (Refactored) ---

from nexus.core.plugin.decorator import PLUGIN_REGISTRY
from nexus.core.plugin.discovery import discover_plugins
from nexus.core.data.handlers.decorator import HANDLER_REGISTRY
from nexus.core.data.handlers.discovery import discover_handlers
from nexus.core.data.hub import DataHub
from nexus.core.context import PluginContext
from logging import Logger
from pydantic import BaseModel
import inspect
import yaml
from pathlib import Path

def _get_default_config(plugin_spec) -> dict:
    """Safely loads the default YAML config for a plugin."""
    try:
        plugin_module = inspect.getmodule(plugin_spec.func)
        if plugin_module and plugin_module.__file__:
            yaml_path = Path(plugin_module.__file__).with_suffix('.yaml')
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
    except Exception:
        return {}
    return {}

def _format_value(value):
    """Formats default values for display in Markdown."""
    if isinstance(value, str) and not value:
        return '""'
    if isinstance(value, list) and not value:
        return '[]'
    if isinstance(value, dict) and not value:
        return '{}'
    return f'`{value}`'

def generate_plugin_documentation():
    """
    Finds all plugins and handlers, extracts their info, and writes PLUGINS.md.
    This refactored version uses the decorator registries for discovery.
    """
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    output_file = project_root / 'REFERENCE.md'
    
    # 1. Discover everything
    import logging
    logger = logging.getLogger(__name__)
    
    global_config_path = project_root / "config" / "global.yaml"
    with open(global_config_path, 'r', encoding='utf-8') as f:
        global_config = yaml.safe_load(f)
    
    plugin_modules = global_config.get("plugin_modules", [])
    discover_plugins(plugin_modules, logger)
    discover_handlers(logger)

    # 2. Process Plugins
    md_content = """# Framework Reference

This document provides a reference for all available Plugins and Data Handlers in the framework.
It is auto-generated by `python run.py generate-docs`. Do not edit it manually.

---

"""
    
    md_content += "## Plugins\n\n"
    
    sorted_plugins = sorted(PLUGIN_REGISTRY.values(), key=lambda p: p.name)
    
    for spec in sorted_plugins:
        md_content += f"### {spec.name}\n\n"
        
        docstring = inspect.getdoc(spec.func)
        md_content += f"{docstring}\n\n" if docstring else "No description provided.\n\n"

        params = inspect.signature(spec.func).parameters
        default_config = _get_default_config(spec)
        
        # Injected Dependencies
        injected_params = [p for p in params.values() if p.annotation in [DataHub, Logger, Path, PluginContext]]
        if injected_params:
            md_content += "**Core Dependencies Injected:**\n"
            md_content += ", ".join([f'`{p.annotation.__name__}`' for p in injected_params])
            md_content += "\n\n"

        # Pydantic Config Model
        pydantic_models = [p for p in params.values() if isinstance(p.annotation, type) and issubclass(p.annotation, BaseModel)]
        if pydantic_models:
            model = pydantic_models[0].annotation
            md_content += "**Configuration Parameters (from Pydantic Model):**\n\n"
            md_content += "| Name | Type | Default | Description |\n"
            md_content += "|------|------|---------|-------------|\n"
            for field_name, field in model.model_fields.items():
                default_val = _format_value(field.default)
                description = field.description or ''
                md_content += f"| `{field_name}` | `{field.annotation.__name__}` | {default_val} | {description} |\n"
            md_content += "\n"
        else:
            # Fallback to simple config parameters if no Pydantic model
            config_params = [p for p in params.values() if p.annotation not in [DataHub, Logger, Path, PluginContext]]
            if config_params:
                md_content += "**Configuration Parameters:**\n\n"
                md_content += "| Name | Default Value (from .yaml) |\n"
                md_content += "|------|----------------------------|\n"
                for p in config_params:
                    default_val = _format_value(default_config.get(p.name, 'N/A'))
                    md_content += f"| `{p.name}` | {default_val} |\n"
                md_content += "\n"

    # 3. Process Handlers
    md_content += "---\n## Data Handlers\n\n"
    md_content += "Data Handlers are responsible for reading and writing different data formats.\n\n"
    md_content += "| Name | Supported Extensions | Description |\n"
    md_content += "|------|----------------------|-------------|\n"

    # Process registry to be one line per handler class
    processed_handlers = {}
    for key, handler_cls in HANDLER_REGISTRY.items():
        if handler_cls not in processed_handlers:
            processed_handlers[handler_cls] = {'name': 'N/A', 'extensions': []}
        
        if key.startswith('.'):
            processed_handlers[handler_cls]['extensions'].append(f'`{key}`')
        else:
            processed_handlers[handler_cls]['name'] = f'`{key}`'

    sorted_handlers = sorted(processed_handlers.items(), key=lambda item: item[1]['name'])

    for handler_cls, info in sorted_handlers:
        docstring = inspect.getdoc(handler_cls) or ""
        description = docstring.split('\n')[0] # First line of docstring
        extensions_str = ", ".join(sorted(info['extensions'])) or 'N/A'
        md_content += f"| {info['name']} | {extensions_str} | {description} |\n"

    # 4. Write file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Successfully generated framework reference at {output_file}")
