def run(city):
    """Get weather. Args: city (str)"""
    import urllib.request
    from urllib.parse import quote
    url = f"https://wttr.in/{quote(city)}?format=%C+%t+%w&lang=ar"
    with urllib.request.urlopen(url, timeout=10) as r:
        return f"Weather in {city}: {r.read().decode().strip()}"
