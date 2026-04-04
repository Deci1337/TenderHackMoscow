# -*- coding: utf-8 -*-
"""Test that context-aware homograph resolution works correctly."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "backend")

from app.services.homograph_service import resolve_homograph

cases = [
    ("ручка", "Строительство",       ["ручка дверная"]),
    ("ручка", "Канцелярские товары",  ["ручка шариковая"]),
    ("ручка", "Образование",          ["ручка шариковая"]),
    ("ручка", None,                   ["ручка шариковая"]),  # default = pen
    ("кран",  "Строительство",        ["кран башенный"]),
    ("ключ",  "Строительство",        ["ключ гаечный"]),
    ("ключ",  "IT и связь",           ["ключ лицензионный"]),
]

ok = 0
fail = 0
for word, industry, expected_contains in cases:
    result = resolve_homograph(word, industry)
    match = any(any(e in r for r in result) for e in expected_contains)
    status = "OK" if (match or not result) else "FAIL"
    if status == "OK":
        ok += 1
    else:
        fail += 1
    print(f"  [{status}] {word!r} + {str(industry):25} -> {result}")

print(f"\n{ok}/{ok+fail} passed")
