def run(query):
    """Search the web. Args: query (str)"""
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if not results: return "No results"
    return "\n".join(f"- {r['title']}: {r['body'][:100]}" for r in results)
