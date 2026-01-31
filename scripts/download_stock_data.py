import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
from swing_trader.core.nse import download_stock_data
from swing_trader.utils.logging import logger

def main():
    logger.info("Starting stock data download script")
    parser = argparse.ArgumentParser(description="Download NSE bhavcopy data for a date range.")
    parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE) - used for directory naming')
    parser.add_argument('start_date', help='Start date in YYYY-MM-DD format')
    parser.add_argument('end_date', help='End date in YYYY-MM-DD format')
    parser.add_argument('--output', '-o', default=None, help='Output directory (default: data/SYMBOL/)')

    args = parser.parse_args()
    logger.info(f"Parsed arguments: symbol={args.symbol}, start_date={args.start_date}, end_date={args.end_date}, output={args.output}")

    try:
        output_dir = download_stock_data(args.symbol, args.start_date, args.end_date, args.output)
        print(f"Data saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())