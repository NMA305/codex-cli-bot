def run(symbol="BTCUSDT"):
    """Get crypto price. Args: symbol (str) - e.g., BTCUSDT"""
    import urllib.request, json
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    return f"{symbol}: ${float(data['lastPrice']):.2f} | 24h: {float(data['priceChangePercent']):.2f}%"
