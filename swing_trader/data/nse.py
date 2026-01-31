"""
NSE data acquisition module
"""
import pandas as pd
from jugaad_data.nse import bhavcopy_save
from datetime import datetime, timedelta
import os
import shutil
from ..utils.logging import logger


def download_stock_data(symbol: str, start_date: str, end_date: str, output_file: str = None) -> str:
    """
    Download historical stock data for a symbol from NSE bhavcopy.

    Args:
        symbol: Stock symbol (e.g., 'RELIANCE')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        output_file: Output CSV file path (optional)

    Returns:
        Path to the output CSV file
    """
    logger.info(f"Downloading stock data for {symbol} from {start_date} to {end_date}")

    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    if start > end:
        raise ValueError("Start date must be before end date")

    # Create temp directory for bhavcopy
    temp_dir = 'temp_bhavcopy'
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Download bhavcopy for each date
        current_date = start
        all_data = []
        while current_date <= end:
            logger.info(f"Downloading bhavcopy for {current_date}")
            bhavcopy_save(current_date, temp_dir)

            # Load the CSV and filter for symbol
            filename = f"cm{current_date.strftime('%d%b%Y')}bhav.csv"
            filepath = os.path.join(temp_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                symbol_data = df[df['SYMBOL'] == symbol.upper()]
                if not symbol_data.empty:
                    all_data.append(symbol_data)
                    logger.info(f"Found {len(symbol_data)} records for {symbol} on {current_date}")
                else:
                    logger.warning(f"No data for {symbol} on {current_date}")
            else:
                logger.error(f"Bhavcopy file not found: {filepath}")
            current_date += timedelta(days=1)

        if not all_data:
            raise ValueError(f"No data found for symbol {symbol} in the given date range")

        combined_df = pd.concat(all_data, ignore_index=True)

        if output_file is None:
            # Save in data/{symbol}/ directory
            symbol_dir = os.path.join('data', symbol.upper())
            os.makedirs(symbol_dir, exist_ok=True)
            output_file = os.path.join(symbol_dir, f"{symbol}_{start_date}_to_{end_date}.csv")
        else:
            # If custom output provided, ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

        combined_df.to_csv(output_file, index=False)
        logger.success(f"Data saved to {output_file}")

        return output_file

    finally:
        # Clean up temp files
        shutil.rmtree(temp_dir)
        logger.info("Temp files cleaned up")