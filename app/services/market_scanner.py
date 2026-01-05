"""
Market Scanner Service

Scans the market for top performing stocks based on trading strategy.
Supports flexible filtering (exclude rules) and multi-level sorting.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

from app.services.stock_fetcher import StockFetcher
from app.services.trading_simulator import TradingSimulator
from app.core.config import settings


class MarketScanner:
    """
    Scans the market for stocks matching trading criteria.
    
    Features:
    - Scans multiple stocks concurrently
    - Applies exclude rules to filter results
    - Supports multi-level sorting
    - Rate limiting to avoid API throttling
    """
    
    def __init__(self):
        self.stock_fetcher = StockFetcher()
        self.trading_simulator = TradingSimulator()
        self.max_workers = settings.max_workers
        self.batch_size = settings.batch_size
        self.rate_limit_delay = settings.rate_limit_delay
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
    
    def scan(
        self,
        buy_indicator: str,
        sell_indicator: str,
        period: str = "6mo",
        interval: str = "1d",
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None,
        min_trades: int = 3,
        stock_list: Optional[List[str]] = None,
        market_cap: Optional[List[str]] = None,
        top_n: int = 10,
        exclude_rules: Optional[List[Dict[str, Any]]] = None,
        sort_rules: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Scan the market for top performing stocks.
        
        Args:
            buy_indicator: Indicator for buy signals ('macd' or 'kdj')
            sell_indicator: Indicator for sell signals ('macd' or 'kdj')
            period: Historical data period (e.g., '6mo', '1y')
            interval: Data interval (e.g., '1d')
            buy_threshold: Custom KDJ buy threshold
            sell_threshold: Custom KDJ sell threshold
            min_trades: Minimum number of trades required
            stock_list: Custom list of stocks to scan
            market_cap: Market cap categories to scan
            top_n: Maximum number of results to return
            exclude_rules: Rules to filter out stocks
            sort_rules: Rules for sorting results
        
        Returns:
            Dictionary with scan results and metadata
        """
        # Validate indicators
        valid_indicators = ['macd', 'kdj']
        if buy_indicator.lower() not in valid_indicators:
            return {"error": f"Invalid buy indicator. Must be one of: {valid_indicators}"}
        if sell_indicator.lower() not in valid_indicators:
            return {"error": f"Invalid sell indicator. Must be one of: {valid_indicators}"}
        
        # Get stocks to scan
        stocks_to_scan = self._get_stocks_to_scan(stock_list, market_cap)
        if not stocks_to_scan:
            return {"error": "No stocks to scan"}
        
        print(f"Scanning {len(stocks_to_scan)} stocks...")
        
        # Adjust rate limiting for large scans
        self._adjust_rate_limiting(len(stocks_to_scan))
        
        # Scan stocks
        results, successful, failed = self._scan_stocks(
            stocks_to_scan, buy_indicator, sell_indicator,
            period, interval, buy_threshold, sell_threshold, min_trades
        )
        
        # Apply exclude rules
        if exclude_rules:
            results = self._apply_exclude_rules(results, exclude_rules)
        
        # Apply sorting
        results = self._apply_sorting(results, sort_rules)
        
        # Limit to top N
        if top_n and top_n > 0:
            results = results[:top_n]
        
        # Extract just the stock symbols for easy access
        top_stocks = [r["stock"] for r in results]
        
        return {
            "scan_summary": {
                "total_stocks_scanned": len(stocks_to_scan),
                "successful_scans": successful,
                "failed_scans": failed,
                "stocks_after_filters": len(results),
                "scan_criteria": {
                    "buy_indicator": buy_indicator,
                    "sell_indicator": sell_indicator,
                    "period": period,
                    "interval": interval,
                    "min_trades": min_trades
                }
            },
            "top_stocks": top_stocks,
            "top_results": results
        }
    
    def _get_stocks_to_scan(
        self,
        stock_list: Optional[List[str]],
        market_cap: Optional[List[str]]
    ) -> List[str]:
        """Determine which stocks to scan based on parameters."""
        if stock_list:
            return stock_list
        
        if market_cap:
            return self.stock_fetcher.get_stocks_by_categories(market_cap)
        
        # Default to large cap stocks
        return self.stock_fetcher.get_large_cap_stocks()
    
    def _adjust_rate_limiting(self, num_stocks: int):
        """Adjust rate limiting parameters based on scan size."""
        if num_stocks > 1000:
            self.rate_limit_delay = 0.2
            self.max_workers = 10
            self.batch_size = 25
        elif num_stocks > 500:
            self.rate_limit_delay = 0.15
            self.max_workers = 15
            self.batch_size = 35
        else:
            self.rate_limit_delay = settings.rate_limit_delay
            self.max_workers = settings.max_workers
            self.batch_size = settings.batch_size
    
    def _scan_stocks(
        self,
        stocks: List[str],
        buy_indicator: str,
        sell_indicator: str,
        period: str,
        interval: str,
        buy_threshold: Optional[float],
        sell_threshold: Optional[float],
        min_trades: int
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Scan all stocks and return results."""
        results = []
        successful = 0
        failed = 0
        
        # Process in batches for large scans
        if len(stocks) > self.batch_size:
            for i in range(0, len(stocks), self.batch_size):
                batch = stocks[i:i + self.batch_size]
                batch_results, batch_success, batch_failed = self._scan_batch(
                    batch, buy_indicator, sell_indicator,
                    period, interval, buy_threshold, sell_threshold, min_trades
                )
                results.extend(batch_results)
                successful += batch_success
                failed += batch_failed
                
                # Delay between batches
                if i + self.batch_size < len(stocks):
                    time.sleep(5)
        else:
            results, successful, failed = self._scan_batch(
                stocks, buy_indicator, sell_indicator,
                period, interval, buy_threshold, sell_threshold, min_trades
            )
        
        return results, successful, failed
    
    def _scan_batch(
        self,
        stocks: List[str],
        buy_indicator: str,
        sell_indicator: str,
        period: str,
        interval: str,
        buy_threshold: Optional[float],
        sell_threshold: Optional[float],
        min_trades: int
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Scan a batch of stocks concurrently."""
        results = []
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._scan_single_stock,
                    symbol, buy_indicator, sell_indicator,
                    period, interval, buy_threshold, sell_threshold
                ): symbol for symbol in stocks
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    if result and "error" not in result:
                        if result["trading_summary"]["total_trades"] >= min_trades:
                            results.append(result)
                            successful += 1
                        else:
                            failed += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"Error scanning {symbol}: {e}")
                    failed += 1
        
        return results, successful, failed
    
    def _scan_single_stock(
        self,
        symbol: str,
        buy_indicator: str,
        sell_indicator: str,
        period: str,
        interval: str,
        buy_threshold: Optional[float],
        sell_threshold: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """Scan a single stock with retry logic."""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                
                # Fetch historical data
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval, auto_adjust=True)
                
                if df.empty or len(df) < 50:
                    return {"error": f"Insufficient data for {symbol}"}
                
                # Simulate trading
                result = self.trading_simulator.simulate(
                    df, buy_indicator, sell_indicator,
                    buy_threshold, sell_threshold
                )
                
                if "error" in result:
                    return result
                
                # Add stock symbol
                result["stock"] = symbol.upper()
                
                # Remove detailed trades to reduce response size
                result.pop("trades", None)
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                return {"error": f"Error scanning {symbol}: {str(e)}"}
        
        return {"error": f"Failed to scan {symbol} after {self.max_retries} attempts"}
    
    def _apply_exclude_rules(
        self,
        results: List[Dict[str, Any]],
        rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply exclude rules to filter results.
        
        Each rule has: field, operator, value
        Operators: <, >, <=, >=, ==, !=
        """
        filtered = []
        
        for result in results:
            exclude = False
            summary = result.get("trading_summary", {})
            stats = result.get("statistics", {})
            
            for rule in rules:
                field = rule.get("field", "")
                operator = rule.get("operator", "")
                value = rule.get("value", 0)
                
                # Get field value from summary or statistics
                field_value = summary.get(field) or stats.get(field)
                
                if field_value is None:
                    continue
                
                # Apply operator
                if self._evaluate_condition(field_value, operator, value):
                    exclude = True
                    break
            
            if not exclude:
                filtered.append(result)
        
        return filtered
    
    def _evaluate_condition(self, field_value: float, operator: str, value: float) -> bool:
        """Evaluate a condition (returns True if should be EXCLUDED)."""
        try:
            if operator == "<":
                return field_value < value
            elif operator == ">":
                return field_value > value
            elif operator == "<=":
                return field_value <= value
            elif operator == ">=":
                return field_value >= value
            elif operator == "==":
                return field_value == value
            elif operator == "!=":
                return field_value != value
            return False
        except (TypeError, ValueError):
            return False
    
    def _apply_sorting(
        self,
        results: List[Dict[str, Any]],
        sort_rules: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, Any]]:
        """
        Apply multi-level sorting to results.
        
        Each rule has: field, order (asc/desc)
        First rule is primary sort, subsequent rules are tie-breakers.
        """
        if not results:
            return results
        
        # Default sorting: by return_percentage descending
        if not sort_rules:
            sort_rules = [{"field": "return_percentage", "order": "desc"}]
        
        def get_sort_key(item: Dict[str, Any]) -> tuple:
            """Generate a tuple key for sorting."""
            key_parts = []
            summary = item.get("trading_summary", {})
            stats = item.get("statistics", {})
            
            for rule in sort_rules:
                field = rule.get("field", "")
                order = rule.get("order", "desc").lower()
                
                value = summary.get(field) or stats.get(field) or 0
                
                # Negate for descending order
                if order == "desc":
                    value = -value if isinstance(value, (int, float)) else value
                
                key_parts.append(value)
            
            return tuple(key_parts)
        
        return sorted(results, key=get_sort_key)
    
    def get_scan_criteria_options(self) -> Dict[str, Any]:
        """Return available options for scan criteria."""
        return {
            "indicators": ["macd", "kdj"],
            "periods": ["1mo", "3mo", "6mo", "1y", "2y"],
            "intervals": ["1d", "1wk"],
            "market_cap_options": ["mega_cap", "large_cap", "mid_cap", "small_cap", "micro_cap", "all"],
            "sortable_fields": [
                "return_percentage",
                "success_rate",
                "total_trades",
                "avg_days_between_trades",
                "final_balance",
                "total_return",
                "avg_profit",
                "avg_loss",
                "max_profit",
                "max_loss"
            ],
            "exclude_operators": ["<", ">", "<=", ">=", "==", "!="]
        }

