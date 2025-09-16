import importlib
import pkgutil
import sys
from logging import Logger
from typing import List
from pathlib import Path

def discover_plugins(plugin_modules: List[str], logger: Logger, project_root: Path = None, additional_paths: List[str] = None) -> None:
    """
    Scans a list of packages to find and import all modules,
    which triggers the @plugin decorators to register themselves.
    
    Args:
        plugin_modules: List of plugin modules to scan
        logger: Logger instance for logging
        project_root: Project root path for resolving relative paths
        additional_paths: Additional paths to scan for plugins, defaults to ["./demo"]
    """
    logger.info("Starting plugin discovery...")
    
    # Set default additional paths if not provided
    if additional_paths is None:
        additional_paths = ["./demo"]
    
    # Add additional paths to sys.path if provided
    paths_added = []
    if additional_paths and project_root:
        logger.info(f"Adding additional plugin paths: {additional_paths}")
        for path_str in additional_paths:
            # Resolve relative paths against project root
            if not Path(path_str).is_absolute():
                path = (project_root / path_str).resolve()
            else:
                path = Path(path_str).resolve()
            
            # Add to sys.path if it exists and is not already there
            if path.exists() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
                paths_added.append(str(path))
                logger.debug(f"Added plugin path to sys.path: {path}")
            elif path.exists():
                logger.debug(f"Plugin path already in sys.path: {path}")
            else:
                logger.warning(f"Plugin path does not exist: {path}")
    
    try:
        for module_name in plugin_modules:
            try:
                module = importlib.import_module(module_name)
                logger.info(f"Scanning for plugins in module: {module_name}")
                
                # We can only walk packages, not single-file modules
                if hasattr(module, '__path__'):
                    for _, name, _ in pkgutil.walk_packages(module.__path__, module.__name__ + '.'):
                        try:
                            importlib.import_module(name)
                            logger.debug(f"Successfully imported plugin module: {name}")
                        except Exception as e:
                            logger.error(f"Failed to import plugin module {name}: {e}", exc_info=True)
                else:
                    logger.debug(f"Module {module_name} is not a package, no sub-modules to walk. It has been imported.")

            except ImportError as e:
                logger.error(f"Could not import plugin module '{module_name}'. Is it a valid package? Error: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred while scanning module {module_name}: {e}", exc_info=True)
                
        # Discover plugins from additional paths
        if additional_paths and project_root:
            for path_str in additional_paths:
                # Resolve relative paths against project root
                if not Path(path_str).is_absolute():
                    path = (project_root / path_str).resolve()
                else:
                    path = Path(path_str).resolve()
                
                if path.exists():
                    # If it's a directory, walk it
                    if path.is_dir():
                        logger.info(f"Scanning for plugins in directory: {path}")
                        for _, name, _ in pkgutil.walk_packages([str(path)]):
                            try:
                                importlib.import_module(name)
                                logger.debug(f"Successfully imported external plugin module: {name}")
                            except Exception as e:
                                logger.error(f"Failed to import external plugin module {name}: {e}", exc_info=True)
                    # If it's a file, try to import it directly
                    elif path.is_file() and path.suffix == '.py':
                        module_name = path.stem
                        try:
                            spec = importlib.util.spec_from_file_location(module_name, path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            logger.debug(f"Successfully imported external plugin file: {path}")
                        except Exception as e:
                            logger.error(f"Failed to import external plugin file {path}: {e}", exc_info=True)

    finally:
        # Remove added paths from sys.path
        for path_str in paths_added:
            if path_str in sys.path:
                sys.path.remove(path_str)
    
    from .decorator import PLUGIN_REGISTRY
    logger.info(f"Plugin discovery finished. Found {len(PLUGIN_REGISTRY)} plugins.")
