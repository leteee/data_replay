import importlib
import pkgutil
from logging import Logger
from pathlib import Path

def discover_handlers(logger: Logger) -> None:
    """
    Scans the current package to find and import all modules,
    which triggers the @handler decorators to register themselves.
    """
    logger.info("Starting data handler discovery...")
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

    from .decorator import HANDLER_REGISTRY
    logger.info(f"Handler discovery finished. Found {len(set(HANDLER_REGISTRY.values()))} handlers.")
