# logging_config.py
import logging
import sys

def configure_logging():
    logger = logging.getLogger("ten_baggers")
    # Show log DEBUG and above level
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
        # Handler for console
        console_handler = logging.StreamHandler(sys.stdout)
        # Show log DEBUG and above level
        console_handler.setLevel(logging.DEBUG)

        # Formatter for console
        formatter = logging.Formatter(
            "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
