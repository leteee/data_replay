import logging
import logging.config
import yaml
import os

def setup_logging(case_name=None):
    """Set up logging configuration."""
    # Ensure the base logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Load base logging configuration
    with open("config/logging.yaml", "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)

    # If a case name is provided, add a specific handler for it
    if case_name:
        case_log_dir = os.path.join("logs", case_name)
        os.makedirs(case_log_dir, exist_ok=True)
        case_log_file = os.path.join(case_log_dir, "pipeline.log")

        # Create a file handler for the case
        file_handler = logging.FileHandler(case_log_file, mode="w", encoding='utf-8')
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Add the handler to the root logger
        logging.getLogger().addHandler(file_handler)
