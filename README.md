# Angel Bot

This repository contains a feature-rich trading bot implemented in Python. The bot performs authentication, data fetching, indicator calculation, signal generation, trade simulation, and reporting for stocks traded on the Angel One platform. Below is the detailed overview of the repository, its structure, and functionality.

## Features
- **Authentication:** Securely authenticate using Angel One API and manage token lifecycle.
- **Data Fetching:** Fetch historical data using efficient caching and database storage.
- **Indicator Calculation:** Calculate various technical indicators such as RSI, MACD, VWAP, and ATR.
- **Signal Generation:** Generate buy and sell signals based on configured thresholds.
- **Trade Simulation:** Simulate trades with configurable parameters like leverage, allocation, and charges.
- **Comprehensive Reporting:** Save trading results and performance summaries in well-structured Excel files.
- **Logging:** Comprehensive logging for tracking execution and errors.

---

## Repository Structure

### Files and Directories

1. `main.py`: Entry point for the application, orchestrating all modules and functionalities.
2. `config.json`: Configuration file containing user-defined settings for indicators, trading parameters, and charges.
3. `modules/`:
   - `auth.py`: Handles authentication and token management.
   - `config.py`: Loads and validates configurations from `config.json`.
   - `data_fetcher.py`: Fetches historical data, caches it in SQLite, and ensures minimal API calls.
   - `indicators.py`: Calculates technical indicators using the TA-Lib library.
   - `signals.py`: Generates buy and sell signals based on indicators and thresholds.
   - `simulator.py`: Simulates trading using generated signals and computes profits/losses.
   - `exceptions.py`: Custom exceptions for handling specific errors.
   - `logging_config.py`: Configures logging for the bot.
   - `reporting.py`: Creates detailed reports and summaries in Excel format.
   - `utils.py`: Utility functions for logging, Excel formatting, and DataFrame processing.
4. `requirements.txt`: Dependencies required for running the project.

---

## Getting Started

### Prerequisites
- Python 3.8 or higher.
- Virtual environment tools such as `venv` or `conda`.
- Angel One API credentials.
- TA-Lib installed (refer to [TA-Lib Installation Guide](https://github.com/mrjbq7/ta-lib)).

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/imnekib/angelone.git
   cd angelone
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install TA-Lib if not already installed:
   ```bash
   pip install TA-Lib
   ```

5. Configure environment variables in a `.env` file:
   ```env
   ANGELONE_CLIENT_ID=your_client_id
   ANGELONE_PIN=your_pin
   SMARTAPI_API_KEY=your_api_key
   SMARTAPI_TOTP_SECRET=your_totp_secret
   ```

6. Configure the bot using `config.json`.

---

## Usage

1. Run the bot:
   ```bash
   python main.py
   ```

2. Outputs:
   - Trading results are saved in the `results/` directory.
   - Logs are saved in the `logs/` directory.

---

## Configuration

### Example `config.json`
```json
{
    "HISTORICAL_DATA": {
        "exchange": "NSE",
        "symboltoken": "10217",
        "interval": "TEN_MINUTE",
        "fromdate": "2024-12-12 09:15",
        "todate": "2024-12-13 15:30"
    },
    "INDICATOR_CONFIG": {
        "MACD_FAST": 6,
        "MACD_SLOW": 13,
        "MACD_SIGNAL": 5,
        "RSI_PERIOD": 7,
        "ATR_PERIOD": 14,
        "ATR_THRESHOLD": 1.0,
        "BUY_RSI_THRESHOLD_LOW": 30,
        "BUY_RSI_THRESHOLD_HIGH": 35,
        "BUY_RSI_THRESHOLD": 30,
        "SELL_RSI_THRESHOLD": 70
    },
    "CHARGES": {
        "BUY": {
            "BROKERAGE": 0.05,
            "STT": 0.0,
            "TRANSACTION": 0.003,
            "SEBI": 0.0001,
            "GST": 18,
            "STAMP": 0.003
        },
        "SELL": {
            "BROKERAGE": 0.05,
            "STT": 0.03,
            "TRANSACTION": 0.003,
            "SEBI": 0.0001,
            "GST": 18,
            "STAMP": 0.0
        }
    },
    "TRADE_CONFIG": {
        "INITIAL_CAPITAL": 100000,
        "TRADE_ALLOCATION": 0.1,
        "LEVERAGE": 1,
        "TARGET_PROFIT_PERCENTAGE": 1.0,
        "ATR_MULTIPLIER": 2.0
    },
    "NUM_FILES_TO_LOAD": 1 # Number of stocks to load from istruments.xlsx file. I added this line just for clarity. Remove this comment from the actual config file as json doesn't accept comment.
}
```

---

## Logging
Logs are stored in the `logs/` directory and provide detailed insights into the bot's operations.

---

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch and create a Pull Request.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Support
For issues or questions, open an issue on GitHub or contact the maintainer.

