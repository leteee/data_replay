# 0. Guiding Principles
- **Language Protocol**: The AI assistant will use all languages for internal processing, provide responses in Chinese, and all file outputs must be in English.
- **Built on Best Practices**: From the high-level architecture to the low-level implementation, the project strictly follows industry-recognized mainstream best practices.
- **High Modularity & Flexibility**: The core of the framework is a pluggable, loosely coupled plugin architecture, pursuing ultimate flexibility and scalability.
- **Think Step by Step**: The AI assistant must employ a structured, step-by-step reasoning process for analysis and problem-solving.


# 2. Key Architectural Mechanisms (Refactoring in Progress)

This section delves into the internal workings of the framework's key components. The architecture is currently undergoing a refactoring to better support pure-function plugins and declarative I/O.

### I. Execution Core
- **`PipelineRunner`**: As the core engine, it orchestrates the entire run in a multi-stage process:
    1.  **Dependency Discovery**: The runner pre-scans the Pydantic `config_model` of each active plugin, discovering all fields annotated as `DataSource` (for inputs) and `DataSink` (for outputs).
    2.  **Configuration & Data Loading**: It instantiates the `ConfigManager` to merge all configuration layers, then initializes the `DataHub` to load all required data specified by `DataSource` annotations.
    3.  **Configuration Hydration**: For each plugin, the runner takes the final Pydantic config object and **replaces** any `DataSource` annotated fields with the actual data loaded from the `DataHub`.
    4.  **Execution**: It passes the fully “hydrated” and type-safe config object to the `PluginExecutor` for execution. The executor now captures the return value of the plugin.
    5.  **Result Handling (New)**: After the plugin executes, the runner checks for a `DataSink` annotation in the config. If found, it instructs the `DataHub` to write the plugin's return value to the destination specified by the `DataSink`.
- **`PluginExecutor`**: Its role is to receive a fully prepared `PluginContext`, execute the plugin function, and **return the result** to the `PipelineRunner`.

### II. Configuration Core
- **`ConfigManager`**: Acts as a run-specific, stateless **configuration calculator**. The lowest priority layer of its configuration is dynamically discovered from the `DataSource` annotations within each plugin's Pydantic `config_model`.

### III. Data Core
- **`DataHub`**: The central data exchange. It is responsible for both reading data from sources and **writing data to sinks**, orchestrated by the `PipelineRunner`.

### IV. Extensibility Subsystem
- **`@plugin` Decorator**: Used to register a function as a plugin. Its `default_config` parameter points to a Pydantic model, which is the **single source of truth** for declaring all of a plugin's parameters and I/O dependencies.
- **`DataSource` & `DataSink`**: These are annotation markers used within a plugin's `config_model` to declare I/O.
    - `Annotated[<type>, DataSource(path=...)]`: Declares a required **input**.
    - `Annotated[<type>, DataSink(path=...)]`: Declares a desired **output** destination for the plugin's return value.
- **`@handler` Decorator**: Used to register a class as a data handler for a specific file type, used by the `DataHub` for both reading and writing.

### V. Developer Experience & Tooling
- **Unified CLI (`data-replay`)**: A single, `Typer`-based command-line interface provides all framework interactions.

# 3. Feature Checklist

This checklist is used to record the core features that the project must support.

- **Pluggable Architecture**: Core business logic is implemented by independent, reusable plugins.
- **Pure-function Plugins**: Plugins are designed as pure data transformation functions that receive inputs via a config object and return a result, separating them from I/O operations.
- **Unified Dependency Declaration**: A plugin's Pydantic `config_model` serves as a single, unified “manifest” for all its dependencies, using `Annotated` types to declare both `DataSource` inputs and `DataSink` outputs.
- **Automated I/O**: The framework automatically discovers, loads, injects all `DataSource` dependencies, and writes the plugin's return value to the specified `DataSink`.
- **Minimal Plugin Signature**: Plugins require a minimal function signature (e.g., `(config, logger)`), with a single, defined return value if output is needed.
- **Layered Configuration**:
    - Supports multiple levels of configuration priority: **Command-line arguments > Case configuration > Global configuration > In-code `DataSource` declarations**.
    - Automatically resolves relative paths against the case directory.
- **Configuration Validation**: The Pydantic model provides automatic validation for all parameters.
- **Centralized Data Hub**: All data is exchanged through the `DataHub` for both reads and writes.
- **Extensible I/O Handlers**: `DataHub` supports reading and writing different data formats through pluggable `Handlers`.
- **Automatic Discovery**: The framework automatically discovers all plugins (`@plugin`) and handlers (`@handler`).
- **Plugin Enable/Disable**: Allows enabling or disabling individual plugins via `enable: true/false` in `case.yaml`.
- **Flexible Path Handling**:
    - All path configurations support both absolute and relative paths.
    - Relative paths are automatically resolved from the case directory by default.
- **End-to-End Testing**: The project includes a robust, `pytest`-based end-to-end test suite.

# 4. Refactoring Progress

This section tracks the progress of architectural refactoring.

### Phase 1 (Completed)
- [x] **Step 1: Define Core Types**. Create `src/nexus/core/plugin/typing.py` and define the `DataSource` and `DataSink` annotation classes.
- [x] **Step 2: Update Core Logic**.
    - [x] Modify `PipelineRunner` to discover `DataSource`/`DataSink` annotations.
    - [x] Modify `PipelineRunner` to handle plugin return values and orchestrate writing to the `DataSink`.
    - [x] Modify `PluginExecutor` to propagate the plugin's return value.
- [x] **Step 3: Refactor a Plugin**. Choose a representative plugin and update its `config_model` and function signature to use the new pure-function, declarative I/O pattern.
- [x] **Step 4: Update Handlers & DataHub**. Ensure `DataHub` and data handlers can be called for writing data, not just reading.
- [x] **Step 5: Update Tests**. Modify the `e2e_test.py` to validate the new, complete I/O roundtrip for the refactored plugin.

### Phase 2: Architectural Evolution (In Progress)
- [x] **Step 1: Define Core Types V2**. Redefine core types in `src/nexus/core/plugin/typing.py`.
    - [x] Introduce `PluginContext` to act as the universal execution environment for plugins.
    - [x] Modify `DataSource` and `DataSink` to use a logical `name` instead of a physical `path`, decoupling plugins from the filesystem.
- [x] **Step 2: Purify `ConfigManager`**. Remove all awareness of `DataSource`/`DataSink` from the configuration system, making it a pure, layered key-value store.
- [x] **Step 3: Evolve `PipelineRunner`**.
    - [x] Update `PipelineRunner` to orchestrate the new execution flow.
    - [x] Implement the "Pre-flight Check" for type safety by comparing plugin annotations against handler capabilities.
    - [x] Instead of "hydrating" configs, prepare and pass the `PluginContext` to the executor.
- [x] **Step 4: Enhance `DataHub` and `Handlers`**.
    - [x] Update `DataHub` to resolve logical `name`s via the `io_mapping` in the case config.
    - [x] Augment the `@handler` decorator or a base class to include a `produced_type` "contract".
- [ ] **Step 5: Refactor Plugins and Tests**.
    - [ ] Update all existing plugins to use the new `(context: PluginContext)` signature.
    - [ ] Update `case.yaml` files to use the new `io_mapping` section.
    - [ ] Update `e2e_test.py` to validate the new, fully-decoupled I/O and execution model.

# 5. Architectural Evolution Plan (Phase 2 Refactoring)

To further enhance modularity, robustness, and developer experience, a second phase of refactoring is planned. The core goal is to achieve a complete **separation of concerns** between **static configuration (Config)**, **dynamic data (Data)**, and **business logic (Logic)**.

### I. Step 1: Purify `ConfigManager`'s Role
The `ConfigManager` will be simplified to be a pure, stateless calculator for hierarchical configuration (CLI > Case > Global). It will no longer have any knowledge of `DataSource` or `DataSink`, making its responsibility singular and clear.

### II. Step 2: Introduce `PluginContext`
The "config hydration" pattern will be replaced. A new `PluginContext` class will be introduced as the sole argument to a plugin's execution function. This context object acts as a clean, organized container for the run.

- **Plugin Signature Change**:
    - **Before**: `def my_plugin(config: HydratedModel, logger: Logger)`
    - **After**: `def my_plugin(context: PluginContext)`
- **`PluginContext` Contents**:
    - `context.config`: The plugin's Pydantic `config_model` instance, containing only validated static parameters.
    - `context.data`: A dictionary-like accessor to the actual input data loaded by the `DataHub`.
    - `context.logger`: A pre-configured logger instance.

This change makes plugin testing trivial, as `config` and `data` can be mocked independently.

### III. Step 3: Decouple I/O with Logical Names
This is the most impactful change, designed to make plugins maximally reusable. `DataSource` and `DataSink` will be modified to refer to data by a **logical `name`** instead of a hardcoded `path`. The mapping from this logical name to a physical file path is defined within the `case.yaml` configuration.

- **Before: Tightly Coupled Declaration**
    ```python
    # In plugin code
    class MyConfig(BaseModel):
        input_data: Annotated[pd.DataFrame, DataSource(path="data/input.csv")]
    ```

- **After: Decoupled Declaration**
    ```python
    # In plugin code
    class MyConfig(BaseModel):
        input_data: Annotated[pd.DataFrame, DataSource(name="raw_events")]
        some_param: float
    ```
    ```yaml
    # In case.yaml
    io_mapping:
      raw_events:
        path: "case_specific_data/input.csv"
        handler: "csv"
      processed_events:
        path: "{output_dir}/final_result.parquet"

    plugins:
      my_plugin:
        enable: true
        config:
          some_param: 0.95
    ```

This turns `case.yaml` into a powerful "wiring" diagram for data pipelines, allowing the same plugin to be reused in different contexts without any code changes.

### IV. Robustness: Pre-flight Type Safety Check
To prevent runtime errors, the `PipelineRunner` will perform a "pre-flight check" before execution. It will validate that the data type produced by a `Handler` (e.g., `JsonHandler` produces a `dict`) matches the type expected by the plugin (e.g., `pd.DataFrame`).

This requires `Handlers` to declare their produced type, for example:
`@handler(file_type="csv", produced_type=pd.DataFrame)`

If a mismatch is detected, the framework will fail fast with a clear, actionable error message, pinpointing the exact location of the configuration error.