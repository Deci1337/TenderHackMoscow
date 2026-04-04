# -*- coding: utf-8 -*-
"""Verify that 'ручка' returns door handles for Строительство, pens for Канцелярия."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests

BASE = "http://127.0.0.1:8000/api/v1"

def search(query, interests, label):
    resp = requests.post(f"{BASE}/search", json={
        "query": query, "user_inn": "test_context",
        "interests": interests, "limit": 8
    }, timeout=30)
    data = resp.json()
    items = data.get("results", [])
    print(f"\n--- {label} ---  query='{query}'  total={data.get('total', 0)}")
    for i, item in enumerate(items, 1):
        name = item.get("name", "")[:60]
        cat = item.get("category", "")[:40]
        score = item.get("score", 0)
        print(f"  {i}. {name:<60}  [{cat}]  score={score:.3f}")

search("ручка", ["Строительство"], "СТРОИТЕЛЬСТВО (ожидаем: дверные ручки сверху)")
search("ручка", ["Канцелярские товары"], "КАНЦЕЛЯРИЯ (ожидаем: шариковые ручки сверху)")
search("ручка", ["Образование"], "ОБРАЗОВАНИЕ (ожидаем: шариковые ручки)")
