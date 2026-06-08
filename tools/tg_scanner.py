"""🔮 Telegram Scanner v2070 - Telethon Powered"""
import sys, json, asyncio, time, threading
sys.path.insert(0, "/root/telegram-bot/scanner")
from telethon_scanner import scanner

def run(target):
    """Full scan of a Telegram user. Args: target - user ID, @username"""
    target = target.strip()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if target.startswith("@"):
            result = loop.run_until_complete(scanner.scan_user_by_username(target))
        else:
            uid = int(target) if target.isdigit() else target
            result = loop.run_until_complete(scanner.scan_user_by_id(uid, fast=True))
        
        loop.close()
    except Exception as e:
        return f"❌ خطأ: {str(e)[:100]}"
    
    if not result or result.get("error"):
        return f"❌ {result.get('error', 'ما لقيت المستخدم')}"
    
    info = result.get("info", {})
    report = "🔮 *TELEGRAM SCAN REPORT* 🔮\n\n"
    report += f"👤 *{info.get('first_name','?')} {info.get('last_name','')}*\n"
    if info.get("username"):
        report += f"🔗 @{info['username']}\n"
    report += f"🆔 `{info.get('id')}`\n"
    
    flags = []
    if info.get("is_verified"): flags.append("✅ Verified")
    if info.get("is_scam"): flags.append("⚠️ Scam")
    if info.get("is_fake"): flags.append("👻 Fake")
    if info.get("is_bot"): flags.append("🤖 Bot")
    if info.get("restricted"): flags.append("🔒 Restricted")
    if flags:
        report += f"🏷️ {' | '.join(flags)}\n"
    
    status = result.get("status", "غير معروف")
    report += f"🕐 {status}\n"
    if info.get("phone"):
        report += f"📞 `{info['phone']}`\n"
    
    common = result.get("groups_common", [])
    if common:
        report += f"\n📌 *القروبات المشتركة ({len(common)}):*\n"
        for g in common[:20]:
            report += f"• {g.get('name','?')}\n"
        if len(common) > 20:
            report += f"...و {len(common)-20} أخرى\n"
    else:
        report += "\n📌 *ما في قروبات مشتركة*\n"
    
    # Try to get more groups in background
    if len(common) < 200:
        report += "\n🔄 جاري المسح المتقدم للقروبات (قد يستغرق دقيقة)..."
        threading.Thread(target=_bg_scan, args=(target,), daemon=True).start()
    
    return report

def _bg_scan(target):
    """Background scan all groups."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if target.startswith("@"):
            entity = loop.run_until_complete(scanner.client.get_entity(target))
            uid = entity.id
        else:
            uid = int(target)
        
        # Get all groups user is in
        groups = loop.run_until_complete(scanner.get_user_groups(uid))
        loop.close()
        
        # Save to a file that can be retrieved later
        if groups:
            f = Path(f"/root/telegram-bot/scanner/scan_{uid}_groups.json")
            f.write_text(json.dumps(groups, ensure_ascii=False, indent=2))
            print(f"✅ Full scan complete: {len(groups)} groups for {uid}")
    except Exception as e:
        print(f"❌ Background scan error: {e}")
