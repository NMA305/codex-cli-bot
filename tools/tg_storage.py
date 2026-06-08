"""Telegram Group Storage - Save and manage groups"""
import json, os, time
from pathlib import Path

STORAGE_FILE = Path("/root/telegram-bot/groups_db.json")

def load_groups():
    if STORAGE_FILE.exists():
        try: return json.loads(STORAGE_FILE.read_text())
        except: pass
    return {"groups": [], "categories": {}, "saved_at": time.time()}

def save_groups(data):
    data["saved_at"] = time.time()
    STORAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def run(action, data=None):
    """
    Manage saved Telegram groups.
    Args: action (str) - "list", "add", "search", "save"
          data (dict) - group info
    Returns: string result
    """
    db = load_groups()
    
    if action == "list":
        if not db["groups"]:
            return "ما في قروبات محفوظة"
        out = f"📁 القروبات المحفوظة: {len(db['groups'])}\n\n"
        for i, g in enumerate(db["groups"], 1):
            out += f"{i}. {g.get('name','?')} - {g['link']}\n"
        return out
    
    elif action == "add" and data:
        link = data.get("link", "")
        name = data.get("name", link.split("/")[-1])
        
        # Check duplicate
        for g in db["groups"]:
            if g["link"] == link:
                return f"موجود مسبقاً: {name}"
        
        db["groups"].append({
            "name": name,
            "link": link,
            "added": time.time(),
            "type": data.get("type", "group")
        })
        save_groups(db)
        return f"✅ تم الحفظ: {name}"
    
    elif action == "search" and data:
        keyword = data.lower()
        found = [g for g in db["groups"] if keyword in g["name"].lower() or keyword in g["link"].lower()]
        if not found:
            return f"ما لقيت قروب بـ: {data}"
        out = f"🔍 نتائج البحث عن: {data}\n\n"
        for g in found:
            out += f"• {g['name']} - {g['link']}\n"
        return out
    
    elif action == "stats":
        return f"📊 القروبات: {len(db['groups'])} | الفئات: {len(db.get('categories',{}))}"
    
    return "أمر غير معروف. استخدم: list, add, search, stats"
