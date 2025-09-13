"""
Example demonstrating the enhanced configuration management system.
"""

import os
import tempfile
from pathlib import Path

from nexus.core.config.enhanced_manager import EnhancedConfigManager, create_enhanced_config_manager


def main():
    """Demonstrate the enhanced configuration management system."""
    print("=== Enhanced Configuration Management Example ===\n")
    
    # Create a temporary directory structure for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        case_path = project_root / "my_case"
        case_path.mkdir(exist_ok=True)
        
        # Create directory structure
        config_dir = project_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create global configuration
        global_config_path = config_dir / "global.yaml"
        global_config_path.write_text("""
# Global configuration for the Nexus framework
cases_root: "./cases"
log_level: "INFO"
log_file: "./logs/nexus.log"

# Plugin configuration
plugin_enable: true
plugin_modules:
  - "demo"
plugin_paths:
  - "./custom_plugins"
handler_paths:
  - "./custom_handlers"

# Additional global settings
max_workers: 4
cache_enabled: true
""")
        
        # Create case configuration
        case_config_path = case_path / "case.yaml"
        case_config_path.write_text("""
# Case-specific configuration
case_name: "temperature_analysis"
description: "Analyzing temperature data with machine learning"

# I/O Mapping
io_mapping:
  raw_temperature_data:
    path: "input/temperature.csv"
    handler: "csv"
  processed_data:
    path: "intermediate/processed.parquet"
    handler: "parquet"
  ml_model:
    path: "models/temperature_model.pkl"
    handler: "pickle"
  analysis_results:
    path: "output/analysis_report.pdf"
    handler: "pdf"

# Pipeline configuration
pipeline:
  - plugin: "Data Preprocessor"
    enable: true
    config:
      filter_threshold: 0.95
      smoothing_window: 5
      
  - plugin: "ML Trainer"
    enable: true
    config:
      model_type: "random_forest"
      n_estimators: 100
      random_state: 42
      
  - plugin: "Report Generator"
    enable: true
    config:
      report_title: "Temperature Analysis Report"
      include_charts: true
""")
        
        print("1. Creating enhanced configuration manager...")
        config_manager = EnhancedConfigManager(project_root, case_path)
        
        print("   [PASS] Configuration manager created successfully\n")
        
        print("2. Demonstrating configuration access...")
        
        # Access simple configuration values
        log_level = config_manager.get("log_level")
        print(f"   Log level: {log_level}")
        
        plugin_enable = config_manager.get("plugin_enable")
        print(f"   Plugins enabled: {plugin_enable}")
        
        max_workers = config_manager.get("max_workers")
        print(f"   Max workers: {max_workers}")
        
        # Access list configuration values
        plugin_modules = config_manager.get("plugin_modules", [])
        print(f"   Plugin modules: {plugin_modules}")
        
        # Access nested configuration values
        pipeline = config_manager.get("pipeline", [])
        print(f"   Pipeline steps: {len(pipeline)}")
        for i, step in enumerate(pipeline):
            print(f"     {i+1}. {step.get('plugin', 'Unknown')} (enabled: {step.get('enable', False)})")
        
        print("\n3. Demonstrating environment variable override...")
        
        # Set environment variables to override configuration
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["MAX_WORKERS"] = "8"
        os.environ["PLUGIN_MODULES"] = "demo,custom_module"
        
        print("   Environment variables set:")
        print("     LOG_LEVEL=DEBUG")
        print("     MAX_WORKERS=8")
        print("     PLUGIN_MODULES=demo,custom_module")
        
        # Reload configuration to pick up environment changes
        config_manager.reload()
        
        print("   Configuration reloaded with environment variables\n")
        
        # Verify environment variable overrides
        log_level_env = config_manager.get("log_level")
        print(f"   Log level (from env): {log_level_env}")
        
        max_workers_env = config_manager.get("max_workers")
        print(f"   Max workers (from env): {max_workers_env}")
        
        plugin_modules_env = config_manager.get("plugin_modules", [])
        print(f"   Plugin modules (from env): {plugin_modules_env}")
        
        print("\n4. Demonstrating command-line argument override...")
        
        # Simulate command-line arguments
        cli_args = {
            "log_level": "WARNING",
            "custom_experiment": True,
            "experiment_name": "temperature_optimization"
        }
        
        config_manager.set_cli_config(cli_args)
        
        print("   Command-line arguments set:")
        for key, value in cli_args.items():
            print(f"     {key}={value}")
        
        # Verify CLI overrides
        log_level_cli = config_manager.get("log_level")
        print(f"   Log level (from CLI): {log_level_cli}")
        
        experiment_flag = config_manager.get("custom_experiment")
        print(f"   Custom experiment flag: {experiment_flag}")
        
        experiment_name = config_manager.get("experiment_name")
        print(f"   Experiment name: {experiment_name}")
        
        print("\n5. Demonstrating configuration validation...")
        
        # Validate configuration
        is_valid = config_manager.validate_config()
        print(f"   Configuration is valid: {is_valid}")
        
        print("\n6. Demonstrating getting all configuration...")
        
        # Get all configuration values
        all_config = config_manager.get_all()
        print(f"   Total configuration keys: {len(all_config)}")
        print(f"   Sample keys: {list(all_config.keys())[:5]}")
        
        print("\n7. Demonstrating factory function...")
        
        # Use factory function
        factory_args = {"deployment_mode": "production"}
        factory_manager = create_enhanced_config_manager(
            project_root, case_path, factory_args
        )
        
        deployment_mode = factory_manager.get("deployment_mode")
        print(f"   Deployment mode (from factory): {deployment_mode}")
        
        # Clean up environment variables
        env_vars_to_clean = ["LOG_LEVEL", "MAX_WORKERS", "PLUGIN_MODULES"]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
    
    print("\n=== Demonstration Complete ===")
    print("\nKey Benefits of Enhanced Configuration Management:")
    print("[PASS] Multiple configuration sources (defaults, files, environment, CLI)")
    print("[PASS] Automatic configuration merging with proper precedence")
    print("[PASS] Runtime configuration reloading")
    print("[PASS] Flexible configuration access (simple values, lists, nested structures)")
    print("[PASS] Environment variable support with type conversion")
    print("[PASS] Configuration validation")
    print("[PASS] Easy integration with existing code")


if __name__ == "__main__":
    main()