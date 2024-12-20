# modules/signals.py

import logging

def generate_signals(data, indicator_config):
    """
    Generate buy and sell signals based on SMA, MACD, RSI, ATR, and VWAP.
    ATR is used as a volatility filter.
    """
    if data.empty:
        logging.warning("Empty data received for signal generation.")
        return data, None, None
    try:
        # Fetch indicator thresholds from configuration
        atr_threshold = indicator_config.get('ATR_THRESHOLD')
        buy_rsi_threshold_low = indicator_config.get('BUY_RSI_THRESHOLD_LOW') # This is needed for RSI recovery logic for buy signal
        buy_rsi_threshold_high = indicator_config.get('BUY_RSI_THRESHOLD_HIGH') # This is needed for RSI recovery logic for buy signal
        buy_rsi_threshold = indicator_config.get('BUY_RSI_THRESHOLD') # This is needed for normal RSI for buy signal
        sell_rsi_threshold = indicator_config.get('SELL_RSI_THRESHOLD')

        # Calculate SMA 50 and SMA 200
        data['SMA50'] = data['close'].rolling(window=50).mean()
        data['SMA200'] = data['close'].rolling(window=200).mean()

        # RSI Recovery Logic
        data['RSI_Recovery'] = (data['RSI'].shift(1) < buy_rsi_threshold_low) & (data['RSI'] > buy_rsi_threshold_high)

        # VWAP Recovery Logic
        data['VWAP_Recovery'] = (data['close'].shift(1) < data['VWAP']) & (data['close'] > data['VWAP'])

        # Buy Signal Logic
        data['Buy_Signal'] = (
            data['RSI_Recovery'] &
            #(data['RSI'] < buy_rsi_threshold) &
            (data['MACD'] > data['Signal']) &
            (data['ATR'] > atr_threshold) &
            #(data['close'] < data['VWAP']) &
            data['VWAP_Recovery'] 
            #(data['SMA50'] > data['SMA200']) &
            #(data['SMA50'].shift(1) <= data['SMA200'].shift(1))  # Golden Cross
        )

        # Sell Signal Logic
        data['Sell_Signal'] = (
            (data['MACD'] < data['Signal']) &
            (data['RSI'] > sell_rsi_threshold) &
            (data['ATR'] > atr_threshold) &
            (data['close'] > data['VWAP'])
        )

        logging.info(f"Generated {data['Buy_Signal'].sum()} Buy and {data['Sell_Signal'].sum()} Sell signals.")
    except Exception as e:
        logging.error(f"Error generating signals: {e}")
    return data, buy_rsi_threshold_low, buy_rsi_threshold_high
