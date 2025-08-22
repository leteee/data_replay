import logging
import logging.config
import yaml
import os

def setup_logger(cfg, case_dir=None):
    # Ensure the base logs directory exists
    os.makedirs("logs", exist_ok=True)

    with open("config/logging.yaml", "r", encoding='utf-8') as f: # Ensure reading config.yaml with utf-8
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

    logger = logging.getLogger()
    if case_dir:
        os.makedirs(os.path.join("logs", case_dir), exist_ok=True)
        # Explicitly set encoding for FileHandler
        file_handler = logging.FileHandler(os.path.join("logs", case_dir, "pipeline.log"), mode="w", encoding='utf-8')
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        # Remove existing handlers to prevent duplicate logs if setup_logger is called multiple times
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(file_handler)
    return logger

def get_logger(name):
    """Returns a logger instance for a given name."""
    return logging.getLogger(name)