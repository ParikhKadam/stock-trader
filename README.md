# Swing Trader

A Python project for downloading, analyzing, and trading historical stock data from the National Stock Exchange (NSE) of India.

## Features

- Download daily historical stock data for NSE symbols using bhavcopy
- Modular architecture for easy extension
- Portfolio management
- Trading strategy framework
- Structured logging with loguru
- Command-line interface

## Project Structure

```
swing-trader/
├── swing_trader/          # Main package
│   ├── __init__.py
│   ├── data/             # Data acquisition
│   │   ├── __init__.py
│   │   └── nse.py       # NSE data downloading
│   ├── core/            # Core trading logic
│   │   ├── __init__.py
│   │   ├── portfolio.py # Portfolio management
│   │   └── strategy.py  # Trading strategies
│   └── utils/           # Utilities
│       ├── __init__.py
│       └── logging.py   # Logging configuration
├── scripts/             # CLI scripts
│   └── download_stock_data.py
├── config/              # Configuration files
├── data/                # Data storage
├── logs/                # Log files
├── tests/               # Unit tests
├── docs/                # Documentation
├── pyproject.toml       # Project dependencies
└── README.md
```

## Setup

This project uses `uv` for dependency management and virtual environment handling.

1. Ensure `uv` is installed. If not, install it from [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv).

2. Clone or navigate to the project directory:
   ```
   cd /home/kadam/data/me/swing-trader
   ```

3. Install dependencies:
   ```
   uv sync
   ```

## Usage

### Download Stock Data

Download historical data for a stock symbol:

```bash
uv run python scripts/download_stock_data.py RELIANCE 2024-01-01 2024-01-05
```

This will create a CSV file `data/RELIANCE/RELIANCE_2024-01-01_to_2024-01-05.csv` with the historical data.

### Data Organization

- Downloaded data is automatically organized in `data/{SYMBOL}/` directories
- Logs are stored in the `logs/` directory
- Both `data/` and `logs/` are excluded from version control

### Using the Package

```python
from swing_trader.data.nse import download_stock_data
from swing_trader.core.portfolio import Portfolio
from swing_trader.core.strategy import SimpleMovingAverageStrategy

# Download data
data_file = download_stock_data('RELIANCE', '2024-01-01', '2024-01-05')

# Load and analyze data
import pandas as pd
df = pd.read_csv(data_file)

# Use a strategy
strategy = SimpleMovingAverageStrategy(short_window=5, long_window=10)
signal = strategy.generate_signals(df)
print(f"Signal: {signal}")

# Manage portfolio
portfolio = Portfolio(initial_cash=100000)
portfolio.buy('RELIANCE', 10, df.iloc[-1]['CLOSE'])
print(f"Portfolio value: {portfolio.get_value({'RELIANCE': df.iloc[-1]['CLOSE']})}")
```

3. The project is already initialized with `uv init`. Dependencies are managed in `pyproject.toml`.

4. To install dependencies (already done, but for reference):
   ```
   uv sync
   ```

## Usage

Run the script to download stock data:

```
uv run python scripts/download_stock_data.py RELIANCE 2024-01-01 2024-01-31
```

This downloads data for RELIANCE from Jan 1, 2024, to Jan 31, 2024, and saves it to `RELIANCE_2024-01-01_to_2024-01-31.csv`.

### Options

- `symbol`: The NSE stock symbol (e.g., RELIANCE, TCS).
- `start_date`: Start date in YYYY-MM-DD format.
- `end_date`: End date in YYYY-MM-DD format.
- `--output` or `-o`: Optional output file name.

Example with custom output:
```
uv run python scripts/download_stock_data.py SBIN 2023-01-01 2023-12-31 -o sbin_2023.csv
```

## Requirements

- Python 3.8+
- `jugaad-data` library (automatically installed via uv)

## Notes

- Data is fetched from NSE's official website. Ensure you have a stable internet connection.
- For large date ranges, the download may take time due to rate limits.
- The script uses the "EQ" series by default (equity shares).

## License

[Add license if applicable]
