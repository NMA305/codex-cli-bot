# Tool Registry - agents can create, register and use tools
import os, json, logging, importlib.util, sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
REGISTRY_FILE = TOOLS_DIR / "registry.json"
log = logging.getLogger("codex-bot.tools")

def load_registry():
    if REGISTRY_FILE.exists():
        try: return json.loads(REGISTRY_FILE.read_text())
        except: pass
    return {"tools": {}, "versions": {}}

def save_registry(reg):
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False))

def register_tool(name, description, code, version=1):
    reg = load_registry()
    reg["tools"][name] = {"name": name, "desc": description, "file": f"{name}.py", "version": version}
    reg["versions"][name] = version
    save_registry(reg)
    
    # Write the tool file
    tool_file = TOOLS_DIR / f"{name}.py"
    tool_file.write_text(code, "utf-8")
    log.info(f"🔧 Tool created: {name} v{version}")
    return True

def get_tool(name):
    reg = load_registry()
    if name not in reg["tools"]: return None
    return reg["tools"][name]

def call_tool(name, *args, **kwargs):
    """Dynamically import and call a tool."""
    try:
        spec = importlib.util.spec_from_file_location(name, TOOLS_DIR / f"{name}.py")
        if not spec or not spec.loader: return f"❌ Tool {name} not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'run'):
            return module.run(*args, **kwargs)
        return f"❌ Tool {name} has no run() function"
    except Exception as e:
        return f"❌ Tool error: {e}"

def list_tools():
    reg = load_registry()
    return [(t["name"], t["desc"], t["version"]) for t in reg["tools"].values()]

# Built-in tools that ship with the bot
BUILTIN_TOOLS = {
    "search_web": {
        "description": "Search the web for information",
        "code": '''def run(query):
    """Search the web. Args: query (str)"""
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if not results: return "No results"
    return "\\n".join(f"- {r['title']}: {r['body'][:100]}" for r in results)
'''
    },
    "get_crypto_price": {
        "description": "Get current cryptocurrency price",
        "code": '''def run(symbol="BTCUSDT"):
    """Get crypto price. Args: symbol (str) - e.g., BTCUSDT"""
    import urllib.request, json
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    return f"{symbol}: ${float(data['lastPrice']):.2f} | 24h: {float(data['priceChangePercent']):.2f}%"
'''
    },
    "get_weather": {
        "description": "Get weather for any city",
        "code": '''def run(city):
    """Get weather. Args: city (str)"""
    import urllib.request
    from urllib.parse import quote
    url = f"https://wttr.in/{quote(city)}?format=%C+%t+%w&lang=ar"
    with urllib.request.urlopen(url, timeout=10) as r:
        return f"Weather in {city}: {r.read().decode().strip()}"
'''
    }
}
