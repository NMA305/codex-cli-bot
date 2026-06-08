"""🔌 AI Proxy"""
import urllib.request, json
def run(messages, model=None):
    keys = ["YOUR_OPENROUTER_KEY1"]
    m = model or "google/gemma-4-26b-a4b-it:free"
    for key in keys:
        try:
            body = json.dumps({"model":m,"messages":messages,"max_tokens":1024}).encode()
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=body, headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except: pass
    return None
