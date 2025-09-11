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

# 5. Architectural Evolution Plan (Phase 3 Refactoring)

Phase 2 of the refactoring has been completed successfully. All plugins now use the new `PluginContext` signature, and the `case.yaml` files have been updated to use the new `io_mapping` section. The end-to-end tests have been updated and are passing.

## Next Steps for Phase 3

With the successful completion of Phase 2, we can now plan the next steps for Phase 3 of the architectural evolution. The core goals for Phase 3 will be to further enhance modularity, robustness, and developer experience.

### Potential Areas for Improvement

1. **Enhanced Type Safety**: Implement more comprehensive type checking and validation mechanisms to catch errors at compile time rather than runtime.

2. **Improved Error Handling**: Develop a more sophisticated error handling system that provides detailed context and suggestions for resolving issues.

3. **Performance Optimization**: Optimize the framework's performance, especially for large datasets and complex pipelines.

4. **Extended Plugin Ecosystem**: Create a richer ecosystem of plugins and handlers to support a wider range of use cases.

5. **Advanced Configuration Management**: Implement advanced configuration management features such as configuration validation, versioning, and migration.

6. **Enhanced Testing Framework**: Develop a more comprehensive testing framework that includes unit tests, integration tests, and performance tests.

7. **Documentation and Tutorials**: Create comprehensive documentation and tutorials to help new users get started with the framework.

By focusing on these areas, we can continue to evolve the framework into a more powerful, flexible, and user-friendly tool for building data processing pipelines.