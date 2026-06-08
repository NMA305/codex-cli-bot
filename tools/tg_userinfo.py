"""Telegram User Info Checker - Get info about Telegram users"""
import urllib.request, json, time
from pathlib import Path

TOKEN = "YOUR_TG_BOT2_TOKEN"
CACHE_FILE = Path("/root/telegram-bot/user_cache.json")

def load_cache():
    if CACHE_FILE.exists():
        try: return json.loads(CACHE_FILE.read_text())
        except: pass
    return {"users": {}}

def save_cache(data):
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def run(target):
    """
    Get info about a Telegram user.
    Args: target (str) - @username, user ID, or name
    Returns: info string
    """
    cache = load_cache()
    
    # If starts with @, try to resolve
    target = target.strip()
    
    # Try as user ID first
    try:
        chat_id = int(target)
        url = f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id={chat_id}"
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        if data.get("ok"):
            info = data["result"]
            result = f"👤 *معلومات المستخدم*\n"
            result += f"🆔 ID: {info.get('id')}\n"
            result += f"📝 الاسم: {info.get('first_name', '')} {info.get('last_name', '')}\n"
            if info.get("username"):
                result += f"🔗 @{info['username']}\n"
            result += f"📌 النوع: {info.get('type')}\n"
            if info.get("is_bot"):
                result += "🤖 هذا بوت\n"
            result += f"✅ تم التحميل: {time.strftime('%H:%M:%S')}"
            
            # Cache it
            cache["users"][str(info["id"])] = info
            save_cache(cache)
            
            return result
    except ValueError:
        pass
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return "❌ ما يقدر يجيب معلومات باليوزرنيم (@). يحتاج ID رقمي"
        return f"❌ خطأ: {e.code}"
    
    # Try resolving @username via known chats in storage
    if target.startswith("@"):
        # Check if user has chatted with bot before (we can get their info)
        try:
            # Try to resolve via updates (but we already consumed them)
            # Alternative: search in our cached users
            for uid, info in cache.get("users", {}).items():
                if info.get("username", "").lower() == target[1:].lower():
                    return run(uid)
        except: pass
        
        return f"⚠️ ما اقدر اجيب معلومات @{target[1:]}\nلازم ID رقمي (في تيليقرام: IDBot يعطيك)"
    
    # Try searching by name in cache
    for uid, info in cache.get("users", {}).items():
        full_name = f"{info.get('first_name','')} {info.get('last_name','')}"
        if target.lower() in full_name.lower():
            return run(uid)
    
    return f"❌ ما لقيت معلومات عن: {target}\nجرب ID: /userinfo 757074572"
