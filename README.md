# Data Replay & Processing Framework

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo/nexus)

A flexible, configuration-driven Python framework for building robust, extensible, and maintainable data processing pipelines. It is designed from the ground up with a focus on dependency injection, automatic discovery, and a declarative workflow.

## Key Features

- **Declarative Pipelines**: Define complex, multi-stage workflows in simple and readable `YAML` files.
- **Functional & Pluggable**: Write plugins as simple, decorated Python functions (`@plugin`). No boilerplate classes needed.
- **Automatic Dependency Injection**: Framework services (`DataHub`, `Logger`), data objects, paths, and configuration parameters are automatically injected into your plugin functions based on type hints and parameter names.
- **Centralized Data Management**: A powerful `DataHub` manages the lifecycle of all data, providing lazy loading and automatic I/O handling.
- **Extensible I/O Handlers**: Add support for new data formats by creating simple, decorated `DataHandler` classes (`@handler`).
- **Hierarchical Configuration**: A multi-layered configuration system (Plugin Default < Global < Case) provides maximum flexibility and reusability.
- **Automatic Discovery**: Plugins and Handlers are discovered automatically by the framework. No manual registration required.
- **Auto-Generated Documentation**: A command-line tool to generate a complete reference for all plugins and handlers.

## Project Structure

```
.
├── cases/                # Contains different data processing cases (e.g., demo).
├── config/               # Global framework configuration.
├── logs/                 # Directory for log files.
├── src/
│   └── demo/             # Source code for the demo plugins.
│   └── nexus/            # Core framework source code.
├── templates/            # Templates for generating new cases.
├── tests/
├── .gitignore
├── REFERENCE.md          # Auto-generated reference for all plugins and handlers.
├── README.md
└── pyproject.toml        # Project configuration and dependencies.
```

## Getting Started

### Prerequisites
- Python 3.10+

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <repository-name>
   ```

2. Install the project in editable mode. This will install all dependencies and make the `data-replay` command available in your environment.
   ```bash
   pip install -e .
   ```

## Usage: The Unified CLI

All interactions with the framework are handled through the central `data-replay` command.

### 1. Generate Demo Data

First, generate the sample data required to run the demo case.

```bash
data-replay generate-data
```

### 2. Run a Pipeline

Execute the entire pipeline for a given case. 

```bash
# Run the demo pipeline
data-replay pipeline --case demo
```

### 3. Run a Single Plugin

Execute a specific plugin from a case definition. This is useful for debugging or testing individual components. The framework will set up the full context required to run just that plugin.

```bash
# Example: Run only the "Frame Renderer" plugin for the demo case
data-replay plugin "Latency Compensator" --case demo
data-replay plugin "Frame Renderer" --case demo
data-replay plugin "Video Creator" --case demo
```

### 4. Generate Documentation

Scan all registered plugins and handlers and update the `REFERENCE.md` file.

```bash
data-replay docs
```

## Testing

The project includes a robust end-to-end test suite built with `pytest` to ensure all core functionalities are working as expected. These tests cover data generation, full pipeline execution, individual plugin runs, and documentation generation.

To run the entire test suite, navigate to the project root and execute:

```bash
pytest tests/e2e_test.py
```

This will automatically generate necessary demo data and clean up the environment before and after the tests.

## Core Concepts

### `case.yaml`

This file is the heart of a pipeline run. It defines two key sections:

- **`data_sources`**: A catalog of all data "nouns" in the pipeline. It maps a logical name (e.g., `predicted_states`) to a physical path and an optional handler, allowing the framework to manage I/O.
- **`pipeline`**: A list of the plugins (the "verbs") to execute in sequence. You can enable/disable plugins and override their default parameters here.

*Example snippet from `cases/demo/case.yaml`.*
```yaml
pipeline:
  # The first plugin in the demo compensates for latency.
  - plugin: "Latency Compensator"
    config:
      latency_to_compensate_s: 0.2

  # The next plugin renders the results into image frames.
  - plugin: "Frame Renderer"
    config:
      zoom_factor: 5
```

### Plugins (`@plugin`)
A plugin is a simple Python function decorated with `@plugin`. It defines the logic for a single processing step. Its parameters are automatically supplied by the dependency injection system.

*Example Plugin Signature:*
```python
from nexus.core.plugin.decorator import plugin
from logging import Logger
import pandas as pd

@plugin(name="My Awesome Plugin")
def my_plugin(
    raw_data: pd.DataFrame,  # Injected from DataHub by name
    logger: Logger,          # Core service injected by type
    some_parameter: int      # Injected from config
) -> pd.DataFrame:
    # ... your logic here ...
    logger.info(f"Processing with some_parameter = {some_parameter}")
    return raw_data.copy() # The return value is stored in DataHub
```

### Handlers (`@handler`)
A Handler is a class decorated with `@handler` that teaches the `DataHub` how to read and write a specific data format (e.g., `.csv`, `.parquet`, `.json`). The framework automatically discovers them, making it easy to add support for new file types.

```
