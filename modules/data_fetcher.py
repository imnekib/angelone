from datetime import datetime
import logging
import pandas as pd
import sqlite3

DB_FILE = "historical_data.db"

def fetch_tokens_from_file(file_path="data/instruments.xlsx", num_files_to_load=None):
    """
    Reads the top N instrument names and tokens from the specified Excel file.

    Args:
        file_path (str): Path to the Excel file.
        num_files_to_load (int or None): Number of top rows to read. If None, fetch all rows.

    Returns:
        List of tuples [(name, token)].
    """
    try:
        logging.info(f"Attempting to read names and tokens from {file_path}")
        df = pd.read_excel(file_path, usecols=[0, 4])  # Column A = 'name', Column E = 'token'

        if num_files_to_load is not None:
            df = df.iloc[:num_files_to_load]  # Limit rows

        # Extract names and tokens as a list of tuples
        data = list(zip(df.iloc[:, 0].astype(str), df.iloc[:, 1].astype(str)))
        logging.info(f"Successfully fetched {len(data)} names and tokens from {file_path}")
        return data
    except Exception as e:
        logging.error(f"Error reading names and tokens from {file_path}: {e}")
        return []

# Initialize SQLite database
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_data (
            symboltoken TEXT,
            interval TEXT,
            timestamp TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symboltoken, interval, timestamp)
        )
    """)
    conn.commit()
    conn.close()

# Save data to SQLite database
def save_data_to_db(symboltoken, interval, data):
    conn = sqlite3.connect(DB_FILE)
    try:
        # Remove duplicates by ensuring no overlap with existing data in the database
        existing_data_query = """
            SELECT timestamp FROM historical_data
            WHERE symboltoken = ? AND interval = ?
        """
        existing_timestamps = pd.read_sql_query(existing_data_query, conn, params=(symboltoken, interval))
        
        # Filter out rows with timestamps already in the database
        if not existing_timestamps.empty:
            existing_timestamps = existing_timestamps['timestamp'].astype(str).tolist()
            data = data[~data['timestamp'].astype(str).isin(existing_timestamps)]
        
        # If there's any data left to save, insert it
        if not data.empty:
            data['symboltoken'] = symboltoken
            data['interval'] = interval
            data.to_sql('historical_data', conn, if_exists='append', index=False, method='multi')
            logging.info(f"Successfully saved {len(data)} new records to the database.")
        else:
            logging.info(f"No new data to save for {symboltoken} ({interval}). All records already exist in the database.")

    except Exception as e:
        logging.error(f"Error saving data to the database: {e}")
    finally:
        conn.close()

# Load data from SQLite database
def load_data_from_db(symboltoken, interval, from_date, to_date):
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT * FROM historical_data
        WHERE symboltoken = ? AND interval = ? AND timestamp BETWEEN ? AND ?
    """
    data = pd.read_sql_query(query, conn, params=(symboltoken, interval, from_date, to_date))
    conn.close()
    if not data.empty:
        data['timestamp'] = pd.to_datetime(data['timestamp'])  # Ensure timestamp is datetime
    return data

# Fetch historical data with caching

def fetch_historical_data_with_cache(obj, historical_data_config):
    try:
        # Validate required keys
        required_keys = ["exchange", "symboltoken", "interval", "fromdate", "todate"]
        for key in required_keys:
            if key not in historical_data_config:
                raise ValueError(f"Missing required key '{key}' in historical_data_config.")

        # Parse dates as strings and then convert to pandas Timestamps
        from_date_str = historical_data_config["fromdate"]
        to_date_str = historical_data_config["todate"]

        from_date = pd.to_datetime(from_date_str, format="%Y-%m-%d %H:%M:%S")
        to_date = pd.to_datetime(to_date_str, format="%Y-%m-%d %H:%M:%S")

        # Ensure from_date and to_date are timezone-naive
        from_date = from_date.tz_localize(None)
        to_date = to_date.tz_localize(None)

        # Load existing data from the database
        cached_data = load_data_from_db(
            historical_data_config["symboltoken"], 
            historical_data_config["interval"], 
            from_date_str, 
            to_date_str
        )

        # Ensure cached_data['timestamp'] is timezone-naive
        if not cached_data.empty:
            cached_data['timestamp'] = cached_data['timestamp'].dt.tz_localize(None)

        # Determine ranges to fetch
        missing_data = pd.DataFrame()
        if not cached_data.empty:
            cached_start = cached_data['timestamp'].min()
            cached_end = cached_data['timestamp'].max()

            # Fetch data outside of cached range
            if from_date < cached_start:
                logging.info(f"Fetching data before cache for {historical_data_config['symboltoken']} from {from_date} to {cached_start}.")
                params = historical_data_config.copy()
                params["fromdate"] = from_date_str
                params["todate"] = cached_start.strftime("%Y-%m-%d %H:%M")
                response = obj.getCandleData(params)
                if response.get('status'):
                    raw_data = response['data']
                    if raw_data:
                        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        missing_data_1 = pd.DataFrame(raw_data, columns=columns)
                        missing_data_1['timestamp'] = pd.to_datetime(missing_data_1['timestamp']).dt.tz_localize(None)
                        missing_data = pd.concat([missing_data, missing_data_1])

            if to_date > cached_end:
                logging.info(f"Fetching data after cache for {historical_data_config['symboltoken']} from {cached_end} to {to_date}.")
                params = historical_data_config.copy()
                params["fromdate"] = cached_end.strftime("%Y-%m-%d %H:%M")
                params["todate"] = to_date_str
                response = obj.getCandleData(params)
                if response.get('status'):
                    raw_data = response['data']
                    if raw_data:
                        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        missing_data_2 = pd.DataFrame(raw_data, columns=columns)
                        missing_data_2['timestamp'] = pd.to_datetime(missing_data_2['timestamp']).dt.tz_localize(None)
                        missing_data = pd.concat([missing_data, missing_data_2])
        else:
            # Fetch the entire range if no cache exists
            logging.info(f"Fetching complete range for {historical_data_config['symboltoken']} from {from_date} to {to_date}.")
            params = historical_data_config.copy()
            params["fromdate"] = from_date_str
            params["todate"] = to_date_str
            response = obj.getCandleData(params)
            if response.get('status'):
                raw_data = response['data']
                if raw_data:
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    missing_data = pd.DataFrame(raw_data, columns=columns)
                    missing_data['timestamp'] = pd.to_datetime(missing_data['timestamp']).dt.tz_localize(None)

        # Save new data to database
        if not missing_data.empty:
            missing_data.drop_duplicates(subset=['timestamp'], inplace=True)
            save_data_to_db(historical_data_config["symboltoken"], historical_data_config["interval"], missing_data)

        # Combine cached and missing data
        all_data = pd.concat([cached_data, missing_data]).drop_duplicates(subset=['timestamp']).sort_values(by='timestamp')
        return all_data

    except Exception as e:
        logging.getLogger("trading_bot").error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

# Initialize database
initialize_db()
