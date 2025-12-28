"""
Request Models

Pydantic models for API request validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExcludeRule(BaseModel):
    """
    Rule for filtering out stocks from scan results.
    
    Example: {"field": "return_percentage", "operator": "<", "value": 10}
    This would exclude stocks with return_percentage less than 10%.
    """
    field: str = Field(
        ...,
        description="Field to check (e.g., return_percentage, success_rate)"
    )
    operator: str = Field(
        ...,
        description="Comparison operator: <, >, <=, >=, ==, !="
    )
    value: float = Field(
        ...,
        description="Value to compare against"
    )
    
    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v):
        valid_operators = ['<', '>', '<=', '>=', '==', '!=']
        if v not in valid_operators:
            raise ValueError(f"Operator must be one of: {valid_operators}")
        return v


class SortRule(BaseModel):
    """
    Rule for sorting scan results.
    
    Example: {"field": "success_rate", "order": "desc"}
    Multiple rules can be provided for tie-breaking.
    """
    field: str = Field(
        ...,
        description="Field to sort by (e.g., success_rate, return_percentage)"
    )
    order: str = Field(
        default="desc",
        description="Sort order: asc or desc"
    )
    
    @field_validator('order')
    @classmethod
    def validate_order(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower()


class MarketScanRequest(BaseModel):
    """
    Request model for market scanner endpoint.
    
    Scans the market for stocks based on technical indicators
    and applies filtering/sorting rules.
    """
    buy_indicator: str = Field(
        default="macd",
        description="Indicator for buy signals: macd or kdj"
    )
    sell_indicator: str = Field(
        default="macd",
        description="Indicator for sell signals: macd or kdj"
    )
    period: str = Field(
        default="6mo",
        description="Historical data period: 1mo, 3mo, 6mo, 1y, 2y"
    )
    interval: str = Field(
        default="1d",
        description="Data interval: 1d or 1wk"
    )
    buy_threshold: Optional[float] = Field(
        default=None,
        description="Custom KDJ buy threshold (default: 20)"
    )
    sell_threshold: Optional[float] = Field(
        default=None,
        description="Custom KDJ sell threshold (default: 80)"
    )
    min_trades: int = Field(
        default=3,
        ge=1,
        description="Minimum number of trades required"
    )
    stock_list: Optional[List[str]] = Field(
        default=None,
        description="Custom list of stock symbols to scan"
    )
    market_cap: Optional[List[str]] = Field(
        default=None,
        description="Market cap categories: mega_cap, large_cap, mid_cap, small_cap, micro_cap, all"
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )
    exclude: Optional[List[ExcludeRule]] = Field(
        default=None,
        description="Rules for filtering out stocks"
    )
    sort: Optional[List[SortRule]] = Field(
        default=None,
        description="Rules for sorting results (first = primary, rest = tie-breakers)"
    )
    
    @field_validator('buy_indicator', 'sell_indicator')
    @classmethod
    def validate_indicator(cls, v):
        valid_indicators = ['macd', 'kdj']
        if v.lower() not in valid_indicators:
            raise ValueError(f"Indicator must be one of: {valid_indicators}")
        return v.lower()
    
    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y']
        if v not in valid_periods:
            raise ValueError(f"Period must be one of: {valid_periods}")
        return v
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        valid_intervals = ['1d', '1wk', '1mo']
        if v not in valid_intervals:
            raise ValueError(f"Interval must be one of: {valid_intervals}")
        return v
    
    @field_validator('market_cap')
    @classmethod
    def validate_market_cap(cls, v):
        if v is None:
            return v
        valid_caps = ['mega_cap', 'large_cap', 'mid_cap', 'small_cap', 'micro_cap', 'all']
        for cap in v:
            if cap not in valid_caps:
                raise ValueError(f"Market cap must be one of: {valid_caps}")
        return v


class TradingSignalsRequest(BaseModel):
    """
    Request model for trading signals endpoint.
    
    Gets current trading signals for a list of stocks.
    """
    stocks: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of stock symbols to analyze (max 100)"
    )
    buy_indicator: str = Field(
        default="macd",
        description="Indicator for buy signals: macd or kdj"
    )
    sell_indicator: str = Field(
        default="macd",
        description="Indicator for sell signals: macd or kdj"
    )
    buy_threshold: Optional[float] = Field(
        default=None,
        description="Custom KDJ buy threshold (default: 20)"
    )
    sell_threshold: Optional[float] = Field(
        default=None,
        description="Custom KDJ sell threshold (default: 80)"
    )
    period: str = Field(
        default="1mo",
        description="Data period for analysis: 1mo, 3mo, 6mo"
    )
    
    @field_validator('buy_indicator', 'sell_indicator')
    @classmethod
    def validate_indicator(cls, v):
        valid_indicators = ['macd', 'kdj']
        if v.lower() not in valid_indicators:
            raise ValueError(f"Indicator must be one of: {valid_indicators}")
        return v.lower()
    
    @field_validator('stocks')
    @classmethod
    def validate_stocks(cls, v):
        # Convert to uppercase
        return [s.upper() for s in v]

