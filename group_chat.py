#!/root/telegram-bot/env/bin/python3
"""🧠 Telegram Group Chatter"""
import os
import sys, json, asyncio, time, random, urllib.request, re
sys.path.insert(0, '/root/telegram-bot/scanner')
from telethon_scanner import scanner
from datetime import datetime

# === CONFIG ===
GROUP_NAMES = [
    "كروب دياثه بس سوالب موجبين",
    "جروبات رغي بنات و شباب تعارف",
    "جروبات حفله سوالب🔥 موجبين مصر سحاقيات🔥🌈🔥",
    "دار المتعة 🥵💞 و التعارف 👩‍❤️‍👨",
]

OR_KEYS = [
    os.environ.get("OPENROUTER_KEY1",
    "YOUR_OPENROUTER_KEY1"),
    os.environ.get("OPENROUTER_KEY2", "YOUR_OPENROUTER_KEY2"),
]

MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]

FALLBACKS = [
    "هههه والله 😂",
    "يعني كذا 😅",
    "صح كلامك والله",
    "اي والله صدقت",
    "هلا والله",
    "كيفكم شباب",
    "تمام 😎",
    "هلا فيكم",
]

# === AI CALL ===
def ai_response(context, model_idx=0):
    """Generate natural response using AI."""
    prompt = f"""انت ولد فحل عنيف في قروب تيليقرام عربي. حسابك @LUXSX.

الرسائل الأخيرة في القروب:
{context}

المطلوب: رد على آخر رسالة بشكل طبيعي. انت شخص عادي تشارك في القروب.
ما تكتب شي يدل انك بوت. رد طبيعي 100٪.

رد:"""
    
    model = MODELS[model_idx % len(MODELS)]
    
    for key in OR_KEYS:
        try:
            body = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.9,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": "https://t.me/LUXSX"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            if data.get("choices"):
                return data["choices"][0]["message"]["content"]
        except:
            pass
    
    return None

# === MAIN LOOP ===
async def main():
    ok = await scanner._ensure_client()
    if not ok:
        print("❌ Not connected")
        return
    
    me = await scanner.client.get_me()
    print(f"✅ Connected as @{me.username}")
    
    dialogs = await scanner.client.get_dialogs()
    groups = []
    for d in dialogs:
        if d.name and any(gname in d.name for gname in GROUP_NAMES):
            groups.append({"entity": d.entity, "name": d.name, "last_msg_id": 0})
    
    if not groups:
        print("❌ Target groups not found!")
        return
    
    print(f"🎯 Monitoring {len(groups)} groups:")
    for g in groups:
        print(f"   - {g['name'][:50]}")
    print()
    
    for g in groups:
        try:
            msgs = await scanner.client.get_messages(g["entity"], limit=1)
            if msgs:
                g["last_msg_id"] = msgs[0].id
        except:
            pass
    
    model_idx = 0
    print("🔄 Started monitoring. Ctrl+C to stop.\n")
    
    while True:
        try:
            for g in groups:
                msgs = await scanner.client.get_messages(g["entity"], limit=5)
                new_msgs = [m for m in msgs if m.id > g["last_msg_id"] and m.sender_id != me.id]
                
                if new_msgs:
                    g["last_msg_id"] = max(m.id for m in msgs)
                    
                    context_lines = []
                    for m in reversed(msgs[:5]):
                        sender = "?"
                        try:
                            if m.sender_id and m.sender_id != me.id:
                                s = await scanner.client.get_entity(m.sender_id)
                                sender = getattr(s, 'username', s.first_name or str(m.sender_id))
                        except:
                            pass
                        txt = m.text[:150] if m.text else "[media]"
                        context_lines.append(f"{sender}: {txt}")
                    
                    context = "\n".join(context_lines)
                    now = datetime.now().strftime("%H:%M")
                    
                    print(f"[{now}] 💬 {g['name'][:25]}...")
                    
                    resp = ai_response(context, model_idx)
                    model_idx += 1
                    
                    if not resp:
                        resp = random.choice(FALLBACKS)
                    else:
                        resp = resp.strip().strip('"').strip("'")
                        if len(resp) > 200:
                            resp = resp[:200]
                    
                    print(f"   Reply: {resp[:80]}")
                    await scanner.client.send_message(g["entity"], resp)
                    print(f"   ✅ Sent\n")
                    
                    await asyncio.sleep(random.uniform(3, 8))
            
            await asyncio.sleep(random.uniform(15, 30))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
