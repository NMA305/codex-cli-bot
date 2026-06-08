"""Trading Module - Binance + News + Signals"""
import json, logging, os, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

log = logging.getLogger("codex-bot.trading")

# ─── Binance Public API ────────────────────────────────────────────────
def binance_price(symbol="BTCUSDT"):
    """Get live price from Binance (no key needed)."""
    try:
        symbol = symbol.upper().strip()
        if not symbol.endswith("USDT"): symbol += "USDT"
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        p = float(data["lastPrice"])
        h = float(data["highPrice"])
        l = float(data["lowPrice"])
        c = float(data["priceChangePercent"])
        v = float(data["volume"])
        em = "🟢" if c >= 0 else "🔴"
        return f"💰 *{symbol}*\nالسعر: {p:.2f}\nأعلى: {h:.2f}\nأدنى: {l:.2f}\nالتغيير: {em} {c:.2f}%\nالحجم: {v:.2f}"
    except urllib.error.HTTPError as e:
        if e.code == 400: return "❌ رمز غير صحيح. مثال: BTC, ETH, SOL"
        return f"❌ {e}"
    except Exception as e:
        return f"❌ {e}"


def binance_multi(pairs=None):
    """Get prices for multiple pairs."""
    if not pairs: pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    results = []
    for p in pairs:
        r = binance_price(p)
        results.append(r)
        time.sleep(0.2)
    return "\n\n".join(results)


def binance_klines(symbol="BTCUSDT", interval="1h", limit=20):
    """Get candlestick data for analysis."""
    try:
        import requests
        url = f"https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if not data or "code" in data: return "❌ خطأ"
        closes = [float(c[4]) for c in data]
        avg = sum(closes) / len(closes)
        current = closes[-1]
        trend = "صاعد 📈" if current > avg else "هابط 📉"
        return f"📊 *تحليل {symbol}*\nآخر {limit} شمعة ({interval})\nالمتوسط: {avg:.2f}\nالحالي: {current:.2f}\nالاتجاه: {trend}"
    except Exception as e:
        return f"❌ {e}"


# ─── News Monitoring ────────────────────────────────────────────────────
def crypto_news(max_items=5):
    """Get latest crypto news from RSS feeds (free)."""
    try:
        import feedparser
        feeds = [
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
        ]
        articles = []
        for feed_url in feeds:
            try:
                f = feedparser.parse(feed_url)
                for entry in f.entries[:3]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "source": feed_url.split(".")[1].capitalize() if "//" in feed_url else "News"
                    })
            except:
                continue
        
        if not articles: return "❌ ما لقيت أخبار حالياً."
        # Remove duplicates
        seen = set()
        unique = []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)
        
        result = "📰 *آخر أخبار الكريبتو:*\n\n"
        for i, a in enumerate(unique[:max_items], 1):
            result += f"{i}. *{a['title']}*\n[اقرأ المزيد]({a['link']})\n\n"
        return result[:4000]
    except Exception as e:
        return f"❌ {e}"


# ─── Trading Signals ────────────────────────────────────────────────────
def analyze_market(pair="BTCUSDT"):
    """Simple market analysis for signals."""
    try:
        import requests
        s = pair.upper().strip()
        if not s.endswith("USDT"): s += "USDT"
        
        # Get 24hr ticker
        ticker = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}", timeout=10).json()
        if "code" in ticker: return "❌ رمز غير صحيح"
        
        price = float(ticker["lastPrice"])
        change = float(ticker["priceChangePercent"])
        high = float(ticker["highPrice"])
        low = float(ticker["lowPrice"])
        volume = float(ticker["volume"])
        
        # Get recent klines for trend analysis
        klines = requests.get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=12", timeout=10).json()
        if not klines or "code" in klines: return "❌"
        
        closes = [float(k[4]) for k in klines]
        sma_short = sum(closes[-4:]) / 4
        sma_long = sum(closes) / len(closes)
        
        # Simple signal generation
        signal = "محايد ⏸️"
        reason = []
        if change > 5: signal = "شراء قوي 🟢🟢"; reason.append(f"ارتفاع {change:.1f}%")
        elif change > 2: signal = "شراء 🟢"; reason.append(f"ارتفاع {change:.1f}%")
        elif change < -5: signal = "بيع قوي 🔴🔴"; reason.append(f"انخفاض {change:.1f}%")
        elif change < -2: signal = "بيع 🔴"; reason.append(f"انخفاض {change:.1f}%")
        
        if sma_short > sma_long: reason.append("اتجاه قصير صاعد")
        else: reason.append("اتجاه قصير هابط")
        
        result = f"📈 *تحليل {s}*\n"
        result += f"السعر: {price:.2f}\n"
        result += f"التغيير: {change:.2f}%\n"
        result += f"الإشارة: {signal}\n"
        result += f"الأسباب: {', '.join(reason)}\n"
        result += f"\nنطاق اليوم: {low:.2f} - {high:.2f}"
        
        return result
    except Exception as e:
        return f"❌ {e}"


# ─── Binance Trading (requires API keys) ────────────────────────────────
def binance_trade(symbol="BTCUSDT", side="BUY", quantity=None, api_key="", api_secret=""):
    """Execute a trade on Binance (requires API keys)."""
    if not api_key or not api_secret:
        return "❌ ما في API Keys. خليهم في ملف `config.json`:\n/binance_config مفاتيحك"
    
    try:
        from binance.client import Client
        client = Client(api_key, api_secret)
        
        symbol = symbol.upper().strip()
        if not symbol.endswith("USDT"): symbol += "USDT"
        
        # Get account info first
        account = client.get_account()
        balances = {b["asset"]: float(b["free"]) for b in account["balances"]}
        
        base_asset = symbol.replace("USDT", "")
        
        if side == "BUY":
            # Calculate quantity based on USDT balance
            usdt_balance = balances.get("USDT", 0)
            if usdt_balance <= 0: return "❌ ما فيك رصيد USDT"
            
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            
            if quantity:
                qty = quantity
            else:
                # Use 10% of balance by default
                qty = round((usdt_balance * 0.1) / price, 6)
            
            if qty * price > usdt_balance:
                qty = round(usdt_balance * 0.95 / price, 6)
            
            if qty <= 0: return "❌ الكمية صفر"
            
            order = client.order_market_buy(symbol=symbol, quantity=qty)
            return f"✅ *أمر شراء منفذ!*\n{symbol}: {qty} بسعر {price:.2f}\nالمجموع: ${qty * price:.2f}"
        
        elif side == "SELL":
            base_balance = balances.get(base_asset, 0)
            if base_balance <= 0: return f"❌ ما عندك {base_asset}"
            
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            
            if quantity:
                qty = quantity
            else:
                qty = round(base_balance * 0.5, 6)
            
            if qty > base_balance:
                qty = round(base_balance * 0.95, 6)
            
            if qty <= 0: return "❌ الكمية صفر"
            
            order = client.order_market_sell(symbol=symbol, quantity=qty)
            return f"✅ *أمر بيع منفذ!*\n{symbol}: {qty} بسعر {price:.2f}\nالمجموع: ${qty * price:.2f}"
    
    except Exception as e:
        error_str = str(e)
        if "-1013" in error_str: return "❌ مشكلة في الكمية. جرب كمية أقل."
        if "-2010" in error_str: return "❌ الرصيد غير كافي."
        if "APIError" in error_str: return f"❌ خطأ API: {error_str[:100]}"
        return f"❌ {error_str[:100]}"


def get_account_summary(api_key="", api_secret=""):
    """Get account balance summary."""
    if not api_key or not api_secret:
        return "❌ ما في API Keys"
    try:
        from binance.client import Client
        client = Client(api_key, api_secret)
        account = client.get_account()
        balances = {b["asset"]: float(b["free"]) + float(b["locked"]) for b in account["balances"] if float(b["free"]) + float(b["locked"]) > 0}
        
        result = "💼 *محفظة Binance:*\n"
        total_usdt = 0
        for asset, amount in sorted(balances.items(), key=lambda x: -x[1]):
            if asset == "USDT":
                result += f"💰 USDT: {amount:.2f}\n"
                total_usdt += amount
            else:
                # Get price in USDT
                try:
                    ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                    price = float(ticker["price"])
                    usdt_value = amount * price
                    total_usdt += usdt_value
                    result += f"  {asset}: {amount:.6f} (${usdt_value:.2f})\n"
                except:
                    result += f"  {asset}: {amount:.6f}\n"
        
        result += f"\n💵 *المجموع: ${total_usdt:.2f}*"
        return result
    except Exception as e:
        return f"❌ {e}"


# ─── Config Management ──────────────────────────────────────────────────
CONFIG_PATH = Path("/root/telegram-bot/trading_config.json")

def save_config(api_key="", api_secret=""):
    """Save Binance API keys."""
    cfg = {"api_key": api_key, "api_secret": api_secret}
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    return "✅ تم حفظ المفاتيح!"

def load_config():
    """Load Binance API keys."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except:
            pass
    return {"api_key": "", "api_secret": ""}
