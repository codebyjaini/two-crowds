"""MCP server: ask Claude (or any MCP client) where the prediction-market crowd and the options crowd disagree."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import service

mcp = MCPServer(
    "two-crowds",
    instructions=(
        "Two Crowds compares Polymarket's odds on stock questions with the probability the options market implies "
        "(from Unusual Whales implied volatility), and keeps a scored record of which crowd forecast better. "
        "Probabilities are 0-1. A positive gap means options are more bullish than the prediction market. "
        "It is research, not trading advice."
    ),
)


@mcp.tool()
def two_crowds_today(limit: int = 15) -> dict[str, Any]:
    """Open Polymarket stock markets (closing levels, up/down, earnings) priced by both crowds, biggest disagreements first.
    Each card has crowd_prob (Polymarket), options_prob (implied by options), gap, verdict, Unusual Whales bought-flow lean
    and any Unusual Predictions flags (smart money, possible insiders)."""
    board = service.today()
    return {**board, "priced": board["priced"][:limit], "other": board["other"][:limit]}


@mcp.tool()
def two_crowds_market(market_id: str) -> dict[str, Any]:
    """One market by its Polymarket id: both crowds' probabilities and, if resolved, the outcome."""
    return service.market(market_id) or {"error": f"No market {market_id}"}


@mcp.tool()
def two_crowds_track_record(gap: float = 0.10) -> dict[str, Any]:
    """Which crowd forecast better on resolved markets: Brier scores (lower is better), how often options were closer when
    the two disagreed by at least `gap`, and the return of buying the options crowd's side on Polymarket after a 1-cent cost."""
    return service.track_record(gap)


@mcp.tool()
def implied_probability(ticker: str, level: float, event_date: str, direction: str = "above") -> dict[str, Any]:
    """The options market's probability that a stock closes above (or below) `level` on `event_date` (YYYY-MM-DD)."""
    return service.implied_probability(ticker, level, event_date, direction)


@mcp.prompt()
def where_do_the_crowds_disagree() -> str:
    """Today's biggest disagreements between Polymarket and the options market, and whether to trust either."""
    return (
        "Use two_crowds_today to list the five biggest disagreements between Polymarket and the options market, "
        "with each question, both probabilities and the gap. Then use two_crowds_track_record and say in two plain "
        "sentences which crowd has forecast better when they disagreed, with the sample size. Research, not advice."
    )


if __name__ == "__main__":
    mcp.run()
