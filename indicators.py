# modules/indicators.py

import talib
import logging

def calculate_indicators(data, indicator_config):
    """Calculate MACD, RSI, VWAP, and ATR indicators."""
    if data.empty:
        logging.warning("Empty data received for indicator calculation.")
        return data
    try:
        data['MACD'], data['Signal'], _ = talib.MACD(
            data['close'],
            fastperiod=indicator_config['MACD_FAST'],
            slowperiod=indicator_config['MACD_SLOW'],
            signalperiod=indicator_config['MACD_SIGNAL']
        )
        data['RSI'] = talib.RSI(data['close'], timeperiod=indicator_config['RSI_PERIOD'])
        data['VWAP'] = (data['close'] * data['volume']).cumsum() / data['volume'].cumsum()
        data['ATR'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=indicator_config['ATR_PERIOD'])
        logging.info("Indicators calculated successfully.")
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
    return data
