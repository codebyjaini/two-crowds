"""Polymarket's public APIs (no key): market lists by tag and each outcome's price history."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .http import JsonClient
from .store import Store

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (two-crowds research tool)", "Accept": "application/json"}


def _list(v: Any) -> list[Any]:
    if isinstance(v, list):
        return v
    try:
        out = json.loads(v or "[]")
        return out if isinstance(out, list) else []
    except (TypeError, ValueError):
        return []


@dataclass
class Market:
    id: str
    question: str
    end_date: str  # ISO timestamp
    closed: bool
    yes_token: str | None
    outcomes: list[str]
    prices: list[float]  # current, or final once resolved (1 / 0)
    event_title: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def yes_price(self) -> float | None:
        return self.prices[0] if self.prices else None

    @property
    def resolved_yes(self) -> bool | None:
        """True/False once the market settled cleanly at 1/0, else None."""
        if not self.closed or len(self.prices) < 2:
            return None
        if self.prices[0] >= 0.99:
            return True
        if self.prices[0] <= 0.01:
            return False
        return None


def to_market(m: dict[str, Any], event_title: str = "") -> Market:
    tokens = _list(m.get("clobTokenIds"))
    return Market(
        id=str(m.get("id")),
        question=m.get("question") or "",
        end_date=m.get("endDate") or "",
        closed=bool(m.get("closed")),
        yes_token=str(tokens[0]) if tokens else None,
        outcomes=[str(o) for o in _list(m.get("outcomes"))],
        prices=[float(p) for p in _list(m.get("outcomePrices")) if p not in (None, "")],
        event_title=event_title,
        raw=m,
    )


class Polymarket:
    def __init__(self, store: Store):
        self.gamma = JsonClient(GAMMA, store, headers=HEADERS, per_minute=240)
        self.clob = JsonClient(CLOB, store, headers=HEADERS, per_minute=240)

    def markets_by_tag(self, tag_slug: str, closed: bool, pages: int = 3, page_size: int = 100) -> list[Market]:
        out: list[Market] = []
        for page in range(pages):
            events = self.gamma.get(
                "/events",
                {
                    "tag_slug": tag_slug,
                    "closed": str(closed).lower(),
                    "limit": page_size,
                    "offset": page * page_size,
                    "order": "endDate",
                    "ascending": "false",
                },
                max_age=None if closed else 120,
            )
            if not isinstance(events, list) or not events:
                break
            for e in events:
                for m in e.get("markets", []) or []:
                    out.append(to_market(m, e.get("title") or ""))
            if len(events) < page_size:
                break
        return out

    def price_history(self, token: str, start_ts: int, end_ts: int) -> list[tuple[int, float]]:
        body = self.clob.get(
            "/prices-history",
            {"market": token, "startTs": start_ts, "endTs": end_ts, "fidelity": 60},
            max_age=None,
        )
        pts = body.get("history", []) if isinstance(body, dict) else []
        return [(int(p["t"]), float(p["p"])) for p in pts if "t" in p and "p" in p]

    def full_history(self, token: str) -> list[tuple[int, float]]:
        body = self.clob.get("/prices-history", {"market": token, "interval": "max", "fidelity": 60}, max_age=3600)
        pts = body.get("history", []) if isinstance(body, dict) else []
        return [(int(p["t"]), float(p["p"])) for p in pts if "t" in p and "p" in p]


def price_at(history: list[tuple[int, float]], ts: int, max_staleness: int = 6 * 3600) -> float | None:
    """The last traded price at or before `ts`, if it is recent enough to mean something."""
    best: tuple[int, float] | None = None
    for t, p in history:
        if t <= ts and (best is None or t > best[0]):
            best = (t, p)
    if best is None or ts - best[0] > max_staleness:
        return None
    return best[1]
