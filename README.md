# Nexus

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo/nexus)

**Nexus** is an industrial-grade Python framework for building robust, extensible, and maintainable data processing pipelines.

## Core Philosophy

This framework is designed from the ground up to support complex, multi-stage data processing tasks where traceability, configurability, and modularity are critical. It enforces a clean separation between the core orchestration logic, the individual processing steps (plugins), and the data itself.

## Key Features

- **Unified CLI**: A single, consistent entry point (`run.py`) for all project operations.
- **Modular & Pluggable**: Encapsulate processing logic into standalone plugins. Easily extend the framework by adding new plugins without altering the core engine.
- **Case Templating**: Quickly scaffold new cases using predefined templates.
- **Centralized Data Management**: A powerful `DataHub` manages the lifecycle of all data, providing in-memory caching, lazy loading, and automatic persistence.
- **Hierarchical Configuration**: A multi-layered configuration system for flexible and reusable pipeline definitions.
- **Modern Python Structure**: Uses the standard `src` layout for a clean and maintainable codebase.

## Project Structure

```
.
├── cases/
├── config/
├── logs/
├── templates/
├── src/
│   └── nexus/
│       ├── __init__.py
│       ├── core/
│       ├── modules/
│       └── scripts/
├── tests/
├── .gitignore
├── pyproject.toml
├── README.md
└── run.py
```

## Usage: The Unified CLI

All interactions with the framework are handled through the central `run.py` script.
```bash
python run.py --help
```

### Creating a New Case from a Template

To create a new case, use the `--template` argument. For example, to create `my_new_case` using the `demo` template, run:

```bash
python run.py pipeline --case my_new_case --template demo
```

This command will:
1. Create the `cases/my_new_case/` directory.
2. Copy `templates/demo_case.yaml` to `cases/my_new_case/case.yaml`.
3. Execute the pipeline for the new case.

### Running an Existing Pipeline

Once a case exists, you can run it without the `--template` argument:
```bash
python run.py pipeline --case my_new_case
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

- **Run a Single Plugin**: Executes a specific plugin from a case definition. This is useful for debugging or testing individual components.
  ```bash
  python run.py plugin <PluginName> --case <case_name>
  ```
  Replace `<PluginName>` with the exact class name of the plugin.
  Replace `<case_name>` with the name of the case directory (e.g., `demo`).

  **Examples using the `demo` case:**
  ```bash
  # Run the InitialDataReader plugin for the demo case
  python run.py plugin InitialDataReader --case demo

  # Run the LatencyCompensator plugin for the demo case
  python run.py plugin LatencyCompensator --case demo

  # Run the FrameRenderer plugin for the demo case
  python run.py plugin FrameRenderer --case demo

  # Run the VideoCreator plugin for the demo case
  python run.py plugin VideoCreator --case demo
  ```

## How It Works

### 1. The `case.yaml`

This file is the heart of a pipeline run, created from a template or manually. It defines:
- **`data_sources`**: A catalog of all data "nouns" in the pipeline.
- **`pipeline`**: A list of the plugins (the "verbs") to execute in sequence.

### 2. The DataHub

The `DataHub` is a central object passed through the pipeline that manages all data.

### 3. Plugins

A plugin is a Python class that inherits from `BasePlugin` and implements the `run` method. New plugins should be added to `src/nexus/plugins/`.

## Framework in Practice: The Demo Case

Let's trace the execution for `python run.py pipeline --case demo --template demo`.

1.  **Initiation**: The `main` function in `run.py` parses the command.

2.  **Templating**: The script sees the `--template demo` argument and copies `templates/demo_case.yaml` to `cases/demo/case.yaml`.

3.  **Configuration Loading**: The `PipelineRunner` initializes the `ConfigManager`, which loads and merges `global.yaml` and the newly created `cases/demo/case.yaml`.

4.  **DataHub Creation**: The `PipelineRunner` initializes the `DataHub` with the data sources defined in the case file.

5.  **Pipeline Execution**: The `PipelineRunner` iterates through the plugins defined in the `pipeline` section, executing each one in sequence.

6.  **Completion**: After the pipeline finishes, `run.py` prints a summary of the `DataHub`'s final state.

## Future Development

- **Configuration Overrides**: Implement command-line overrides for case configuration values.
- **Data Quality Plugins**: Add a standard set of plugins for data validation and quality analysis.
- **Enhanced Plugin Discovery**: Improve the plugin loading mechanism to be more dynamic.