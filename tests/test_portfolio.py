"""
Tests for swing trader package
"""
import pytest
from swing_trader.core.portfolio import Portfolio


def test_portfolio_initialization():
    """Test portfolio initialization"""
    portfolio = Portfolio(initial_cash=50000.0)
    assert portfolio.cash == 50000.0
    assert portfolio.positions == {}
    assert portfolio.trades == []


def test_portfolio_buy():
    """Test buying shares"""
    portfolio = Portfolio(initial_cash=1000.0)

    # Successful buy
    success = portfolio.buy('TEST', 10, 50.0)
    assert success
    assert portfolio.cash == 500.0
    assert portfolio.positions['TEST'] == 10
    assert len(portfolio.trades) == 1

    # Insufficient cash
    success = portfolio.buy('TEST2', 20, 50.0)
    assert not success
    assert 'TEST2' not in portfolio.positions


def test_portfolio_sell():
    """Test selling shares"""
    portfolio = Portfolio(initial_cash=1000.0)
    portfolio.buy('TEST', 10, 50.0)

    # Successful sell
    success = portfolio.sell('TEST', 5, 60.0)
    assert success
    assert portfolio.cash == 500.0 + 300.0  # 500 remaining + 300 from sale
    assert portfolio.positions['TEST'] == 5

    # Insufficient shares
    success = portfolio.sell('TEST', 10, 60.0)
    assert not success


def test_portfolio_value():
    """Test portfolio valuation"""
    portfolio = Portfolio(initial_cash=1000.0)
    portfolio.buy('TEST1', 10, 50.0)  # 500 invested
    portfolio.buy('TEST2', 5, 100.0)  # 500 invested

    current_prices = {'TEST1': 60.0, 'TEST2': 120.0}
    value = portfolio.get_value(current_prices)
    expected = 1000.0 - 500.0 - 500.0 + (10 * 60.0) + (5 * 120.0)  # cash + position values
    assert value == expected