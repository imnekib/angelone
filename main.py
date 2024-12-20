import os
import sys
import pandas as pd
import logging
from datetime import datetime

from modules.logging_config import setup_logging
from modules.config import load_config
from modules.auth import (
    initial_authentication,
    generate_new_token,
    get_auth_token
)
from modules.data_fetcher import fetch_historical_data_with_cache, initialize_db, fetch_tokens_from_file
from modules.indicators import calculate_indicators
from modules.signals import generate_signals
from modules.simulator import simulate_trades
from modules.exceptions import AuthenticationError, TokenError
from modules.reporting import save_results, save_summary

def main():
    # Set up logging
    logger = setup_logging()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Load configuration
    config = load_config()
    INDICATOR_CONFIG = config.get("INDICATOR_CONFIG")
    TRADE_CONFIG = config.get("TRADE_CONFIG")
    CHARGES = config.get("CHARGES")
    HISTORICAL_DATA = config.get("HISTORICAL_DATA")
    FROM_DATE = HISTORICAL_DATA['fromdate']
    TO_DATE = HISTORICAL_DATA['todate']

    # Read the number of files to load from config
    num_files_to_load = config.get("NUM_FILES_TO_LOAD")

    # Initialize SmartConnect object
    from SmartApi.smartConnect import SmartConnect
    obj = SmartConnect(api_key=os.getenv("SMARTAPI_API_KEY"))

    # Authentication
    try:
        auth_token = get_auth_token(
            obj,
            client_id=os.getenv("ANGELONE_CLIENT_ID"),
            pin=os.getenv("ANGELONE_PIN"),
            totp_secret=os.getenv("SMARTAPI_TOTP_SECRET")
        )
    except AuthenticationError as auth_err:
        logger.critical(f"Authentication failed: {auth_err}")
        sys.exit(1)
    except TokenError as token_err:
        logger.critical(f"Token handling failed: {token_err}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during authentication: {e}")
        sys.exit(1)

    # Fetch names and tokens from instruments.xlsx
    token_data = fetch_tokens_from_file(num_files_to_load=num_files_to_load)
    if not token_data:
        logger.critical("No tokens found. Please check the instruments.xlsx file.")
        sys.exit(1)
        
    # Fetch RSI thresholds from config
    buy_rsi_threshold_low = INDICATOR_CONFIG.get('BUY_RSI_THRESHOLD_LOW')
    buy_rsi_threshold_high = INDICATOR_CONFIG.get('BUY_RSI_THRESHOLD_HIGH')
    sell_rsi_threshold = INDICATOR_CONFIG.get('SELL_RSI_THRESHOLD')
    
    # Initialize a list to collect summary data
    summary_data = []

    # Process each token one by one
    for name, token in token_data:  # Unpack name and token properly
        logger.info(f"Starting simulation for stock: {name} (token: {token})")

        # Update config dynamically for the token
        config["HISTORICAL_DATA"]["symboltoken"] = token

        # Fetch historical data
        initialize_db()
        raw_data = fetch_historical_data_with_cache(obj, config["HISTORICAL_DATA"])
        if raw_data is None:
            logger.warning(f"No historical data available for stock: {name}. Skipping.")
            continue

        # Calculate indicators
        data = calculate_indicators(raw_data, INDICATOR_CONFIG)

        # Generate signals
        data, _, _ = generate_signals(data, INDICATOR_CONFIG)
        
        # Simulate trading
        trades, missed_signals, daily_summary, final_summary = simulate_trades(
            data,
            initial_capital=TRADE_CONFIG['INITIAL_CAPITAL'],
            trade_allocation=TRADE_CONFIG['TRADE_ALLOCATION'],
            leverage=TRADE_CONFIG.get('LEVERAGE', 1),
            target_profit_percentage=TRADE_CONFIG['TARGET_PROFIT_PERCENTAGE'],
            atr_multiplier=TRADE_CONFIG.get('ATR_MULTIPLIER', 1),
            charges_config=CHARGES,
            indicator_config=INDICATOR_CONFIG,
            historical_data=HISTORICAL_DATA
        )

        # Prepare signals data for reporting
        signals_data = data.loc[data['Buy_Signal'] | data['Sell_Signal'], [
            'timestamp', 'close', 'RSI', 'MACD', 'Signal', 'VWAP', 'ATR', 'volume'
        ]].copy()

        signals_data['Signal Type'] = signals_data.apply(
            lambda row: 'Buy' if row.name in data[data['Buy_Signal']].index else 'Sell',
            axis=1
        )
        signals_data = signals_data[['timestamp', 'close', 'Signal Type', 'volume', 'RSI', 'MACD', 'Signal', 'VWAP', 'ATR']]

        # Save trading results
        #save_results(trades, missed_signals, daily_summary, final_summary, signals_data, name, output_dir="results")

        # Calculate win rate
        completed_trades = trades[trades['Type'].isin(['Sell', 'Square Off'])]
        wins = len(completed_trades[completed_trades['Profit/Loss'] > 0])
        total_trades = len(completed_trades)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        # Append performance metrics to summary data
        summary_data.append({
            "Stock Name": name,
            "Profit/Loss": final_summary['Total Profit/Loss'],
            "Win Rate (%)": round(win_rate, 2)
        })

    # Save the summary to an Excel file with dynamic RSI settings
    summary_file = os.path.join("results", f"summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx")
    save_summary(
        summary_data=summary_data,
        summary_file=summary_file,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        buy_rsi_threshold=f"<{buy_rsi_threshold_low} and >{buy_rsi_threshold_high}",
        sell_rsi_threshold=sell_rsi_threshold,
        trade_config=TRADE_CONFIG,
        indicator_config=INDICATOR_CONFIG,
        historical_data=HISTORICAL_DATA
    )

if __name__ == "__main__":
    try:
        main()
    except AuthenticationError as auth_err:
        logging.getLogger("trading_bot").critical(f"Authentication failed: {auth_err}")
        sys.exit(1)
    except TokenError as token_err:
        logging.getLogger("trading_bot").critical(f"Token handling failed: {token_err}")
        sys.exit(1)
    except Exception as e:
        logging.getLogger("trading_bot").critical(f"An unexpected error occurred: {e}")
        sys.exit(1)
