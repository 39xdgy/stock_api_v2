"""
Trading Simulator Service

Simulates paper trading based on buy/sell signals.
Executes trades at next day's open price after signal is generated.
"""

import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from app.services.signal_detector import SignalDetector
from app.core.config import settings


class TradingSimulator:
    """
    Paper trading simulator that executes trades based on technical signals.
    
    Trading rules:
    - Buy signal on day N close -> Execute buy at day N+1 open
    - Sell signal on day N close -> Execute sell at day N+1 open
    - Commission is applied to each trade
    - Only one position at a time (full investment)
    """
    
    def __init__(self):
        self.initial_balance = settings.initial_balance
        self.commission_rate = settings.commission_rate
        self.signal_detector = SignalDetector()
    
    def simulate(
        self,
        df: pd.DataFrame,
        buy_indicator: str,
        sell_indicator: str,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run a paper trading simulation on historical data.
        
        Args:
            df: DataFrame with OHLCV data
            buy_indicator: Indicator for buy signals ('macd' or 'kdj')
            sell_indicator: Indicator for sell signals ('macd' or 'kdj')
            buy_threshold: Custom threshold for KDJ buy
            sell_threshold: Custom threshold for KDJ sell
        
        Returns:
            Dictionary containing trading results and statistics
        """
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data for trading simulation (need >= 50 data points)"}
        
        # Generate signals
        buy_signals, sell_signals = self.signal_detector.generate_signals(
            df, buy_indicator, sell_indicator, buy_threshold, sell_threshold
        )
        
        # Execute trades
        trades, final_balance = self._execute_trades(df, buy_signals, sell_signals)
        
        # Calculate statistics
        stats = self._calculate_statistics(trades, final_balance)
        
        return {
            "trading_summary": {
                "initial_balance": self.initial_balance,
                "final_balance": round(final_balance, 2),
                "total_return": round(final_balance - self.initial_balance, 2),
                "return_percentage": round(((final_balance - self.initial_balance) / self.initial_balance) * 100, 2),
                "total_trades": len(trades),  # Count all trades (BUY + SELL) for consistency with V1
                "success_rate": stats["success_rate"],
                "avg_days_between_trades": stats["avg_trade_frequency"],
                "buy_indicator": buy_indicator,
                "sell_indicator": sell_indicator
            },
            "trades": trades,
            "statistics": stats
        }
    
    def _execute_trades(
        self,
        df: pd.DataFrame,
        buy_signals: List[int],
        sell_signals: List[int]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute trades based on signals.
        
        Uses next day's open price for execution to simulate realistic trading.
        """
        trades = []
        balance = self.initial_balance
        shares = 0.0
        position_open = False
        buy_price = 0.0
        buy_date = None
        pending_buy = False
        pending_sell = False
        signal_date = None
        
        for i in range(len(df)):
            current_date = df.index[i]
            
            # Check for buy signal on current day's close
            if buy_signals[i] == 1 and not position_open and not pending_buy:
                pending_buy = True
                signal_date = current_date
                continue
            
            # Check for sell signal on current day's close
            if sell_signals[i] == 1 and position_open and not pending_sell:
                pending_sell = True
                signal_date = current_date
                continue
            
            # Execute pending buy at next day's open
            if pending_buy and i > 0:
                execution_price = df['Open'].iloc[i]
                commission = balance * self.commission_rate
                shares = (balance - commission) / execution_price
                buy_price = execution_price
                buy_date = current_date
                position_open = True
                pending_buy = False
                
                trades.append({
                    "type": "BUY",
                    "signal_date": self._format_date(signal_date),
                    "execution_date": self._format_date(current_date),
                    "signal_price": round(df['Close'].iloc[i-1], 2),
                    "execution_price": round(execution_price, 2),
                    "shares": round(shares, 4),
                    "commission": round(commission, 2),
                    "balance_after": round(balance - commission, 2)
                })
            
            # Execute pending sell at next day's open
            elif pending_sell and i > 0:
                execution_price = df['Open'].iloc[i]
                sell_value = shares * execution_price
                commission = sell_value * self.commission_rate
                net_proceeds = sell_value - commission
                
                # Calculate profit/loss
                cost_basis = shares * buy_price + trades[-1]["commission"]
                profit_loss = net_proceeds - cost_basis
                profit_loss_pct = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
                
                # Calculate hold days
                hold_days = (current_date - buy_date).days if hasattr(current_date, '__sub__') else 0
                
                balance = net_proceeds
                
                trades.append({
                    "type": "SELL",
                    "signal_date": self._format_date(signal_date),
                    "execution_date": self._format_date(current_date),
                    "signal_price": round(df['Close'].iloc[i-1], 2),
                    "execution_price": round(execution_price, 2),
                    "shares": round(shares, 4),
                    "commission": round(commission, 2),
                    "proceeds": round(sell_value, 2),
                    "net_proceeds": round(net_proceeds, 2),
                    "profit_loss": round(profit_loss, 2),
                    "profit_loss_percentage": round(profit_loss_pct, 2),
                    "balance_after": round(balance, 2),
                    "hold_days": hold_days
                })
                
                shares = 0
                position_open = False
                pending_sell = False
        
        # Close any remaining position at end of period
        if position_open:
            current_price = df['Close'].iloc[-1]
            current_date = df.index[-1]
            sell_value = shares * current_price
            commission = sell_value * self.commission_rate
            net_proceeds = sell_value - commission
            
            cost_basis = shares * buy_price + trades[-1]["commission"]
            profit_loss = net_proceeds - cost_basis
            profit_loss_pct = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
            hold_days = (current_date - buy_date).days if hasattr(current_date, '__sub__') else 0
            
            balance = net_proceeds
            
            trades.append({
                "type": "SELL",
                "signal_date": "End of period",
                "execution_date": self._format_date(current_date),
                "signal_price": round(current_price, 2),
                "execution_price": round(current_price, 2),
                "shares": round(shares, 4),
                "commission": round(commission, 2),
                "proceeds": round(sell_value, 2),
                "net_proceeds": round(net_proceeds, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percentage": round(profit_loss_pct, 2),
                "balance_after": round(balance, 2),
                "hold_days": hold_days
            })
        
        return trades, balance
    
    def _calculate_statistics(
        self,
        trades: List[Dict[str, Any]],
        final_balance: float
    ) -> Dict[str, Any]:
        """Calculate trading statistics from executed trades."""
        if not trades:
            return self._empty_statistics()
        
        sell_trades = [t for t in trades if t["type"] == "SELL"]
        
        if not sell_trades:
            return self._empty_statistics()
        
        # Separate profitable and losing trades
        profits = [t["profit_loss"] for t in sell_trades if t["profit_loss"] > 0]
        losses = [t["profit_loss"] for t in sell_trades if t["profit_loss"] < 0]
        
        # Success rate
        success_rate = (len(profits) / len(sell_trades)) * 100 if sell_trades else 0
        
        # Average days between trades
        if len(trades) >= 2:
            first_date = pd.to_datetime(trades[0]["execution_date"])
            last_date = pd.to_datetime(trades[-1]["execution_date"])
            days_between = (last_date - first_date).days
            avg_trade_frequency = days_between / len(sell_trades) if sell_trades else 0
        else:
            avg_trade_frequency = 0
        
        # Hold days
        hold_days = [t["hold_days"] for t in sell_trades if t.get("hold_days", 0) > 0]
        avg_hold_days = sum(hold_days) / len(hold_days) if hold_days else 0
        
        return {
            "success_rate": round(success_rate, 2),
            "avg_trade_frequency": round(avg_trade_frequency, 2),
            "total_profit": round(sum(profits), 2),
            "total_loss": round(sum(losses), 2),
            "avg_profit": round(sum(profits) / len(profits), 2) if profits else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            "max_profit": round(max(profits), 2) if profits else 0,
            "max_loss": round(min(losses), 2) if losses else 0,
            "avg_hold_days": round(avg_hold_days, 1)
        }
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics when no trades occurred."""
        return {
            "success_rate": 0,
            "avg_trade_frequency": 0,
            "total_profit": 0,
            "total_loss": 0,
            "avg_profit": 0,
            "avg_loss": 0,
            "max_profit": 0,
            "max_loss": 0,
            "avg_hold_days": 0
        }
    
    def _format_date(self, date) -> str:
        """Format a date for output."""
        if hasattr(date, 'strftime'):
            return date.strftime('%Y-%m-%d %H:%M:%S')
        return str(date)

