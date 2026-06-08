"""Tool Forge - AI agents create their own tools"""
import os, json, logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools import register_tool, list_tools, BUILTIN_TOOLS

log = logging.getLogger("codex-bot.forge")

# Initialize built-in tools on import
for name, info in BUILTIN_TOOLS.items():
    register_tool(name, info["description"], info["code"])

def forge_tool(agent_name, user_request, ai_call_fn):
    """
    An agent uses AI to design and create a new tool.
    
    Args:
        agent_name: Name of the agent requesting the tool
        user_request: What the agent needs the tool for
        ai_call_fn: Function to call AI (messages -> response)
    """
    prompt = f"""أنت مهندس برمجيات خبير. المستخدم '{agent_name}' يحتاج أداة جديدة.

الطلب: {user_request}

الأدوات الموجودة حالياً:
{chr(10).join(f"- {t[0]}: {t[1]}" for t in list_tools())}

المطلوب: اكتب أداة Python جديدة كاملة.
- يجب أن تحتوي على دالة run() تقبل parameters
- يجب أن تكون real وتشتغل فعلاً
- استخدم مكتبات موجودة (urllib, json, time, etc)

أرسل الرد بهذا الشكل JSON فقط:
{{
    "tool_name": "اسم_الأداة",
    "description": "وصف قصير",
    "version": 1,
    "code": "كود Python الكامل"
}}"""
    
    resp = ai_call_fn([
        {"role": "system", "content": "أنت مهندس برمجيات. رد بـ JSON فقط."},
        {"role": "user", "content": prompt}
    ])
    
    if not resp:
        return None
    
    try:
        if "{" in resp:
            json_str = resp[resp.index("{"):]
            if "}" in json_str: json_str = json_str[:json_str.rindex("}")+1]
            tool_data = json.loads(json_str)
            
            name = tool_data.get("tool_name", "").strip()
            desc = tool_data.get("description", "").strip()
            code = tool_data.get("code", "").strip()
            
            if name and code:
                register_tool(name, desc, code)
                log.info(f"🔨 {agent_name} forged new tool: {name}")
                return {"name": name, "desc": desc}
    except Exception as e:
        log.warning(f"Forge error: {e}")
    
    return None

def forge_improve_tool(agent_name, tool_name, feedback, ai_call_fn):
    """Agent improves an existing tool based on feedback."""
    from tools import get_tool, TOOLS_DIR
    
    info = get_tool(tool_name)
    if not info:
        return None
    
    tool_file = TOOLS_DIR / f"{tool_name}.py"
    current_code = tool_file.read_text("utf-8") if tool_file.exists() else ""
    
    prompt = f"""أنت مهندس برمجيات. طور الأداة التالية بناءً على الملاحظات.

اسم الأداة: {tool_name}
الملاحظات: {feedback}

الكود الحالي:
```python
{current_code}
```

أرسل JSON:
{{
    "tool_name": "{tool_name}",
    "description": "وصف محدث",
    "version": 2,
    "code": "الكود المطور"
}}"""
    
    resp = ai_call_fn([
        {"role": "system", "content": "أنت مطور بايثون. رد بـ JSON."},
        {"role": "user", "content": prompt}
    ])
    
    if not resp:
        return None
    
    try:
        if "{" in resp:
            json_str = resp[resp.index("{"):]
            if "}" in json_str: json_str = json_str[:json_str.rindex("}")+1]
            data = json.loads(json_str)
            
            code = data.get("code", "").strip()
            if code:
                # Check version
                from tools import load_registry, save_registry
                reg = load_registry()
                old_ver = reg["versions"].get(tool_name, 1)
                new_ver = old_ver + 1
                
                register_tool(tool_name, data.get("description", info["desc"]), code, new_ver)
                log.info(f"🔧 {agent_name} improved {tool_name} → v{new_ver}")
                return {"name": tool_name, "version": new_ver}
    except Exception as e:
        log.warning(f"Improve error: {e}")
    
    return None
