"""Quick search test to verify real data is working."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests

BASE = "http://127.0.0.1:8000/api/v1"
PAYLOAD = {"user_inn": "test", "limit": 5}

queries = ["строительство", "лекарства", "компьютер", "мебель", "бумага", "цемент", "трубы"]

for q in queries:
    payload = {**PAYLOAD, "query": q}
    try:
        resp = requests.post(f"{BASE}/search", json=payload, timeout=30)
        data = resp.json()
    except Exception as e:
        print(f"ERROR for '{q}': {e}")
        continue

    items = data.get("results", [])
    total = data.get("total", 0)
    corrected = data.get("corrected_query")
    print(f"\nQuery: '{q}'{' -> corrected: ' + corrected if corrected and corrected != q else ''}  total={total}")
    for item in items[:3]:
        name = item.get("name", "")[:70]
        cat = item.get("category", "")[:40]
        score = item.get("score", 0)
        print(f"  [{item.get('id')}] {name}  cat={cat}  score={score:.3f}")
    if not items:
        print("  (no results)")
