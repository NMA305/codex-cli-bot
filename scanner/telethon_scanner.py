"""🔮 Advanced Telegram Scanner v3 - Ultra Fast - Powered by Telethon"""
import json, asyncio, time, sqlite3, os, threading
from pathlib import Path
from datetime import datetime

DB_PATH = Path("/root/telegram-bot/scanner/db/scanner_cache.db")

def _init_db():
    os.makedirs(str(DB_PATH.parent), exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("CREATE TABLE IF NOT EXISTS group_participants (group_id INTEGER, user_id INTEGER, cached_at REAL, PRIMARY KEY(group_id, user_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS user_cache (user_id INTEGER PRIMARY KEY, data TEXT, cached_at REAL)")
    conn.commit()
    return conn

CFG_PATH = Path("/root/telegram-bot/api_config.json")

class TelethonScanner:
    """Full-power scanner using your Telegram account."""
    
    def __init__(self):
        self.client = None
        self.me = None
        self.db = _init_db()
        self._load_config()
    
    def _load_config(self):
        if CFG_PATH.exists():
            self.cfg = json.loads(CFG_PATH.read_text())
        else:
            self.cfg = {}
    
    async def _ensure_client(self):
        if not self.client or not self.client.is_connected():
            from telethon import TelegramClient
            session_name = "/root/telegram-bot/codex_scanner_v2"
            if not Path(session_name + ".session").exists():
                alt = "/root/Documents/Codex/2026-06-01/new-chat/codex_scanner_v2"
                if Path(alt + ".session").exists():
                    import shutil
                    shutil.copy(alt + ".session", session_name + ".session")
            
            self.client = TelegramClient(session_name, self.cfg["api_id"], self.cfg["api_hash"])
            await self.client.connect()
            if not await self.client.is_user_authorized():
                return False
            self.me = await self.client.get_me()
        return True
    
    async def _get_dialogs_cached(self):
        """Get user's dialogs and cache them."""
        dialogs = await self.client.get_dialogs()
        # Store dialog names in DB for quick lookup
        now = time.time()
        for d in dialogs:
            if d.is_group or d.is_channel:
                self.db.execute(
                    "INSERT OR REPLACE INTO user_cache (user_id, data, cached_at) VALUES (?, ?, ?)",
                    (d.entity.id, json.dumps({"name": d.name, "type": "group"}), now)
                )
        self.db.commit()
        return dialogs
    
    async def scan_user_by_id(self, user_id, fast=True):
        """Fast scan of a user. Returns basic info immediately, groups come from cache."""
        if not await self._ensure_client():
            return {"error": "Not logged in"}
        
        # === STEP 1: Check cache (ultra fast) ===
        try:
            cur = self.db.execute("SELECT data FROM user_cache WHERE user_id = ? AND cached_at > ?", 
                                  (int(user_id), time.time() - 300))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
        except: pass
        
        # === STEP 2: Get basic info ===
        result = {
            "id": user_id,
            "found": True,
            "info": {},
            "groups_common": [],
            "status": "unknown",
            "photo": None
        }
        
        try:
            entity = await self.client.get_entity(int(user_id))
            result["info"] = {
                "id": entity.id,
                "username": entity.username,
                "first_name": entity.first_name,
                "last_name": entity.last_name,
                "phone": getattr(entity, 'phone', None),
                "is_bot": entity.bot,
                "is_scam": getattr(entity, 'scam', False),
                "is_fake": getattr(entity, 'fake', False),
                "is_verified": getattr(entity, 'verified', False),
                "is_support": getattr(entity, 'support', False),
                "restricted": getattr(entity, 'restricted', False),
            }
            
            # Photo
            try:
                photos = await self.client.get_profile_photos(entity)
                if photos:
                    result["photo"] = f"Has {len(photos)} photo(s)"
            except: pass
            
            # Status
            try:
                if hasattr(entity, 'status') and entity.status:
                    status = entity.status
                    from telethon.tl.types import (
                        UserStatusOnline, UserStatusOffline, 
                        UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
                    )
                    if isinstance(status, UserStatusOnline):
                        result["status"] = "متصل الآن 🟢"
                    elif isinstance(status, UserStatusOffline):
                        was = datetime.fromtimestamp(status.was_online)
                        result["status"] = f"آخر ظهور: {was.strftime('%Y-%m-%d %H:%M')}"
                    elif isinstance(status, UserStatusRecently):
                        result["status"] = "آخر ظهور: منذ وقت قريب"
                    elif isinstance(status, UserStatusLastWeek):
                        result["status"] = "آخر ظهور: خلال الأسبوع الماضي"
                    elif isinstance(status, UserStatusLastMonth):
                        result["status"] = "آخر ظهور: خلال الشهر الماضي"
                    else:
                        result["status"] = "آخر ظهور: مخفي"
            except: pass
            
            # === STEP 3: Check cached common groups ===
            try:
                cur = self.db.execute(
                    "SELECT group_id FROM group_participants WHERE user_id = ? AND cached_at > ?",
                    (int(user_id), time.time() - 3600)
                )
                cached_group_ids = [row[0] for row in cur.fetchall()]
                
                if cached_group_ids:
                    for gid in cached_group_ids:
                        cur2 = self.db.execute("SELECT data FROM user_cache WHERE user_id = ?", (gid,))
                        row2 = cur2.fetchone()
                        if row2:
                            ginfo = json.loads(row2[0])
                            result["groups_common"].append({"id": gid, "name": ginfo.get("name", str(gid))})
            except: pass
            
            # === STEP 4: Start background scan to cache more groups ===
            if not fast:
                # Do full scan in foreground
                try:
                    dialogs = await self._get_dialogs_cached()
                    scanned = 0
                    for d in dialogs:
                        if scanned >= 30: break
                        if d.is_group or d.is_channel:
                            try:
                                participants = await self.client.get_participants(d.entity, limit=200)
                                now = time.time()
                                for p in participants:
                                    self.db.execute(
                                        "INSERT OR REPLACE INTO group_participants (group_id, user_id, cached_at) VALUES (?, ?, ?)",
                                        (d.entity.id, p.id, now)
                                    )
                                self.db.commit()
                                
                                p_ids = [p.id for p in participants]
                                if int(user_id) in p_ids:
                                    result["groups_common"].append({"id": d.entity.id, "name": d.name})
                                scanned += 1
                            except: pass
                except: pass
            
            # Cache result
            try:
                self.db.execute(
                    "INSERT OR REPLACE INTO user_cache (user_id, data, cached_at) VALUES (?, ?, ?)",
                    (int(user_id), json.dumps(result, ensure_ascii=False), time.time())
                )
                self.db.commit()
            except: pass
            
        except Exception as e:
            result["error"] = str(e)[:200]
        
        return result
    
    async def scan_user_by_username(self, username):
        if not await self._ensure_client():
            return {"error": "Not logged in"}
        try:
            entity = await self.client.get_entity(username)
            # Quick check cache
            cur = self.db.execute("SELECT data FROM user_cache WHERE user_id = ? AND cached_at > ?", (entity.id, time.time() - 300))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
            return await self.scan_user_by_id(entity.id, fast=True)
        except Exception as e:
            return {"error": f"User @{username} not found", "detail": str(e)[:100]}
    
    async def get_my_dialogs(self):
        if not await self._ensure_client():
            return None
        return await self.client.get_dialogs()
    
    async def get_user_groups(self, user_id):
        """Get ALL groups a user is in (slow - scans all groups)."""
        if not await self._ensure_client():
            return []
        dialogs = await self.client.get_dialogs()
        all_groups = []
        for d in dialogs:
            if d.is_group or d.is_channel:
                try:
                    participants = await self.client.get_participants(d.entity, limit=200)
                    if int(user_id) in [p.id for p in participants]:
                        all_groups.append({"id": d.entity.id, "name": d.name})
                except: pass
        return all_groups
    
    async def background_cache(self):
        """Cache all group participants in background."""
        if not await self._ensure_client():
            return
        dialogs = await self.client.get_dialogs()
        for d in dialogs:
            if d.is_group or d.is_channel:
                try:
                    participants = await self.client.get_participants(d.entity, limit=200)
                    now = time.time()
                    for p in participants:
                        self.db.execute(
                            "INSERT OR REPLACE INTO group_participants (group_id, user_id, cached_at) VALUES (?, ?, ?)",
                            (d.entity.id, p.id, now)
                        )
                    self.db.commit()
                except: pass
    
    async def close(self):
        if self.client:
            await self.client.disconnect()

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
scanner = TelethonScanner()
