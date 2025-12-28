# Stock API V2

A lightweight FastAPI application for stock trading signals with MACD peak detection.

## Features

- **MACD and KDJ indicators only** - Streamlined for essential technical analysis
- **New MACD sell logic** - Peak detection instead of death cross
- **Flexible filtering** - Exclude rules with operators (`<`, `>`, `<=`, `>=`, `==`, `!=`)
- **Multi-level sorting** - Primary and secondary sort criteria
- **No database required** - Simple, stateless API

## Key Differences from V1

| Feature | V1 | V2 |
|---------|-----|-----|
| Indicators | RSI, MACD, KDJ | MACD, KDJ only |
| MACD Sell | Death cross (histogram < 0) | Peak detection (histogram declining) |
| Filtering | Basic sort_by | Flexible exclude rules |
| Sorting | Single field | Multi-level sorting |
| Database | MongoDB | None |

## MACD Sell Logic (V2)

Instead of waiting for the histogram to cross below zero (death cross), V2 detects when the histogram **peaks and starts declining**:

```
Sell when:
- day_before_yesterday_macdh < yesterday_macdh  (was rising)
- yesterday_macdh > today_macdh                  (now declining)
- yesterday_macdh > 0                             (in positive territory)
```

This allows selling at the peak rather than waiting for a reversal.

## API Endpoints

### POST `/api/v1/market_scanner/scan`

Scan the market for top performing stocks.

**Request Body:**
```json
{
    "buy_indicator": "macd",
    "sell_indicator": "macd",
    "period": "6mo",
    "interval": "1d",
    "min_trades": 3,
    "stock_list": ["AAPL", "GOOGL", "MSFT"],
    "market_cap": ["mega_cap", "large_cap"],
    "top_n": 10,
    "exclude": [
        {"field": "return_percentage", "operator": "<", "value": 10}
    ],
    "sort": [
        {"field": "success_rate", "order": "desc"},
        {"field": "return_percentage", "order": "desc"}
    ]
}
```

### POST `/api/v1/trading_signals/current`

Get current trading signals for stocks.

**Request Body:**
```json
{
    "stocks": ["AAPL", "GOOGL", "MSFT"],
    "buy_indicator": "macd",
    "sell_indicator": "macd",
    "period": "3mo"
}
```

**Response:**
```json
{
    "signals": [
        {
            "stock": "AAPL",
            "signal": "BUY",
            "current_price": 150.25,
            "indicators": {
                "macd_histogram_today": 0.5,
                "macd_histogram_yesterday": -0.2
            },
            "reasoning": "MACD golden cross: histogram crossed above zero"
        }
    ]
}
```

## Quick Start

### Local Development

```bash
cd stock_api_V2
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker

```bash
docker build -t stock-api-v2 .
docker run -p 8001:8001 stock-api-v2
```

## Testing

Run the MACD comparison test to verify calculations match V1:

```bash
python3 test_macd_comparison.py
```

## Available Options

### Indicators
- `macd` - Moving Average Convergence Divergence
- `kdj` - Stochastic Oscillator (KDJ)

### Periods
- `1mo`, `3mo`, `6mo`, `1y`, `2y`

### Market Cap Categories
- `mega_cap` - >= $200B
- `large_cap` - >= $10B
- `mid_cap` - $2B - $10B
- `small_cap` - $300M - $2B
- `micro_cap` - < $300M
- `all` - All available stocks

### Exclude Operators
- `<`, `>`, `<=`, `>=`, `==`, `!=`

### Sortable Fields
- `return_percentage`
- `success_rate`
- `total_trades`
- `avg_days_between_trades`
- `final_balance`
- `total_return`
- `avg_profit`, `avg_loss`
- `max_profit`, `max_loss`

## License

MIT

