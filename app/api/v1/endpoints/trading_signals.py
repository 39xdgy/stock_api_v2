"""
Trading Signals Endpoint

POST /api/v1/trading_signals/current
Get current trading signals for a list of stocks.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime

import yfinance as yf

from app.schemas.requests import TradingSignalsRequest
from app.services.signal_detector import SignalDetector, SignalType

router = APIRouter()
signal_detector = SignalDetector()


@router.post("/current")
async def get_current_trading_signals(request: TradingSignalsRequest) -> Dict[str, Any]:
    """
    Get current trading signals for a list of stocks.
    
    This endpoint analyzes current market conditions and provides
    BUY/SELL/HOLD recommendations based on technical indicators.
    
    **Signal Logic:**
    
    MACD:
    - BUY: Histogram crosses above zero (golden cross)
    - SELL: Histogram peaks and starts declining (peak detection)
    
    KDJ:
    - BUY: K and D both below threshold (default 20, oversold)
    - SELL: K and D both above threshold (default 80, overbought)
    
    **Returns:**
    - BUY: Current conditions suggest buying
    - SELL: Current conditions suggest selling
    - HOLD: No clear signal, maintain current position
    - ERROR: Unable to analyze due to insufficient data
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "buy_indicator": request.buy_indicator,
        "sell_indicator": request.sell_indicator,
        "buy_threshold": request.buy_threshold,
        "sell_threshold": request.sell_threshold,
        "period": request.period,
        "signals": [],
        "summary": {
            "total_stocks": len(request.stocks),
            "buy_signals": 0,
            "sell_signals": 0,
            "hold_signals": 0,
            "failed_analyses": 0
        }
    }
    
    for stock in request.stocks:
        try:
            signal_data = _analyze_stock(
                stock,
                request.buy_indicator,
                request.sell_indicator,
                request.buy_threshold,
                request.sell_threshold,
                request.period
            )
            results["signals"].append(signal_data)
            
            # Update summary
            if signal_data["signal"] == "BUY":
                results["summary"]["buy_signals"] += 1
            elif signal_data["signal"] == "SELL":
                results["summary"]["sell_signals"] += 1
            elif signal_data["signal"] == "HOLD":
                results["summary"]["hold_signals"] += 1
            else:
                results["summary"]["failed_analyses"] += 1
                
        except Exception as e:
            error_signal = {
                "stock": stock,
                "signal": "ERROR",
                "error": str(e),
                "current_price": None,
                "indicators": {},
                "reasoning": f"Failed to analyze {stock}: {str(e)}"
            }
            results["signals"].append(error_signal)
            results["summary"]["failed_analyses"] += 1
    
    return results


def _analyze_stock(
    stock: str,
    buy_indicator: str,
    sell_indicator: str,
    buy_threshold: float,
    sell_threshold: float,
    period: str
) -> Dict[str, Any]:
    """Analyze a single stock for current trading signals."""
    # Fetch current data
    ticker = yf.Ticker(stock)
    df = ticker.history(period=period, interval="1d")
    
    if df.empty:
        raise ValueError(f"No data available for {stock}")
    
    # Get current price
    current_price = df['Close'].iloc[-1]
    
    # Get signal
    signal_type, reasoning, indicators = signal_detector.get_current_signal(
        df, buy_indicator, sell_indicator, buy_threshold, sell_threshold
    )
    
    return {
        "stock": stock,
        "signal": signal_type.value,
        "current_price": round(current_price, 2),
        "indicators": indicators,
        "reasoning": reasoning,
        "last_updated": df.index[-1].strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/indicators")
async def get_available_indicators() -> Dict[str, Any]:
    """
    Get information about available technical indicators.
    """
    return {
        "available_indicators": ["macd", "kdj"],
        "indicator_details": {
            "macd": {
                "name": "Moving Average Convergence Divergence",
                "description": "Trend-following momentum indicator",
                "buy_logic": "Histogram crosses above zero (golden cross)",
                "sell_logic": "Histogram peaks and starts declining (peak detection - NEW in V2)",
                "parameters": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9
                }
            },
            "kdj": {
                "name": "Stochastic Oscillator (KDJ)",
                "description": "Momentum indicator using Webull-style smoothing",
                "buy_logic": "K and D both below threshold (default: 20)",
                "sell_logic": "K and D both above threshold (default: 80)",
                "parameters": {
                    "k_period": 9,
                    "smoothing": "2/3 previous + 1/3 current (Webull style)"
                }
            }
        }
    }

