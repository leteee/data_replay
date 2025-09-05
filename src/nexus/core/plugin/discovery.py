import importlib
import pkgutil
from logging import Logger
from typing import List

def discover_plugins(plugin_modules: List[str], logger: Logger) -> None:
    """
    Scans a list of packages to find and import all modules,
    which triggers the @plugin decorators to register themselves.
    """
    logger.info("Starting plugin discovery...")
    
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

    from .decorator import PLUGIN_REGISTRY
    logger.info(f"Plugin discovery finished. Found {len(PLUGIN_REGISTRY)} plugins.")
