"""
Click logging service for collecting real user feedback.

Stores search events (impressions + clicks) in JSONL format for:
  1. Retraining the ranker on real relevance signals
  2. Computing online metrics (CTR, MRR from clicks)
  3. A/B testing CatBoost vs. baseline

Each event contains the query, shown results with scores, and which items
were clicked. This data can be directly converted to LTR training pairs.
"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from loguru import logger

DATA_DIR = Path(__file__).parent.parent / "data"
EVENTS_FILE = DATA_DIR / "search_events.jsonl"


@dataclass
class ShownItem:
    ste_id: int
    position: int
    bm25_score: float
    semantic_score: float
    final_score: float
    category: str = ""


@dataclass
class SearchEvent:
    event_id: str
    timestamp: float
    customer_inn: str
    query: str
    shown_items: list[ShownItem] = field(default_factory=list)
    clicked_ste_ids: list[int] = field(default_factory=list)
    purchased_ste_ids: list[int] = field(default_factory=list)
    backend: str = "catboost"


class ClickLoggingService:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []
        self._flush_every = 10

    def log_search(
        self,
        customer_inn: str,
        query: str,
        results: list[dict],
        backend: str = "catboost",
    ) -> str:
        """Log a search impression. Returns event_id for later click attribution."""
        event_id = f"{int(time.time() * 1000)}_{customer_inn[:8]}"
        shown = [
            ShownItem(
                ste_id=r["ste_id"],
                position=i,
                bm25_score=r.get("bm25_score", 0.0),
                semantic_score=r.get("semantic_score", 0.0),
                final_score=r.get("final_score", 0.0),
                category=r.get("category", ""),
            )
            for i, r in enumerate(results)
        ]
        event = SearchEvent(
            event_id=event_id,
            timestamp=time.time(),
            customer_inn=customer_inn,
            query=query,
            shown_items=shown,
            backend=backend,
        )
        self._write_event(event)
        return event_id

    def log_click(self, event_id: str, ste_id: int):
        """Log a click on a search result."""
        click = {
            "type": "click",
            "event_id": event_id,
            "ste_id": ste_id,
            "timestamp": time.time(),
        }
        self._buffer.append(click)
        if len(self._buffer) >= self._flush_every:
            self._flush()

    def log_purchase(self, event_id: str, ste_id: int):
        """Log a purchase after search (strongest relevance signal)."""
        purchase = {
            "type": "purchase",
            "event_id": event_id,
            "ste_id": ste_id,
            "timestamp": time.time(),
        }
        self._buffer.append(purchase)
        self._flush()

    def export_training_pairs(self, output_path: str | None = None) -> list[dict]:
        """Convert logged events to LTR training pairs.

        Relevance mapping:
          purchased item = 4, clicked item = 3,
          shown but not clicked (top 3) = 1, shown but not clicked (rest) = 0
        """
        self._flush()
        events = self._load_events()

        clicks_by_event: dict[str, set[int]] = {}
        purchases_by_event: dict[str, set[int]] = {}
        search_events: dict[str, dict] = {}

        for ev in events:
            if ev.get("type") == "click":
                clicks_by_event.setdefault(ev["event_id"], set()).add(ev["ste_id"])
            elif ev.get("type") == "purchase":
                purchases_by_event.setdefault(ev["event_id"], set()).add(ev["ste_id"])
            elif "shown_items" in ev:
                search_events[ev["event_id"]] = ev

        pairs = []
        for eid, search in search_events.items():
            clicked = clicks_by_event.get(eid, set())
            purchased = purchases_by_event.get(eid, set())

            for item in search.get("shown_items", []):
                sid = item["ste_id"]
                if sid in purchased:
                    rel = 4
                elif sid in clicked:
                    rel = 3
                elif item["position"] < 3 and sid not in clicked:
                    rel = 1
                else:
                    rel = 0

                pairs.append({
                    "query": search["query"],
                    "customer_inn": search["customer_inn"],
                    "ste_id": sid,
                    "relevance": rel,
                    "bm25_score": item.get("bm25_score", 0),
                    "semantic_score": item.get("semantic_score", 0),
                    "final_score": item.get("final_score", 0),
                    "position": item["position"],
                })

        if output_path:
            import pandas as pd
            pd.DataFrame(pairs).to_csv(output_path, index=False)
            logger.info(f"Exported {len(pairs)} training pairs to {output_path}")

        return pairs

    def get_stats(self) -> dict:
        """Return basic stats about logged events."""
        events = self._load_events()
        searches = [e for e in events if "shown_items" in e]
        clicks = [e for e in events if e.get("type") == "click"]
        purchases = [e for e in events if e.get("type") == "purchase"]
        return {
            "total_searches": len(searches),
            "total_clicks": len(clicks),
            "total_purchases": len(purchases),
            "avg_ctr": len(clicks) / max(len(searches), 1),
        }

    def _write_event(self, event: SearchEvent):
        raw = asdict(event)
        raw["shown_items"] = [asdict(si) for si in event.shown_items]
        self._buffer.append(raw)
        if len(self._buffer) >= self._flush_every:
            self._flush()

    def _flush(self):
        if not self._buffer:
            return
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            for item in self._buffer:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._buffer.clear()

    def _load_events(self) -> list[dict]:
        if not EVENTS_FILE.exists():
            return []
        events = []
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events


_click_service: ClickLoggingService | None = None


def get_click_logging_service() -> ClickLoggingService:
    global _click_service
    if _click_service is None:
        _click_service = ClickLoggingService()
    return _click_service
