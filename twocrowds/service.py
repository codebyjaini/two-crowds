"""One place that builds the clients and answers the questions the web page, CLI and MCP tools ask.

Demo mode (no UW_API_KEY, or TWO_CROWDS_DEMO=1) reads data/demo.json, a saved
real run, and makes no network calls.
"""

from __future__ import annotations

import json
import threading
import time
from functools import lru_cache
from typing import Any

from . import backtest as bt
from .config import ROOT, settings
from .live import board as live_board
from .polymarket import Polymarket
from .store import Store
from .uw import UnusualWhales

DEMO_FILE = ROOT / "data" / "demo.json"


@lru_cache(maxsize=1)
def store() -> Store:
    return Store(settings().db_path)


@lru_cache(maxsize=1)
def clients() -> tuple[Polymarket, UnusualWhales]:
    cfg = settings()
    if not cfg.uw_api_key:
        raise RuntimeError("Set UW_API_KEY in .env to fetch live data (or run in demo mode).")
    return Polymarket(store()), UnusualWhales(cfg.uw_api_key, store(), cfg.uw_rpm)


def demo() -> dict[str, Any]:
    if not DEMO_FILE.exists():
        return {"board": {"as_of": None, "priced": [], "other": [], "unusual_count": 0}, "backtest": []}
    return json.loads(DEMO_FILE.read_text())


def mode() -> str:
    return "live" if settings().live else "demo"


# ---- answers ---------------------------------------------------------------


def backtest_rows() -> list[dict[str, Any]]:
    """Stored results; a fresh deploy with no backtest yet uses the saved real run."""
    rows = store().backtest_rows() if mode() == "live" else []
    return rows or demo()["backtest"]


def track_record(gap: float = 0.10) -> dict[str, Any]:
    rows = backtest_rows()
    cases = bt.from_rows(rows)
    s = bt.score(cases, gap=gap)
    by_kind = {k: bt.score_dict(bt.score([c for c in cases if c.kind == k], gap=gap)) for k in sorted({c.kind for c in cases})}
    daily: dict[str, list[float]] = {}
    for c in cases:
        r = bt.trade_return(c, gap)
        if r is not None:
            daily.setdefault(c.event_date, []).append(r)
    equity, total = [], 0.0
    for d in sorted(daily):
        total += sum(daily[d])
        equity.append({"date": d, "trades": len(daily[d]), "day": round(sum(daily[d]), 4), "cumulative": round(total, 4)})
    return {
        "mode": mode(),
        "gap": gap,
        "equity": equity,
        "score": {**bt.score_dict(s), "pnl_ci95": bt.day_bootstrap(cases, gap=gap)},
        "by_kind": by_kind,
        "calibration": {"crowd": bt.calibration(cases, "crowd_prob"), "options": bt.calibration(cases, "options_prob")},
        "biggest_disagreements": [
            {**r, "gap": round(r["options_prob"] - r["crowd_prob"], 4)}
            for r in sorted(rows, key=lambda r: -abs(r["options_prob"] - r["crowd_prob"]))[:25]
        ],
    }


_board: dict[str, Any] = {"value": None, "at": 0.0}
_board_lock = threading.Lock()
BOARD_TTL = 15 * 60


def refresh_board() -> dict[str, Any]:
    pm, uw = clients()
    value = {**live_board(pm, uw), "mode": "live"}
    with _board_lock:
        _board["value"], _board["at"] = value, time.time()
    return value


def today() -> dict[str, Any]:
    if mode() == "demo":
        return {**demo()["board"], "mode": "demo"}
    with _board_lock:
        cached, at = _board["value"], _board["at"]
    if cached and time.time() - at < BOARD_TTL:
        return cached
    if cached:
        return cached  # stale but instant; the background refresher replaces it
    return refresh_board()


def start_refresher(every: float = 600) -> None:
    """Keep the live board fresh in a background thread so page loads never wait on the APIs."""
    if mode() != "live":
        return

    def loop() -> None:
        while True:
            try:
                refresh_board()
            except Exception as err:  # keep serving the last good board
                print(f"board refresh failed: {err}", flush=True)
            time.sleep(every)

    threading.Thread(target=loop, daemon=True, name="board-refresher").start()


def market(market_id: str) -> dict[str, Any] | None:
    board = today()
    for card in board["priced"] + board["other"]:
        if card["market_id"] == market_id:
            return card
    for r in backtest_rows():
        if r["market_id"] == market_id:
            return {**r, "gap": round(r["options_prob"] - r["crowd_prob"], 4), "resolved": True}
    return None


def run_backtest(pages: int = 10, log=print) -> dict[str, Any]:
    pm, uw = clients()
    markets = pm.markets_by_tag("stocks", closed=True, pages=pages)
    log(f"{len(markets)} closed stock markets from Polymarket")
    cases = bt.collect(pm, uw, markets, log=log)
    store().put_backtest(bt.to_rows(cases))
    log(f"{len(cases)} scored")
    return bt.score_dict(bt.score(cases))


def export_demo() -> int:
    """Save the current live board and the stored backtest as the demo dataset."""
    payload = {"board": refresh_board() if mode() == "live" else today(), "backtest": backtest_rows()}
    DEMO_FILE.write_text(json.dumps(payload, indent=1, default=str))
    return len(payload["backtest"])


def implied_probability(ticker: str, level: float, event_date: str, direction: str = "above") -> dict[str, Any]:
    """The options market's probability that `ticker` closes above (or below) `level` on `event_date`."""
    from datetime import date, datetime

    from .implied import options_prob
    from .live import NY, trading_days_until

    _, uw = clients()
    closes = uw.daily_closes(ticker.upper(), limit=3)
    iv = uw.interpolated_iv(ticker.upper())
    if not closes or not iv:
        return {"error": f"No price or implied volatility for {ticker.upper()}"}
    spot = closes[max(closes)]
    td = trading_days_until(date.fromisoformat(event_date), datetime.now(NY))
    if td <= 0:
        return {"error": f"{event_date} has already closed"}
    view = options_prob("close_above" if direction == "above" else "close_below", spot, level, iv, td)
    if not view:
        return {"error": "Not enough implied volatility data"}
    return {
        "ticker": ticker.upper(),
        "level": level,
        "direction": direction,
        "event_date": event_date,
        "probability": round(view.prob, 4),
        "spot": spot,
        "implied_volatility": round(view.sigma, 4),
        "trading_days": round(td, 3),
        "method": "N(d2) under the lognormal model options are priced with, using Unusual Whales interpolated implied volatility",
    }
