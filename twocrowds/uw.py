"""Unusual Whales API: prediction markets, implied volatility, prices and options flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .http import JsonClient
from .store import Store

BASE = "https://api.unusualwhales.com"


def _num(v: Any) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _rows(body: Any) -> list[dict[str, Any]]:
    """UW wraps lists as {"data": [...]}, sometimes {"data": {"data": [...]}}."""
    data = body.get("data", body) if isinstance(body, dict) else body
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    return data if isinstance(data, list) else []


@dataclass
class IvPoint:
    days: int
    volatility: float  # annualised, as a fraction (0.45 = 45%)
    implied_move: float | None  # fraction for that horizon


@dataclass
class FlowTilt:
    ticker: str
    bought_calls: float
    bought_puts: float
    alerts: int

    @property
    def lean(self) -> float:
        """-1 (all puts bought) .. +1 (all calls bought); 0 when nothing was bought."""
        total = self.bought_calls + self.bought_puts
        return 0.0 if total == 0 else (self.bought_calls - self.bought_puts) / total


class UnusualWhales:
    def __init__(self, api_key: str, store: Store, per_minute: int = 100):
        self.http = JsonClient(
            BASE,
            store,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json", "UW-CLIENT-API-ID": "100001"},
            per_minute=per_minute,
        )

    # ---- prediction markets (Unusual Predictions) ---------------------------
    def unusual_markets(self, categories: str | None = "Finance,Technology,Politics,Crypto", limit: int = 50) -> list[dict[str, Any]]:
        return _rows(self.http.get("/api/predictions/unusual", {"categories": categories, "limit": limit}, max_age=300))

    def smart_money(self, categories: str | None = None) -> list[dict[str, Any]]:
        return _rows(self.http.get("/api/predictions/smart-money", {"categories": categories}, max_age=600))

    def insiders(self) -> list[dict[str, Any]]:
        return _rows(self.http.get("/api/predictions/insiders", max_age=600))

    def market(self, asset_id: str, max_age: float | None = 600) -> dict[str, Any] | None:
        body = self.http.get(f"/api/predictions/market/{asset_id}", max_age=max_age)
        data = body.get("data") if isinstance(body, dict) else None
        return data if isinstance(data, dict) else None

    # ---- options and prices -------------------------------------------------
    def interpolated_iv(self, ticker: str, date: str | None = None) -> list[IvPoint]:
        # Past dates never change, so they are cached for good.
        rows = _rows(self.http.get(f"/api/stock/{ticker}/interpolated-iv", {"date": date}, max_age=None if date else 300))
        out = []
        for r in rows:
            days, vol = _num(r.get("days")), _num(r.get("volatility"))
            if days is None or vol is None or vol <= 0:
                continue
            out.append(IvPoint(int(days), vol, _num(r.get("implied_move_perc"))))
        return sorted(out, key=lambda p: p.days)

    def daily_closes(self, ticker: str, end_date: str | None = None, limit: int = 30) -> dict[str, float]:
        rows = _rows(self.http.get(f"/api/stock/{ticker}/ohlc/1d", {"end_date": end_date, "limit": limit}, max_age=None if end_date else 300))
        out = {}
        for r in rows:
            day = (r.get("date") or (r.get("start_time") or "")[:10])
            close = _num(r.get("close"))
            if day and close:
                out[day[:10]] = close
        return out

    def flow_tilt(self, ticker: str, newer_than: str | None = None, older_than: str | None = None) -> FlowTilt:
        rows = _rows(
            self.http.get(
                "/api/option-trades/flow-alerts",
                {"ticker_symbol": ticker, "newer_than": newer_than, "older_than": older_than, "limit": 200},
                max_age=300,
            )
        )
        calls = puts = 0.0
        for r in rows:
            ask, bid = _num(r.get("total_ask_side_prem")) or 0.0, _num(r.get("total_bid_side_prem")) or 0.0
            if ask <= bid:
                continue  # sold or mixed: not a bet in either direction
            if r.get("type") == "call":
                calls += ask
            elif r.get("type") == "put":
                puts += ask
        return FlowTilt(ticker, calls, puts, len(rows))
