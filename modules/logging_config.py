# modules/logging_config.py

import logging
import os
import sys

def setup_logging(log_file='logs/trading_bot.log', level=logging.INFO):
    """Configure logging for the trading bot."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - [%(levelname)s] - %(thread)d - %(filename)s.%(funcName)s(%(lineno)d) - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Create a logger for the trading bot
    logger = logging.getLogger("trading_bot")
    return logger
