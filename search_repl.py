"""
Interactive search REPL for testing any query against the running backend.

Usage:
    python search_repl.py
    python search_repl.py --user demo_school    # use specific user
    python search_repl.py --debug               # show query processing details

Commands inside the REPL:
    <any text>          search for it
    -d <query>          show debug info for query (how it's processed)
    -u <user_id>        switch user
    :exit / :quit       exit
    :help               show help

Supports negative queries: "принтер -лазерный"
No hardcoded queries — tests exactly what you type.
"""
import argparse
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://127.0.0.1:8000/api/v1"
PRICE_TREND = {"up": " (цена растёт)", "down": " (цена снижается)", "stable": ""}
RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"


def _request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    url = BASE + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"{RED}HTTP {e.code}: {body[:200]}{RESET}")
        return {}
    except Exception as e:
        print(f"{RED}Connection error: {e}{RESET}")
        return {}


def do_search(query: str, user: str, show_debug: bool = False) -> None:
    if show_debug:
        params = urllib.parse.urlencode({"q": query})
        dbg = _request(f"/search/debug?{params}")
        if dbg:
            print(f"\n{DIM}--- Query processing ---{RESET}")
            print(f"  Input:              {dbg.get('input')}")
            print(f"  After strip:        {dbg.get('after_boilerplate_strip')}")
            print(f"  Transliterated:     {dbg.get('after_transliteration')}")
            print(f"  Lemmatized:         {dbg.get('lemmatized')}")
            print(f"  Negative terms:     {dbg.get('negative_terms') or 'none'}")
            print(f"  Manual synonyms:    {dbg.get('manual_synonyms') or 'none'}")
            print(f"  Catalog expansion:  {dbg.get('catalog_expansion') or 'none'}")
            print(f"  Final tsquery:      {dbg.get('final_ts_query')}")
            print()

    result = _request("/search", "POST", {"query": query, "user_inn": user})
    if not result:
        return

    total = result.get("total", 0)
    corrected = result.get("corrected_query")
    did_you_mean = result.get("did_you_mean")

    if corrected:
        print(f"  {YELLOW}Исправлено:{RESET} «{query}» -> «{corrected}»")
    if did_you_mean:
        print(f"  {DIM}{did_you_mean}{RESET}")

    print(f"\n{BOLD}Найдено: {total} результатов{RESET}  (показаны первые {min(total, 10)})\n")

    for i, item in enumerate(result.get("results", [])[:10], 1):
        name = item.get("name", "—")
        cat = item.get("category") or ""
        score = item.get("score", 0)
        avg_price = item.get("avg_price")
        price_trend = item.get("price_trend") or "stable"
        snippet = item.get("snippet") or ""
        explanations = item.get("explanations", [])

        price_str = ""
        if avg_price is not None:
            price_str = f"  {GREEN}~{avg_price:,.0f} ₽{PRICE_TREND.get(price_trend, '')}{RESET}"

        # Strip ts_headline markers for terminal display
        snippet_clean = snippet.replace("<<", "").replace(">>", "")

        print(f"  {BOLD}{i:>2}.{RESET} {name}")
        if cat:
            print(f"      {DIM}{cat}{RESET}{price_str}")
        if snippet_clean and snippet_clean != name:
            print(f"      {DIM}... {snippet_clean} ...{RESET}")
        if explanations:
            tags = " | ".join(e.get("reason", "") for e in explanations[:3])
            print(f"      {BLUE}[{tags}]{RESET}")
        print(f"      {DIM}score: {score:.4f}{RESET}")
        print()


def print_help() -> None:
    print(f"""
{BOLD}Команды:{RESET}
  <запрос>          — поиск (любой текст, в т.ч. на латинице)
  -d <запрос>       — поиск + детали обработки запроса
  -u <user_id>      — сменить пользователя
  :exit / :quit     — выход

{BOLD}Примеры запросов:{RESET}
  бумага офисная          — многословный запрос
  принтер -лазерный       — негативный запрос (исключить слово)
  сварка                  — слово не из словаря → catalog expansion
  printer                 — транслитерация (→ принтер)
  закупка бумаги а4       — boilerplate stripping (→ бумага а4)
  ЗИП для насоса          — аббревиатура → синоним из словаря

Используй {BOLD}-d{RESET} чтобы увидеть как именно обрабатывается любой запрос.
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive search REPL")
    parser.add_argument("--user", default="anon_test", help="User ID for personalization")
    parser.add_argument("--debug", action="store_true", help="Always show query debug info")
    args = parser.parse_args()

    current_user = args.user
    always_debug = args.debug

    print(f"\n{BOLD}Smart Search REPL{RESET}  (пользователь: {current_user})")
    print(f"Бэкенд: {BASE}  |  Введи :help для справки\n")

    # Check backend availability
    health = _request("/../../health")
    if not health:
        print(f"{RED}Бэкенд недоступен. Убедись что сервер запущен на порту 8000.{RESET}\n")

    while True:
        try:
            raw = input(f"{BLUE}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nПока!")
            break

        if not raw:
            continue
        if raw in (":exit", ":quit", "exit", "quit"):
            print("Пока!")
            break
        if raw == ":help":
            print_help()
            continue

        # Switch user
        if raw.startswith("-u "):
            current_user = raw[3:].strip()
            print(f"  Пользователь: {current_user}")
            continue

        # Debug mode for this query
        show_debug = always_debug
        if raw.startswith("-d "):
            raw = raw[3:].strip()
            show_debug = True

        do_search(raw, current_user, show_debug=show_debug)


if __name__ == "__main__":
    main()
