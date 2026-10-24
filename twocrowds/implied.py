"""What the options market says the probability is.

Under the same lognormal model options are priced with, the chance a stock
closes above a level K after T years at volatility sigma is N(d2), with
d2 = (ln(S/K) - sigma^2 T / 2) / (sigma sqrt(T)) (rates are negligible over a day
or a week). Sigma comes from Unusual Whales' interpolated implied volatility
for the matching horizon, so this is the options crowd's own forecast.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .uw import IvPoint

TRADING_DAYS = 252


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def prob_above(spot: float, strike: float, sigma: float, years: float) -> float:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if sigma <= 0 or years <= 0:
        return 1.0 if spot > strike else 0.0
    sd = sigma * math.sqrt(years)
    d2 = (math.log(spot / strike) - 0.5 * sd * sd) / sd
    return norm_cdf(d2)


def vol_for_horizon(points: list[IvPoint], trading_days: float) -> float | None:
    """Interpolate implied volatility (in variance terms) to the horizon, in trading days."""
    if not points:
        return None
    pts = sorted(points, key=lambda p: p.days)
    # UW quotes horizons in calendar days; a trading day is about 1.45 calendar days.
    target = trading_days * 365 / TRADING_DAYS
    if target <= pts[0].days:
        return pts[0].volatility
    if target >= pts[-1].days:
        return pts[-1].volatility
    for lo, hi in zip(pts, pts[1:]):
        if lo.days <= target <= hi.days:
            w = (target - lo.days) / (hi.days - lo.days)
            var = (1 - w) * lo.volatility**2 * lo.days + w * hi.volatility**2 * hi.days
            return math.sqrt(var / target)
    return pts[-1].volatility


@dataclass
class OptionsView:
    prob: float
    spot: float
    sigma: float
    trading_days: float


def options_prob(kind: str, spot: float, strike: float | None, iv: list[IvPoint], trading_days: float) -> OptionsView | None:
    sigma = vol_for_horizon(iv, trading_days)
    if sigma is None:
        return None
    years = trading_days / TRADING_DAYS
    if kind == "close_above" and strike:
        p = prob_above(spot, strike, sigma, years)
    elif kind == "close_below" and strike:
        p = 1.0 - prob_above(spot, strike, sigma, years)
    elif kind == "up_down":
        # "Up" means closing above the prior close; pass it as `strike` (defaults to the current price).
        p = prob_above(spot, strike or spot, sigma, years)
    else:
        return None
    return OptionsView(p, spot, sigma, trading_days)


def brier(prob: float, outcome: bool) -> float:
    return (prob - (1.0 if outcome else 0.0)) ** 2
