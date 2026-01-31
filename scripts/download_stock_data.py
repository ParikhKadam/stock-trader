import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
from swing_trader.data.nse import download_stock_data
from swing_trader.utils.logging import logger

def main():
    logger.info("Starting stock data download script using bhavcopy")
    parser = argparse.ArgumentParser(description="Download historical stock data from NSE bhavcopy.")
    parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE)')
    parser.add_argument('start_date', help='Start date in YYYY-MM-DD format')
    parser.add_argument('end_date', help='End date in YYYY-MM-DD format')
    parser.add_argument('--output', '-o', default=None, help='Output CSV file name (default: symbol_start_to_end.csv)')

    args = parser.parse_args()
    logger.info(f"Parsed arguments: symbol={args.symbol}, start_date={args.start_date}, end_date={args.end_date}, output={args.output}")

    try:
        output_file = download_stock_data(args.symbol, args.start_date, args.end_date, args.output)
        print(f"Data saved to {output_file}")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())