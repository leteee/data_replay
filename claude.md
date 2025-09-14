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
    4.  **Execution**: It passes the fully "hydrated" and type-safe config object to the `PluginExecutor` for execution. The executor now captures the return value of the plugin.
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

# 4. Refactoring Plan (2025-09-14)

## I. Unify Configuration Management

**Observation**: The project currently contains three conflicting configuration managers (`manager.py`, `simple_manager.py`, `enhanced_manager.py`), leading to redundancy, increased complexity, and deviation from the architectural blueprint which specifies a single, stateless "configuration calculator".

**Plan**:
1.  **Consolidate**: Refactor all configuration logic into a single, authoritative `ConfigManager` within `src/nexus/core/config/manager.py`.
2.  **Integrate Features**: Merge useful functionalities, such as environment variable loading, from the redundant managers into the unified one.
3.  **Enforce Architecture**: The new `ConfigManager` will be enhanced to handle the entire configuration loading and merging lifecycle, providing a single, clean factory method for the `PipelineRunner` to call. It will strictly adhere to the documented priority order: CLI > Case > Global > Defaults/DataSource.
4.  **Eliminate Redundancy**: Once the unified manager is integrated, `simple_manager.py` and `enhanced_manager.py` will be deleted.

## II. Consolidate Configuration Processing Logic

**Observation**: The file `src/nexus/core/config/processor.py` contains outdated and duplicated configuration logic that is inconsistent with the unified `ConfigManager` and the main `PipelineRunner` flow.

**Plan**:
1.  **Analyze Callers**: Identify all parts of the codebase that import and use functions from `processor.py`.
2.  **Refactor Callers**: Modify the identified code to use the authoritative, unified `ConfigManager` directly, instead of relying on the outdated logic in `processor.py`.
3.  **Eliminate Redundancy**: Once all dependencies on `processor.py` are removed, the file will be deleted to eliminate the duplicated logic permanently.
4.  **Verify**: Run the full test suite after each major change to ensure no regressions are introduced.

## III. Simplify Exception Hierarchy

**Observation**: The exception hierarchy in `src/nexus/core/exceptions.py` may be overly complex. There is an opportunity to reduce the number of custom exceptions and rely more on Python's built-in exceptions, making error handling more idiomatic.

**Plan**:
1.  **Analyze**: Review all custom exceptions in `exceptions.py` to identify candidates for replacement or consolidation.
2.  **Propose**: Formulate a new, flatter hierarchy. This will likely involve a single base `NexusError` for framework-specific issues and replacing many custom exceptions with standard ones like `ValueError` or `KeyError`.
3.  **Implement**: Modify the `exceptions.py` file with the new structure.
4.  **Refactor Usages**: Search the codebase for all `raise` and `except` clauses that use the old exceptions and update them to the new, simplified ones.
5.  **Verify**: Run the test suite continuously to ensure that error handling paths still function as expected.

## IV. Code Quality Improvements

Based on a comprehensive analysis of the codebase, the following improvements are recommended:

### 1. Eliminate Duplicate Code

**Problem**: In `cli.py`, the `pipeline` and `plugin` commands have a lot of duplicate setup code.

**Solution**: Create a shared context setup function to reduce duplication.

### 2. Simplify PipelineRunner

**Problem**: The `PipelineRunner` class is too large and承担了太多职责.

**Solution**: Separate some responsibilities into dedicated service classes:
- Create `IODiscoveryService` to handle IO declaration discovery
- Create `TypeChecker` to handle pre-flight type checking
- Create `PluginExecutionService` to handle plugin execution

### 3. Improve Dependency Injection Usage

**Problem**: The DI container is powerful but not used sufficiently; some components still depend directly on concrete implementations.

**Solution**:
- Add more service interfaces and adapters
- Use the DI container to resolve dependencies in more places

### 4. Performance Optimizations

**Problem**: Some computationally intensive operations lack caching, which may cause performance issues.

**Solution**:
- Add caching for configuration loading
- Add caching for path resolution

### 5. Maintainability Improvements

**Problem**: Plugin configuration models can be more concise.

**Solution**:
- Provide simpler base classes
- Reduce boilerplate code

# 5. Implementation Plan

## Phase 1: Code Quality Improvements (Completed)
1. ✅ Eliminate duplicate code in CLI commands
2. ✅ Simplify PipelineRunner class by extracting services
3. ✅ Improve exception handling consistency

## Phase 2: Architecture Optimization (Completed)
1. ✅ Enhance dependency injection usage
2. ✅ Separate concerns into independent services
3. ✅ Simplify plugin configuration models

## Phase 3: Performance Optimization (In Progress)
1. ✅ Add caching mechanisms
2. ✅ Optimize data processing
3. ⬤ Support batch operations

## Phase 4: Maintainability Improvements
1. Improve documentation generation
2. Add unit tests
3. Improve test structure