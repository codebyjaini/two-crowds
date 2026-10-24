import math
from datetime import date

from twocrowds.backtest import Case, calibration, previous_trading_day, score, trade_return
from twocrowds.implied import norm_cdf, options_prob, prob_above, vol_for_horizon
from twocrowds.parse import parse
from twocrowds.polymarket import price_at, to_market
from twocrowds.uw import FlowTilt, IvPoint


def test_parses_the_three_question_shapes():
    q = parse("Will NVIDIA (NVDA) close above $205 on October 23?", "2026-10-23T20:00:00Z")
    assert (q.kind, q.ticker, q.strike, q.event_date) == ("close_above", "NVDA", 205.0, date(2026, 10, 23))
    q = parse("Will Tesla (TSLA) finish below $1,050.50 on December 31?", "2026-12-31T21:00:00Z")
    assert (q.kind, q.strike) == ("close_below", 1050.5)
    q = parse("Micron (MU) Up or Down on October 23?", "2026-10-23T20:00:00Z")
    assert (q.kind, q.ticker) == ("up_down", "MU")
    assert parse("SPY Opens Up or Down on October 23?") is None
    q = parse("Will Meta (META) beat quarterly earnings?", "2026-10-21T20:00:00Z")
    assert (q.kind, q.ticker, q.priceable) == ("earnings_beat", "META", False)
    assert parse("Will SpaceX or OpenAI IPO first?") is None


def test_probability_above_matches_black_scholes():
    assert abs(norm_cdf(0) - 0.5) < 1e-12
    # At the money for one day, slightly under 50% (the -sigma^2/2 drift).
    p = prob_above(100, 100, 0.40, 1 / 252)
    assert 0.49 < p < 0.5
    # Deep in and out of the money.
    assert prob_above(100, 80, 0.40, 1 / 252) > 0.999
    assert prob_above(100, 120, 0.40, 1 / 252) < 0.001
    # Higher strikes are always less likely.
    probs = [prob_above(200, k, 0.5, 1 / 252) for k in (195, 200, 205, 210)]
    assert probs == sorted(probs, reverse=True)


def test_volatility_interpolates_in_variance():
    pts = [IvPoint(1, 0.60, None), IvPoint(7, 0.40, None), IvPoint(30, 0.35, None)]
    assert vol_for_horizon(pts, 0.5) == 0.60  # below the first horizon: use it
    v = vol_for_horizon(pts, 2)  # 2 trading days ~ 2.9 calendar days, between 1 and 7
    assert 0.40 < v < 0.60
    assert vol_for_horizon([], 1) is None


def test_options_view_by_kind():
    iv = [IvPoint(1, 0.5, None), IvPoint(7, 0.5, None)]
    above = options_prob("close_above", 200, 205, iv, 1).prob
    below = options_prob("close_below", 200, 205, iv, 1).prob
    assert abs(above + below - 1) < 1e-12
    assert options_prob("earnings_beat", 200, None, iv, 1) is None


def test_price_at_uses_the_last_trade_before_and_ignores_stale_ones():
    hist = [(100, 0.40), (200, 0.55), (300, 0.70)]
    assert price_at(hist, 250) == 0.55
    assert price_at(hist, 99) is None
    assert price_at(hist, 300 + 7 * 3600) is None


def test_market_resolution_from_final_prices():
    m = to_market({"id": 1, "question": "q", "closed": True, "outcomePrices": '["1", "0"]', "clobTokenIds": '["a", "b"]', "outcomes": '["Yes", "No"]'})
    assert m.resolved_yes is True and m.yes_token == "a"
    m = to_market({"id": 2, "question": "q", "closed": True, "outcomePrices": '["0.5", "0.5"]'})
    assert m.resolved_yes is None


def case(crowd, options, outcome, day="2026-10-23"):
    return Case("id", "q", "NVDA", "close_above", day, 205.0, crowd, options, outcome, 200.0, 0.5, "2026-10-22")


def test_scores_both_crowds_and_the_gap_trade():
    cases = [case(0.30, 0.60, 1), case(0.80, 0.50, 0), case(0.50, 0.52, 1), case(0.90, 0.95, 1, "2026-10-22")]
    s = score(cases, gap=0.10, cost=0.0)
    assert s.cases == 4 and s.days == 2
    assert s.options_brier < s.crowd_brier
    assert (s.disagreements, s.options_closer) == (2, 2)
    # Buy Yes at 0.30 and it happened: +2.33 per dollar. Buy No at 0.20 and it didn't happen: +4 per dollar.
    assert s.trades == 2 and math.isclose(s.pnl_per_dollar, ((1 - 0.3) / 0.3 + (1 - 0.2) / 0.2) / 2)
    assert trade_return(case(0.50, 0.55, 1), gap=0.10) is None


def test_calibration_buckets():
    cal = calibration([case(0.05, 0.1, 0), case(0.07, 0.1, 1), case(0.95, 0.9, 1)], "crowd_prob")
    assert cal[0]["n"] == 2 and cal[0]["happened"] == 0.5
    assert cal[-1]["n"] == 1


def test_previous_trading_day_skips_weekends():
    assert previous_trading_day(date(2026, 10, 26)) == date(2026, 10, 23)  # Monday -> Friday
    assert previous_trading_day(date(2026, 10, 23)) == date(2026, 10, 22)


def test_flow_tilt_lean():
    assert FlowTilt("X", 300, 100, 5).lean == 0.5
    assert FlowTilt("X", 0, 0, 0).lean == 0.0


def test_verdict_uses_the_gap_as_shown():
    from twocrowds.live import verdict

    assert verdict(-0.0999) == "options more bearish"  # shown as -10 pts
    assert verdict(0.094) == "crowds agree"
    assert verdict(None) == "no options view"


def test_day_bootstrap_brackets_the_mean():
    from twocrowds.backtest import day_bootstrap

    cases = [case(0.30, 0.60, i % 2, f"2026-10-{10 + i:02d}") for i in range(10)]
    lo, hi = day_bootstrap(cases, cost=0.0)
    assert lo <= hi
    assert day_bootstrap(cases[:3]) is None
