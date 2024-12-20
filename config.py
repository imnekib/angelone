# modules/config.py

import json
import sys
import logging

def load_config(config_path="config.json"):
    """Load and validate configuration from a JSON file."""
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
        
        # Validate 'HISTORICAL_DATA' section
        if "HISTORICAL_DATA" not in config:
            raise KeyError("Missing 'HISTORICAL_DATA' section in config.json.")
        
        HISTORICAL_DATA_keys = ["exchange", "symboltoken", "interval", "fromdate", "todate"]
        for key in HISTORICAL_DATA_keys:
            if key not in config["HISTORICAL_DATA"]:
                raise KeyError(f"Missing '{key}' in 'HISTORICAL_DATA' section.")
        
        # Validate other sections as needed (INDICATOR_CONFIG, CHARGES, TRADE_CONFIG)
        required_sections = ["INDICATOR_CONFIG", "CHARGES", "TRADE_CONFIG"]
        for section in required_sections:
            if section not in config:
                logging.warning(f"Missing '{section}' section in config.json. Using empty dictionary.")
                config[section] = {}
        
        logging.info("Configuration loaded successfully from config.json.")
        return config
    except Exception as e:
        logging.critical(f"Failed to load configuration: {e}")
        sys.exit(1)
        
