import logging
import logging.config
import yaml
import os

_is_initialized = False
_added_handlers = set()

def initialize_logging():
    """
    Sets up the base logging configuration from the YAML file.
    This should only be called once at application startup.
    """
    global _is_initialized
    if _is_initialized:
        return

    os.makedirs("logs", exist_ok=True)
    try:
        with open("config/logging.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        _is_initialized = True
    except FileNotFoundError:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        logging.warning("config/logging.yaml not found. Using basic logging configuration.")
        _is_initialized = True # Mark as initialized even if basic config is used

def add_case_log_handler(case_name: str):
    """
    Adds a specific file handler for a given case, if not already added.
    """
    if not _is_initialized:
        initialize_logging()

    if case_name in _added_handlers:
        return

    case_log_dir = os.path.join("logs", case_name)
    os.makedirs(case_log_dir, exist_ok=True)
    case_log_file = os.path.join(case_log_dir, "pipeline.log")

    # Create a file handler for the case, using mode 'w' to clear the log for each new run.
    file_handler = logging.FileHandler(case_log_file, mode="w", encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Add the handler to the root logger
    logging.getLogger().addHandler(file_handler)
    _added_handlers.add(case_name)

def get_logger(name):
    """
    Returns a logger instance with the specified name.
    """
    return logging.getLogger(name)
