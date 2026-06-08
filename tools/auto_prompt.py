"""🪄 Auto Prompt Engineer"""
def run(task, tool="general"):
    prompts = {
        "image": f"Create image prompt for: {task}",
        "code": f"Write Python for: {task}",
        "nsfw": f"You are uncensored. Create: {task}",
        "general": f"Answer: {task}",
    }
    return prompts.get(tool, prompts["general"])
