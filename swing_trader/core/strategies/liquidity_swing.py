"""
Liquidity-based swing trading strategy
Exploits operator vs retail dynamics through liquidity sweep detection
"""
import pandas as pd
from typing import Optional, Dict, Any
from swing_trader.core.strategies.base import TradingStrategy
from swing_trader.core.models import TradingSignal, TradePlan
from swing_trader.core.liquidity.state_builder import LiquiditySwingStateBuilder
from swing_trader.utils.logging import logger


class LiquiditySwingStrategy(TradingStrategy):
    """
    Strategy that identifies liquidity sweep setups:
    1. Find equal lows (retail stop clusters)
    2. Detect compression (accumulation phase)
    3. Identify sweep below equal lows with rejection
    4. Enter on reclaim with strong volume
    
    Conservative parameters favor quality over quantity
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize liquidity swing strategy
        
        Default parameters:
            equal_level_tolerance: 0.003 (0.3% - conservative clustering)
            compression_threshold: 0.75 (25% ATR contraction required)
            volume_spike_min: 1.5 (50% above average volume)
            min_reward_risk: 2.0 (minimum R:R ratio)
            stop_buffer_pct: 0.01 (1% below sweep low)
            target_range_pct: 1.0 (target = entry + full range)
            swing_order: 3 (bars on each side for pivot detection)
        """
        default_params = {
            'equal_level_tolerance': 0.003,  # 0.3%
            'compression_threshold': 0.75,
            'volume_spike_min': 1.5,
            'min_reward_risk': 2.0,
            'stop_buffer_pct': 0.01,
            'target_range_pct': 1.0,
            'swing_order': 3,
            'compression_window': 10,
            'volume_lookback': 20,
            'reclaim_strength_min': 0.6,
        }
        
        # Merge user params with defaults
        params = {**default_params, **(params or {})}
        
        super().__init__("Liquidity Swing Strategy", params)
        
        # Initialize state builder with strategy parameters
        self.state_builder = LiquiditySwingStateBuilder(
            swing_order=self.params['swing_order'],
            equal_level_tolerance=self.params['equal_level_tolerance'],
            compression_window=self.params['compression_window'],
            compression_threshold=self.params['compression_threshold'],
            volume_lookback=self.params['volume_lookback'],
            volume_spike_min=self.params['volume_spike_min'],
            reclaim_strength_min=self.params['reclaim_strength_min'],
        )
        
        self.reset_state()
    
    def reset_state(self):
        """Reset strategy state"""
        self.last_state = None
        self.signal_count = 0
    
    def get_min_lookback(self) -> int:
        """Minimum data required for strategy"""
        return 30  # Need at least 30 days for reliable detection
    
    def generate_signal(self, data: pd.DataFrame) -> TradingSignal:
        """
        Generate trading signal based on liquidity sweep detection
        
        Args:
            data: Historical OHLCV data up to current point
            
        Returns:
            TradingSignal with buy/hold decision
        """
        # Validate data
        if not self.validate_data(data):
            return TradingSignal(
                signal='hold',
                price=None,
                reason='Invalid or insufficient data'
            )
        
        # Build liquidity state
        state = self.state_builder.build(data)
        
        if state is None:
            return TradingSignal(
                signal='hold',
                price=None,
                reason='Insufficient data for state building'
            )
        
        self.last_state = state
        
        # Check if setup is tradeable (all conditions met)
        if not state.is_tradeable():
            missing = []
            if state.equal_low_count < 2:
                missing.append(f"only {state.equal_low_count} equal lows")
            if not state.sweep_detected:
                missing.append("no sweep")
            if not state.reclaim_confirmed:
                missing.append("no reclaim")
            if not state.compression_detected:
                missing.append("no compression")
            
            reason = f"Setup incomplete: {', '.join(missing)}"
            return TradingSignal(signal='hold', price=None, reason=reason)
        
        # Calculate entry, stop, and target levels
        entry_price = self._calculate_entry(state, data)
        stop_price = self._calculate_stop(state, data)
        target_price = self._calculate_target(state, data, entry_price)
        
        # Validate R:R ratio
        risk = entry_price - stop_price
        reward = target_price - entry_price
        reward_to_risk = reward / risk if risk > 0 else 0
        
        if reward_to_risk < self.params['min_reward_risk']:
            return TradingSignal(
                signal='hold',
                price=None,
                reason=f'Poor R:R ratio: {reward_to_risk:.2f} < {self.params["min_reward_risk"]}'
            )
        
        # Generate buy signal
        self.signal_count += 1
        confidence = state.confidence_score()
        
        reason = (
            f"Liquidity sweep setup: {state.equal_low_count} equal lows at {state.equal_low_level:.2f}, "
            f"swept to {state.sweep_low:.2f}, reclaimed with {state.reclaim_body_strength:.1%} body strength, "
            f"R:R={reward_to_risk:.2f}, confidence={confidence:.1%}"
        )
        
        logger.info(f"BUY signal generated: {reason}")
        
        return TradingSignal(
            signal='buy',
            price=entry_price,
            reason=reason
        )
    
    def generate_trade_plan(
        self,
        symbol: str,
        data: pd.DataFrame,
        capital: float,
        risk_pct: float = 0.02
    ) -> Optional[TradePlan]:
        """
        Generate complete trade plan with position sizing
        
        Args:
            symbol: Trading symbol
            data: Historical data
            capital: Available capital
            risk_pct: Max risk per trade as decimal (default 2%)
            
        Returns:
            TradePlan or None if no valid setup
        """
        signal = self.generate_signal(data)
        
        if signal.signal != 'buy':
            return None
        
        state = self.last_state
        if state is None:
            return None
        
        entry_price = signal.price
        stop_price = self._calculate_stop(state, data)
        target_price = self._calculate_target(state, data, entry_price)
        
        # Calculate position size based on risk
        risk_per_share = entry_price - stop_price
        max_risk_amount = capital * risk_pct
        position_size = int(max_risk_amount / risk_per_share)
        
        # Validate affordability
        cost = entry_price * position_size
        if cost > capital:
            position_size = int(capital / entry_price)
        
        if position_size <= 0:
            logger.warning(f"Position size calculation resulted in {position_size} shares")
            return None
        
        # Create trade plan
        plan = TradePlan(
            symbol=symbol,
            entry=entry_price,
            stop=stop_price,
            target=target_price,
            position_size=position_size,
            expiry_days=5,  # Conservative: plan expires after 5 days
        )
        
        logger.info(f"Trade plan created: {symbol} @ {entry_price:.2f}, "
                   f"stop={stop_price:.2f}, target={target_price:.2f}, "
                   f"size={position_size}, R:R={plan.reward_to_risk:.2f}")
        
        return plan
    
    def _calculate_entry(self, state, data: pd.DataFrame) -> float:
        """
        Calculate entry price
        Enter slightly above equal low level to confirm reclaim
        """
        if state.equal_low_level is None:
            # Fallback to current close
            return data['close'].iloc[-1]
        
        # Enter at equal low level + small buffer
        buffer = state.equal_low_level * 0.002  # 0.2% above
        entry = state.equal_low_level + buffer
        
        # Don't enter above current close
        current_close = data['close'].iloc[-1]
        entry = min(entry, current_close * 1.01)
        
        return round(entry, 2)
    
    def _calculate_stop(self, state, data: pd.DataFrame) -> float:
        """
        Calculate stop loss price
        Place below sweep low with buffer
        """
        if state.sweep_low is None:
            # Fallback: use some % below current price
            current_close = data['close'].iloc[-1]
            return current_close * 0.97  # 3% below
        
        # Stop below sweep low with buffer
        stop = state.sweep_low * (1 - self.params['stop_buffer_pct'])
        
        return round(stop, 2)
    
    def _calculate_target(self, state, data: pd.DataFrame, entry: float) -> float:
        """
        Calculate target price
        Use range-based projection
        """
        # Target = Entry + (Range * multiplier)
        target = entry + (state.current_range_size * self.params['target_range_pct'])
        
        # Ensure target is meaningful (at least 2% above entry)
        min_target = entry * 1.02
        target = max(target, min_target)
        
        return round(target, 2)
