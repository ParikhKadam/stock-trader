# Trading Strategies

This directory contains all trading strategy implementations for the swing trading system.

## Structure

- `base.py`: Base classes (`TradingStrategy`, `TradingSignal`)
- `sma.py`: Simple Moving Average crossover strategy
- `rsi.py`: Relative Strength Index strategy
- `__init__.py`: Package exports

## Adding a New Strategy

To add a new trading strategy:

1. **Create a new file** in this directory (e.g., `my_strategy.py`)

2. **Implement your strategy class** inheriting from `TradingStrategy`:

```python
from .base import TradingStrategy, TradingSignal

class MyStrategy(TradingStrategy):
    def __init__(self, params=None):
        default_params = {'param1': default_value, 'param2': default_value}
        params = {**default_params, **(params or {})}
        super().__init__("My Strategy Name", params)
        self.reset_state()

    def reset_state(self):
        # Reset any cached state
        pass

    def get_min_lookback(self):
        # Return minimum historical days needed
        return your_min_lookback

    def generate_signal(self, historical_data):
        # Implement your signal generation logic
        # Return TradingSignal object
        return TradingSignal(signal='buy'|'sell'|'hold', price=execution_price, reason='explanation')
```

3. **Update `__init__.py`** to export your new strategy:

```python
from .my_strategy import MyStrategy

__all__ = [
    # ... existing exports
    'MyStrategy',
]
```

4. **Update main core `__init__.py`** to export the strategy:

```python
from .strategies import MyStrategy
```

## Strategy Interface

All strategies must implement:

- `generate_signal(historical_data: pd.DataFrame) -> TradingSignal`: Generate signal for next day
- `get_min_lookback() -> int`: Minimum historical data points needed
- `reset_state()`: Reset internal state between backtests

## Available Strategies

- **SimpleMovingAverageStrategy**: SMA crossover signals
- **RSIStrategy**: RSI overbought/oversold signals

## Testing

Run the test suite to ensure your strategy works:

```bash
uv run python test_backtest.py
```

Replace the strategy in the test file to test your new implementation.