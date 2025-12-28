"""
Response Models

Pydantic models for API response serialization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class TradingSummary(BaseModel):
    """Summary of trading simulation results."""
    initial_balance: float
    final_balance: float
    total_return: float
    return_percentage: float
    total_trades: int
    success_rate: float
    avg_days_between_trades: float
    buy_indicator: str
    sell_indicator: str


class TradingStatistics(BaseModel):
    """Detailed trading statistics."""
    success_rate: float
    avg_trade_frequency: float
    total_profit: float
    total_loss: float
    avg_profit: float
    avg_loss: float
    max_profit: float
    max_loss: float
    avg_hold_days: float


class StockScanResult(BaseModel):
    """Result for a single stock in market scan."""
    stock: str
    trading_summary: TradingSummary
    statistics: TradingStatistics


class ScanSummary(BaseModel):
    """Summary of the market scan operation."""
    total_stocks_scanned: int
    successful_scans: int
    failed_scans: int
    stocks_after_filters: int
    scan_criteria: Dict[str, Any]


class MarketScanResponse(BaseModel):
    """Response model for market scanner endpoint."""
    scan_summary: ScanSummary
    top_results: List[StockScanResult]
    metadata: Optional[Dict[str, Any]] = None


class SignalIndicators(BaseModel):
    """Current indicator values for a stock."""
    macd_histogram_today: Optional[float] = None
    macd_histogram_yesterday: Optional[float] = None
    macd_histogram_day_before: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None


class StockSignal(BaseModel):
    """Trading signal for a single stock."""
    stock: str
    signal: str  # BUY, SELL, HOLD, ERROR
    current_price: Optional[float] = None
    indicators: Dict[str, Any]
    reasoning: str
    last_updated: Optional[str] = None
    error: Optional[str] = None


class SignalsSummary(BaseModel):
    """Summary of trading signals."""
    total_stocks: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    failed_analyses: int


class TradingSignalsResponse(BaseModel):
    """Response model for trading signals endpoint."""
    timestamp: str
    buy_indicator: str
    sell_indicator: str
    buy_threshold: Optional[float]
    sell_threshold: Optional[float]
    period: str
    signals: List[StockSignal]
    summary: SignalsSummary


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


class IndicatorInfo(BaseModel):
    """Information about an indicator."""
    name: str
    description: str
    buy_logic: str
    sell_logic: str


class CriteriaOptionsResponse(BaseModel):
    """Available options for scan criteria."""
    indicators: List[str]
    periods: List[str]
    intervals: List[str]
    market_cap_options: List[str]
    sortable_fields: List[str]
    exclude_operators: List[str]

