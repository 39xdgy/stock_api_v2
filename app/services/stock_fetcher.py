"""
Stock Fetcher Service

Fetches stock symbols from NASDAQ FTP server and categorizes by market cap.
Uses a local JSON file as a cache to avoid repeated API calls.
"""

import json
import os
import time
import urllib.request
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

from app.core.config import settings


class StockFetcher:
    """
    Fetches and categorizes stocks by market capitalization.
    
    Market Cap Categories:
    - mega_cap: >= $200B
    - large_cap: >= $10B
    - mid_cap: $2B - $10B
    - small_cap: $300M - $2B
    - micro_cap: < $300M
    """
    
    NASDAQ_FTP_URL = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt'
    STOCKS_CACHE_FILE = 'stocks_by_market_cap.json'
    
    def __init__(self):
        self.max_workers = settings.max_workers
        self.timeout = 5
    
    def ensure_database_exists(self) -> bool:
        """
        Ensure the stocks cache file exists. Create if it doesn't.
        
        Returns:
            True if database exists or was created successfully
        """
        if os.path.exists(self.STOCKS_CACHE_FILE):
            return True
        
        print("Stocks database not found. Creating initial database...")
        try:
            data = self.update_stocks_database(force_update=True)
            return "error" not in data
        except Exception as e:
            print(f"Error creating initial database: {e}")
            return False
    
    def fetch_nasdaq_symbols(self) -> List[str]:
        """
        Fetch all NASDAQ listed stock symbols from FTP server.
        
        Returns:
            List of stock symbols (excluding ETFs)
        """
        try:
            print("Fetching NASDAQ stocks from FTP server...")
            
            with urllib.request.urlopen(self.NASDAQ_FTP_URL, timeout=30) as response:
                content = response.read().decode('utf-8')
            
            lines = content.strip().split('\n')
            stocks = []
            
            # Skip header line
            for line in lines[1:]:
                if line.strip():
                    parts = line.split('|')
                    if len(parts) >= 8:
                        symbol = parts[0].strip()
                        etf_flag = parts[6].strip()
                        
                        # Only include non-ETF stocks
                        if etf_flag == 'N':
                            stocks.append(symbol)
            
            print(f"Found {len(stocks)} NASDAQ stocks")
            return stocks
            
        except Exception as e:
            print(f"Error fetching NASDAQ stocks: {e}")
            return []
    
    def get_market_cap_category(self, market_cap: float) -> str:
        """Categorize a stock by its market cap."""
        if market_cap >= 200e9:
            return "mega_cap"
        elif market_cap >= 10e9:
            return "large_cap"
        elif market_cap >= 2e9:
            return "mid_cap"
        elif market_cap >= 300e6:
            return "small_cap"
        else:
            return "micro_cap"
    
    def check_market_cap(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get market cap info for a single stock.
        
        Returns:
            Dict with symbol, market_cap, category, etc. or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            market_cap = info.get('marketCap', 0)
            
            if market_cap and market_cap > 0:
                return {
                    "symbol": symbol,
                    "market_cap": market_cap,
                    "category": self.get_market_cap_category(market_cap),
                    "name": info.get('longName', symbol),
                    "sector": info.get('sector', 'N/A'),
                    "industry": info.get('industry', 'N/A')
                }
            return None
            
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            return None
    
    def categorize_stocks(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Categorize a list of stocks by market cap using concurrent requests.
        
        Args:
            symbols: List of stock symbols to categorize
        
        Returns:
            Dictionary with stocks organized by category
        """
        print(f"Categorizing {len(symbols)} stocks by market cap...")
        
        categorized = {
            "mega_cap": [],
            "large_cap": [],
            "mid_cap": [],
            "small_cap": [],
            "micro_cap": [],
            "uncategorized": []
        }
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.check_market_cap, symbol): symbol
                for symbol in symbols
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    if result:
                        categorized[result["category"]].append(result)
                        successful += 1
                    else:
                        categorized["uncategorized"].append({"symbol": symbol})
                        failed += 1
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
                    categorized["uncategorized"].append({"symbol": symbol})
                    failed += 1
        
        summary = {
            "total_stocks": len(symbols),
            "successful_checks": successful,
            "failed_checks": failed,
            "categories": {cat: len(stocks) for cat, stocks in categorized.items()}
        }
        
        return {
            "summary": summary,
            "stocks": categorized,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def save_to_json(self, data: Dict[str, Any]) -> bool:
        """Save categorized stocks to JSON cache file."""
        try:
            with open(self.STOCKS_CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Stocks saved to {self.STOCKS_CACHE_FILE}")
            return True
        except Exception as e:
            print(f"Error saving stocks to JSON: {e}")
            return False
    
    def load_from_json(self) -> Optional[Dict[str, Any]]:
        """Load categorized stocks from JSON cache file."""
        try:
            if os.path.exists(self.STOCKS_CACHE_FILE):
                with open(self.STOCKS_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                
                if self._validate_data(data):
                    print(f"Stocks loaded from {self.STOCKS_CACHE_FILE}")
                    return data
                else:
                    print(f"Invalid data in {self.STOCKS_CACHE_FILE}")
                    return None
            return None
        except Exception as e:
            print(f"Error loading stocks from JSON: {e}")
            return None
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate loaded data has expected structure."""
        if not isinstance(data, dict):
            return False
        
        if "summary" not in data or "stocks" not in data:
            return False
        
        required_categories = ["mega_cap", "large_cap", "mid_cap", "small_cap", "micro_cap"]
        stocks = data.get("stocks", {})
        
        return all(cat in stocks for cat in required_categories)
    
    def update_stocks_database(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Update the stocks database from NASDAQ FTP.
        
        Args:
            force_update: If True, always fetch fresh data
        
        Returns:
            Updated stocks data
        """
        if not force_update:
            existing = self.load_from_json()
            if existing:
                print("Using existing stocks database")
                return existing
        
        symbols = self.fetch_nasdaq_symbols()
        if not symbols:
            print("No symbols fetched, trying to load existing data")
            existing = self.load_from_json()
            if existing:
                return existing
            return {"error": "No stocks available"}
        
        categorized = self.categorize_stocks(symbols)
        self.save_to_json(categorized)
        
        return categorized
    
    def get_stocks_by_category(self, category: str) -> List[str]:
        """
        Get stock symbols for a specific market cap category.
        
        Args:
            category: One of mega_cap, large_cap, mid_cap, small_cap, micro_cap
        
        Returns:
            List of stock symbols
        """
        data = self.load_from_json()
        if not data:
            print(f"No stocks database found. Updating for category: {category}")
            data = self.update_stocks_database(force_update=False)
            if "error" in data:
                return []
        
        stocks = data.get("stocks", {}).get(category, [])
        return [s["symbol"] for s in stocks if isinstance(s, dict) and "symbol" in s]
    
    def get_all_stocks(self) -> List[str]:
        """Get all stock symbols from all categories."""
        data = self.load_from_json()
        if not data:
            print("No stocks database found. Updating for all stocks")
            data = self.update_stocks_database(force_update=False)
            if "error" in data:
                return []
        
        all_symbols = []
        for category in ["mega_cap", "large_cap", "mid_cap", "small_cap", "micro_cap"]:
            stocks = data.get("stocks", {}).get(category, [])
            symbols = [s["symbol"] for s in stocks if isinstance(s, dict) and "symbol" in s]
            all_symbols.extend(symbols)
        
        return all_symbols
    
    def get_large_cap_stocks(self) -> List[str]:
        """Get mega-cap and large-cap stocks combined."""
        mega = self.get_stocks_by_category("mega_cap")
        large = self.get_stocks_by_category("large_cap")
        return mega + large
    
    def get_stocks_by_categories(self, categories: List[str]) -> List[str]:
        """
        Get stocks from multiple categories.
        
        Args:
            categories: List of category names
        
        Returns:
            List of unique stock symbols
        """
        all_symbols = []
        seen = set()
        
        for category in categories:
            if category == "all":
                symbols = self.get_all_stocks()
            elif category == "large_cap":
                symbols = self.get_large_cap_stocks()
            else:
                symbols = self.get_stocks_by_category(category)
            
            for symbol in symbols:
                if symbol not in seen:
                    seen.add(symbol)
                    all_symbols.append(symbol)
        
        return all_symbols
    
    def get_stocks_summary(self) -> Dict[str, Any]:
        """Get summary of available stocks by category."""
        data = self.load_from_json()
        if not data:
            print("No stocks database found. Updating for summary")
            data = self.update_stocks_database(force_update=False)
            if "error" in data:
                return {"error": "No stocks database found"}
        
        return {
            "summary": data.get("summary", {}),
            "last_updated": data.get("last_updated", "Unknown"),
            "categories": {
                cat: len(stocks) for cat, stocks in data.get("stocks", {}).items()
            }
        }

