"""
NSE data acquisition module
"""
from datetime import datetime
import os
from ..utils.logging import logger

try:
    import yfinance as yf
except ImportError:
    yf = None

def download_stock_data(symbol: str, start_date: str, end_date: str, output_file: str = None) -> str:
    """
    Download historical stock data for a symbol from NSE using yfinance.

    Args:
        symbol: Stock symbol (e.g., 'HINDUNILVR')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        output_file: Output CSV file path (optional)

    Returns:
        Path to the output CSV file
    """
    if yf is None:
        raise ImportError("yfinance not available. Please install it.")

    logger.info(f"Downloading stock data for {symbol} from {start_date} to {end_date}")

    try:
        if output_file is None:
            # Save in data/{symbol}/ directory
            symbol_dir = os.path.join('data', symbol.upper())
            os.makedirs(symbol_dir, exist_ok=True)
            output_file = os.path.join(symbol_dir, f"{symbol}_{start_date}_to_{end_date}.csv")
        else:
            # If custom output provided, ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Download data using yfinance
        ticker = f"{symbol}.NS"
        df = yf.download(ticker, start=start_date, end=end_date, interval="1d")

        if df.empty:
            raise ValueError(f"No data found for symbol {symbol} in the given date range")
        
        # Flatten MultiIndex columns and convert to snakecase
        df.columns = df.columns.droplevel(1)
        df.columns = [col.lower() for col in df.columns]  # Convert to snakecase
        
        # Set index name to snakecase
        df.index.name = 'date'
        
        df.to_csv(output_file, index=True)
        logger.success(f"Data saved to {output_file}")

        return output_file

    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        raise