"""
Trading strategy base classes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from ..utils.logging import logger


class TradingStrategy(ABC):
    """
    Base class for trading strategies
    """

    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on data

        Args:
            data: DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

        Returns:
            DataFrame with columns ['Date', 'signal', 'price', 'reason']
            signal: 'buy', 'sell', 'hold'
            price: float (execution price, NaN for hold)
            reason: str (explanation)
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that data has required columns (case-insensitive)"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        data_columns = [col.lower() for col in data.columns]
        missing = [col for col in required_columns if col not in data_columns]
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return False
        # Normalize column names to uppercase
        data.columns = [col.upper() for col in data.columns]
        return True

    def get_current_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get signal for the latest data point (for prediction)

        Args:
            data: Recent data DataFrame

        Returns:
            Dict with 'signal', 'price', 'reason'
        """
        signals_df = self.generate_signals(data)
        if signals_df.empty:
            return {'signal': 'hold', 'price': None, 'reason': 'no_data'}
        latest = signals_df.iloc[-1]
        return {
            'signal': latest['signal'],
            'price': latest['price'],
            'reason': latest['reason']
        }


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Simple moving average crossover strategy
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {'short_window': 20, 'long_window': 50}
        params = {**default_params, **(params or {})}
        super().__init__("SMA Crossover", params)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        if not self.validate_data(data):
            logger.error("Invalid data format for SMA strategy")
            return pd.DataFrame(columns=['Date', 'signal', 'price', 'reason'])

        # Ensure Date is datetime
        data = data.copy()
        if 'DATE' in data.columns:
            data['Date'] = pd.to_datetime(data['DATE'])
            data.set_index('Date', inplace=True)
        elif data.index.name != 'Date':
            data.index = pd.to_datetime(data.index)

        short_window = self.params['short_window']
        long_window = self.params['long_window']

        # Calculate moving averages
        data['SMA_short'] = data['CLOSE'].rolling(window=short_window).mean()
        data['SMA_long'] = data['CLOSE'].rolling(window=long_window).mean()

        # Initialize signals DataFrame
        signals = pd.DataFrame(index=data.index, columns=['signal', 'price', 'reason'])
        signals['signal'] = 'hold'
        signals['price'] = pd.NA
        signals['reason'] = 'no_crossover'

        # Generate signals
        prev_short = data['SMA_short'].shift(1)
        prev_long = data['SMA_long'].shift(1)

        # Buy signal: short crosses above long
        buy_mask = (data['SMA_short'] > data['SMA_long']) & (prev_short <= prev_long)
        signals.loc[buy_mask, 'signal'] = 'buy'
        signals.loc[buy_mask, 'price'] = data.loc[buy_mask, 'CLOSE']
        signals.loc[buy_mask, 'reason'] = f'SMA{short_window} crossed above SMA{long_window}'

        # Sell signal: short crosses below long
        sell_mask = (data['SMA_short'] < data['SMA_long']) & (prev_short >= prev_long)
        signals.loc[sell_mask, 'signal'] = 'sell'
        signals.loc[sell_mask, 'price'] = data.loc[sell_mask, 'CLOSE']
        signals.loc[sell_mask, 'reason'] = f'SMA{short_window} crossed below SMA{long_window}'

        # Reset index to have Date as column
        signals.reset_index(inplace=True)
        signals.rename(columns={'index': 'Date'}, inplace=True)

        return signals