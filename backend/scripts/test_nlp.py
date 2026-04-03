"""Test NLP pipeline: typos + synonyms + search."""
import json
import urllib.request


def search(query, inn="7701234567"):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/search",
        data=json.dumps({"query": query, "user_inn": inn, "limit": 5}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


tests = [
    ("\u0431\u0443\u043c\u0430\u0433\u0430", "normal query"),
    ("\u0431\u0443\u043c\u0430\u0433\u0430\u0430", "typo: bumaga -> bumagaa"),
    ("\u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440", "synonym: computer"),
    ("\u043f\u043a", "synonym: pk -> computer"),
    ("\u043c\u0444\u0443", "synonym: mfu -> printer"),
    ("\u043a\u0430\u0442\u0440\u0438\u0434\u0436", "typo: katridzh (missing r)"),
    ("\u043d\u043e\u0443\u0442\u0431\u0443\u043a", "normal: noutbuk"),
    ("\u043b\u044d\u043f\u0442\u043e\u043f", "synonym: laptop -> noutbuk"),
    ("\u043c\u0430\u0441\u043a\u0430", "synonym: maska"),
    ("\u0440\u0435\u0441\u043f\u0438\u0440\u0430\u0442\u043e\u0440", "synonym: respirator -> maska"),
    ("\u0441\u0442\u0443\u043b \u043e\u0444\u0438\u0441\u043d\u044b\u0439", "two words"),
    ("\u0444\u043b\u0435\u0448\u043a\u0430", "synonym: fleshka"),
]

for query, desc in tests:
    r = search(query)
    corrected = r.get("corrected_query")
    names = [item["name"][:50] for item in r["results"][:3]]
    correction_note = f" [corrected -> {corrected}]" if corrected else ""
    print(f"[{desc}] q='{query}'{correction_note} -> {r['total']} results")
    for n in names:
        print(f"    {n}")
    print()
