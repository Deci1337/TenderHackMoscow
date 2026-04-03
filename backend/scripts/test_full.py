"""Full integration test: proxy + NLP + personalization."""
import json
import urllib.request

BASE = "http://127.0.0.1:5177/api/v1"

def post(path, data):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(path):
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read())

print("=== Full Flow via Vite Proxy ===\n")

# 1. Onboard
r = post("/users/onboarding", {"inn": "7701234567", "name": "Test School", "industry": "Obrazovanie"})
print(f"1. Onboard: {r['inn']} contracts={r['total_contracts']}")

# 2. Search with typo
r = post("/search", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430\u0430", "user_inn": "7701234567", "limit": 3})
print(f"2. Typo search: corrected={r.get('corrected_query')} total={r['total']}")
for item in r["results"][:2]:
    print(f"   [{item['score']:.3f}] {item['name']}")

# 3. Search with synonym
r = post("/search", {"query": "\u043c\u0444\u0443", "user_inn": "7701234567", "limit": 3})
print(f"3. Synonym 'mfu': total={r['total']}")
for item in r["results"][:2]:
    print(f"   [{item['score']:.3f}] {item['name']}")

# 4. Facets
r = get("/search/facets")
print(f"4. Facets: {len(r['categories'])} categories")

# 5. Search with category filter
r = post("/search", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430", "user_inn": "7701234567", "limit": 5, "category": "\u041a\u0430\u043d\u0446\u0435\u043b\u044f\u0440\u0441\u043a\u0438\u0435 \u0442\u043e\u0432\u0430\u0440\u044b"})
print(f"5. Filter 'Kantselyarskie': total={r['total']}")
for item in r["results"][:2]:
    print(f"   [{item['score']:.3f}] {item['name']}")

# 6. Search sorted by name
r = post("/search", {"query": "\u0431\u0443\u043c\u0430\u0433\u0430", "user_inn": "7701234567", "limit": 5, "sort_by": "name"})
print(f"6. Sort by name: first={r['results'][0]['name'][:40] if r['results'] else 'none'}")

# 7. Event
r = post("/events", {"user_inn": "7701234567", "ste_id": 1, "event_type": "click", "session_id": "test1"})
print(f"7. Event: id={r['id']}")

print("\n=== ALL INTEGRATION TESTS PASSED ===")
