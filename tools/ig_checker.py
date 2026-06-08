"""Instagram Username Checker - Check if usernames are available/taken"""
import urllib.request, json, re, time

def run(username_or_list):
    """
    Check Instagram usernames.
    Args: username (str) or comma-separated list (e.g. "ab,cd,ef")
    Returns: status of each username
    """
    # Parse input
    if "," in username_or_list:
        usernames = [u.strip() for u in username_or_list.split(",")]
    else:
        usernames = [username_or_list.strip()]
    
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36"}
    
    for username in usernames:
        if not username or len(username) < 1:
            continue
        
        url = f"https://www.instagram.com/{username}/"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                html = r.read().decode(errors='ignore')[:10000]
                
                # Try to determine status
                if "Page Not Found" in html or "page isn't available" in html.lower():
                    results.append(f"@{username}: ✅ متاح")
                elif f'"username":"{username}"' in html:
                    results.append(f"@{username}: ❌ مأخوذ")
                elif f'"id":' in html and 'biography' in html:
                    results.append(f"@{username}: ❌ مأخوذ")
                elif "Login" in html and "Sign up" in html:
                    results.append(f"@{username}: ⚠️ يحتاج تسجيل دخول للتأكيد")
                else:
                    results.append(f"@{username}: ⚠️ غير معروف (يجرب يدوي)")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                results.append(f"@{username}: ✅ متاح")
            else:
                results.append(f"@{username}: ❌ {e.code}")
        except Exception as e:
            results.append(f"@{username}: ❌ خطأ اتصال")
        
        time.sleep(1)  # Rate limit
    
    return "\n".join(results)
