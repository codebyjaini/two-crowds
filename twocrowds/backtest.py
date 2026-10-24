"""Which crowd forecast better? Score both on markets that have already resolved.

For every resolved Polymarket stock-price market we take two forecasts at the
same moment, the previous trading day's close (4pm New York):

- the prediction-market crowd: the market's last traded "Yes" price, and
- the options crowd: N(d2) from that day's close and Unusual Whales' implied
  volatility for a one-day horizon.

Both are scored against what happened with the Brier score (lower is better).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .implied import brier, options_prob
from .parse import parse
from .polymarket import Market, Polymarket, price_at
from .uw import UnusualWhales

NY = ZoneInfo("America/New_York")
# Markets that resolve within a few days; ladders on longer horizons are rare and noisier.
KINDS = {"close_above", "close_below", "up_down"}


def previous_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def close_ts(d: date) -> int:
    return int(datetime.combine(d, time(16, 0), NY).timestamp())


@dataclass
class Case:
    market_id: str
    question: str
    ticker: str
    kind: str
    event_date: str
    strike: float | None
    crowd_prob: float
    options_prob: float
    outcome: int
    spot: float
    sigma: float
    as_of: str

    @property
    def gap(self) -> float:
        return self.options_prob - self.crowd_prob


def collect(pm: Polymarket, uw: UnusualWhales, markets: Iterable[Market], log=print) -> list[Case]:
    cases: list[Case] = []
    iv_cache: dict[tuple[str, str], Any] = {}
    close_cache: dict[tuple[str, str], dict[str, float]] = {}
    for m in markets:
        q = parse(m.question, m.end_date)
        if not q or q.kind not in KINDS or not q.event_date or m.resolved_yes is None or not m.yes_token:
            continue
        as_of = previous_trading_day(q.event_date)
        crowd = price_at(pm.price_history(m.yes_token, close_ts(as_of) - 2 * 86400, close_ts(as_of) + 60), close_ts(as_of))
        if crowd is None:
            continue  # the market didn't trade by the previous close
        key = (q.ticker, as_of.isoformat())
        try:
            if key not in close_cache:
                close_cache[key] = uw.daily_closes(q.ticker, end_date=as_of.isoformat(), limit=5)
            if key not in iv_cache:
                iv_cache[key] = uw.interpolated_iv(q.ticker, as_of.isoformat())
        except Exception as err:  # one ticker failing shouldn't stop the run
            log(f"  skip {q.ticker} {as_of}: {err}")
            close_cache.setdefault(key, {})
            iv_cache.setdefault(key, [])
            continue
        spot = close_cache[key].get(as_of.isoformat())
        if not spot or not iv_cache[key]:
            continue
        view = options_prob(q.kind, spot, q.strike, iv_cache[key], trading_days=1)
        if not view:
            continue
        cases.append(
            Case(
                market_id=m.id,
                question=m.question,
                ticker=q.ticker,
                kind=q.kind,
                event_date=q.event_date.isoformat(),
                strike=q.strike,
                crowd_prob=round(crowd, 4),
                options_prob=round(view.prob, 4),
                outcome=1 if m.resolved_yes else 0,
                spot=spot,
                sigma=round(view.sigma, 4),
                as_of=as_of.isoformat(),
            )
        )
    return cases


# ---- scoring ---------------------------------------------------------------


@dataclass
class Score:
    cases: int
    days: int
    crowd_brier: float | None
    options_brier: float | None
    # Of the cases where the two crowds disagreed by at least `gap`, how often the options side was closer.
    disagreements: int
    options_closer: int
    # Trading the gap: buy Yes on Polymarket when options say it's underpriced, No when overpriced.
    trades: int
    pnl_per_dollar: float | None
    hit_rate: float | None
    pnl_ci95: tuple[float, float] | None


def score(cases: list[Case], gap: float = 0.10, cost: float = 0.01) -> Score:
    if not cases:
        return Score(0, 0, None, None, 0, 0, 0, None, None, None)
    cb = sum(brier(c.crowd_prob, bool(c.outcome)) for c in cases) / len(cases)
    ob = sum(brier(c.options_prob, bool(c.outcome)) for c in cases) / len(cases)
    dis = [c for c in cases if abs(c.gap) >= gap]
    closer = sum(1 for c in dis if abs(c.options_prob - c.outcome) < abs(c.crowd_prob - c.outcome))
    returns = [trade_return(c, gap, cost) for c in cases]
    trades = [r for r in returns if r is not None]
    pnl = sum(trades) / len(trades) if trades else None
    ci = None
    if len(trades) >= 10:
        mean = pnl or 0.0
        sd = math.sqrt(sum((r - mean) ** 2 for r in trades) / (len(trades) - 1))
        half = 1.96 * sd / math.sqrt(len(trades))
        ci = (mean - half, mean + half)
    return Score(
        cases=len(cases),
        days=len({c.event_date for c in cases}),
        crowd_brier=cb,
        options_brier=ob,
        disagreements=len(dis),
        options_closer=closer,
        trades=len(trades),
        pnl_per_dollar=pnl,
        hit_rate=sum(1 for r in trades if r > 0) / len(trades) if trades else None,
        pnl_ci95=ci,
    )


def trade_return(c: Case, gap: float = 0.10, cost: float = 0.01) -> float | None:
    """Return per dollar staked from taking the options crowd's side at the Polymarket price, after `cost`."""
    if c.options_prob - c.crowd_prob >= gap:
        price = min(0.99, c.crowd_prob + cost)
        return (c.outcome - price) / price
    if c.crowd_prob - c.options_prob >= gap:
        price = min(0.99, (1 - c.crowd_prob) + cost)
        return ((1 - c.outcome) - price) / price
    return None


def calibration(cases: list[Case], which: str, buckets: int = 10) -> list[dict[str, float]]:
    """Forecast bucket vs how often it happened, for a reliability chart."""
    out = []
    for i in range(buckets):
        lo, hi = i / buckets, (i + 1) / buckets
        inside = [c for c in cases if lo <= getattr(c, which) < hi or (i == buckets - 1 and getattr(c, which) == 1.0)]
        if inside:
            out.append(
                {
                    "lo": lo,
                    "hi": hi,
                    "n": len(inside),
                    "forecast": sum(getattr(c, which) for c in inside) / len(inside),
                    "happened": sum(c.outcome for c in inside) / len(inside),
                }
            )
    return out


def to_rows(cases: list[Case]) -> list[dict[str, Any]]:
    return [
        {
            "market_id": c.market_id,
            "question": c.question,
            "ticker": c.ticker,
            "kind": c.kind,
            "event_date": c.event_date,
            "strike": c.strike,
            "crowd_prob": c.crowd_prob,
            "options_prob": c.options_prob,
            "outcome": c.outcome,
            "payload": {"spot": c.spot, "sigma": c.sigma, "as_of": c.as_of},
        }
        for c in cases
    ]


def from_rows(rows: list[dict[str, Any]]) -> list[Case]:
    return [
        Case(
            market_id=r["market_id"],
            question=r["question"],
            ticker=r["ticker"],
            kind=r["kind"],
            event_date=r["event_date"],
            strike=r["strike"],
            crowd_prob=r["crowd_prob"],
            options_prob=r["options_prob"],
            outcome=r["outcome"],
            spot=r["payload"].get("spot", 0.0),
            sigma=r["payload"].get("sigma", 0.0),
            as_of=r["payload"].get("as_of", ""),
        )
        for r in rows
    ]


def score_dict(s: Score) -> dict[str, Any]:
    return asdict(s)


def day_bootstrap(cases: list[Case], gap: float = 0.10, cost: float = 0.01, n: int = 2000, seed: int = 7) -> tuple[float, float] | None:
    """95% range of the mean gap-trade return, resampling whole days (strikes on one day move together)."""
    import random

    by_day: dict[str, list[float]] = {}
    for c in cases:
        r = trade_return(c, gap, cost)
        if r is not None:
            by_day.setdefault(c.event_date, []).append(r)
    days = sorted(by_day)
    if len(days) < 5:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        picked = [r for _ in days for r in by_day[rng.choice(days)]]
        means.append(sum(picked) / len(picked))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]
