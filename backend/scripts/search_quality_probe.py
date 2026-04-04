#!/usr/bin/env python3
"""
Probe search API with hand-picked tricky queries (typos, ambiguity, multi-word).

Run when stack is up (docker compose up) and ML indexes are built (~2 min after backend):
  python backend/scripts/search_quality_probe.py

Env:
  SEARCH_URL=http://localhost:8000/api/v1/search
  PROBE_INN=1234567890123
  PROBE_LIMIT=5

Iterate: add rows to CASES, re-run, adjust ranking in app/api/search.py and search_service.py.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("SEARCH_URL", "http://localhost:8000/api/v1/search")
INN = os.environ.get("PROBE_INN", "1234567890123")
LIMIT = int(os.environ.get("PROBE_LIMIT", "5"))

# id, query, note (what we roughly expect)
CASES: list[tuple[str, str, str]] = [
    ("q01", "карандаш", "direct product name"),
    ("q02", "карандашь", "typo: extra soft sign"),
    ("q03", "карандош", "typo: wrong vowels"),
    ("q04", "ручкаа", "typo: double letter"),
    ("q05", "бумага а4", "specific format"),
    ("q06", "бумага а5", "another format"),
    ("q07", "мышь", "typo vs mouse"),
    ("q08", "мышь компьютерная", "disambiguate mouse"),
    ("q09", "ключ", "ambiguous: tool vs software"),
    ("q10", "программа", "very vague"),
    ("q11", "для офиса", "no product noun"),
    ("q12", "канцелярия", "category word"),
    ("q13", "печать", "printing vs stamp"),
    ("q14", "сервер", "IT hardware"),
    ("q15", "коврик", "mouse pad vs rug"),
    ("q16", "стол", "furniture"),
    ("q17", "охлаждение", "cooling / AC"),
    ("q18", "линейка", "ruler"),
    ("q19", "КАРАНДАШ", "case normalization"),
    ("q20", "смартфон телефон", "two nouns"),
]


def main() -> int:
    print(f"URL={URL} limit={LIMIT}\n")
    fails = 0
    for cid, query, note in CASES:
        body = json.dumps(
            {"query": query, "user_inn": INN, "limit": LIMIT, "offset": 0, "sort_by": "relevance"}
        ).encode()
        req = urllib.request.Request(
            URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"[{cid}] FAIL HTTP {e.code} query={query!r}")
            fails += 1
            continue
        except Exception as e:
            print(f"[{cid}] FAIL {e} query={query!r}")
            fails += 1
            continue

        corr = data.get("corrected_query")
        total = data.get("total", 0)
        rows = data.get("results") or []
        print(f"--- [{cid}] {query!r} | note: {note}")
        if corr:
            print(f"    corrected: {corr!r}")
        print(f"    total={total}")
        for i, r in enumerate(rows[:LIMIT], 1):
            name = (r.get("name") or "")[:90]
            cat = (r.get("category") or "")[:50]
            sc = r.get("score")
            print(f"    {i}. [{sc}] {name}")
            if cat:
                print(f"       ({cat})")
        print()
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
