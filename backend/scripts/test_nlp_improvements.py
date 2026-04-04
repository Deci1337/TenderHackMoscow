"""Smoke test for boilerplate stripping, abbreviations, and popularity logic."""
import sys
sys.path.insert(0, "c:/Users/HONOR/Desktop/TenderHackMoscow/backend")

from app.services.query_processor import strip_procurement_boilerplate, process_query
from app.services.synonyms import expand_query

TESTS = [
    ("поставка бумаги офисной",   "boilerplate"),
    ("закупка компьютеров",        "boilerplate"),
    ("приобретение мебели",        "boilerplate"),
    ("лкм для стен",               "abbreviation"),
    ("пэвм",                       "abbreviation"),
    ("гсм топливо",                "abbreviation"),
    ("сиз перчатки",               "abbreviation"),
    ("зип детали",                 "abbreviation"),
    ("стройка материалы",          "synonym"),
    ("ремонт",                     "synonym"),
]

print("=== Boilerplate + Abbreviation tests ===")
ok = 0
for q, kind in TESTS:
    stripped = strip_procurement_boilerplate(q)
    expanded, syns = expand_query(stripped)
    changed = (stripped != q) or bool(syns)
    status = "OK" if changed else "~"
    ok += 1 if changed else 0
    print(f"  [{status}] [{kind}] '{q}' -> stripped='{stripped}', syns={syns[:2]}")

print(f"\n{ok}/{len(TESTS)} queries improved")
