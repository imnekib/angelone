# modules/trades.py

import logging
from collections import deque
import pandas as pd

def calculate_transaction_charges(price, quantity, transaction_type, charges_config):
    """
    Calculate transaction charges based on price, quantity, and transaction type (BUY/SELL).
    """
    turnover = price * quantity
    brokerage = min(turnover * (charges_config[transaction_type]['BROKERAGE'] / 100), 20)
    stt = turnover * (charges_config[transaction_type]['STT'] / 100)
    transaction_charge = turnover * (charges_config[transaction_type]['TRANSACTION'] / 100)
    sebi_charge = turnover * (charges_config[transaction_type]['SEBI'] / 100)
    gst = (brokerage + transaction_charge + sebi_charge) * (charges_config[transaction_type]['GST'] / 100)
    stamp_duty = turnover * (charges_config[transaction_type]['STAMP'] / 100) if transaction_type == "BUY" else 0
    total_charges = brokerage + stt + transaction_charge + sebi_charge + gst + stamp_duty
    return {
        'total': total_charges,
        'brokerage': brokerage,
        'stt': stt,
        'transaction_charge': transaction_charge,
        'sebi_charge': sebi_charge,
        'gst': gst,
        'stamp_duty': stamp_duty
    }

def simulate_trades(data, initial_capital, trade_allocation, leverage, target_profit_percentage, atr_multiplier, charges_config, indicator_config, historical_data):
    """
    Simulate trades based on generated signals, calculate profits/losses, and record trades.
    
    Parameters:
        data (pd.DataFrame): Data containing price and indicator information.
        initial_capital (float): Starting capital for trading.
        trade_allocation (float): Fraction of capital to allocate per trade.
        leverage (int): Leverage factor.
        target_profit_percentage (float): Percentage at which to take profit.
        atr_multiplier (float): Multiplier for ATR to set stop-loss.
        charges_config (dict): Configuration for transaction charges.
        indicator_config (dict): Configuration for indicators like RSI period.
        historical_data (dict): Historical data configurations (e.g., interval, dates).
    
    Returns:
        trades_df (pd.DataFrame): DataFrame containing all executed trades.
        missed_signals_df (pd.DataFrame): DataFrame containing all missed signals.
        daily_summary_df (pd.DataFrame): DataFrame containing daily capital summaries.
        final_summary (dict): Dictionary containing overall performance metrics.
    """
    capital = initial_capital  # Total capital including realized profits/losses
    free_cash = initial_capital  # Tracks cash available for margin allocation
    total_profit_loss = 0  # Tracks the cumulative profit or loss
    total_revenue = 0      # Tracks the total revenue from selling shares
    total_cost = 0         # Tracks the total cost of buying shares
    trades = []           # List to store all trades
    missed_signals = []   # Tracks missed buy/sell signals
    daily_summary = []    # Tracks daily start/end capital
    long_positions = deque()  # Queue to track active buy positions
    current_day = None
    daily_margin_used = 0  # Tracks margin used for the day
    daily_profit_loss = 0  # Tracks profit/loss for the day

    # Unpack historical_data for use within the function
    instrument_key = historical_data.get('INSTRUMENT_KEY', 'N/A')
    FROM_DATE = historical_data.get('fromdate', 'N/A')
    TO_DATE = historical_data.get('todate', 'N/A')

    for i, row in data.iterrows():
        timestamp = row['timestamp']
        price = row['close']
        trade_day = timestamp.date()

        # Define cutoff times for the day
        market_close_time = timestamp.replace(hour=15, minute=30, second=0, microsecond=0)
        square_off_time = market_close_time - pd.Timedelta(minutes=30)  # 30 minutes before close
        no_new_buys_time = market_close_time - pd.Timedelta(minutes=60)  # 60 minutes before close

        # Square off all positions 30 minutes before market close
        if timestamp >= square_off_time and long_positions:
            for position in list(long_positions):
                shares_to_sell = position['shares']
                sell_charges_details = calculate_transaction_charges(price, shares_to_sell, "SELL", charges_config)
                sell_revenue = shares_to_sell * price - sell_charges_details['total']
                cost = shares_to_sell * position['price'] + position['buy_charges']  # Include buy charges
                profit_loss = sell_revenue - cost  # Deduct buy cost from sell revenue

                total_profit_loss += profit_loss  # Track cumulative profit/loss
                daily_profit_loss += profit_loss  # Track daily profit/loss
                capital += profit_loss  # Update total capital
                free_cash += position['margin_used'] + sell_revenue  # Replenish free cash (margin + revenue)
                long_positions.remove(position)

                trades.append({
                    'Time': timestamp,
                    'Type': 'Square Off',
                    'Price': price,
                    'Shares': shares_to_sell,
                    'Profit/Loss': profit_loss,
                    'Charges': sell_charges_details['total'],
                    'Brokerage': sell_charges_details['brokerage'],
                    'STT': sell_charges_details['stt'],
                    'Transaction Charge': sell_charges_details['transaction_charge'],
                    'SEBI Charge': sell_charges_details['sebi_charge'],
                    'GST': sell_charges_details['gst'],
                    'Stamp Duty': sell_charges_details['stamp_duty'],
                    'Reason': "Square Off Before Market Close"
                })

        # Start of a new day
        if current_day != trade_day:
            if current_day is not None:
                # Log the previous day's summary
                daily_summary.append({
                    'Date': current_day,
                    'Start of Day Capital': start_of_day_capital,
                    'End of Day Capital': capital
                })
            # Prepare for the new day
            current_day = trade_day
            start_of_day_capital = capital
            free_cash = capital  # Reset free cash for the new day
            daily_margin_used = 0
            daily_profit_loss = 0

        # Skip buy trades 60 minutes before market close
        if timestamp >= no_new_buys_time:
            if row['Buy_Signal']:
                missed_signals.append({'Time': timestamp, 'Price': price, 'Reason': 'Buy restricted near market close'})
                continue

        # Buy Signal Logic
        if row['Buy_Signal']:
            allocated_margin = free_cash * trade_allocation  # Margin for the trade
            leveraged_buying_power = allocated_margin * leverage  # Effective buying power

            if leveraged_buying_power >= price:
                shares_to_buy = int(leveraged_buying_power // price)
                if shares_to_buy > 0:
                    buy_charges_details = calculate_transaction_charges(price, shares_to_buy, "BUY", charges_config)
                    buy_cost = shares_to_buy * price + buy_charges_details['total']
                    total_cost += buy_cost
                    free_cash -= allocated_margin  # Deduct margin from free cash
                    daily_margin_used += allocated_margin  # Track daily margin usage

                    # Append the buy position
                    long_positions.append({
                        'shares': shares_to_buy,
                        'price': price,
                        'buy_charges': buy_charges_details['total'],  # Store buy charges
                        'margin_used': allocated_margin,  # Store the margin used for the position
                        'target_price': price * (1 + target_profit_percentage / 100),
                        'trailing_stop_loss': price - (row['ATR'] * atr_multiplier)
                    })

                    trades.append({
                        'Time': timestamp,
                        'Type': 'Buy',
                        'Price': price,
                        'Shares': shares_to_buy,
                        'Profit/Loss': 0,
                        'Charges': buy_charges_details['total'],
                        'Brokerage': buy_charges_details['brokerage'],
                        'STT': buy_charges_details['stt'],
                        'Transaction Charge': buy_charges_details['transaction_charge'],
                        'SEBI Charge': buy_charges_details['sebi_charge'],
                        'GST': buy_charges_details['gst'],
                        'Stamp Duty': buy_charges_details['stamp_duty'],
                        'Reason': "Buy Signal"
                    })
            else:
                missed_signals.append({'Time': timestamp, 'Price': price, 'Reason': 'Insufficient Funds'})

        # Sell Signal Logic
        if long_positions:
            for position in list(long_positions):
                reason = None
                if row['Sell_Signal']:
                    reason = "Sell Signal Triggered"
                elif price >= position['target_price']:
                    reason = "Target Profit Reached"
                elif price <= position['trailing_stop_loss']:
                    reason = "Trailing Stop-Loss Triggered"
                elif timestamp >= square_off_time:
                    reason = "Square Off Before Market Close"

                if reason:
                    shares_to_sell = position['shares']
                    sell_charges_details = calculate_transaction_charges(price, shares_to_sell, "SELL", charges_config)
                    sell_revenue = shares_to_sell * price - sell_charges_details['total']
                    cost = shares_to_sell * position['price'] + position['buy_charges']  # Include buy charges
                    profit_loss = sell_revenue - cost  # Deduct buy cost from sell revenue

                    total_profit_loss += profit_loss
                    daily_profit_loss += profit_loss
                    total_revenue += sell_revenue
                    capital += profit_loss
                    free_cash += position['margin_used'] + sell_revenue  # Replenish free cash (margin + revenue)

                    trades.append({
                        'Time': timestamp,
                        'Type': 'Sell',
                        'Price': price,
                        'Shares': shares_to_sell,
                        'Profit/Loss': profit_loss,
                        'Charges': sell_charges_details['total'],
                        'Brokerage': sell_charges_details['brokerage'],
                        'STT': sell_charges_details['stt'],
                        'Transaction Charge': sell_charges_details['transaction_charge'],
                        'SEBI Charge': sell_charges_details['sebi_charge'],
                        'GST': sell_charges_details['gst'],
                        'Stamp Duty': sell_charges_details['stamp_duty'],
                        'Reason': reason
                    })
                    long_positions.remove(position)

    # Final summary at the end of the simulation
    if current_day:
        daily_summary.append({
            'Date': current_day,
            'Start of Day Capital': start_of_day_capital,
            'End of Day Capital': capital
        })

    # Calculate the final capital
    final_capital = initial_capital + total_profit_loss
    current_stock_holding = sum(pos['shares'] for pos in long_positions)

    # Create DataFrames for results
    trades_df = pd.DataFrame(trades, columns=['Time', 'Type', 'Reason', 'Price', 'Shares', 'Profit/Loss', 'Charges',
                                              'Brokerage', 'STT', 'Transaction Charge', 'SEBI Charge', 'GST',
                                              'Stamp Duty'])
    missed_signals_df = pd.DataFrame(missed_signals, columns=['Time', 'Price', 'Reason'])
    daily_summary_df = pd.DataFrame(daily_summary)

    # Create the final_summary dictionary
    final_summary = {
        'Final Capital': final_capital,
        'Total Profit/Loss': total_profit_loss,
        'Total Revenue': total_revenue,
        'Total Cost': total_cost,
        'Initial Capital': initial_capital,
        'Current Stock Holding': current_stock_holding,
        'Leverage Used': leverage,
        'RSI_PERIOD': indicator_config.get('RSI_PERIOD', 'N/A'),
        'MACD_FAST': indicator_config.get('MACD_FAST', 'N/A'),
        'MACD_SLOW': indicator_config.get('MACD_SLOW', 'N/A'),
        'MACD_SIGNAL': indicator_config.get('MACD_SIGNAL', 'N/A'),
        'ATR_PERIOD': indicator_config.get('ATR_PERIOD', 'N/A'),
        'ATR_THRESHOLD': indicator_config.get('ATR_THRESHOLD', 'N/A'),
        'INTERVAL': historical_data.get('interval', 'N/A'),
        'SYMBOL_TOKEN': historical_data.get('symboltoken', 'N/A'),
        'FROM_DATE': FROM_DATE,
        'TO_DATE': TO_DATE,
        'TRADE_ALLOCATION': trade_allocation,
        'TARGET_PROFIT_PERCENTAGE': target_profit_percentage,
        'ATR_MULTIPLIER': atr_multiplier
    }

    return trades_df, missed_signals_df, daily_summary_df, final_summary
