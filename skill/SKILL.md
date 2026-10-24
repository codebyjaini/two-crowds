---
name: two-crowds
description: Compare what Polymarket bettors and the options market each think will happen to a stock, using Unusual Whales data. Use when someone asks whether a Polymarket stock question (close above a level, up or down, beat earnings) is mispriced, what options imply for a price level by a date, or which crowd has forecast better.
---

# Two Crowds

Two crowds bet on the same stock questions: prediction-market traders on Polymarket and options traders. This skill puts their
probabilities side by side and says where they disagree, and how often each has been right before.

## Tools

- **Two Crowds MCP** (`two-crowds`): `two_crowds_today`, `two_crowds_market`, `two_crowds_track_record`, `implied_probability`.
  Add it with `claude mcp add --transport http two-crowds http://127.0.0.1:8040/mcp-server/mcp` while the dashboard runs,
  or `claude mcp add two-crowds -- python -m twocrowds.cli mcp` from the project folder.
- **Unusual Whales MCP** (`https://api.unusualwhales.com/api/mcp`, your own key) for live context: `get_flow_alerts`,
  `get_prediction_unusual_markets`, `get_prediction_smart_money`, `get_prediction_whales`, `get_options_chain`.

## How to answer

1. **A specific Polymarket question** ("Will NVDA close above $210 Friday?"): call `implied_probability(ticker, level, date)` for
   the options view and `two_crowds_market` or `two_crowds_today` for Polymarket's price. Report both as percentages and the gap in points.
2. **"Where do they disagree today?"**: `two_crowds_today`, the five biggest gaps. For each, add the Unusual Whales flags
   (smart money, possible insiders) and which way big bought options bets lean.
3. **"Who's usually right?"**: `two_crowds_track_record`. Give both Brier scores (lower is better; 0.25 is a coin flip), how often
   options were closer when the crowds disagreed by 10+ points, and the sample size in days, not just markets.
4. **Earnings questions** can't be priced by options directly: give Polymarket's odds next to the bought-flow lean and say so.

## Rules

- Every number comes from a tool result. Say "about" when rounding.
- Options probabilities use at-the-money implied volatility; say they are less exact far from the current price.
- This is research. Never tell anyone to place a bet or trade, and never call a gap "free money".
