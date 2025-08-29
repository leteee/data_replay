# Data Replay Framework

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo/data-replay)

An industrial-grade Python framework for building robust, extensible, and maintainable data processing pipelines.

## Core Philosophy

This framework is designed from the ground up to support complex, multi-stage data processing tasks where traceability, configurability, and modularity are critical. It enforces a clean separation between the core orchestration logic, the individual processing steps (plugins), and the data itself.

## Key Features

- **Unified CLI**: A single, consistent entry point (`run.py`) for all project operations, from running pipelines to generating data and documentation.
- **Modular & Pluggable**: Encapsulate processing logic into standalone plugins. Easily extend the framework by adding new plugins without altering the core engine.
- **Case Templating**: Quickly scaffold new cases using predefined templates. Create a template once and reuse it to ensure consistency across multiple cases.
- **Centralized Data Management**: A powerful `DataHub` manages the lifecycle of all data, providing in-memory caching, lazy loading from disk, and automatic persistence.
- **Hierarchical Configuration**: A multi-layered configuration system combines global settings with case-specific parameters, allowing for flexible and reusable pipeline definitions.
- **Standalone & Pipeline Execution**: Plugins can be run for an entire pipeline or executed individually for debugging and testing.

## Project Structure

```
.
├── cases
│   └── ...
├── config
│   ├── global.yaml
│   └── logging.yaml
├── core
│   ├── config_manager.py
│   ├── data_hub.py
│   └── ...
├── modules
│   ├── base_plugin.py
│   └── ...
├── templates
│   └── demo_case.yaml
├── scripts
│   └── generation.py
├── .gitignore
├── run.py
└── README.md
```

## Usage: The Unified CLI

All interactions with the framework are handled through the central `run.py` script. You can see a full list of commands by running:
```bash
python run.py --help
```

### Running a Pipeline

To execute a full pipeline for a given case (e.g., `demo`):
```bash
python run.py pipeline --case demo
```

### Creating a New Case from a Template

You can easily create a new case using a template from the `templates` directory. For example, to create a new case named `my_new_case` using the `demo` template, run:

```bash
python run.py pipeline --case my_new_case --template demo
```

This command will:
1. Create the `cases/my_new_case/` directory if it doesn't exist.
2. Copy `templates/demo_case.yaml` to `cases/my_new_case/case.yaml`.
3. Execute the pipeline for `my_new_case`.

### Running a Single Plugin

For debugging or testing, you can run any plugin from a case in isolation. For example, to run only the `InitialDataReader` from the `demo` case:
```bash
python run.py plugin InitialDataReader --case demo
```

### Utility Commands

- **Generate Demo Data**: Cleans and regenerates all raw data for the demo case.
  ```bash
  python run.py generate-data
  ```

- **Generate Plugin Docs**: Scans all plugins and updates the `PLUGINS.md` reference file.
  ```bash
  python run.py generate-docs
  ```

## How It Works

### 1. The `case.yaml`

This file is the heart of a pipeline run. It can be created manually or generated from a template. It defines:
- **`data_sources`**: A catalog of all data "nouns" in the pipeline.
- **`pipeline`**: A list of the plugins (the "verbs") to execute in sequence.

### 2. The DataHub

The `DataHub` is a central object passed through the pipeline that manages all data.

### 3. Plugins

A plugin is a Python class that inherits from `BasePlugin` and implements the `run` method.

## Framework in Practice: The Demo Case

The `demo` case provides a concrete example of how the framework's components work together. Let's trace the execution step by step when you run `python run.py pipeline --case demo`.

1.  **Initiation**: The `main` function in `run.py` parses the `pipeline` command and calls the `run_pipeline` function, passing it the `demo` case name.

2.  **Configuration Loading**: The `PipelineRunner` initializes the `ConfigManager`, which loads and merges `global.yaml` and `cases/demo/case.yaml`.

3.  **DataHub Creation**: The `PipelineRunner` initializes the `DataHub`, populating its registry with the data sources defined in `case.yaml`.

4.  **Pipeline Execution**: The `PipelineRunner` iterates through the plugins defined in the `pipeline` section of `case.yaml`, executing each one in sequence.

5.  **Completion**: After the pipeline finishes, `run.py` prints a summary of the `DataHub`'s final state.

This walkthrough demonstrates the core principles: a declarative pipeline defined in YAML, orchestrated by the `PipelineRunner`, with all data flowing through and managed by the central `DataHub`.

## Future Development

- **Configuration Overrides**: Implement command-line overrides for case configuration values.
- **Data Quality Plugins**: Add a standard set of plugins for data validation and quality analysis.
- **Enhanced Plugin Discovery**: Improve the plugin loading mechanism to be more dynamic.
