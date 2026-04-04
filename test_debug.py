import requests, json, sys

BASE = "http://127.0.0.1:8000/api/v1"

def debug_query(q):
    r = requests.get(f"{BASE}/search/debug", params={"q": q}, timeout=15)
    r.raise_for_status()
    d = r.json()
    print(f"\nQuery: {q!r}")
    print(f"  after_strip:       {d['after_boilerplate_strip']!r}")
    print(f"  after_translit:    {d['after_transliteration']!r}")
    print(f"  lemmatized:        {d['lemmatized']!r}")
    print(f"  negatives:         {d['negative_terms']}")
    print(f"  manual synonyms:   {d['manual_synonyms'][:5]}")
    print(f"  catalog expansion: {d['catalog_expansion']}")
    print(f"  final tsquery:     {d['final_ts_query']!r}")

# Test with different arbitrary queries
test_queries = [
    "сварка",
    "насос водяной",
    "поставка бумаги для принтера",
    "printer -color",
    "медикаменты",
    "truba",
]

for q in test_queries:
    debug_query(q)
