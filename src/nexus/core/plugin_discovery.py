import importlib
import pkgutil
from logging import Logger

# Import the top-level package containing the plugins
from .. import plugins

def discover_plugins(logger: Logger) -> None:
    """
    Scans the `nexus.plugins` package to find and import all modules,
    which triggers the @plugin decorators to register themselves.
    """
    logger.info("Starting plugin discovery...")
    
    # Use the imported package's __path__ to find submodules
    for _, name, _ in pkgutil.walk_packages(plugins.__path__, plugins.__name__ + '.'):
        try:
            importlib.import_module(name)
            logger.debug(f"Successfully imported plugin module: {name}")
        except Exception as e:
            logger.error(f"Failed to import plugin module {name}: {e}", exc_info=True)
    
    from .plugin_decorator import PLUGIN_REGISTRY
    logger.info(f"Plugin discovery finished. Found {len(PLUGIN_REGISTRY)} plugins.")