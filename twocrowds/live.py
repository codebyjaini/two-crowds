"""Right now: open Polymarket stock markets, priced by both crowds."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .implied import options_prob
from .parse import parse
from .polymarket import Market, Polymarket
from .uw import UnusualWhales

NY = ZoneInfo("America/New_York")
CATEGORY_ORDER = {"Finance": 0, "Technology": 1, "Politics": 2, "Crypto": 3}
OPEN, CLOSE = time(9, 30), time(16, 0)


def trading_days_until(event: date, now: datetime) -> float:
    """Trading time from `now` to the close on `event`, in trading days (6.5 h each)."""
    now = now.astimezone(NY)
    today = now.date()
    if event < today:
        return 0.0
    left_today = 0.0
    if today.weekday() < 5:
        start = max(now, datetime.combine(today, OPEN, NY))
        end = datetime.combine(today, CLOSE, NY)
        left_today = max(0.0, (end - start).total_seconds()) / (6.5 * 3600)
    if event == today:
        return left_today
    whole = 0
    d = today + timedelta(days=1)
    while d <= event:
        if d.weekday() < 5:
            whole += 1
        d += timedelta(days=1)
    return left_today + whole


@dataclass
class Card:
    market_id: str
    question: str
    ticker: str
    kind: str
    event_date: str
    strike: float | None
    crowd_prob: float | None
    options_prob: float | None
    spot: float | None
    sigma: float | None
    trading_days: float | None
    flow_lean: float | None = None
    flow_bought_calls: float | None = None
    flow_bought_puts: float | None = None
    unusual: dict[str, Any] | None = None
    note: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def gap(self) -> float | None:
        if self.crowd_prob is None or self.options_prob is None:
            return None
        return self.options_prob - self.crowd_prob

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "gap": self.gap, "verdict": verdict(self.gap)}


def verdict(gap: float | None, threshold: float = 0.10) -> str:
    if gap is None:
        return "no options view"
    gap = round(gap, 2)  # judge the gap as shown, in whole points
    if gap >= threshold:
        return "options more bullish"
    if gap <= -threshold:
        return "options more bearish"
    return "crowds agree"


def board(pm: Polymarket, uw: UnusualWhales, now: datetime | None = None, horizon_days: int = 5) -> dict[str, Any]:
    now = now or datetime.now(NY)
    markets = pm.markets_by_tag("stocks", closed=False, pages=3) + pm.markets_by_tag("earnings", closed=False, pages=1)
    try:
        unusual_rows = uw.unusual_markets()
    except Exception:
        unusual_rows = []
    unusual = {str(u.get("asset_id")): u for u in unusual_rows}
    spot_cache: dict[str, float | None] = {}
    iv_cache: dict[str, Any] = {}
    flow_cache: dict[str, Any] = {}
    cards: list[Card] = []
    seen: set[str] = set()
    for m in markets:
        if m.id in seen:
            continue
        seen.add(m.id)
        q = parse(m.question, m.end_date)
        if not q or not q.event_date:
            continue
        if q.event_date < now.date() or (q.event_date - now.date()).days > horizon_days + 2:
            continue
        card = Card(m.id, m.question, q.ticker, q.kind, q.event_date.isoformat(), q.strike, m.yes_price, None, None, None, None)
        flag = unusual.get(m.yes_token or "")
        if flag:
            card.unusual = {
                "score": flag.get("unusual_score"),
                "smart_volume": flag.get("smart_volume"),
                "tags": [t.get("tag") for t in flag.get("tags") or []],
                "insiders": len(flag.get("top_insiders") or []),
            }
        try:
            if q.ticker not in flow_cache:
                flow_cache[q.ticker] = uw.flow_tilt(q.ticker, newer_than=(now.date() - timedelta(days=3)).isoformat())
            ft = flow_cache[q.ticker]
            card.flow_lean, card.flow_bought_calls, card.flow_bought_puts = round(ft.lean, 3), ft.bought_calls, ft.bought_puts
        except Exception as err:
            card.note = f"flow unavailable ({err})"
        if q.priceable:
            try:
                if q.ticker not in spot_cache:
                    closes = uw.daily_closes(q.ticker, limit=5)
                    spot_cache[q.ticker] = closes  # date -> close; today's bar updates during the session
                    iv_cache[q.ticker] = uw.interpolated_iv(q.ticker)
                closes, iv = spot_cache[q.ticker] or {}, iv_cache.get(q.ticker) or []
                spot = closes[max(closes)] if closes else None
                td = trading_days_until(q.event_date, now)
                strike = q.strike
                if q.kind == "up_down" and closes:
                    # Up/down is measured from the close before the event day.
                    before = [d for d in closes if d < q.event_date.isoformat()]
                    strike = closes[max(before)] if before else spot
                if spot and iv and td > 0:
                    view = options_prob(q.kind, spot, strike, iv, td)
                    if view:
                        card.options_prob, card.spot, card.sigma, card.trading_days = round(view.prob, 4), spot, round(view.sigma, 4), round(td, 3)
            except Exception as err:
                card.note = f"options view unavailable ({err})"
        cards.append(card)
    priced = sorted([c for c in cards if c.gap is not None], key=lambda c: -abs(c.gap or 0))
    other = [c for c in cards if c.gap is None]
    return {
        "as_of": now.astimezone(NY).isoformat(timespec="minutes"),
        "priced": [c.as_dict() for c in priced],
        "other": [c.as_dict() for c in other],
        "unusual_count": sum(1 for c in cards if c.unusual),
        "uw_unusual": [
            {
                "market": u.get("market"),
                "outcome": u.get("outcome"),
                "price": u.get("current"),
                "category": u.get("category"),
                "resolves": u.get("resolves"),
                "unusual_score": u.get("unusual_score"),
                "smart_volume": u.get("smart_volume"),
                "volume": u.get("volume"),
                "tags": [t.get("tag") for t in u.get("tags") or []],
                "insiders": len(u.get("top_insiders") or []),
                "insider_usd": sum(float(i.get("total_invested_usd") or 0) for i in u.get("top_insiders") or []),
            }
            for u in sorted(
                # Minute-by-minute crypto up/down markets crowd out the rest; finance and tech first.
                [u for u in unusual_rows if " - " not in (u.get("market") or "") or "Up or Down" not in (u.get("market") or "")],
                key=lambda u: (CATEGORY_ORDER.get(u.get("category") or "", 9), -float(u.get("unusual_score") or 0)),
            )[:12]
        ],
    }
