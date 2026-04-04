import requests, json

BASE = "http://127.0.0.1:8000/api/v1"

def search(q, user="test_user"):
    r = requests.post(f"{BASE}/search", json={"query": q, "user_inn": user}, timeout=10)
    r.raise_for_status()
    return r.json()

print("=== Negative queries ===")
res = search("принтер -лазерный")
print(f"  'принтер -лазерный': {res['total']} results")
for item in res['results'][:3]:
    has_laser = "лазерный" in item['name'].lower()
    print(f"    [{'+' if not has_laser else 'BAD'}] {item['name'][:60]}")

print("\n=== Snippet (ts_headline) ===")
res = search("бумага офисная")
for item in res['results'][:2]:
    print(f"  name:    {item['name'][:60]}")
    print(f"  snippet: {item.get('snippet', 'n/a')}")

print("\n=== Price analytics ===")
res = search("принтер")
for item in res['results'][:3]:
    price_str = f"~{item['avg_price']:,.0f} руб ({item['price_trend']})" if item.get('avg_price') else "no price data"
    print(f"  {item['name'][:40]}: {price_str}")

print("\nAll tests done.")
