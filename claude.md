# 0. Guiding Principles
- **Language Protocol**: The AI assistant will use all languages for internal processing, provide responses in Chinese, and all file outputs must be in English.
- **Built on Best Practices**: From the high-level architecture to the low-level implementation, the project strictly follows industry-recognized mainstream best practices.
- **High Modularity & Flexibility**: The core of the framework is a pluggable, loosely coupled plugin architecture, pursuing ultimate flexibility and scalability.


# 2. Key Architectural Mechanisms

This section delves into the internal workings of the framework's key components.

### I. Execution Core
- **`PipelineRunner`**: As the core engine, it orchestrates the entire run. It discovers plugins and handlers, prepares the configuration by instantiating the `ConfigManager`, sets up the `DataHub`, and then executes each plugin in the sequence defined by `case.yaml`.
- **`PluginExecutor`**: Responsible for the lifecycle of a single plugin. It uses a **Resolver Chain** to perform dependency injection. This chain-of-responsibility pattern makes the injection logic for different types of dependencies (services, data, paths, configs) highly modular and extensible.
- **`PluginContext`**: A tailored context environment for each plugin, encapsulating `DataHub`, `Logger`, path information, and the final, effective configuration parameters for that plugin instance.

### II. Configuration Core
- **`ConfigManager`**: Acts as a run-specific, stateless **configuration calculator**. At the start of a pipeline run, the `PipelineRunner` instantiates it with all raw configuration sources (global config, case config, and all relevant plugin default configs). The `ConfigManager` then performs a deep merge to produce the two final, authoritative configuration objects for the run: the globally merged `data_sources` map for the `DataHub`, and the specific parameter map for each plugin instance.

### III. Data Core
- **`DataHub`**: The central data exchange, acting as an in-memory container for all data flowing through the pipeline. It provides plugins with a unified, abstract interface for data access, decoupling them from the underlying storage details.
- **I/O Abstraction via `Handlers`**: `DataHub` delegates I/O operations to a system of extensible `Handlers`. This mechanism separates the logical data identifier (e.g., "raw_telemetry") from the physical read/write logic (e.g., loading a specific CSV file). Handlers are discovered automatically via the `@handler` decorator, making the framework's I/O capabilities easy to extend.

### IV. Extensibility Subsystem
- **`@plugin` Decorator**: Used to register a function as a plugin. The framework automatically discovers all functions decorated with `@plugin` across specified modules.
- **`@handler` Decorator**: Used to register a class as a data handler. The framework automatically discovers all classes decorated with `@handler`, making it simple to add support for new file types.

# 3. Feature Checklist

This checklist is used to record the core features that the project must support, ensuring they are not overlooked in future refactoring.

- **Pluggable Architecture**: Core business logic is implemented by independent, reusable plugins.
- **Functional Plugins**: Supports creating plugins using a simple `@plugin` decorator without writing classes.
- **Unified `PluginContext`**: All plugins receive a `PluginContext` object containing core services and configuration during execution.
- **Dependency-Injected Execution**: Plugin function parameters are automatically injected via type hints, without manual retrieval.
- **Layered Configuration**:
    - Supports four levels of configuration priority: **Command-line arguments > Case configuration > Global configuration > Plugin default configuration**.
    - Automatically replaces dynamic variables (e.g., `{case_path}`) in the configuration.
- **Configuration Validation**: Plugins can use Pydantic models to automatically validate and convert their configuration.
- **Standalone Plugin Execution**: Any plugin can be run directly as a standalone script, separate from the full pipeline.
- **Centralized Data Hub**: All data is exchanged through the `DataHub`, achieving decoupling between plugins.
- **Extensible I/O Handlers**: `DataHub` supports reading and writing different data formats through pluggable `Handlers` registered with the `@handler` decorator.
- **Automatic Discovery**: The framework automatically discovers all plugins (`@plugin`) and handlers (`@handler`) in the project without manual registration.
- **Automatic Documentation Generation**: Provides a command-line tool that can automatically generate `PLUGINS.md` documentation for all plugins and handlers based on their docstrings, signatures, and default configurations.
- **Plugin Enable/Disable**: Allows enabling or disabling individual plugins via an `enable: true/false` switch in `case.yaml`.
- **Flexible Path Handling**: All path configurations in the project support both absolute and relative paths.
- **Case Templating**: Provides a command-line tool to quickly create new standardized cases from templates.
- **End-to-End Testing**: The project includes an end-to-end test to verify the correct coordination of the entire framework's core functions.
