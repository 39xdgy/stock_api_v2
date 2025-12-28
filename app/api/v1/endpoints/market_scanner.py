"""
Market Scanner Endpoint

POST /api/v1/market_scanner/scan
Scans the market for top performing stocks based on trading strategy.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.schemas.requests import MarketScanRequest
from app.services.market_scanner import MarketScanner

router = APIRouter()
market_scanner = MarketScanner()


@router.post("/scan")
async def scan_market(request: MarketScanRequest) -> Dict[str, Any]:
    """
    Scan the market for top performing stocks based on trading strategy.
    
    This endpoint analyzes stocks using MACD and/or KDJ indicators,
    simulates trading over the specified period, and returns the
    top performing stocks based on the sorting criteria.
    
    **Indicators:**
    - MACD: Buy on golden cross (histogram crosses above 0), 
            Sell on peak detection (histogram peaks and starts declining)
    - KDJ: Buy when K & D are oversold (<20), Sell when overbought (>80)
    
    **Filtering (exclude):**
    Use exclude rules to filter out stocks that don't meet criteria.
    Example: `{"field": "return_percentage", "operator": "<", "value": 10}`
    
    **Sorting:**
    Provide multiple sort rules for multi-level sorting.
    First rule is primary, subsequent rules are tie-breakers.
    Example: `[{"field": "success_rate", "order": "desc"}, {"field": "return_percentage", "order": "desc"}]`
    
    **Market Cap Categories:**
    - mega_cap: >= $200B
    - large_cap: >= $10B
    - mid_cap: $2B - $10B
    - small_cap: $300M - $2B
    - micro_cap: < $300M
    - all: All available stocks
    """
    try:
        # Convert exclude rules to dicts
        exclude_rules = None
        if request.exclude:
            exclude_rules = [rule.model_dump() for rule in request.exclude]
        
        # Convert sort rules to dicts
        sort_rules = None
        if request.sort:
            sort_rules = [rule.model_dump() for rule in request.sort]
        
        # Run scan
        result = market_scanner.scan(
            buy_indicator=request.buy_indicator,
            sell_indicator=request.sell_indicator,
            period=request.period,
            interval=request.interval,
            buy_threshold=request.buy_threshold,
            sell_threshold=request.sell_threshold,
            min_trades=request.min_trades,
            stock_list=request.stock_list,
            market_cap=request.market_cap,
            top_n=request.top_n,
            exclude_rules=exclude_rules,
            sort_rules=sort_rules
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Add metadata
        result["metadata"] = {
            "buy_indicator": request.buy_indicator,
            "sell_indicator": request.sell_indicator,
            "period": request.period,
            "interval": request.interval,
            "buy_threshold": request.buy_threshold,
            "sell_threshold": request.sell_threshold,
            "min_trades": request.min_trades,
            "market_cap_filter": request.market_cap,
            "custom_stocks_used": request.stock_list is not None,
            "exclude_rules_applied": len(exclude_rules) if exclude_rules else 0,
            "sort_rules_applied": len(sort_rules) if sort_rules else 0,
            "top_n_requested": request.top_n,
            "top_n_returned": len(result.get("top_results", []))
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in market scan: {str(e)}"
        )


@router.get("/criteria")
async def get_scan_criteria() -> Dict[str, Any]:
    """
    Get available options for scan criteria.
    
    Returns all valid values for indicators, periods, intervals,
    market cap filters, sortable fields, and exclude operators.
    """
    return market_scanner.get_scan_criteria_options()

