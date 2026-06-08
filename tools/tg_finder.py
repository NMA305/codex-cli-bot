"""Telegram Group Finder - Search & validate Telegram groups"""
import urllib.request, json, re, time
from urllib.parse import quote

TG_TOKEN = "YOUR_TG_BOT2_TOKEN"

def run(keywords, max_results=30):
    """
    Search for Telegram groups/channels by keywords.
    Validates links and returns only working ones.
    """
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36"}
    
    # Search queries
    search_queries = [
        f"site:t.me {keywords}",
        f"telegram group {keywords} invite",
        f"telegram channel {keywords}",
        f"تليقرام {keywords}",
        f"رابط تليقرام {keywords}",
        f"t.me/joinchat {keywords}",
    ]
    
    for query in search_queries[:4]:
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode()
                # Find ALL t.me links
                links = re.findall(r'(https?://t\.me/[a-zA-Z0-9_/+-]+)', html)
                for link in links:
                    if link not in [r["link"] for r in results]:
                        results.append({
                            "name": link.split("/")[-1],
                            "link": link,
                            "type": "group" if "joinchat" in link or "+" in link.split("/")[-1] else "channel",
                            "source": "web",
                            "valid": None
                        })
        except: pass
        time.sleep(0.5)
    
    # Validate links by trying to access them
    print(f"Found {len(results)} links, validating...")
    for g in results:
        try:
            req = urllib.request.Request(g["link"], headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                g["valid"] = r.status == 200
        except:
            g["valid"] = False
        time.sleep(0.3)
    
    # Return only valid links
    valid = [g for g in results if g["valid"]]
    print(f"Valid: {len(valid)}/{len(results)}")
    return valid[:max_results]
