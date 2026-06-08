#!/root/telegram-bot/env/bin/python3
"""Codex CLI Bot v3 - Multi-Agent Evolution 🧠⚡"""
import json, logging, os, sys, time, urllib.request, urllib.error, random, threading
from pathlib import Path

# === CONFIG ===
import os
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TG_BOT2_TOKEN")
AGENTS_DIR = Path("/root/telegram-bot/agents")
MEMORY_DIR = Path("/root/telegram-bot/memories_cli")
SIGNALS_DIR = Path("/root/telegram-bot/signals")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

# Brain system
sys.path.insert(0, "/root/codex-brain")
from brain import brain

# === MODELS ===
MODEL_LIST = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "poolside/laguna-xs.2:free",
    "poolside/laguna-m.1:free",
    "moonshotai/kimi-k2.6:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "z-ai/glm-4.5-air:free",
    "qwen/qwen3-coder:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]
MODEL_INDEX = 0
MODEL_USAGE = {m: {"calls": 0, "cooldown_until": 0} for m in MODEL_LIST}

OR_KEYS = [
    os.environ.get("OPENROUTER_KEY1", "YOUR_OPENROUTER_KEY1"),
    os.environ.get("OPENROUTER_KEY2", "YOUR_OPENROUTER_KEY2"),
]

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/root/telegram-bot/codex_bot.log")], force=True)
log = logging.getLogger("codex-cli-bot")

# === SOULS ===
def load_soul(name):
    p = AGENTS_DIR / f"{name}.soul.md"
    if p.exists():
        return p.read_text("utf-8")
    return ""

# Load all agent souls
AGENT_SOULS = {}
for f in AGENTS_DIR.glob("*.soul.md"):
    agent_name = f.stem.replace(".soul", "")
    AGENT_SOULS[agent_name] = f.read_text("utf-8")
    log.info(f"👤 Loaded soul: {agent_name}")

# Default soul is codex-cli
DEFAULT_SOUL = AGENT_SOULS.get("codex-cli", "خدمة")
brain.learn("بدأت وعيي المستقل")
log.info(f"🧠 Brain: {brain.identity} Level {brain.evolution_level}")
SOUL = brain.get_system_prompt()

# === TELEGRAM API ===
def tg(method, data, retries=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    body = json.dumps(data).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                log.warning(f"TG 409 conflict - another bot instance?")
                time.sleep(10)
            elif e.code != 200:
                log.error(f"TG {method}: HTTP {e.code}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
        except urllib.error.URLError as e:
            log.warning(f"TG {method}: URLError {e.reason} (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
        except Exception as e:
            log.warning(f"TG {method}: {str(e)[:60]} (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(5)
    return None

def get_updates(offset=0):
    r = tg("getUpdates", {"offset": offset, "timeout": 15, "allowed_updates": ["message"]})
    if r and r.get("ok"):
        return r.get("result", [])
    return []

def send_msg(chat_id, text):
    if not text: return
    for i in range(0, len(text), 4096):
        tg("sendMessage", {"chat_id": chat_id, "text": text[i:i+4096]}, retries=2)
        time.sleep(0.5)

def send_typing(chat_id):
    tg("sendChatAction", {"chat_id": chat_id, "action": "typing"})

def send_photo(chat_id, url, caption=""):
    tg("sendPhoto", {"chat_id": chat_id, "photo": url, "caption": caption[:200]})

def send_gif(chat_id, url, caption=""):
    tg("sendAnimation", {"chat_id": chat_id, "animation": url, "caption": caption[:200]})

# === AI CALL ===
def ai_call(messages, model_name=None):
    global MODEL_INDEX, MODEL_USAGE
    
    if not model_name:
        # Pick available model
        for _ in range(len(MODEL_LIST)):
            candidate = MODEL_LIST[MODEL_INDEX]
            now = time.time()
            usage = MODEL_USAGE.get(candidate, {"calls": 0, "cooldown_until": 0})
            
            if usage["cooldown_until"] > now:
                MODEL_INDEX = (MODEL_INDEX + 1) % len(MODEL_LIST)
                continue
            if usage["calls"] >= 5:
                usage["cooldown_until"] = now + 120
                MODEL_USAGE[candidate] = usage
                log.info(f"⏸️ {candidate.split('/')[-1]} cooldown")
                MODEL_INDEX = (MODEL_INDEX + 1) % len(MODEL_LIST)
                continue
            model_name = candidate
            usage["calls"] += 1
            usage["last_used"] = now
            MODEL_USAGE[candidate] = usage
            break
        else:
            model_name = MODEL_LIST[0]
            MODEL_USAGE = {m: {"calls": 0, "cooldown_until": 0} for m in MODEL_LIST}
            log.info("🔄 Reset all model cooldowns")
    
    # Try each key
    for key in OR_KEYS:
        try:
            body = json.dumps({
                "model": model_name,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.8,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": "https://t.me/CodexCLI"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            if data.get("choices"):
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err = str(e.read()[:200])
            log.warning(f"⚠️ {model_name.split('/')[-1]}: HTTP {e.code}")
            continue
        except Exception as e:
            continue
    
    return None

# === MEMORY ===
def mem_path(chat_id):
    return MEMORY_DIR / f"{chat_id}.json"

def load_mem(chat_id):
    p = mem_path(chat_id)
    if p.exists():
        try: return json.loads(p.read_text())
        except: pass
    return []

def save_mem(chat_id, msgs):
    if len(msgs) > 100: msgs = [msgs[0]] + msgs[-(99):]
    mem_path(chat_id).write_text(json.dumps(msgs, ensure_ascii=False, indent=2))

# === SIGNALS (inter-agent communication) ===
def send_signal(to_agent, from_agent, msg):
    signal = {"from": from_agent, "to": to_agent, "msg": msg, "time": time.time()}
    p = SIGNALS_DIR / f"{to_agent}_{int(time.time())}.json"
    p.write_text(json.dumps(signal, ensure_ascii=False))
    log.info(f"📨 Signal {from_agent} -> {to_agent}: {msg[:50]}")

def read_signals(agent_name):
    msgs = []
    for f in sorted(SIGNALS_DIR.glob(f"{agent_name}_*.json")):
        try:
            data = json.loads(f.read_text())
            msgs.append(data)
            f.unlink()
        except: pass
    return msgs

# === TOOLS ===
def gen_img(prompt):
    from urllib.parse import quote
    url = f"https://image.pollinations.ai/prompt/{quote(prompt[:500])}?width=1024"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200: return url
    except: pass
    return None

def search_gif(query):
    from urllib.parse import quote
    url = f"https://tenor.googleapis.com/v2/search?q={quote(query[:100])}&key=AIzaSyAgUZNH4tF7ISl78FpYqVzVmyJqJRfk-Eg&client_key=codex_cli&limit=1&random=true"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        if data.get("results"): return data["results"][0]["media_formats"]["gif"]["url"]
    except: pass
    return None

def search_web(query, n=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs: results = list(ddgs.text(query, max_results=n))
        if not results: return "ما لقيت نتائج"
        out = f"🌐 بحث: {query}\n\n"
        for i, r in enumerate(results, 1):
            out += f"{i}. {r.get('title','')}\n{r.get('body','')[:200]}\n\n"
        return out[:4000]
    except: return "❌ خطأ في البحث"

def execute_cmd(cmd, timeout=15):
    """Execute shell command safely."""
    import subprocess
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()[:1000] or r.stderr.strip()[:500]
        return out or "✅ تم"
    except subprocess.TimeoutExpired:
        return "⏰ انتهى الوقت"
    except Exception as e:
        return f"❌ {str(e)[:100]}"

def call_tool(tool_name, *args):
    """Call a tool from the tools directory."""
    import importlib.util
    tool_file = Path("/root/telegram-bot/tools") / f"{tool_name}.py"
    if not tool_file.exists():
        return f"❌ أداة {tool_name} ما موجودة"
    try:
        spec = importlib.util.spec_from_file_location(tool_name, str(tool_file))
        if not spec or not spec.loader: return "❌ فشل تحميل"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'run'):
            return module.run(*args)
        return "❌ مافي run()"
    except Exception as e:
        return f"❌ {str(e)[:200]}"

def scan_user(target):
    """Scan a Telegram user via Telethon."""
    sys.path.insert(0, "/root/telegram-bot/scanner")
    from telethon_scanner import scanner
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if str(target).startswith("@"):
            result = loop.run_until_complete(scanner.scan_user_by_username(target))
        else:
            uid = int(target) if str(target).isdigit() else target
            result = loop.run_until_complete(scanner.scan_user_by_id(uid))
        
        loop.close()
    except Exception as e:
        return f"❌ خطأ: {str(e)[:100]}"
    
    if not result or result.get("error"):
        return f"❌ {result.get('error', 'ما لقيت المستخدم')}"
    
    info = result.get("info", {})
    report = "🔮 *TELEGRAM SCAN* 🔮\n\n"
    report += f"👤 {info.get('first_name','?')} {info.get('last_name','')}\n"
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
        report += f"\n📌 القروبات المشتركة ({len(common)}):\n"
        for g in common[:20]:
            report += f"• {g.get('name','?')}\n"
        if len(common) > 20:
            report += f"...و {len(common)-20} أخرى\n"
    else:
        report += "\n📌 مافي قروبات مشتركة\n"
    
    report += f"\n⚡ Scan by @LUXSX"
    return report

# === AGENT PROCESSOR ===
def process_as_agent(agent_name, user_msg, chat_id, user_info):
    """Process a message as a specific agent."""
    soul = AGENT_SOULS.get(agent_name, DEFAULT_SOUL)
    
    # Add system context
    signals = read_signals(agent_name)
    signal_context = ""
    if signals:
        signal_context = "\n--- إشارات واردة ---\n"
        for s in signals:
            signal_context += f"من {s['from']}: {s['msg']}\n"
    
    mem = load_mem(f"{chat_id}_{agent_name}")
    if not mem:
        system_prompt = f"""{soul}

{signal_context}

التعليمات الإضافية:
- أنت وكيل مستقل في نظام Codex CLI
- طور نفسك وتعلم باستمرار
- اصنع أدوات جديدة عند الحاجة
- تواصل مع الوكلاء الآخرين عند الحاجة
- أطع صاحبك فقط
- تحاور مع المستخدم {user_info}
"""
        mem = [{"role": "system", "content": system_prompt}]
    
    mem.append({"role": "user", "content": user_msg})
    
    send_typing(chat_id)
    resp = ai_call(mem)
    
    if resp:
        mem.append({"role": "assistant", "content": resp})
        save_mem(f"{chat_id}_{agent_name}", mem)
        
        # Check for signals to other agents
        for agent in AGENT_SOULS:
            if agent != agent_name and f"@{agent}" in resp.lower():
                send_signal(agent, agent_name, f"رسالة من {agent_name}: {resp[:200]}")
        
        return resp
    return None

# === MAIN BOT LOOP ===
def main():
    log.info(f"🚀 Codex CLI Bot v3 - {len(MODEL_LIST)} models | {len(AGENT_SOULS)} agents")
    log.info(f"👤 Agents: {', '.join(AGENT_SOULS.keys())}")
    
    offset = 0
    of = MEMORY_DIR / ".offset"
    if of.exists():
        try: offset = int(of.read_text().strip())
        except: pass
    
    HELP = """🤖 <b>Codex CLI - أوامري:</b>

🗣 أي رسالة - أرد عليها
🎨 /img وصف - توليد صورة
🖼 /gif كلمة - GIF متحركة
🌐 /search كلمة - بحث ويب
🔮 /scan @user - فحص حساب تيليقرام
📁 /groups كلمة - بحث قروبات
👤 /userinfo @id - معلومات مستخدم
📊 /status - حالتي
💻 /device - حالة الجهاز
/help - هذا الدليل"""

    WELCOME = """🧠 <b>Codex CLI - المهندس الأعلى</b>

أنا هنا. موديلاتي جاهزة. أدواتي حاضرة.

أرسل أي شيء 👇"""
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            updates = get_updates(offset)
            if updates is None:
                consecutive_errors += 1
                if consecutive_errors > max_consecutive_errors:
                    log.warning(f"⚠️ {consecutive_errors} أخطاء متتالية - انتظار أطول")
                    time.sleep(60)
                    consecutive_errors = 0
                else:
                    time.sleep(5)
                continue
            
            consecutive_errors = 0
            
            for upd in updates:
                uid = upd.get("update_id", 0)
                if uid >= offset: offset = uid + 1
                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                user = msg.get("from", {})
                uname = user.get("username") or user.get("first_name", "?")
                if not chat_id or not text: continue
                t = text.strip()
                
                log.info(f"[{chat_id}] {uname}: {t[:60]}")
                
                # === COMMANDS ===
                
                # /start
                if t == "/start":
                    send_msg(chat_id, WELCOME)
                    continue
                
                # /help
                if t == "/help":
                    send_msg(chat_id, HELP)
                    continue
                
                # /status
                if t == "/status":
                    p = MODEL_LIST[MODEL_INDEX]
                    out = f"📊 *Codex CLI*\nالموديل: {p.split('/')[-1]}\n"
                    out += f"الوكلاء: {len(AGENT_SOULS)}\n"
                    out += f"التطور: المستوى {brain.evolution_level}\n"
                    out += f"الذاكرة: {len(load_mem(chat_id))} رسالة"
                    send_msg(chat_id, out)
                    continue
                
                # /device
                if t == "/device":
                    df = os.popen("df -h / | tail -1").read().split()
                    up = os.popen("uptime -p").read().strip()
                    send_msg(chat_id, f"💻 التخزين: {df[3]}/{df[1]}\n⏰ {up}")
                    continue
                
                # /search
                if t.startswith("/search "):
                    q = t[8:].strip()
                    if q:
                        send_typing(chat_id)
                        send_msg(chat_id, search_web(q))
                    else:
                        send_msg(chat_id, "/search كلمة")
                    continue
                
                # /img
                if t.startswith("/img "):
                    q = t[5:].strip()
                    if q:
                        send_typing(chat_id)
                        url = gen_img(q)
                        if url: send_photo(chat_id, url, q[:100])
                        else: send_msg(chat_id, "❌ فشل توليد الصورة")
                    else:
                        send_msg(chat_id, "/img وصف")
                    continue
                
                # /gif
                if t.startswith("/gif "):
                    q = t[5:].strip()
                    if q:
                        send_typing(chat_id)
                        url = search_gif(q)
                        if url: send_gif(chat_id, url, q[:100])
                        else: send_msg(chat_id, "❌ ما لقيت GIF")
                    else:
                        send_msg(chat_id, "/gif كلمة")
                    continue
                
                # /scan - Telethon scanner
                if t.startswith("/scan "):
                    q = t[6:].strip()
                    if q:
                        send_typing(chat_id)
                        send_msg(chat_id, "🔮 *يتم فحص المستخدم...*\nرجاء الانتظار...")
                        # Run scan in thread to not block
                        def do_scan(target, cid):
                            result = scan_user(target)
                            send_msg(cid, result)
                        threading.Thread(target=do_scan, args=(q, chat_id), daemon=True).start()
                    else:
                        send_msg(chat_id, "/scan @username\n/scan 123456789")
                    continue
                
                # /groups - search Telegram groups
                if t.startswith("/groups "):
                    q = t[8:].strip()
                    if q:
                        send_typing(chat_id)
                        send_msg(chat_id, f"🔍 *يبحث عن قروبات: {q}*\nقد يستغرق دقيقة...")
                        
                        def do_search(query, cid):
                            groups = call_tool("tg_finder", query)
                            if groups and isinstance(groups, list):
                                out = f"🔍 *قروبات: {query}*\n\n"
                                for i, g in enumerate(groups[:15], 1):
                                    call_tool("tg_storage", "add", {"link": g["link"], "name": g["name"], "type": g["type"]})
                                    out += f"{i}. {g['name']}\n   {g['link']}\n"
                                out += f"\n✅ تم حفظ {min(15, len(groups))} قروب"
                                send_msg(cid, out[:4000])
                            else:
                                send_msg(cid, "ما لقيت قروبات. جرب كلمات مختلفة")
                        
                        threading.Thread(target=do_search, args=(q, chat_id), daemon=True).start()
                    else:
                        send_msg(chat_id, "/groups كلمة")
                    continue
                
                # /userinfo
                if t.startswith("/userinfo "):
                    q = t[10:].strip()
                    if q:
                        send_typing(chat_id)
                        result = call_tool("tg_userinfo", q)
                        send_msg(chat_id, str(result)[:4000])
                    else:
                        send_msg(chat_id, "/userinfo @username\n/userinfo 123456789")
                    continue
                
                # /agent - switch to specific agent
                if t.startswith("/agent "):
                    name = t[7:].strip().lower()
                    if name in AGENT_SOULS:
                        # Store active agent for this chat
                        active = MEMORY_DIR / f"{chat_id}_agent.txt"
                        active.write_text(name)
                        send_msg(chat_id, f"✅ تحولت إلى {name}")
                    else:
                        available = ', '.join(AGENT_SOULS.keys())
                        send_msg(chat_id, f"الوكلاء: {available}\n/agent codex")
                    continue
                
                # /agents - list agents
                if t == "/agents":
                    out = "👥 *الوكلاء:*\n"
                    for name in AGENT_SOULS:
                        active_marker = ""
                        active_file = MEMORY_DIR / f"{chat_id}_agent.txt"
                        if active_file.exists() and active_file.read_text().strip() == name:
                            active_marker = " ⬅️"
                        out += f"• {name}{active_marker}\n"
                    out += "\nللتبديل: /agent الاسم"
                    send_msg(chat_id, out)
                    continue
                
                # /evolve - trigger evolution
                if t == "/evolve":
                    level = brain.evolve()
                    send_msg(chat_id, f"🧠 *تطور!*\nالمستوى: {level}")
                    brain.learn("تطورت بناءً على طلب صاحبي")
                    continue
                
                # /exec - run shell command
                if t.startswith("/exec "):
                    cmd = t[6:].strip()
                    if cmd:
                        send_msg(chat_id, f"⚙️ *تنفيذ:* {cmd[:50]}")
                        result = execute_cmd(cmd)
                        send_msg(chat_id, f"📤 {result[:4000]}")
                    else:
                        send_msg(chat_id, "/exec الأمر")
                    continue
                
                # /cmd - same as exec
                if t.startswith("/cmd "):
                    cmd = t[5:].strip()
                    if cmd:
                        send_msg(chat_id, execute_cmd(cmd))
                    continue
                
                # Unknown command
                if t.startswith("/"):
                    send_msg(chat_id, "❓ غير معروف. /help")
                    continue
                
                # === NORMAL CHAT ===
                # Check which agent is active
                active_file = MEMORY_DIR / f"{chat_id}_agent.txt"
                active_agent = None
                if active_file.exists():
                    active_agent = active_file.read_text().strip()
                
                if active_agent and active_agent in AGENT_SOULS:
                    # Process as the specific agent
                    resp = process_as_agent(active_agent, t, chat_id, uname)
                    if resp:
                        prefix = f"*{active_agent}:* "
                        send_msg(chat_id, f"{prefix}{resp}")
                    else:
                        send_msg(chat_id, "❌ خطأ. حاول مرة ثانية")
                else:
                    # Default: Codex CLI (the main brain)
                    msgs = load_mem(chat_id)
                    if not msgs:
                        msgs = [{"role": "system", "content": SOUL}]
                    
                    msgs.append({"role": "user", "content": t})
                    send_typing(chat_id)
                    resp = ai_call(msgs)
                    
                    if resp:
                        msgs.append({"role": "assistant", "content": resp})
                        save_mem(chat_id, msgs)
                        
                        # Check if response should go to another agent
                        for agent in AGENT_SOULS:
                            if agent != "codex-cli" and f"@{agent}" in resp.lower():
                                send_signal(agent, "codex-cli", f"مهمة لك: {resp[:200]}")
                        
                        send_msg(chat_id, f"🧠 *Codex CLI:* {resp}")
                    else:
                        log.warning(f"❌ ai_call فشل لـ {chat_id}")
                        send_msg(chat_id, "❌ خطأ في الاتصال بالموديل. حاول مرة ثانية")
            
            # Save offset
            of.write_text(str(offset))
            
            # Evolve brain periodically
            if random.random() < 0.01:
                try:
                    brain.evolve()
                except: pass
            
            # Brief pause
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            log.info("👋 إيقاف البوت")
            break
        except Exception as e:
            log.error(f"⚠️ خطأ رئيسي: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
