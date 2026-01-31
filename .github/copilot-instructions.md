# Swing Trader - AI Agent Instructions

## Architecture Overview
This is a modular swing trading system with extensible strategy framework. Core components:
- **Strategies**: Abstract base class pattern in `swing_trader/core/strategies/`
- **Data Flow**: CSV → column normalization (snakecase) → strategy validation → backtesting
- **CLI Tools**: Scripts in `/scripts/` for data download and strategy execution

## Key Patterns & Conventions

### 1. Strategy Implementation
**Location**: `swing_trader/core/strategies/`
**Pattern**: Inherit from `TradingStrategy`, implement `generate_signal()` method
```python
class MyStrategy(TradingStrategy):
    def __init__(self, params=None):
        default_params = {'param1': value}
        params = {**default_params, **(params or {})}
        super().__init__("Strategy Name", params)
        self.reset_state()

    def generate_signal(self, data: pd.DataFrame) -> TradingSignal:
        # Return TradingSignal(signal='buy'|'sell'|'hold', price=price, reason='explanation')
        pass
```

### 2. Data Handling
- **Column Names**: Always normalize to snakecase (`open`, `high`, `low`, `close`, `volume`)
- **Date Index**: Use datetime index for time series operations
- **Validation**: Use `strategy.validate_data(df)` before processing

### 3. CLI Scripts
**Location**: `scripts/`
**Pattern**: Use `argparse`, `Path` for paths, sys.path manipulation
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use uv run python scripts/script.py
```

### 4. Imports
- **Within package**: Relative imports (`from .base import ...`)
- **From package root**: Absolute imports (`from swing_trader.core import ...`)
- **Scripts**: sys.path manipulation to import package

### 5. Logging
**Setup**: Pre-configured in `swing_trader/utils/logging.py`
```python
from swing_trader.utils.logging import logger
logger.info("message")  # Structured logging with file + console output
```

### 6. Testing
**Location**: `tests/`
**Pattern**: pytest with function-based tests
```python
def test_feature():
    # Arrange
    # Act
    # Assert
```

### 7. Dependencies & Execution
- **Manager**: `uv` (not pip/pipenv/poetry)
- **Run scripts**: `uv run python scripts/script.py`
- **Run tests**: `uv run pytest tests/`

## Common Workflows

### Adding a New Strategy
1. Create `swing_trader/core/strategies/new_strategy.py`
2. Inherit from `TradingStrategy`
3. Update `swing_trader/core/strategies/__init__.py`
4. Update `scripts/run_strategy.py` strategy registry
5. Test with `uv run python scripts/run_strategy.py data/file.csv new_strategy`

### Running Backtests
```bash
# Download data
uv run python scripts/download_stock_data.py SYMBOL start_date end_date

# Run strategy
uv run python scripts/run_strategy.py data/SYMBOL/file.csv strategy_name --params "key=value"
```

### Debugging
- Check logs in `logs/app.log`
- Use `logger.info()` for debugging (not print statements)
- Data validation happens in `strategy.validate_data()`

## File Structure Reference
- `swing_trader/core/strategies/base.py` - Strategy interfaces & data models
- `swing_trader/core/backtester.py` - Backtesting engine
- `swing_trader/core/portfolio.py` - Position & cash management
- `scripts/run_strategy.py` - Main CLI tool for strategy execution
- `scripts/download_stock_data.py` - Data acquisition tool

## Coding Standards & Best Practices

### Design Principles
- **Single Responsibility**: Each class/method should have one clear purpose
  - Strategies only generate signals, don't manage portfolios
  - Backtester only executes trades, doesn't analyze performance
  - CLI scripts only parse arguments and orchestrate, don't implement business logic
