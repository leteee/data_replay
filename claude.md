# 0. Guiding Principles
- **Language Protocol**: The AI assistant will use all languages for internal processing, provide responses in Chinese, and all file outputs must be in English.
- **Built on Best Practices**: From the high-level architecture to the low-level implementation, the project strictly follows industry-recognized mainstream best practices.
- **High Modularity & Flexibility**: The core of the framework is a pluggable, loosely coupled plugin architecture, pursuing ultimate flexibility and scalability.
- **Think Step by Step**: The AI assistant must employ a structured, step-by-step reasoning process for analysis and problem-solving.
- **Pythonic**: All code must follow Pythonic principles, emphasizing readability, simplicity, and the use of Python's idiomatic features.

# 1. Project Overview

Nexus Framework is a flexible, configuration-driven Python framework for building robust, extensible, and maintainable data processing pipelines. It is designed from the ground up with a focus on dependency injection, automatic discovery, and a declarative workflow.

The framework has undergone a comprehensive refactoring to simplify code structure, eliminate redundancy, enhance performance and maintainability, and improve Pythonic characteristics.

# 2. Key Architectural Mechanisms (Refactoring Completed)

This section delves into the internal workings of the framework's key components. The architecture has been successfully refactored to better support pure-function plugins and declarative I/O.

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

# 4. Refactoring Plan (2025-09-14) - COMPLETED

## I. Unify Configuration Management
✅ **Observation**: The project contained three conflicting configuration managers (`manager.py`, `simple_manager.py`, `enhanced_manager.py`), leading to redundancy, increased complexity, and deviation from the architectural blueprint which specifies a single, stateless "configuration calculator".

✅ **Plan**:
1.  **Consolidate**: Refactored all configuration logic into a single, authoritative `ConfigManager` within `src/nexus/core/config/manager.py`.
2.  **Integrate Features**: Merged useful functionalities, such as environment variable loading, from the redundant managers into the unified one.
3.  **Enforce Architecture**: The new `ConfigManager` was enhanced to handle the entire configuration loading and merging lifecycle, providing a single, clean factory method for the `PipelineRunner` to call. It strictly adheres to the documented priority order: CLI > Case > Global > Defaults/DataSource.
4.  **Eliminate Redundancy**: Once the unified manager was integrated, `simple_manager.py` and `enhanced_manager.py` were deleted.

## II. Simplify Exception Hierarchy
✅ **Observation**: The exception hierarchy in `src/nexus/core/exceptions.py` may be overly complex. There was an opportunity to reduce the number of custom exceptions and rely more on Python's built-in exceptions, making error handling more idiomatic.

✅ **Plan**:
1.  **Analyze**: Reviewed all custom exceptions in `exceptions.py` to identify candidates for replacement or consolidation.
2.  **Propose**: Formulated a new, flatter hierarchy. This likely involved a single base `NexusError` for framework-specific issues and replacing many custom exceptions with standard ones like `ValueError` or `KeyError`.
3.  **Implement**: Modified the `exceptions.py` file with the new structure.
4.  **Refactor Usages**: Searched the codebase for all `raise` and `except` clauses that use the old exceptions and updated them to the new, simplified ones.
5.  **Verify**: Ran the test suite continuously to ensure that error handling paths still function as expected.

## III. Enhance Dependency Injection Usage
✅ **Observation**: The DI container in `src/nexus/core/di/container.py` was powerful but not used sufficiently; some components still depended directly on concrete implementations.

✅ **Plan**:
1.  **Analyze**: Reviewed all components that could benefit from DI to identify candidates for refactoring.
2.  **Implement**: Added more service interfaces and adapters to the DI system.
3.  **Refactor Usages**: Modified components to use the DI container to resolve dependencies in more places.
4.  **Verify**: Ran the test suite to ensure that DI integration works correctly.

## IV. Separate Concerns into Independent Services
✅ **Observation**: The `PipelineRunner` class was too large and承担了太多职责.

✅ **Plan**:
1.  **Analyze**: Identified distinct responsibilities within `PipelineRunner`.
2.  **Implement**: Created dedicated service classes for these responsibilities:
    - `IODiscoveryService` to handle IO declaration discovery
    - `TypeChecker` to handle pre-flight type checking
    - `PluginExecutionService` to handle plugin execution
    - `ConfigurationService` to handle configuration-related operations
3.  **Refactor**: Modified `PipelineRunner` to delegate to these services.
4.  **Verify**: Ran the test suite to ensure that separation of concerns works correctly.

## V. Simplify Plugin Configuration Models
✅ **Observation**: Plugin configuration models could be more concise.

✅ **Plan**:
1.  **Analyze**: Reviewed existing plugin configuration models to identify common patterns.
2.  **Implement**: Provided simpler base classes to reduce boilerplate code:
    - `PluginConfig` base class that sets `model_config = {"arbitrary_types_allowed": True}` by default
3.  **Refactor**: Updated existing plugins to use the new base class.
4.  **Verify**: Ran the test suite to ensure that simplified models work correctly.

## VI. Performance Optimizations
✅ **Observation**: Some computationally intensive operations lacked caching, which could cause performance issues.

✅ **Plan**:
1.  **Analyze**: Identified slow operations that could benefit from caching.
2.  **Implement**: Added caching mechanisms:
    - Memory cache with TTL support for frequently accessed data
    - File cache for persistent caching
    - Batch processing utilities for handling large datasets
3.  **Refactor**: Applied caching to appropriate operations:
    - Configuration loading
    - Type hint resolution
    - Data processing operations
4.  **Verify**: Ran performance tests to ensure caching improves performance.

## VII. Maintainability Improvements
✅ **Observation**: The framework could benefit from better documentation and test coverage.

✅ **Plan**:
1.  **Analyze**: Reviewed existing documentation and tests to identify gaps.
2.  **Implement**: Improved documentation generation:
    - Enhanced `REFERENCE.md` generation to show detailed I/O information
    - Added data source and data sink details to plugin documentation
3.  **Add Unit Tests**: Added comprehensive unit tests for all core services and utilities:
    - Configuration service tests
    - IO discovery service tests
    - Plugin execution service tests
    - Type checker tests
    - Cache utility tests
    - Data processing utility tests
4.  **Improve Test Structure**: Organized tests into modular structure with clear separation of concerns.
5.  **Verify**: Ran the full test suite to ensure all tests pass.

## VIII. Code Quality Improvements

Based on a comprehensive analysis of the codebase, the following improvements were implemented:

### 1. Eliminate Duplicate Code

**Problem**: In `cli.py`, the `pipeline` and `plugin` commands had a lot of duplicate setup code.

**Solution**: Create a shared context setup function to reduce duplication.

### 2. Simplify PipelineRunner

**Problem**: The `PipelineRunner` class was too large and承担了太多职责.

**Solution**: Separate some responsibilities into dedicated service classes:
- Create `IODiscoveryService` to handle IO declaration discovery
- Create `TypeChecker` to handle pre-flight type checking
- Create `PluginExecutionService` to handle plugin execution

### 3. Improve Dependency Injection Usage

**Problem**: The DI container was powerful but not used sufficiently; some components still depended directly on concrete implementations.

**Solution**:
- Add more service interfaces and adapters
- Use the DI container to resolve dependencies in more places

### 4. Performance Optimizations

**Problem**: Some computationally intensive operations lacked caching, which may cause performance issues.

**Solution**:
- Add caching for configuration loading
- Add caching for path resolution

### 5. Maintainability Improvements

**Problem**: Plugin configuration models could be more concise.

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

## Phase 3: Performance Optimization (Completed)
1. ✅ Add caching mechanisms
2. ✅ Optimize data processing
3. ✅ Support batch operations

## Phase 4: Maintainability Improvements (Completed)
1. ✅ Improve documentation generation
2. ✅ Add unit tests
3. ✅ Improve test structure

# 6. Technical Implementation Highlights

## 1. Caching System
Implemented memory cache and file cache systems with TTL expiration mechanism:
```python
@memory_cache(ttl=60)  # Cache for 60 seconds
def expensive_function(x, y):
    return x + y
```

## 2. Batch Processing and Parallel Processing
Implemented batch processing and parallel processing in data processing utilities:
```python
# Batch process items
results = batch_process(
    items=large_item_list,
    process_func=expensive_operation,
    batch_size=100,
    n_workers=4
)
```

## 3. Plugin Configuration Simplification
Provided simplified base classes to reduce boilerplate code:
```python
from nexus.core.plugin.base import PluginConfig

class MyPluginConfig(PluginConfig):
    """Configuration model for My Plugin."""
    # No longer need model_config = {"arbitrary_types_allowed": True}
    # Base class has already set it
    
    measurements: Annotated[
        pd.DataFrame,
        DataSource(name="latent_measurements")
    ]
```

## 4. Enhanced Documentation Generation
Documentation generation now displays detailed data source and data sink information, making it easier for users to understand plugin I/O dependencies.

# 7. Test Results

All tests passed:
- **75 tests passed**
- **End-to-end tests**: Verified complete pipeline execution
- **Unit tests**: Comprehensive test coverage for all core services and utilities
- **Integration tests**: Verified dependency injection container and other core component integration

# 8. Performance Improvements

Performance was improved through:
1. **Caching mechanisms**: Reduced duplicate configuration loading and type hint resolution
2. **Batch processing**: Reduced function call overhead through batch operations
3. **Parallel processing**: Used parallel processing where applicable to leverage multi-core CPUs
4. **Lazy loading**: Optimized data loading to reduce memory usage

# 9. Architecture Improvements

## 1. Backward Compatibility Maintained
All changes maintained backward compatibility, allowing existing plugins and configurations to continue working without modification.

## 2. Loosely Coupled Pluggable Architecture
The framework continues to maintain a loosely coupled plugin architecture, with all core components easily replaceable through dependency injection.

## 3. Unified Configuration Management
Configuration priority correctly implemented: Command-line arguments > Case configuration > Global configuration > Plugin default configuration

# 10. Pythonic Principles

Throughout the refactoring process, we consistently followed Pythonic principles:

1. **Simplicity**: Code is as concise and clear as possible
2. **Readability**: Clear naming, intuitive structure
3. **Consistency**: Follows Python community best practices
4. **Elegance**: Uses Python's features and idioms
5. **Practicality**: Focuses on practical usage effectiveness

# 11. Conclusion

Through this comprehensive refactoring, the Nexus Framework is now:

1. **More Robust**: Improved error handling and exception management
2. **More Efficient**: Improved performance through caching and batch processing
3. **More Maintainable**: Improved maintainability through modularization and clear architecture
4. **More User-Friendly**: Improved usability through simplified APIs and enhanced documentation
5. **More Pythonic**: Follows Python's best practices and idioms

The framework is now ready to support more complex use cases and has established a solid foundation for future expansion and maintenance. All functionality has been thoroughly tested to ensure high quality and reliability.

This refactoring not only solved existing problems but also established a good foundation for the framework's long-term development, making it an ideal choice for building robust, scalable, and maintainable data processing pipelines.

# 12. Project Functionality Checklist

## Core Framework Features

### 1. Plugin System
- [x] Plugin registration via `@plugin` decorator
- [x] Pure-function plugin design
- [x] Plugin configuration via Pydantic models
- [x] Plugin execution with dependency injection
- [x] Plugin enable/disable functionality
- [x] Plugin-specific configuration parameters
- [x] Plugin return value handling
- [x] Plugin documentation generation

### 2. Data Handling
- [x] DataHub as central data exchange
- [x] Lazy loading of data sources
- [x] Automatic I/O handling
- [x] Data source registration and management
- [x] Data sink handling for plugin outputs
- [x] Type safety checks for data operations

### 3. Data Handlers
- [x] CSV handler for reading/writing CSV files
- [x] Parquet handler for reading/writing Parquet files
- [x] JSON handler for reading/writing JSON files
- [x] Directory handler for directory-based operations
- [x] File handler for direct file operations
- [x] Handler registration via `@handler` decorator
- [x] Automatic handler discovery
- [x] Extension-based handler selection

### 4. Configuration Management
- [x] Layered configuration system (CLI > Case > Global > Defaults)
- [x] YAML-based configuration files
- [x] Environment variable support
- [x] Configuration validation via Pydantic
- [x] Path resolution and handling
- [x] Plugin default configuration
- [x] Configuration merging and priority
- [x] Plugin-specific configuration filtering (only relevant fields passed to plugin models)

### 5. Dependency Injection
- [x] DI container for service management
- [x] Service registration and resolution
- [x] Multiple lifecycle modes (Singleton, Transient, Scoped)
- [x] Constructor-based dependency injection
- [x] Type-based service resolution
- [x] Factory function support
- [x] Core service registration (Logger, DataHub)

### 6. Exception Handling
- [x] Base framework exception (NexusError)
- [x] Context-aware error reporting
- [x] Exception chaining support
- [x] Global exception handler
- [x] Specific exception types for different error categories
- [x] Error context preservation
- [x] Detailed error logging

### 7. CLI Commands
- [x] Unified CLI interface via `data-replay` command
- [x] Pipeline execution command
- [x] Individual plugin execution command
- [x] Demo data generation command
- [x] Documentation generation command
- [x] Case template support
- [x] Command-line argument handling
- [x] Help and version information

### 8. Testing
- [x] End-to-end test suite
- [x] Unit tests for core components
- [x] Integration tests for framework components
- [x] Dependency testing
- [x] Performance benchmarking
- [x] DI container testing
- [x] Test fixtures and helpers

### 9. Utilities and Helpers
- [x] Batch processing utilities
- [x] Memory caching with TTL
- [x] Path resolution utilities
- [x] Type hint resolution
- [x] Configuration loading utilities
- [x] Logging initialization
- [x] Data processing helpers

### 10. Documentation
- [x] Auto-generated plugin reference
- [x] Data handler documentation
- [x] Plugin I/O documentation
- [x] Configuration parameter documentation
- [x] README with usage instructions
- [x] Code-level documentation
- [x] Architecture documentation

## Demo Plugins

### 1. Latency Compensator
- [x] Extended Kalman Filter implementation
- [x] Constant Turn Rate and Velocity model
- [x] Measurement data processing
- [x] Latency compensation calculations
- [x] State prediction algorithms
- [x] Configurable algorithm parameters
- [x] DataFrame-based data processing

### 2. Frame Renderer
- [x] Image frame generation
- [x] Data visualization
- [x] Coordinate transformation
- [x] Dynamic camera positioning
- [x] Grid rendering
- [x] Data point visualization
- [x] Batch processing support
- [x] Configurable rendering parameters

### 3. Video Creator
- [x] Video generation from image frames
- [x] Frame sequence processing
- [x] Video encoding
- [x] Configurable frame rate
- [x] File output handling
- [x] Error handling for video creation

## Performance Features
- [x] Memory caching with TTL expiration
- [x] Batch processing for large datasets
- [x] Parallel processing support
- [x] Lazy loading for data sources
- [x] Optimized configuration loading
- [x] Cached type hint resolution
- [x] Efficient data handling

## Maintainability Features
- [x] Modular architecture
- [x] Clear separation of concerns
- [x] Comprehensive test coverage
- [x] Auto-generated documentation
- [x] Consistent error handling
- [x] Pythonic code principles
- [x] Clear code documentation

# 13. Plugin Discovery and Path Support

## Plugin Discovery Mechanism

The framework supports flexible plugin discovery through multiple mechanisms:

### 1. Module-based Discovery
- Plugins can be organized as Python packages/modules
- Specified via `plugin_modules` in global configuration
- Automatically scanned using `pkgutil.walk_packages`

### 2. Path-based Discovery
- Plugins can be loaded from filesystem paths
- Supports both relative and absolute paths
- Specified via `plugin_paths` in global configuration
- Resolves relative paths against project root

### 3. Handler Discovery
- Data handlers are discovered similarly to plugins
- Supports custom handler paths via `handler_paths` configuration
- Built-in handlers are automatically loaded

## Path Support Features

### Relative Path Resolution
- All relative paths are resolved against the project root directory
- Consistent behavior across different execution contexts
- Clear and predictable path resolution

### Absolute Path Support
- Direct support for absolute filesystem paths
- No additional processing required for absolute paths
- Useful for external plugin/handler locations

### Configuration Integration
- Path resolution integrated into configuration management
- Works seamlessly with layered configuration system
- Supports CLI, case, and global configuration levels

# 14. Project Structure Reorganization Plan

## Current Structure Issues (Fixed)
1. Mixed responsibilities in `demo` directory (plugins + example data)
2. Unclear separation between framework code and user content
3. Inconsistent organization of templates and examples
4. Configuration issues passing all global config fields to plugin models

## Analysis of Mainstream Best Practices

After reviewing mainstream Python project structures (Django, Flask, FastAPI, etc.), the following patterns emerge:

1. **Framework code is organized within the src/ directory**
2. **Plugins and extensions are part of the framework package, not separate top-level directories**
3. **User content (cases, examples) is kept separate from framework code**
4. **Configuration files are in dedicated directories**
5. **Templates and documentation have clear locations**

## Recommended Structure Following Best Practices
```
D:\Projects\data_replay/
├── cases/                 # User cases and data (user content)
│   └── demo/              # Demo case with data
│       ├── case.yaml      # Case configuration
│       ├── raw_data/      # Input data for demo
│       └── output/        # Output directory for results
├── config/                # Framework configuration
│   └── global.yaml        # Global framework settings
├── logs/                  # Log files
├── src/
│   └── nexus/             # Core framework code
│       ├── __init__.py
│       ├── cli.py         # Command-line interface
│       ├── core/          # Core framework modules
│       │   ├── config/
│       │   ├── data/
│       │   ├── di/
│       │   ├── plugin/
│       │   ├── refactoring/
│       │   ├── services/
│       │   ├── utils/
│       │   └── ...
│       ├── plugins/       # Built-in plugins (part of framework package)
│       │   ├── __init__.py
│       │   ├── prediction/    # Prediction plugins
│       │   └── visualization/ # Visualization plugins
│       └── handlers/      # Built-in data handlers (part of framework package)
│           ├── __init__.py
│           └── ...        # Handler implementations
├── templates/             # Case templates
│   └── demo_case.yaml     # Demo case template
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example cases and usage (if needed)
├── README.md
├── pyproject.toml
└── claude.md
```

## Benefits of This Structure
1. **Follows mainstream Python packaging conventions**
2. **Keeps framework code within the src/ directory**
3. **Integrates plugins and handlers as part of the framework package**
4. **Separates user content (cases) from framework code**
5. **Maintains clear organization of templates and configuration**
6. **Provides a clean separation between framework internals and user content**
7. **Aligns with setuptools and pip packaging standards**

## Implementation Plan (Completed)
1. ✅ Move demo plugins from `demo/` to `src/nexus/plugins/`
2. ✅ Move data handlers from `src/nexus/core/data/handlers/` to `src/nexus/handlers/`
3. ✅ Keep user cases in `cases/` directory
4. ✅ Keep templates in `templates/` directory
5. ✅ Update import paths and configuration accordingly
6. ✅ Fixed configuration passing to prevent all global config fields from being passed to plugin models
7. ✅ Updated global configuration to only include `nexus.plugins` module and handler paths
8. ✅ Verified all functionality works correctly after reorganization