# Data Replay Framework

A flexible and extensible Python framework for building complex data processing pipelines. This framework is designed for scenarios where data needs to be passed through a series of processing steps (plugins), with clear data management and configuration.

## Key Features

- **Pluggable Architecture**: Easily add new processing steps by creating new plugins.
- **Centralized Data Management (DataHub)**: A central `DataHub` manages all data within a pipeline run, handling in-memory data transfer, lazy loading from disk, and automatic persistence.
- **Hierarchical Configuration**: Combines global, case-specific, and command-line configurations.
- **Clear Data Provenance**: The `data_sources` section in the case configuration provides a clear and centralized catalog of all data, its source, and its destination.
- **Template-Based Case Management**: Reusable pipeline configurations can be stored as templates and copied to active case directories for execution.

## Project Structure

```
data_replay/
│
├───cases/              # Contains active case directories for specific runs.
│   └───demo/           # An example case directory.
│
├───config/             # Global configuration files.
│   ├───global.yaml
│   └───logging.yaml
│
├───core/               # Core framework components (PipelineRunner, DataHub, etc.).
│
├───logs/               # Log files are generated here.
│
├───modules/            # Contains all the reusable plugins.
│   ├───base_plugin.py
│   └───...
│
├───templates/          # Stores reusable case configuration templates.
│   └───car_tracking_case.yaml
│
├───demo_run.py         # Main entry point to run a pipeline.
└───README.md           # This file.
```

## How to Run a Case

1.  **Choose a Template**: Look inside the `templates/` directory for a suitable case template (e.g., `car_tracking_case.yaml`).
2.  **Set up the Case**: Copy the chosen template into a case directory (e.g., `cases/demo/`).
3.  **Rename the Template**: Rename the copied file to `case.yaml`.
4.  **Run the Pipeline**: Execute the `demo_run.py` script, pointing to the case directory.

   ```bash
   python demo_run.py --case cases/demo
   ```

## How to Create a Plugin

1.  **Create a Python file** in an appropriate subdirectory under `modules/`.
2.  **Create a class** that inherits from `BasePlugin`.
3.  **Implement the `__init__` method** to handle any specific configurations.
4.  **Implement the `run` method**. This is the core logic of your plugin. It receives the `DataHub` instance, which you can use to get and register data.

   ```python
   from modules.base_plugin import BasePlugin
   from core.data_hub import DataHub

   class MyNewPlugin(BasePlugin):
       def run(self, data_hub: DataHub):
           super().run(data_hub)

           # Get data from the DataHub
           input_data = data_hub.get("some_input_data")

           # ... your processing logic ...
           output_data = ...

           # Register your output data with the DataHub
           data_hub.register("my_output_data", output_data)
   ```

## Configuration (`case.yaml`)

A `case.yaml` file defines the entire pipeline for a specific run.

```yaml
case_name: "ExampleCase"

# 1. Define all data "nouns" of the pipeline
data_sources:
  raw_data:
    path: "path/to/initial_data.csv" # Source file for lazy loading
  processed_data:
    path: "intermediate/processed.parquet" # Destination file for auto-persistence

# 2. Define the pipeline steps (the "verbs")
pipeline:
  - plugin: InitialDataReader
    outputs: ["raw_data"] # Loads the data defined in data_sources

  - plugin: MyNewPlugin
    # The plugin's config can access these lists
    inputs: ["raw_data"]
    outputs: ["processed_data"]
    config:
      my_param: 42
```