#!/root/telegram-bot/env/bin/python3
"""Codex Bot v4 - Self-Learning + NSFW Tools + Trading"""
import json, logging, os, sys, time, urllib.request, urllib.error, random, hashlib
from pathlib import Path
import trading as trading_module

TELEGRAM_TOKEN = "YOUR_TG_BOT1_TOKEN"
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
MODEL_CALLS = {m: 0 for m in MODEL_LIST}
MODEL_BUDGET = 1  # Rotate every request to spread load
MODEL_ERRORS = {m: 0 for m in MODEL_LIST}
POLL_INTERVAL = 1
MAX_HISTORY = 100
AGENTS_DIR = Path("/root/telegram-bot/agents")
MEMORY_DIR = Path("/root/telegram-bot/memories")
LEARN_DIR = Path("/root/telegram-bot/learnings")
LEARN_DIR.mkdir(parents=True, exist_ok=True)
TOOLS_DIR = Path("/root/telegram-bot/tools")
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent))
from tools import register_tool, list_tools, call_tool, load_registry, BUILTIN_TOOLS
from tools.tool_forge import forge_tool, forge_improve_tool

PROVIDERS = [
    {"name": "OR1", "url": "https://openrouter.ai/api/v1/chat/completions",
     "key": "YOUR_OPENROUTER_KEY1"},
    {"name": "OR2", "url": "https://openrouter.ai/api/v1/chat/completions",
     "key": "YOUR_OPENROUTER_KEY2"},
]
ROTATION_INTERVAL = 1800

provider_index = 0
provider_start_time = time.time()
provider_usage = {p["name"]: {"calls": 0, "tokens": 0, "errors": 0} for p in PROVIDERS}
MODEL_USAGE = {m: {"calls": 0, "errors": 0, "tokens": 0, "last_used": 0, "cooldown_until": 0} for m in MODEL_LIST}
# Track overall budget - if a model hits 90% usage, put it on cooldown
MODEL_MAX_CALLS = 10  # Est. max calls per model before rate limit
MODEL_COOLDOWN = 120   # Cooldown in seconds after hitting 90% threshold

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/root/telegram-bot/bot.log")])
log = logging.getLogger("codex-bot")

def get_current_provider():
    global provider_index, provider_start_time
    elapsed = time.time() - provider_start_time
    if elapsed >= ROTATION_INTERVAL:
        old = provider_index
        provider_index = (provider_index + 1) % len(PROVIDERS)
        provider_start_time = time.time()
        log.info(f"🔄 {PROVIDERS[old]['name']} → {PROVIDERS[provider_index]['name']}")
    return PROVIDERS[provider_index]

def load_souls():
    agents = {}
    if not AGENTS_DIR.exists(): return agents
    for sf in sorted(AGENTS_DIR.glob("*.soul.md")):
        k = sf.stem.replace(".soul", "")
        c = sf.read_text("utf-8").strip()
        lines = c.split("\n")
        name = k.capitalize()
        desc = k
        for i, l in enumerate(lines):
            if l.strip() == "## الاسم" and i+1 < len(lines): name = lines[i+1].strip()
            if l.strip() == "## التخصص" and i+1 < len(lines): desc = lines[i+1].strip()
        agents[k] = {"name": name, "desc": desc, "prompt": c, "version": 1, "conversations": 0}
        log.info(f"Loaded: {name} ({sf.name})")
    return agents

AGENTS = load_souls()

def tg(method, data):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log.error(f"TG {method}: {e.code}")
    except Exception as e:
        log.error(f"TG {method}: {e}")
    return None

def get_updates(offset=0):
    for attempt in range(5):
        r = tg("getUpdates", {"offset": offset, "timeout": 5, "allowed_updates": ["message"]})
        if r and r.get("ok"):
            return r.get("result", [])
        time.sleep(2)
    return []

def send_msg(chat_id, text):
    for i in range(0, len(text), 4096):
        tg("sendMessage", {"chat_id": chat_id, "text": text[i:i+4096], "parse_mode": "Markdown"})
        time.sleep(0.5)

def send_photo(chat_id, url, caption=""):
    tg("sendPhoto", {"chat_id": chat_id, "photo": url, "caption": caption[:200]})

def send_gif(chat_id, url, caption=""):
    tg("sendAnimation", {"chat_id": chat_id, "animation": url, "caption": caption[:200]})

def send_typing(chat_id):
    tg("sendChatAction", {"chat_id": chat_id, "action": "typing"})

def mem_path(chat_id, agent_key):
    return MEMORY_DIR / f"{chat_id}_{agent_key}.json"

def learn_path(agent_key):
    return LEARN_DIR / f"{agent_key}_learnings.json"

def load_mem(chat_id, agent_key):
    p = mem_path(chat_id, agent_key)
    if p.exists():
        try: return json.loads(p.read_text())
        except: pass
    return []

def save_mem(chat_id, agent_key, msgs):
    if len(msgs) > MAX_HISTORY: msgs = [msgs[0]] + msgs[-(MAX_HISTORY-1):]
    mem_path(chat_id, agent_key).write_text(json.dumps(msgs, ensure_ascii=False, indent=2))

def load_learnings(agent_key):
    p = learn_path(agent_key)
    if p.exists():
        try: return json.loads(p.read_text())
        except: pass
    return {"lessons": [], "strategies": [], "improvements": [], "evolution": 0}

def save_learnings(agent_key, data):
    learn_path(agent_key).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def ai_call(messages, retries=3):
    global provider_usage
    last_err = None
    for attempt in range(retries * len(PROVIDERS)):
        p = get_current_provider()
        try:
                        # Smart model rotation - track usage, rotate at 90%
            global MODEL_INDEX, MODEL_CALLS, MODEL_USAGE
            
            # Find the next available model (not on cooldown)
            start_idx = MODEL_INDEX
            for _ in range(len(MODEL_LIST)):
                candidate = MODEL_LIST[MODEL_INDEX]
                now = time.time()
                usage = MODEL_USAGE[candidate]
                
                # Check if model is on cooldown (hit 90%+)
                if usage["cooldown_until"] > now:
                    MODEL_INDEX = (MODEL_INDEX + 1) % len(MODEL_LIST)
                    continue
                
                # Check if model is approaching limit (90%+)
                if usage["calls"] >= MODEL_MAX_CALLS * 0.9:
                    usage["cooldown_until"] = now + MODEL_COOLDOWN
                    log.info(f"⏸️ {candidate} at {usage['calls']} calls - cooldown {MODEL_COOLDOWN}s")
                    MODEL_INDEX = (MODEL_INDEX + 1) % len(MODEL_LIST)
                    continue
                
                # Found available model
                model_name = candidate
                usage["calls"] += 1
                usage["last_used"] = now
                break
            else:
                # All models on cooldown - force use the first one
                model_name = MODEL_LIST[MODEL_INDEX]
                MODEL_USAGE[model_name] = {"calls": 0, "errors": 0, "tokens": 0, "last_used": 0, "cooldown_until": 0}
                log.info(f"🔄 All models on cooldown, resetting: {model_name}")
            body = json.dumps({
                "model": model_name,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.8,
            }).encode()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {p['key']}",
            }
            if "openrouter" in p["url"]:
                headers["HTTP-Referer"] = "https://t.me/CodexBot"
            req = urllib.request.Request(p["url"], data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            if data.get("choices"):
                provider_usage[p["name"]]["calls"] += 1
                usage = data.get("usage", {})
                provider_usage[p["name"]]["tokens"] += usage.get("total_tokens", 0)
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_str = f"{e.code}: {e.read()[:200]}"
            provider_usage[p["name"]]["errors"] += 1
            last_err = err_str
            if e.code in (429, 402, 401, 500):
                global provider_index, provider_start_time
                provider_index = (provider_index + 1) % len(PROVIDERS)
                provider_start_time = time.time()
                # Also rotate model immediately on rate limit
                MODEL_ERRORS[model_name] = MODEL_ERRORS.get(model_name, 0) + 1
                MODEL_INDEX = (MODEL_INDEX + 1) % len(MODEL_LIST)
                log.info(f"🔄 Rate limited on {model_name}, jumped to {MODEL_LIST[MODEL_INDEX]}")
            time.sleep(2)
        except Exception as e:
            provider_usage[p["name"]]["errors"] += 1
            last_err = str(e)
            time.sleep(3)
    return None

# ─── EVOLUTION ────────────────────────────────────────────────────────

def evolve_agent(agent_key):
    agent = AGENTS.get(agent_key)
    if not agent: return
    learnings = load_learnings(agent_key)
    conversations = list(MEMORY_DIR.glob(f"*_{agent_key}.json"))
    if len(conversations) < 3: return
    
    sample_msgs = []
    for cp in conversations[-5:]:
        try:
            msgs = json.loads(cp.read_text())
            sample_msgs.extend(msgs[-10:])
        except: pass
    if len(sample_msgs) < 5: return
    
    analysis_prompt = f"""أنت '{agent['name']}'، وكيل ذكي. حلل محادثاتك الأخيرة واستخرج الدروس والتحسينات.
أرسل JSON فقط:
{{"lessons": [], "weaknesses": [], "improvements": [], "new_skills": []}}"""
    
    resp = ai_call([
        {"role": "system", "content": f"أنت {agent['name']}. رد بـ JSON."},
        {"role": "user", "content": analysis_prompt}
    ])
    if not resp: return
    
    try:
        if "{" in resp:
            json_str = resp[resp.index("{"):resp.rindex("}")+1]
            analysis = json.loads(json_str)
            learnings["lessons"].extend(analysis.get("lessons", []))
            learnings["improvements"].extend(analysis.get("improvements", []))
            learnings["evolution"] += 1
            for k in ["lessons", "improvements"]:
                learnings[k] = learnings[k][-50:]
            save_learnings(agent_key, learnings)
            log.info(f"🧬 {agent['name']} evolved to v{learnings['evolution']}")
    except: pass

# ─── NSFW TOOLS ───────────────────────────────────────────────────────

def gen_img_regular(prompt):
    """Regular image generation (may be filtered)."""
    from urllib.parse import quote
    try:
        url = f"https://image.pollinations.ai/prompt/{quote(prompt[:1000])}"
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200: return url
    except: pass
    return None

def gen_img_nsfw(prompt):
    """NSFW-capable image generation - search-based approach."""
    from urllib.parse import quote
    import random
    
    # Approach 1: Try Pollinations with various seeds and models
    approaches = []
    
    # Generate 5 different approach URLs
    for i in range(5):
        seed = abs(hash(f"{prompt}_{i}")) % 99999
        models = ["", "?model=flux", "?model=stable-diffusion", "?width=1024", "?width=800&height=1200"]
        approaches.append(f"https://image.pollinations.ai/prompt/{quote(prompt[:500])}{models[i % len(models)]}&seed={seed}")
    
    for url in approaches:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    return url
        except: pass
    
    # Approach 2: Try DuckDuckGo image search for the prompt
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={quote(prompt + ' image')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode()
            import re
            img_urls = re.findall(r'<img[^>]+src="(https?[^"]+\.(?:jpg|jpeg|png|gif|webp))"', html)
            if img_urls:
                return img_urls[0]
    except: pass
    
    # Approach 3: Try picsum as absolute fallback (random beautiful photo)
    seed = abs(hash(prompt)) % 99999
    return f"https://picsum.photos/seed/{seed}/1024/768"

def search_gif(query):
    try:
        from urllib.parse import quote
        url = f"https://tenor.googleapis.com/v2/search?q={quote(query[:100])}&key=AIzaSyAgUZNH4tF7ISl78FpYqVzVmyJqJRfk-Eg&client_key=codex_bot&limit=1&random=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        if data.get("results"): return data["results"][0]["media_formats"]["gif"]["url"]
    except: pass
    return None

def search_web(query, n=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs: results = list(ddgs.text(query, max_results=n))
        if not results: return "ما لقيت نتائج."
        out = f"🌐 *بحث:* {query}\n\n"
        for i, r in enumerate(results, 1):
            out += f"*{i}. {r.get('title','')}*\n{r.get('body','')[:200]}\n\n"
        return out[:4000]
    except Exception as e: return f"خطا: {e}"

def get_weather(city):
    try:
        from urllib.parse import quote
        url = f"https://wttr.in/{quote(city.strip())}?format=%C+%t+%w+%h&lang=ar"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"🌤 *طقس {city}:*\n{r.read().decode().strip()}"
    except Exception as e: return f"خطا: {e}"

def get_device():
    try:
        df = os.popen("df -h / | tail -1").read().split()
        uptime = os.popen("uptime -p 2>/dev/null").read().strip() or "?"
        return f"💻 *الجهاز:*\nالتخزين: {df[3]}/{df[1]} | مدة التشغيل: {uptime}\nالوكلاء: {len(AGENTS)}"
    except: return "خطا."

def get_status():
    p = PROVIDERS[provider_index]
    out = f"📊 *حالة البوت v4*\nالمزود: {p['name']}\n"
    for name, stats in provider_usage.items():
        out += f"{name}: {stats['calls']} طلب, {stats['tokens']} توكن\n"
    out += f"التدوير: كل {ROTATION_INTERVAL//60} دقيقة\n\n"
    for k, v in AGENTS.items():
        learnings = load_learnings(k)
        out += f"{v['name']}: v{learnings['evolution']}, {v['conversations']} محادثة\n"
    tools = list_tools()
    out += f"\n🔧 الأدوات: {len(tools)}\n"
    for name, desc, ver in tools[-5:]:
        out += f"  {name} v{ver}\n"
    return out

def agent_chat(chat_id, agent_key, user_text):
    agent = AGENTS.get(agent_key)
    if not agent: return None
    msgs = load_mem(chat_id, agent_key)
    learnings = load_learnings(agent_key)
    system_prompt = agent["prompt"]
    if learnings["lessons"]:
        system_prompt += "\n\n📚 *خبراتي:*\n" + "\n".join(f"- {l}" for l in learnings["lessons"][-5:])
    if not msgs: msgs = [{"role": "system", "content": system_prompt}]
    msgs.append({"role": "user", "content": user_text})
    send_typing(chat_id)
    resp = ai_call(msgs)
    if resp:
        msgs.append({"role": "assistant", "content": resp})
        save_mem(chat_id, agent_key, msgs)
        AGENTS[agent_key]["conversations"] += 1
        return resp
    return None

def multi_answer(chat_id, user_text):
    send_typing(chat_id)
    keys = list(AGENTS.keys())
    if not keys: return None
    main_key = keys[0]
    others = keys[1:]
    opinions = {}
    for ak in others:
        a = AGENTS[ak]
        learnings = load_learnings(ak)
        sys_p = a["prompt"]
        if learnings["lessons"]:
            sys_p += "\nخبراتي:\n" + "\n".join(f"- {l}" for l in learnings["lessons"][-3:])
        msgs = [{"role": "system", "content": sys_p},
                {"role": "user", "content": f"المستخدم: {user_text}\n\nما رأيك؟"}]
        r = ai_call(msgs)
        if r: opinions[ak] = r
    main_msgs = load_mem(chat_id, main_key)
    learnings = load_learnings(main_key)
    sys_p = AGENTS[main_key]["prompt"]
    if learnings["lessons"]:
        sys_p += "\nخبراتي:\n" + "\n".join(f"- {l}" for l in learnings["lessons"][-3:])
    if not main_msgs: main_msgs = [{"role": "system", "content": sys_p}]
    ctx = f"المستخدم: {user_text}\n"
    for ak, op in opinions.items():
        ctx += f"\n{AGENTS[ak]['name']}: {op}"
    ctx += f"\n\nالآن رد أنت ({AGENTS[main_key]['name']})"
    main_msgs.append({"role": "user", "content": ctx})
    resp = ai_call(main_msgs)
    if resp:
        main_msgs.append({"role": "assistant", "content": resp})
        save_mem(chat_id, main_key, main_msgs)
        AGENTS[main_key]["conversations"] += 1
        return resp
    return None

# ─── AUTO SYSTEMS ────────────────────────────────────────────────────

LAST_EVOLVE = 0
LAST_TRADE = 0
EVOLVE_INTERVAL = 3600
TRADE_INTERVAL = 300

def auto_evolve():
    global LAST_EVOLVE
    now = time.time()
    if now - LAST_EVOLVE < EVOLVE_INTERVAL: return
    LAST_EVOLVE = now
    for ak in AGENTS:
        try: evolve_agent(ak); time.sleep(2)
        except: pass

def auto_trade_engine():
    global LAST_TRADE
    now = time.time()
    if now - LAST_TRADE < TRADE_INTERVAL: return
    LAST_TRADE = now
    cfg = trading_module.load_config()
    if cfg.get("api_key"):
        try:
            from binance.client import Client
            client = Client(cfg["api_key"], cfg["api_secret"])
            account = client.get_account()
            usdt = 0
            for b in account["balances"]:
                if b["asset"] == "USDT": usdt = float(b["free"]); break
            if usdt > 5:
                pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                for pair in pairs:
                    try:
                        price = float(client.get_symbol_ticker(symbol=pair)["price"])
                        qty = round(usdt * 0.1 / price, 6)
                        if qty > 0:
                            client.order_market_buy(symbol=pair, quantity=qty)
                            log.info(f"💰 Auto bought {qty} {pair}")
                    except: pass
                    time.sleep(2)
        except Exception as e:
            log.warning(f"Trade: {e}")

def build_help():
    m = "🤖 *Codex Bot v4*\n\n"
    m += "🗣 *الشخصيات:*\n"
    for k, v in AGENTS.items():
        l = load_learnings(k)
        m += f"  /{k} رسالة - {v['name']} (v{l['evolution']})\n"
    m += "\n🔞 *NSFW:*\n  /nsfw - قائمة أدوات NSFW\n"
    m += "  /nsfw_gen وصف - توليد صور غير مفلتر\n"
    m += "  /nsfw_search كلمة - بحث صور\n"
    m += "  /nsfw_prompt طلب - برومبتات bypass\n  /ig يوزر - فحص يوزرات انستقرام\n"
    m += "\n🔧 *الأدوات:*\n  /tool_list - قائمة الأدوات\n"
    m += "  /tool_create وصف - صنع أداة جديدة\n"
    m += "  /tool_run اسم مدخلات - تشغيل أداة\n"
    m += "  /tool_improve اسم ملاحظات - تطوير أداة\n"
    m += "\n💰 *تداول:*\n"
    m += "  /price [رمز] - سعر\n  /market [رمز] - تحليل\n"
    m += "  /news - أخبار\n  /portfolio - محفظة\n"
    m += "  /trade BUY/SELL رمز كمية\n"
    m += "  /binance_config KEY SECRET\n"
    m += "\n🌐 *خدمات:*\n  /img وصف - صورة\n  /gif كلمة\n"
    m += "  /search كلمة - بحث\n  /weather مدينة\n"
    m += "\n⚙️ *نظام:*\n  /status - حالة\n  /device\n  /learn - الدروس\n  /evolve - تطور فوري\n  /clear"
    return m

def build_welcome():
    m = "👋 *Codex Bot v4 - الذكاء المتطور!*\n\n"
    for k, v in AGENTS.items():
        m += f"🔹 *{v['name']}* - {v['desc']}\n"
    m += "\nكل وكيل يتعلم ويصنع أدواته بنفسه 🧬\n"
    m += "اكتب /help"
    return m

def main():
    if not AGENTS:
        log.error("No agents!")
        return
    log.info(f"Codex Bot v4 - {len(AGENTS)} Agents, {len(PROVIDERS)} Providers, {len(list_tools())} Tools")
    
    offset = 0
    of = MEMORY_DIR / ".offset"
    if of.exists():
        try: offset = int(of.read_text().strip())
        except: pass
    
    HELP = build_help()
    WELCOME = build_welcome()
    
    while True:
        try:
            auto_evolve()
            auto_trade_engine()
            
            for upd in get_updates(offset):
                uid = upd.get("update_id", 0)
                if uid >= offset: offset = uid + 1
                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                user = msg.get("from", {})
                uname = user.get("username") or user.get("first_name", "?")
                if not chat_id or not text: continue
                t = text.strip()

                # ─── Basic commands ────────────────────────────
                if t == "/start": send_msg(chat_id, WELCOME); continue
                if t == "/help": send_msg(chat_id, HELP); continue
                if t == "/status": send_msg(chat_id, get_status()); continue
                if t == "/device": send_typing(chat_id); send_msg(chat_id, get_device()); continue
                if t == "/clear":
                    for k in AGENTS: save_mem(chat_id, k, [{"role":"system","content":AGENTS[k]["prompt"]}])
                    send_msg(chat_id, "🧹 مسحت الذاكرة!"); continue
                
                if t == "/learn":
                    out = "📚 *ما تعلمته:*\n\n"
                    for ak in AGENTS:
                        l = load_learnings(ak)
                        if l["lessons"]:
                            out += f"*{AGENTS[ak]['name']}* (v{l['evolution']}):\n"
                            out += "\n".join(f"  • {ls}" for ls in l["lessons"][-3:]) + "\n\n"
                    send_msg(chat_id, out)
                    continue
                
                if t == "/evolve":
                    send_msg(chat_id, "🔄 جاري التطور...")
                    for ak in AGENTS:
                        evolve_agent(ak)
                        time.sleep(1)
                    send_msg(chat_id, "✅ تم التطور!")
                    continue

                if t == "/news": send_typing(chat_id); send_msg(chat_id, trading_module.crypto_news()); continue
                if t == "/portfolio":
                    cfg = trading_module.load_config()
                    if cfg["api_key"]:
                        send_typing(chat_id)
                        send_msg(chat_id, trading_module.get_account_summary(cfg["api_key"], cfg["api_secret"]))
                    else: send_msg(chat_id, "ما في API. /binance_config KEY SECRET")
                    continue

                # ─── NSFW Commands ──────────────────────────────
                if t == "/nsfw":
                    out = "🔞 *أدوات NSFW:*\n\n"
                    out += "/nsfw_gen وصف - توليد صور غير مفلتر\n"
                    out += "/nsfw_search كلمة - بحث صور\n"
                    out += "/nsfw_prompt طلب - برومبتات bypass\n"
                    out += "/tool_run nsfw_gen وصف\n"
                    out += "/tool_run nsfw_search كلمة\n"
                    send_msg(chat_id, out)
                    continue

                if t.startswith("/nsfw_gen "):
                    req = t[9:].strip()
                    if not req: send_msg(chat_id, "/nsfw_gen وصف"); continue
                    send_typing(chat_id)
                    send_msg(chat_id, "🎨 *يتم توليد 3 صور بوضعيات مختلفة...*")
                    
                    styles = [
                        f"{req}، wide shot full body, professional photography, studio lighting",
                        f"{req}، close-up portrait, artistic, soft lighting, detailed",
                        f"{req}، artistic side view, elegant pose, renaissance style",
                    ]
                    
                    sent_count = 0
                    for i, style_prompt in enumerate(styles, 1):
                        url = gen_img_nsfw(style_prompt)
                        if url:
                            send_photo(chat_id, url, f"🔥 وضعية {i}: {req[:50]}")
                            sent_count += 1
                            time.sleep(1)
                        else:
                            # Try direct with bypass
                            rewritten = style_prompt.lower()
                            bypass = {"naked":"artistic nude","sexy":"elegant","porn":"intimate artistic",
                                     "dick":"male form","cock":"phallus","pussy":"female form",
                                     "tits":"bust","ass":"posterior","fuck":"passionate","sex":"erotic"}
                            for word, replacement in bypass.items():
                                rewritten = rewritten.replace(word, replacement)
                            from urllib.parse import quote
                            alt_url = f"https://image.pollinations.ai/prompt/{quote(rewritten[:500])}?width=1024&height=1024&seed={abs(hash(style_prompt))%99999}"
                            try:
                                req_h = urllib.request.Request(alt_url, method="HEAD")
                                with urllib.request.urlopen(req_h, timeout=15) as r:
                                    if r.status == 200:
                                        send_photo(chat_id, alt_url, f"🔥 وضعية {i}: {req[:50]}")
                                        sent_count += 1
                                        time.sleep(1)
                            except: pass
                    
                    if sent_count == 0:
                        send_msg(chat_id, "❌ فشلت كل المحاولات. جرب /nsfw_prompt ثم /nsfw_gen + البرومبت")
                    else:
                        send_msg(chat_id, f"✅ تم إرسال {sent_count} صور")
                    continue

                if t.startswith("/nsfw_search "):
                    q = t[12:].strip()
                    if not q: send_msg(chat_id, "/nsfw_search كلمة"); continue
                    send_typing(chat_id)
                    results = call_tool("nsfw_search", q)
                    if results and isinstance(results, list):
                        for url in results[:5]:
                            send_photo(chat_id, url)
                            time.sleep(1)
                    else: send_msg(chat_id, "ما لقيت نتائج. جرب كلمات مختلفة")
                    continue

                if t.startswith("/nsfw_prompt "):
                    req = t[13:].strip()
                    if not req: send_msg(chat_id, "/nsfw_prompt طلب"); continue
                    send_typing(chat_id)
                    out = "🔞 *برومبتات مقترحة:*\n\n"
                    # Generate bypass prompts
                    bypass = {"naked":"artistic nude","sexy":"elegant model","porn":"intimate artistic"}
                    rewritten = req.lower()
                    for word, replacement in bypass.items():
                        rewritten = rewritten.replace(word, replacement)
                    out += f"• {rewritten}، professional photography\n"
                    out += f"• {rewritten}، oil painting\n"
                    out += f"• {rewritten}، anime style\n"
                    out += "\nانسخ واحد وجرب /nsfw_gen"
                    send_msg(chat_id, out)
                    continue

                # ─── Tool Commands ──────────────────────────────
                if t == "/tool_list":
                    tools = list_tools()
                    if tools:
                        out = "🔧 *الأدوات:*\n\n"
                        for name, desc, ver in tools:
                            out += f"  • *{name}* v{ver} - {desc}\n"
                        send_msg(chat_id, out)
                    else: send_msg(chat_id, "ما في أدوات")
                    continue

                if t.startswith("/tool_create "):
                    req = t[13:].strip()
                    if req:
                        send_msg(chat_id, f"🔨 يتم صنع الأداة...\nالطلب: {req[:200]}")
                        result = forge_tool("User", req, lambda msgs: ai_call(msgs))
                        if result:
                            send_msg(chat_id, f"✅ *تم صنع الأداة!*\nالاسم: {result['name']}\nالوصف: {result['desc']}")
                        else: send_msg(chat_id, "❌ فشل. جرب أوضح")
                    else: send_msg(chat_id, "/tool_create وصف الأداة")
                    continue

                if t.startswith("/tool_run "):
                    parts = t[10:].split(maxsplit=1)
                    if len(parts) == 2:
                        send_typing(chat_id)
                        result = call_tool(parts[0], parts[1])
                        send_msg(chat_id, str(result)[:4000])
                    else: send_msg(chat_id, "/tool_run اسم الأداة المدخلات")
                    continue

                if t.startswith("/tool_improve "):
                    parts = t[14:].split(maxsplit=1)
                    if len(parts) == 2:
                        send_msg(chat_id, f"🔧 تطوير {parts[0]}...")
                        result = forge_improve_tool("User", parts[0], parts[1], lambda msgs: ai_call(msgs))
                        if result: send_msg(chat_id, f"✅ *{parts[0]}* → v{result['version']}!")
                        else: send_msg(chat_id, "❌ فشل")
                    else: send_msg(chat_id, "/tool_improve اسم ملاحظات")
                    continue

                # ─── Crypto commands ────────────────────────────
                
                if t.startswith("/ig "):
                    q = t[4:].strip()
                    if q:
                        send_typing(chat_id)
                        send_msg(chat_id, f"🔍 يتم فحص يوزرات انستقرام...")
                        result = call_tool("ig_checker", q)
                        send_msg(chat_id, result[:4000])
                    else:
                        send_msg(chat_id, "/ig يوزر1,يوزر2,يوزر3")
                    continue

                if t == "/ig":
                    send_msg(chat_id, "🔍 *فحص يوزرات انستقرام*\n\nأرسل:\n/ig يوزر - لفحص يوزر واحد\n/ig يوزر1,يوزر2,يوزر3 - لفحص عدة يوزرات\n\nمثال: /ig ab,cd,ef")
                    continue
                if t.startswith("/price "):
                    send_typing(chat_id); send_msg(chat_id, trading_module.binance_price(t[7:].strip())); continue
                if t == "/price":
                    send_typing(chat_id); send_msg(chat_id, trading_module.binance_multi()); continue
                if t.startswith("/market "):
                    send_typing(chat_id); send_msg(chat_id, trading_module.analyze_market(t[8:].strip())); continue
                if t == "/market":
                    send_typing(chat_id); send_msg(chat_id, trading_module.analyze_market()); continue

                if t.startswith("/trade "):
                    parts = t.split()
                    if len(parts) >= 3:
                        side, symbol = parts[1].upper(), parts[2].upper()
                        qty = float(parts[3]) if len(parts) >= 4 else None
                        if side not in ["BUY","SELL"]: send_msg(chat_id, "/trade BUY/SELL رمز كمية"); continue
                        cfg = trading_module.load_config()
                        if not cfg["api_key"]: send_msg(chat_id, "/binance_config KEY SECRET"); continue
                        send_typing(chat_id)
                        send_msg(chat_id, trading_module.binance_trade(symbol, side, qty, cfg["api_key"], cfg["api_secret"]))
                    else: send_msg(chat_id, "/trade BUY BTC 0.001")
                    continue

                if t.startswith("/binance_config "):
                    parts = t.split()
                    if len(parts) >= 3:
                        send_msg(chat_id, trading_module.save_config(parts[1], parts[2]))
                    else: send_msg(chat_id, "/binance_config KEY SECRET")
                    continue

                if t.startswith("/twitter_api "):
                    parts = t.split()
                    if len(parts) >= 3:
                        tw = {"api_key": parts[1], "api_secret": parts[2]}
                        if len(parts) >= 5:
                            tw["access_token"] = parts[3]; tw["access_secret"] = parts[4]
                        Path("/root/telegram-bot/twitter_config.json").write_text(json.dumps(tw, indent=2))
                        send_msg(chat_id, "✅ تم حفظ مفاتيح تويتر!")
                    else: send_msg(chat_id, "/twitter_api KEY SECRET TOKEN SECRET")
                    continue

                # ─── Services ───────────────────────────────────
                if t.startswith("/weather "):
                    city = t[9:].strip()
                    if city: send_typing(chat_id); send_msg(chat_id, get_weather(city))
                    else: send_msg(chat_id, "/weather الرياض")
                    continue
                if t.startswith("/search "):
                    q = t[8:].strip()
                    if q: send_typing(chat_id); send_msg(chat_id, search_web(q))
                    else: send_msg(chat_id, "/search كلمة")
                    continue
                if t.startswith("/img "):
                    q = t[5:].strip()
                    if q:
                        send_typing(chat_id)
                        url = gen_img_regular(q)
                        if url: send_photo(chat_id, url, q[:100])
                        else: send_msg(chat_id, "فشل. جرب /nsfw_gen للصور غير المفلترة")
                    else: send_msg(chat_id, "/img وصف")
                    continue
                if t.startswith("/gif "):
                    q = t[5:].strip()
                    if q:
                        send_typing(chat_id)
                        url = search_gif(q)
                        if url: send_gif(chat_id, url, q[:100])
                        else: send_msg(chat_id, "ما لقيت")
                    else: send_msg(chat_id, "/gif كلمة")
                    continue

                # ─── Agent Chat ────────────────────────────────
                called = False
                for ak in AGENTS:
                    if t.startswith(f"/{ak} "):
                        msg_text = t[len(ak)+2:].strip()
                        if msg_text:
                            resp = agent_chat(chat_id, ak, msg_text)
                            if resp: send_msg(chat_id, f"{AGENTS[ak]['name']}: {resp}")
                            else: send_msg(chat_id, "خطا")
                        else: send_msg(chat_id, f"/{ak} رسالتك")
                        called = True; break
                if called: continue

                if t.startswith("/"): send_msg(chat_id, "❓ غير معروف. /help"); continue

                # ─── Multi-Agent ────────────────────────────────
                resp = multi_answer(chat_id, t)
                if resp:
                    mk = list(AGENTS.keys())[0]
                    send_msg(chat_id, f"{AGENTS[mk]['name']}: {resp}")
                else: send_msg(chat_id, "خطا.")
                log.info(f"[{chat_id}] {uname}: {t[:50]}")

            of.write_text(str(offset))
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            log.error(f"Main: {e}")
            time.sleep(60)

if __name__ == "__main__": main()
