import importlib
import importlib.util
import pkgutil
import sys
from logging import Logger
from pathlib import Path
from typing import List

def discover_handlers(logger: Logger, project_root: Path = None, additional_paths: List[str] = None) -> None:
    """
    Scans the current package to find and import all modules,
    which triggers the @handler decorators to register themselves.
    """
    logger.info("Starting data handler discovery...")
    
    # Add additional paths to sys.path if provided
    paths_added = []
    if additional_paths and project_root:
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
                logger.debug(f"Added handler path to sys.path: {path}")
    
    # Discover built-in handlers
    package_path = Path(__file__).parent
    package_name = package_path.name
    
    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        # Skip base, decorator, and discovery modules
        if module_name in ['base', 'decorator', 'discovery', '__init__']:
            continue
        
        try:
            # The package is nexus.core.data.handlers
            full_module_name = f"nexus.core.data.handlers.{module_name}"
            importlib.import_module(full_module_name)
            logger.debug(f"Successfully imported handler module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to import handler module {module_name}: {e}", exc_info=True)
    
    # Discover additional handlers from additional_paths
    try:
        for path_str in (additional_paths or []):
            # Resolve relative paths against project root
            if not Path(path_str).is_absolute():
                path = (project_root / path_str).resolve() if project_root else Path(path_str).resolve()
            else:
                path = Path(path_str).resolve()
            
            if path.exists():
                # If it's a directory, walk it
                if path.is_dir():
                    for _, name, _ in pkgutil.walk_packages([str(path)]):
                        try:
                            importlib.import_module(name)
                            logger.debug(f"Successfully imported external handler module: {name}")
                        except Exception as e:
                            logger.error(f"Failed to import external handler module {name}: {e}", exc_info=True)
                # If it's a file, try to import it directly
                elif path.is_file() and path.suffix == '.py':
                    module_name = path.stem
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        logger.debug(f"Successfully imported external handler file: {path}")
                    except Exception as e:
                        logger.error(f"Failed to import external handler file {path}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error during external handler discovery: {e}", exc_info=True)
    finally:
        # Remove added paths from sys.path
        for path_str in paths_added:
            if path_str in sys.path:
                sys.path.remove(path_str)

    from .decorator import HANDLER_REGISTRY
    logger.info(f"Handler discovery finished. Found {len(set(HANDLER_REGISTRY.values()))} handlers.")
