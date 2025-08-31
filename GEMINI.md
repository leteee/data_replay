# Project Overview

The project "Nexus" is an industrial-grade Python framework for building robust, extensible, and maintainable data processing pipelines. It emphasizes modularity, traceability, and configurability. Key features include a unified CLI (`run.py`), a pluggable architecture for processing steps (plugins), case templating, centralized data management via a `DataHub`, and a hierarchical configuration system. It uses a standard `src` layout.

# Building and Running

The project is run via a central `run.py` script. Dependencies are managed through `requirements.txt` and `pyproject.toml`.

*   **Installation:**
    ```bash
    pip install -r requirements.txt
    ```
*   **Running the CLI:**
    ```bash
    python run.py --help
    ```
*   **Creating a New Case from a Template:**
    ```bash
    python run.py pipeline --case <my_new_case> --template <template_name>
    ```
*   **Running an Existing Pipeline:**
    ```bash
    python run.py pipeline --case <my_existing_case>
    ```
*   **Generating Demo Data:**
    ```bash
    python run.py generate-data
    ```
*   **Generating Plugin Documentation:**
    ```bash
    python run.py generate-docs
    ```
*   **Running a Single Plugin:**
    ```bash
    python run.py plugin <PluginName> --case <case_name>
    ```
*   **Running End-to-End Tests:**
    ```bash
    python tests/e2e_test.py
    ```

# Development Conventions

*   **Project Structure:** Uses a `src` layout (`src/nexus/`).
*   **Plugins:** Processing logic is encapsulated in Python classes inheriting from `BasePlugin` (located in `src/nexus/plugins/`).
*   **Configuration:** Hierarchical configuration with `config/global.yaml` and `cases/<case_name>/case.yaml`.
*   **Data Management:** `DataHub` centralizes data handling.
*   **Imports:** Uses relative imports for intra-package modules.
*   **Dependency Management:** Uses `requirements.txt` for pinned dependencies, and `pyproject.toml` for top-level declarations.
