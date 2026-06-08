"""Telegram Directory Scraper - Scrape group directories for NSFW content"""
import urllib.request, json, re, time
from urllib.parse import quote

def run(query="arab", max_results=50):
    """
    Scrape Telegram directories for groups matching query.
    Returns list of valid group links.
    """
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36"}
    
    # Known directories to scrape
    sources = [
        # tgstat.com - Telegram statistics site
        f"https://tgstat.com/en/search?q={quote(query)}",
        "https://tgstat.com/en/categories/adult-18-plus/",
        f"https://tgstat.com/ru/search?q={quote(query)}",
        "https://tgstat.com/ru/channels/top/adult-18-plus/",
        # Other directories
        f"https://tlgrm.eu/search?q={quote(query)}",
        f"https://telegramchannels.me/search/{quote(query)}",
        # Category pages
        "https://tlgrm.eu/channels/adult",
        "https://tlgrm.eu/channels/xxx",
        "https://tlgrm.eu/channels/arabic",
    ]
    
    for source in sources:
        try:
            req = urllib.request.Request(source, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode()
                
                # Extract group links
                links = re.findall(r'(https?://t\.me/[a-zA-Z0-9_/+]+)', html)
                for link in links:
                    if link not in [r["link"] for r in results]:
                        name = link.split("/")[-1]
                        results.append({
                            "name": name,
                            "link": link,
                            "type": "channel",
                            "source": source
                        })
        except: pass
        time.sleep(1)
    
    return results[:max_results]
