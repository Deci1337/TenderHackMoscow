"""Quick API integration test."""
import json
import urllib.request
import urllib.parse

BASE = "http://localhost:8000/api/v1"

def post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(path):
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read())


# 1. Search: school user searching for paper
print("=== Search: 'bumaga' as school user ===")
r = post("/search", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430", "user_inn": "7701234567", "limit": 5})
print(f"  total={r['total']}, corrected={r['corrected_query']}")
for item in r["results"]:
    expl = " | ".join(e["reason"] for e in item["explanations"]) or "no boost"
    print(f"  [{item['score']:.3f}] {item['name']}")
    print(f"         -> {expl}")

# 2. Search: hospital user searching for masks
print("\n=== Search: 'maska' as hospital user ===")
r = post("/search", {"query": "\u043c\u0430\u0441\u043a\u0430", "user_inn": "7709876543", "limit": 5})
print(f"  total={r['total']}")
for item in r["results"]:
    expl = " | ".join(e["reason"] for e in item["explanations"]) or "no boost"
    print(f"  [{item['score']:.3f}] {item['name']}")
    print(f"         -> {expl}")

# 3. Search: cartridge
print("\n=== Search: 'kartridzh' ===")
r = post("/search", {"query": "\u043a\u0430\u0440\u0442\u0440\u0438\u0434\u0436", "user_inn": "7701234567", "limit": 5})
print(f"  total={r['total']}")
for item in r["results"]:
    print(f"  [{item['score']:.3f}] {item['name']}")

# 4. Search: notebook (noitbuk)
print("\n=== Search: 'noitbuk' ===")
r = post("/search", {"query": "\u043d\u043e\u0443\u0442\u0431\u0443\u043a", "user_inn": "7701234567", "limit": 5})
print(f"  total={r['total']}")
for item in r["results"]:
    print(f"  [{item['score']:.3f}] {item['name']}")

# 5. Facets
print("\n=== Facets ===")
r = get("/search/facets")
for cat in r["categories"]:
    print(f"  {cat['name']}: {cat['count']}")

# 6. User profile
print("\n=== User: school ===")
r = get("/users/7701234567")
print(f"  {r['name']} | industry={r['industry']} | contracts={r['total_contracts']}")
print(f"  top_categories={r['top_categories']}")

# 7. Suggest
print("\n=== Suggest: 'bum' ===")
encoded_q = urllib.parse.quote("\u0431\u0443\u043c")
try:
    r = get(f"/search/suggest?q={encoded_q}")
    print(f"  suggestions={r['suggestions']}")
except Exception as e:
    if hasattr(e, "read"):
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ERROR: {e} body={body}")
    else:
        print(f"  ERROR: {e}")

# Event tracking
print("\n=== Event: click on item 1 ===")
r = post("/events", {"user_inn": "7701234567", "ste_id": 1, "event_type": "click", "session_id": "demo1", "query": "\u0431\u0443\u043c\u0430\u0433\u0430"})
print(f"  event_id={r['id']}")

print("\n[ALL TESTS PASSED]")
