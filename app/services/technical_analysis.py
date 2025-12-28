"""
Technical Analysis Service

Calculates MACD and KDJ indicators using the same formulas as Webull.
This ensures consistency between what users see in their trading app
and what this API calculates.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple


class TechnicalAnalysis:
    """
    Technical analysis calculations for MACD and KDJ indicators.
    
    The calculations match Webull's implementation to ensure consistency.
    """
    
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, Any]:
        """
        Calculate MACD (Moving Average Convergence Divergence) indicator.
        
        MACD Line = Fast EMA - Slow EMA
        Signal Line = EMA of MACD Line
        Histogram = MACD Line - Signal Line
        
        Args:
            df: DataFrame with OHLCV data (must have 'Close' column)
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
        
        Returns:
            Dictionary containing MACD values, or error if insufficient data
        """
        if df.empty or len(df) < slow_period:
            return {"error": "Insufficient data for MACD calculation"}
        
        # Calculate EMAs using pandas ewm (matches Webull's calculation)
        ema_fast = df['Close'].ewm(span=fast_period).mean()
        ema_slow = df['Close'].ewm(span=slow_period).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Histogram (MACD - Signal)
        histogram = macd_line - signal_line
        
        return {
            "indicator": "MACD",
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
            "latest": {
                "macd": round(float(macd_line.iloc[-1]), 4) if pd.notna(macd_line.iloc[-1]) else None,
                "signal": round(float(signal_line.iloc[-1]), 4) if pd.notna(signal_line.iloc[-1]) else None,
                "histogram": round(float(histogram.iloc[-1]), 4) if pd.notna(histogram.iloc[-1]) else None
            }
        }
    
    def calculate_kdj(
        self,
        df: pd.DataFrame,
        k_period: int = 9,
        d_period: int = 3,
        j_period: int = 3
    ) -> Dict[str, Any]:
        """
        Calculate KDJ (Stochastic Oscillator) indicator using Webull-style smoothing.
        
        RSV = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        K = 2/3 * prev_K + 1/3 * RSV
        D = 2/3 * prev_D + 1/3 * K
        J = 3K - 2D
        
        Args:
            df: DataFrame with OHLCV data (must have High, Low, Close columns)
            k_period: Period for RSV calculation (default: 9)
            d_period: D smoothing period (default: 3)
            j_period: J calculation period (default: 3)
        
        Returns:
            Dictionary containing KDJ values, or error if insufficient data
        """
        if df.empty or len(df) < k_period:
            return {"error": "Insufficient data for KDJ calculation"}
        
        # Calculate RSV (Raw Stochastic Value)
        low_min = df['Low'].rolling(window=k_period, min_periods=1).min()
        high_max = df['High'].rolling(window=k_period, min_periods=1).max()
        
        # Avoid division by zero
        denominator = high_max - low_min
        denominator = denominator.replace(0, 1)
        
        rsv = ((df['Close'] - low_min) / denominator) * 100
        
        # Initialize K and D series
        k_values = pd.Series(0.0, index=rsv.index)
        d_values = pd.Series(0.0, index=rsv.index)
        
        # Set initial K and D to 50 (Webull convention)
        first_valid = rsv.first_valid_index()
        if first_valid is not None:
            k_values[first_valid] = 50
            d_values[first_valid] = 50
            
            # Calculate K and D with Webull smoothing (2/3 previous + 1/3 current)
            for i in range(rsv.index.get_loc(first_valid) + 1, len(rsv)):
                k_values.iloc[i] = 2/3 * k_values.iloc[i-1] + 1/3 * rsv.iloc[i]
                d_values.iloc[i] = 2/3 * d_values.iloc[i-1] + 1/3 * k_values.iloc[i]
        
        # Calculate J
        j_values = 3 * k_values - 2 * d_values
        
        return {
            "indicator": "KDJ",
            "k_period": k_period,
            "d_period": d_period,
            "j_period": j_period,
            "k": k_values,
            "d": d_values,
            "j": j_values,
            "latest": {
                "k": round(float(k_values.iloc[-1]), 2) if pd.notna(k_values.iloc[-1]) else None,
                "d": round(float(d_values.iloc[-1]), 2) if pd.notna(d_values.iloc[-1]) else None,
                "j": round(float(j_values.iloc[-1]), 2) if pd.notna(j_values.iloc[-1]) else None
            }
        }
    
    def calculate_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate both MACD and KDJ indicators.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Dictionary containing both indicators
        """
        if df.empty:
            return {"error": "No data provided for analysis"}
        
        return {
            "macd": self.calculate_macd(df),
            "kdj": self.calculate_kdj(df)
        }
    
    def get_macd_histogram_series(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """
        Get MACD histogram as a pandas Series for signal detection.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Pandas Series of histogram values, or None if error
        """
        result = self.calculate_macd(df)
        if "error" in result:
            return None
        return result["histogram"]
    
    def get_kdj_series(self, df: pd.DataFrame) -> Optional[Tuple[pd.Series, pd.Series, pd.Series]]:
        """
        Get KDJ K, D, J values as pandas Series for signal detection.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Tuple of (K, D, J) Series, or None if error
        """
        result = self.calculate_kdj(df)
        if "error" in result:
            return None
        return result["k"], result["d"], result["j"]

