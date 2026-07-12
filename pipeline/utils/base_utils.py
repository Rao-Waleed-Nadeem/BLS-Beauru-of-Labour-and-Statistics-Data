import logging
import os
from pathlib import Path

def setup_logger(name: str, log_file: str = None, level=logging.INFO) -> logging.Logger:
    """
    Sets up a logger with standard formatting.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    if log_file:
        log_path = Path(log_file)
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def get_project_root() -> Path:
    """
    Returns the absolute path to the project root directory.
    Assumes this file is in pipeline/utils/
    """
    current_file = Path(__file__).resolve()
    # current_file.parent == utils
    # current_file.parent.parent == pipeline
    # current_file.parent.parent.parent == project root
    return current_file.parent.parent.parent
