"""
Signal Detector Service

Detects buy and sell signals based on MACD and KDJ indicators.

Key difference from V1:
- MACD sell signal uses peak detection instead of death cross
- Sell when MACDH was rising and now starts declining (local maximum)
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from enum import Enum

from app.services.technical_analysis import TechnicalAnalysis


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class IndicatorType(Enum):
    """Supported indicator types."""
    MACD = "macd"
    KDJ = "kdj"


class SignalDetector:
    """
    Detects trading signals based on technical indicators.
    
    MACD Buy: Histogram crosses above zero (golden cross)
    MACD Sell: Histogram peaks and starts declining (peak detection)
    
    KDJ Buy: K and D both below threshold (oversold)
    KDJ Sell: K and D both above threshold (overbought)
    """
    
    def __init__(self):
        self.technical_analysis = TechnicalAnalysis()
        
        # Default thresholds
        self.kdj_buy_threshold = 20
        self.kdj_sell_threshold = 80
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        buy_indicator: str,
        sell_indicator: str,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None
    ) -> Tuple[List[int], List[int]]:
        """
        Generate buy and sell signals for the entire DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
            buy_indicator: Indicator for buy signals ('macd' or 'kdj')
            sell_indicator: Indicator for sell signals ('macd' or 'kdj')
            buy_threshold: Custom threshold for KDJ buy (default: 20)
            sell_threshold: Custom threshold for KDJ sell (default: 80)
        
        Returns:
            Tuple of (buy_signals, sell_signals) as lists of 0/1
        """
        # Calculate indicators
        macd_histogram = self.technical_analysis.get_macd_histogram_series(df)
        kdj_result = self.technical_analysis.get_kdj_series(df)
        
        if kdj_result is None:
            kdj_k = pd.Series([np.nan] * len(df), index=df.index)
            kdj_d = pd.Series([np.nan] * len(df), index=df.index)
        else:
            kdj_k, kdj_d, _ = kdj_result
        
        if macd_histogram is None:
            macd_histogram = pd.Series([np.nan] * len(df), index=df.index)
        
        buy_signals = []
        sell_signals = []
        
        for i in range(len(df)):
            buy_signal = self._check_buy_signal(
                i, buy_indicator, macd_histogram, kdj_k, kdj_d, buy_threshold
            )
            sell_signal = self._check_sell_signal(
                i, sell_indicator, macd_histogram, kdj_k, kdj_d, sell_threshold
            )
            
            buy_signals.append(1 if buy_signal else 0)
            sell_signals.append(1 if sell_signal else 0)
        
        return buy_signals, sell_signals
    
    def _check_buy_signal(
        self,
        index: int,
        indicator: str,
        macd_histogram: pd.Series,
        kdj_k: pd.Series,
        kdj_d: pd.Series,
        threshold: Optional[float]
    ) -> bool:
        """
        Check if there's a buy signal at the given index.
        
        MACD Buy: Histogram crosses above zero (yesterday < 0, today > 0)
        KDJ Buy: K and D both below threshold
        """
        if indicator.lower() == 'macd':
            # Need at least 2 data points for crossover detection
            if index < 1:
                return False
            
            yesterday = macd_histogram.iloc[index - 1]
            today = macd_histogram.iloc[index]
            
            if pd.isna(yesterday) or pd.isna(today):
                return False
            
            # Golden cross: histogram crosses above zero
            return yesterday < 0 and today > 0
        
        elif indicator.lower() == 'kdj':
            k_val = kdj_k.iloc[index]
            d_val = kdj_d.iloc[index]
            
            if pd.isna(k_val) or pd.isna(d_val):
                return False
            
            thresh = threshold if threshold is not None else self.kdj_buy_threshold
            return k_val < thresh and d_val < thresh
        
        return False
    
    def _check_sell_signal(
        self,
        index: int,
        indicator: str,
        macd_histogram: pd.Series,
        kdj_k: pd.Series,
        kdj_d: pd.Series,
        threshold: Optional[float]
    ) -> bool:
        """
        Check if there's a sell signal at the given index.
        
        MACD Sell (Peak Detection):
            - Day before yesterday < yesterday (was rising)
            - Yesterday > today (now declining)
            - Yesterday > 0 (in positive territory)
        
        KDJ Sell: K and D both above threshold
        """
        if indicator.lower() == 'macd':
            # Need at least 3 data points for peak detection
            if index < 2:
                return False
            
            day_before_yesterday = macd_histogram.iloc[index - 2]
            yesterday = macd_histogram.iloc[index - 1]
            today = macd_histogram.iloc[index]
            
            if pd.isna(day_before_yesterday) or pd.isna(yesterday) or pd.isna(today):
                return False
            
            # Peak detection: was rising, now declining, in positive territory
            was_rising = day_before_yesterday < yesterday
            now_declining = yesterday > today
            in_positive_territory = yesterday > 0
            
            return was_rising and now_declining and in_positive_territory
        
        elif indicator.lower() == 'kdj':
            k_val = kdj_k.iloc[index]
            d_val = kdj_d.iloc[index]
            
            if pd.isna(k_val) or pd.isna(d_val):
                return False
            
            thresh = threshold if threshold is not None else self.kdj_sell_threshold
            return k_val > thresh and d_val > thresh
        
        return False
    
    def get_current_signal(
        self,
        df: pd.DataFrame,
        buy_indicator: str,
        sell_indicator: str,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None
    ) -> Tuple[SignalType, str, dict]:
        """
        Get the current trading signal for the most recent data.
        
        Args:
            df: DataFrame with OHLCV data
            buy_indicator: Indicator for buy signals
            sell_indicator: Indicator for sell signals
            buy_threshold: Custom KDJ buy threshold
            sell_threshold: Custom KDJ sell threshold
        
        Returns:
            Tuple of (signal_type, reasoning, indicator_values)
        """
        if len(df) < 3:
            return SignalType.HOLD, "Insufficient data for signal detection", {}
        
        # Calculate indicators
        macd_result = self.technical_analysis.calculate_macd(df)
        kdj_result = self.technical_analysis.calculate_kdj(df)
        
        if "error" in macd_result or "error" in kdj_result:
            return SignalType.HOLD, "Error calculating indicators", {}
        
        macd_histogram = macd_result["histogram"]
        kdj_k = kdj_result["k"]
        kdj_d = kdj_result["d"]
        
        # Get last index
        last_idx = len(df) - 1
        
        # Check signals
        is_buy = self._check_buy_signal(
            last_idx, buy_indicator, macd_histogram, kdj_k, kdj_d, buy_threshold
        )
        is_sell = self._check_sell_signal(
            last_idx, sell_indicator, macd_histogram, kdj_k, kdj_d, sell_threshold
        )
        
        # Build indicator values for response
        indicator_values = {
            "macd_histogram_today": round(float(macd_histogram.iloc[-1]), 4) if pd.notna(macd_histogram.iloc[-1]) else None,
            "macd_histogram_yesterday": round(float(macd_histogram.iloc[-2]), 4) if pd.notna(macd_histogram.iloc[-2]) else None,
            "kdj_k": round(float(kdj_k.iloc[-1]), 2) if pd.notna(kdj_k.iloc[-1]) else None,
            "kdj_d": round(float(kdj_d.iloc[-1]), 2) if pd.notna(kdj_d.iloc[-1]) else None
        }
        
        if len(macd_histogram) >= 3:
            indicator_values["macd_histogram_day_before"] = round(float(macd_histogram.iloc[-3]), 4) if pd.notna(macd_histogram.iloc[-3]) else None
        
        # Determine final signal and reasoning
        if is_buy and is_sell:
            return SignalType.HOLD, "Conflicting signals from buy and sell indicators", indicator_values
        elif is_buy:
            reasoning = self._build_buy_reasoning(buy_indicator, indicator_values, buy_threshold)
            return SignalType.BUY, reasoning, indicator_values
        elif is_sell:
            reasoning = self._build_sell_reasoning(sell_indicator, indicator_values, sell_threshold)
            return SignalType.SELL, reasoning, indicator_values
        else:
            reasoning = self._build_hold_reasoning(buy_indicator, sell_indicator, indicator_values)
            return SignalType.HOLD, reasoning, indicator_values
    
    def _build_buy_reasoning(self, indicator: str, values: dict, threshold: Optional[float]) -> str:
        """Build reasoning string for BUY signal."""
        if indicator.lower() == 'macd':
            yesterday = values.get("macd_histogram_yesterday", "N/A")
            today = values.get("macd_histogram_today", "N/A")
            return f"MACD golden cross: histogram crossed above zero (yesterday: {yesterday}, today: {today})"
        elif indicator.lower() == 'kdj':
            k = values.get("kdj_k", "N/A")
            d = values.get("kdj_d", "N/A")
            thresh = threshold if threshold is not None else self.kdj_buy_threshold
            return f"KDJ oversold: K={k}, D={d} (both below {thresh})"
        return "Buy signal detected"
    
    def _build_sell_reasoning(self, indicator: str, values: dict, threshold: Optional[float]) -> str:
        """Build reasoning string for SELL signal."""
        if indicator.lower() == 'macd':
            day_before = values.get("macd_histogram_day_before", "N/A")
            yesterday = values.get("macd_histogram_yesterday", "N/A")
            today = values.get("macd_histogram_today", "N/A")
            return f"MACD peak detected: histogram peaked and declining (day before: {day_before}, yesterday: {yesterday}, today: {today})"
        elif indicator.lower() == 'kdj':
            k = values.get("kdj_k", "N/A")
            d = values.get("kdj_d", "N/A")
            thresh = threshold if threshold is not None else self.kdj_sell_threshold
            return f"KDJ overbought: K={k}, D={d} (both above {thresh})"
        return "Sell signal detected"
    
    def _build_hold_reasoning(self, buy_ind: str, sell_ind: str, values: dict) -> str:
        """Build reasoning string for HOLD signal."""
        parts = []
        
        if buy_ind.lower() == 'macd' or sell_ind.lower() == 'macd':
            yesterday = values.get("macd_histogram_yesterday", "N/A")
            today = values.get("macd_histogram_today", "N/A")
            parts.append(f"MACD histogram: yesterday={yesterday}, today={today}")
        
        if buy_ind.lower() == 'kdj' or sell_ind.lower() == 'kdj':
            k = values.get("kdj_k", "N/A")
            d = values.get("kdj_d", "N/A")
            parts.append(f"KDJ: K={k}, D={d}")
        
        return "No clear signal. " + ", ".join(parts)

