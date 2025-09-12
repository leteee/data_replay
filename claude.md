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
- **Unified Dependency Declaration**: A plugin's Pydantic `config_model` serves as a single, unified "manifest" for all its dependencies, using `Annotated` types to declare both `DataSource` inputs and `DataSink` outputs.
- **Automated I/O**: The framework automatically discovers, loads, injects all `DataSource` dependencies, and writes the plugin's return value to the specified `DataSink`.
- **Minimal Plugin Signature**: Plugins require a minimal function signature (e.g., `(context: PluginContext)`), with a single, defined return value if output is needed.
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
- **Logical I/O Names**: Plugins use logical names for I/O declarations instead of hardcoded file paths, allowing the same plugin to be reused in different contexts by simply re-wiring its inputs and outputs in the `case.yaml` file.
- **Pre-flight Type Safety Check**: The framework performs a pre-flight type check before execution to validate that the data type produced by a Handler matches the type expected by the plugin, preventing runtime errors.
- **Configurable Plugin and Handler Paths**: Plugins and handlers can be loaded from custom directories specified in the global configuration, supporting both relative and absolute paths.

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

### Phase 2: Architectural Evolution (Completed)
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
- [x] **Step 5: Refactor Plugins and Tests**.
    - [x] Update all existing plugins to use the new `(context: PluginContext)` signature.
    - [x] Update `case.yaml` files to use the new `io_mapping` section.
    - [x] Update `e2e_test.py` to validate the new, fully-decoupled I/O and execution model.

### Phase 3: Enhanced Type Safety (Completed)
- [x] **Step 1: Implement Pre-flight Type Checking**.
    - [x] Add `produced_type` attribute to all data handlers to declare their output types.
    - [x] Enhance the DataSource discovery mechanism to capture expected types from plugin annotations.
    - [x] Implement pre-flight type checks in the PipelineRunner to validate data types before execution.
- [x] **Step 2: Improve Error Handling**.
    - [x] The pre-flight type checks provide early detection of type mismatches.
    - [x] Clear warning messages are logged when type mismatches are detected.

With the successful completion of all three phases, the framework now has a robust architecture with:
1. Pure-function plugins using the PluginContext signature
2. Logical I/O names for better decoupling
3. Enhanced type safety with pre-flight checks

### Phase 4: Simplification and Architectural Reinforcement (Completed)

This phase focuses on cleaning up the existing implementation, reinforcing architectural principles, and improving the decoupling of plugins from the filesystem.

- [x] **Step 1: Code Cleanup**.
    - [x] Remove the duplicated `_discover_io_declarations` method in `pipeline_runner.py` to improve maintainability.
- [x] **Step 2: Reinforce Plugin Purity**.
    - [x] Refactor the `video_creator.py` plugin to better align with architectural principles.
    - [x] Remove hardcoded output paths from the plugin.
    - [x] The `PipelineRunner` now injects the final output path into the `PluginContext` before execution.
    - [x] The plugin now uses the path from the context to write its output, removing its dependency on the file system structure.
- [x] **Step 3: Simplify Core Components**.
    - [x] Review and simplify the `DataHub.get_path` method to ensure it has a single responsibility (returning a path) without triggering side effects.
- [x] **Step 4: Enhanced Plugin and Handler Discovery**.
    - [x] Add support for configurable plugin and handler paths in global configuration.
    - [x] Implement discovery of plugins and handlers from custom directories.
    - [x] Support both relative and absolute paths for plugin and handler directories.

## 5. New Feature: Configurable Plugin and Handler Paths

This feature allows users to load plugins and handlers from custom directories specified in the global configuration. This enhancement provides greater flexibility in organizing and managing custom plugins and handlers.

### Configuration

Users can specify custom plugin and handler paths in the `config/global.yaml` file:

```yaml
plugin_paths:
  - "./custom_plugins"
  - "/absolute/path/to/plugins"
  
handler_paths:
  - "./custom_handlers"
  - "/absolute/path/to/handlers"
```

### Benefits

1. **Flexibility**: Users can organize their custom plugins and handlers in separate directories
2. **Modularity**: Custom components can be developed and maintained independently
3. **Path Support**: Both relative and absolute paths are supported
4. **Backward Compatibility**: Existing configurations and functionality remain unaffected
