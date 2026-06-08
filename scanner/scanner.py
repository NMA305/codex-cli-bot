"""
🔮 TELEGRAM SCANNER v2070 🔮
Advanced Telegram user investigation system
"""
import json, time, os, sqlite3, urllib.request, re
from pathlib import Path
from datetime import datetime

DB_DIR = Path("/root/telegram-bot/scanner/db")
DB_DIR.mkdir(parents=True, exist_ok=True)
USERS_DB = DB_DIR / "users.db"
GROUPS_DB = DB_DIR / "groups.db"
TOKEN = "YOUR_TG_BOT2_TOKEN"

class Scanner:
    """Advanced Telegram Scanner - Future Tech"""
    
    def __init__(self):
        self._init_db()
        self.scan_count = 0
    
    def _init_db(self):
        # Users database
        conn = sqlite3.connect(str(USERS_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                last_seen TEXT,
                    last_scan TEXT,
                groups_count INTEGER DEFAULT 0,
                is_bot INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sightings (
                user_id INTEGER,
                group_id INTEGER,
                group_name TEXT,
                first_seen TEXT,
                last_seen TEXT,
                role TEXT,
                PRIMARY KEY (user_id, group_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def scan_user(self, user_id):
        """Scan a user and return all available info."""
        results = {"id": user_id, "found": False, "info": {}, "groups": [], "status": "unknown"}
        
        # Get basic info via Bot API
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id={user_id}"
            r = urllib.request.urlopen(url, timeout=10)
            data = json.loads(r.read())
            if data.get("ok"):
                info = data["result"]
                results["found"] = True
                results["info"] = {
                    "username": info.get("username"),
                    "first_name": info.get("first_name"),
                    "last_name": info.get("last_name"),
                    "type": info.get("type"),
                    "is_bot": info.get("is_bot", False)
                }
                
                # Save to DB
                self._save_user(user_id, info)
        except: pass
        
        # Check database for past sightings
        results["groups"] = self._get_user_groups(user_id)
        results["db_info"] = self._get_user_db(user_id)
        
        return results
    
    def _save_user(self, user_id, info):
        conn = sqlite3.connect(str(USERS_DB))
        conn.execute("""
            INSERT OR REPLACE INTO users (id, username, first_name, last_name, last_scan, is_bot)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            info.get("username"),
            info.get("first_name"),
            info.get("last_name"),
            datetime.now().isoformat(),
            1 if info.get("is_bot") else 0
        ))
        conn.commit()
        conn.close()
    
    def _get_user_groups(self, user_id):
        conn = sqlite3.connect(str(GROUPS_DB))
        try:
            cursor = conn.execute("""
                SELECT group_name, group_id, first_seen, last_seen, role 
                FROM sightings WHERE user_id = ?
                ORDER BY last_seen DESC
            """, (user_id,))
            return [{"name": r[0], "id": r[1], "first_seen": r[2], "last_seen": r[3], "role": r[4]} for r in cursor.fetchall()]
        finally:
            conn.close()
    
    def _get_user_db(self, user_id):
        conn = sqlite3.connect(str(USERS_DB))
        try:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {"username": row[1], "first_name": row[2], "last_name": row[3], "last_seen": row[5]}
            return None
        finally:
            conn.close()
    
    def record_sighting(self, user_id, username, group_id, group_name, role="member"):
        """Record a user being seen in a group."""
        conn = sqlite3.connect(str(GROUPS_DB))
        try:
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO sightings (user_id, group_id, group_name, first_seen, last_seen, role)
                VALUES (?, ?, ?, COALESCE((SELECT first_seen FROM sightings WHERE user_id=? AND group_id=?), ?), ?, ?)
            """, (user_id, group_id, group_name, user_id, group_id, now, now, role))
            conn.commit()
        finally:
            conn.close()

# Global scanner instance
scanner = Scanner()
