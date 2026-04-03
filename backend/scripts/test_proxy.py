"""Test Vite proxy."""
import json
import urllib.request

def test(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        if data:
            req.data = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        r = urllib.request.urlopen(req)
        body = json.loads(r.read())
        print(f"OK {url} -> {json.dumps(body, ensure_ascii=False)[:200]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERR {e.code} {url} -> {body[:200]}")

# Via Vite proxy (port 5177)
print("=== Via Vite Proxy (5177) ===")
test("http://127.0.0.1:5177/api/v1/search/facets")
test("http://127.0.0.1:5177/api/v1/search", "POST", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430", "user_inn": "7701234567", "limit": 3})
test("http://127.0.0.1:5177/api/v1/users/7701234567")

# Direct backend (port 8000)
print("\n=== Direct Backend (8000) ===")
test("http://127.0.0.1:8000/api/v1/search/facets")
test("http://127.0.0.1:8000/api/v1/search", "POST", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430", "user_inn": "7701234567", "limit": 3})
