"""Dashboard, JSON API and remote MCP endpoint."""

from __future__ import annotations

import contextlib
import html
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from mcp.server.transport_security import TransportSecuritySettings

from . import service
from .mcp_server import mcp

def _transport_security() -> TransportSecuritySettings:
    """Keep DNS-rebinding protection on, but allow the public host(s) this runs behind (PUBLIC_HOSTS=a.com,b.com)."""
    public = [h.strip() for h in os.environ.get("PUBLIC_HOSTS", "").split(",") if h.strip()]
    hosts = ["127.0.0.1:*", "localhost:*", "127.0.0.1", "localhost", *public, *[f"{h}:*" for h in public]]
    origins = ["http://127.0.0.1:*", "http://localhost:*", *[f"https://{h}" for h in public]]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins)


mcp_app = mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=_transport_security())


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    service.start_refresher()
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Two Crowds", lifespan=lifespan)
app.mount("/mcp-server", mcp_app)

CSS = """
:root{--bg:#0a0c11;--panel:#11141c;--panel2:#161a24;--line:#232838;--ink:#eef0f6;--ink2:#a9b0c2;--ink3:#727a90;
--pm:#8b6dff;--pmdim:rgba(139,109,255,.16);--op:#ffb020;--opdim:rgba(255,176,32,.15);--up:#3ddc97;--down:#ff5c7a}
*{box-sizing:border-box}html{background:var(--bg)}body{margin:0;background:radial-gradient(1200px 500px at 15% -10%,rgba(139,109,255,.10),transparent 60%),radial-gradient(900px 500px at 95% 0%,rgba(255,176,32,.07),transparent 60%),var(--bg);
color:var(--ink);font:15.5px/1.55 "Space Grotesk",system-ui,sans-serif;min-height:100vh}
a{color:inherit}main{max-width:1180px;margin:0 auto;padding:22px 20px 80px}
.mono,.n,.num,.big{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-feature-settings:"tnum"}
header.top{display:flex;align-items:center;gap:20px;flex-wrap:wrap;padding-bottom:18px;margin-bottom:30px;border-bottom:1px solid var(--line)}
.brand{font-weight:700;font-size:19px;text-decoration:none;display:flex;align-items:center;gap:10px;letter-spacing:.2px}
.logo{display:inline-grid;grid-template-columns:1fr 1fr;width:26px;height:26px;border-radius:7px;overflow:hidden}.logo i:first-child{background:var(--pm)}.logo i:last-child{background:var(--op)}
nav{display:flex;gap:4px}nav a{padding:6px 12px;border-radius:8px;color:var(--ink2);text-decoration:none;font-weight:500}nav a:hover{background:var(--panel2);color:var(--ink)}
.live{margin-left:auto;display:inline-flex;align-items:center;gap:8px;font-size:12.5px;color:var(--ink2);border:1px solid var(--line);padding:5px 11px;border-radius:999px}
.live i{width:8px;height:8px;border-radius:50%;background:var(--up);box-shadow:0 0 0 4px rgba(61,220,151,.15)}.live.demo i{background:var(--ink3);box-shadow:none}
.kicker{font-family:"JetBrains Mono",monospace;font-size:12.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3)}
h1{font-size:50px;line-height:1.02;letter-spacing:-1.6px;margin:10px 0 16px;max-width:900px;font-weight:700}
h1 .pmc{color:var(--pm)}h1 .opc{color:var(--op)}
h2{font-size:24px;letter-spacing:-.4px;margin:48px 0 4px;font-weight:700}
.lede{font-size:18px;color:var(--ink2);max-width:780px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px}
.score{display:grid;grid-template-columns:1fr auto 1fr;gap:0;margin-top:26px;overflow:hidden}
.score .side{padding:22px 24px}.score .side.pm{background:linear-gradient(90deg,var(--pmdim),transparent)}.score .side.op{text-align:right;background:linear-gradient(270deg,var(--opdim),transparent)}
.score .who{font-size:13px;color:var(--ink2);font-weight:600;letter-spacing:.4px;text-transform:uppercase}.score .big{font-size:44px;font-weight:700;line-height:1.1;margin-top:6px}
.score .pm .big{color:var(--pm)}.score .op .big{color:var(--op)}.score .sub{color:var(--ink3);font-size:13.5px;margin-top:2px}
.score .vs{display:grid;place-items:center;padding:0 18px;border-left:1px solid var(--line);border-right:1px solid var(--line);font-family:"JetBrains Mono",monospace;color:var(--ink3);font-size:13px;text-align:center}
.score .vs b{display:block;font-size:22px;color:var(--ink);font-family:"Space Grotesk",sans-serif}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px}
.stat{padding:18px 20px}.stat .k{color:var(--ink3);font-size:13px;font-weight:600}.stat .n{font-size:30px;font-weight:700;margin-top:6px;letter-spacing:-.5px}
.stat .s{color:var(--ink2);font-size:13.5px;margin-top:2px}.pos{color:var(--up)}.neg{color:var(--down)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px;margin-top:16px}
.duel{padding:16px 18px;display:flex;flex-direction:column;gap:12px}
.duel .q{font-weight:600;line-height:1.3;margin:0;font-size:15.5px}.meta{color:var(--ink3);font-size:12.5px;font-family:"JetBrains Mono",monospace;margin-top:4px}
.vsrow{display:grid;grid-template-columns:1fr auto 1fr;align-items:end;gap:10px}
.vsrow .l .num{color:var(--pm)}.vsrow .r{text-align:right}.vsrow .r .num{color:var(--op)}
.vsrow .num{font-size:30px;font-weight:700;line-height:1}.vsrow small{display:block;color:var(--ink3);font-size:11.5px;letter-spacing:.6px;text-transform:uppercase;margin-bottom:4px}
.gap{font-family:"JetBrains Mono",monospace;font-size:12.5px;padding:4px 9px;border-radius:7px;background:var(--panel2);color:var(--ink2);white-space:nowrap}
.gap.bull{background:var(--opdim);color:var(--op)}.gap.bear{background:var(--pmdim);color:#b9a6ff}
.track{position:relative;height:8px;border-radius:99px;background:var(--panel2)}
.track .m{position:absolute;top:-4px;width:3px;height:16px;border-radius:2px}.track .m.p{background:var(--pm)}.track .m.o{background:var(--op)}
.track .span{position:absolute;top:0;height:8px;border-radius:99px;background:linear-gradient(90deg,rgba(139,109,255,.45),rgba(255,176,32,.45))}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:12px;color:var(--ink2);border:1px solid var(--line);padding:3px 9px;border-radius:999px}
.chip.flag{border-color:rgba(255,176,32,.5);color:var(--op)}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:12px}
td,th{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--ink3);font-weight:600;font-size:12px;letter-spacing:.5px;text-transform:uppercase}
.tablewrap{overflow-x:auto}.tn{text-align:right;font-family:"JetBrains Mono",monospace}.won{color:var(--up);font-weight:600}.lost{color:var(--down);font-weight:600}
.note{color:var(--ink3);font-size:13.5px;max-width:780px}.empty{padding:26px;color:var(--ink2)}
code{font-family:"JetBrains Mono",monospace;font-size:13px;background:var(--panel2);border:1px solid var(--line);padding:1px 6px;border-radius:6px;color:var(--ink)}
pre{background:#05060a;border:1px solid var(--line);color:#dfe3ee;padding:14px 16px;border-radius:10px;overflow-x:auto;font-size:13px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin-top:14px}.steps .panel{padding:18px 20px}.steps b{font-family:"JetBrains Mono",monospace;color:var(--op);font-size:13px}
.legend{display:flex;gap:18px;color:var(--ink2);font-size:13.5px;margin-top:10px}.legend b{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
svg text{font-family:"JetBrains Mono",monospace}
@media(max-width:640px){h1{font-size:36px}.score{grid-template-columns:1fr}.score .vs{border:0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:10px}.score .side.op{text-align:left}}
"""


def pct(x: float | None, digits: int = 0) -> str:
    return "—" if x is None else f"{x * 100:.{digits}f}%"


def esc(s: Any) -> str:
    return html.escape(str(s))


def page(title: str, body: str, mode: str) -> HTMLResponse:
    badge = (
        '<span class="live"><i></i>Live · Unusual Whales + Polymarket</span>'
        if mode == "live"
        else '<span class="live demo"><i></i>Warming up · showing the saved run</span>'
        if mode == "warming"
        else '<span class="live demo"><i></i>Demo · saved real run</span>'
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Two Crowds</title><meta name="description" content="Polymarket odds against the probability the options market implies, scored on every resolved market.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>
<header class="top"><a class="brand" href="/"><span class="logo"><i></i><i></i></span>Two Crowds</a>
<nav><a href="/">Today</a><a href="/record">Track record</a><a href="/ask">Ask</a><a href="/how">How it works</a></nav>{badge}</header>
{body}
<p class="note" style="margin-top:60px">Research, not trading advice. Prediction-market odds from Polymarket. Implied volatility, prices, options flow and
Unusual Predictions data from Unusual Whales. <a href="https://youtu.be/bvo6ilc_MNg">Demo video</a> ·
<a href="https://github.com/codebyjaini/two-crowds">Source</a></p>
</main></body></html>"""
    )


def track(crowd: float | None, options: float | None) -> str:
    if crowd is None or options is None:
        return ""
    lo, hi = sorted((crowd, options))
    return (
        f'<div class="track" aria-hidden="true"><span class="span" style="left:{lo * 100:.1f}%;width:{max(0.5, (hi - lo) * 100):.1f}%"></span>'
        f'<span class="m p" style="left:calc({crowd * 100:.1f}% - 1px)"></span><span class="m o" style="left:calc({options * 100:.1f}% - 1px)"></span></div>'
    )


def gap_chip(card: dict[str, Any]) -> str:
    v = card.get("verdict", "")
    gap = card.get("gap")
    cls = "bull" if "bullish" in v else "bear" if "bearish" in v else ""
    label = "no options view" if gap is None else f"{gap * 100:+.0f} pts"
    return f'<span class="gap {cls}" title="{esc(v)}">{label}</span>'


def card_html(c: dict[str, Any]) -> str:
    meta = [c["ticker"], c["event_date"]]
    if c.get("strike"):
        meta.append(f"K ${c['strike']:,.2f}")
    if c.get("spot"):
        meta.append(f"last ${c['spot']:,.2f}")
    chips = []
    v = c.get("verdict", "")
    if v and v != "no options view":
        chips.append(f'<span class="chip">{esc(v)}</span>')
    if c.get("flow_lean") is not None and (c.get("flow_bought_calls") or c.get("flow_bought_puts")):
        lean = c["flow_lean"]
        chips.append(f'<span class="chip">big bets bought: {abs(lean) * 100:.0f}% more {"calls" if lean > 0 else "puts"}</span>')
    if c.get("unusual"):
        tags = ", ".join(t.replace("_", " ") for t in c["unusual"].get("tags") or []) or "unusual activity"
        chips.append(f'<span class="chip flag">UW Unusual Predictions: {esc(tags)}</span>')
    return f"""<article class="panel duel"><div><p class="q">{esc(c['question'])}</p><div class="meta">{' · '.join(esc(m) for m in meta)}</div></div>
<div class="vsrow"><div class="l"><small>Polymarket</small><span class="num">{pct(c.get('crowd_prob'))}</span></div>{gap_chip(c)}
<div class="r"><small>Options</small><span class="num">{pct(c.get('options_prob'))}</span></div></div>
{track(c.get('crowd_prob'), c.get('options_prob'))}<div class="chips">{''.join(chips)}</div></article>"""


def scoreboard(s: dict[str, Any]) -> str:
    if not s.get("cases"):
        return ""
    share = s["options_closer"] / s["disagreements"] if s["disagreements"] else None
    return f"""<section class="panel score">
<div class="side pm"><div class="who">Polymarket crowd</div><div class="big">{s['crowd_brier']:.3f}</div><div class="sub">Brier score · lower is better</div></div>
<div class="vs"><div>VS<b>{pct(share)}</b>options closer<br>when 10+ pts apart</div></div>
<div class="side op"><div class="who">Options crowd</div><div class="big">{s['options_brier']:.3f}</div><div class="sub">Brier score · from UW implied volatility</div></div>
</section>"""


def money_stats(s: dict[str, Any], rec: dict[str, Any]) -> str:
    if not s.get("cases"):
        return ""
    pnl = s.get("pnl_per_dollar")
    ci = s.get("pnl_ci95")
    eq = rec.get("equity") or []
    return f"""<div class="stats">
<div class="panel stat"><div class="k">Resolved markets scored</div><div class="n">{s['cases']:,}</div><div class="s">{s['days']} trading days · forecasts at the prior close</div></div>
<div class="panel stat"><div class="k">Take the options side on Polymarket</div><div class="n {'pos' if (pnl or 0) > 0 else 'neg'}">{'—' if pnl is None else f"{pnl * 100:+.1f}%"}</div><div class="s">per $1 · {s['trades']} trades · 1¢ cost{'' if not ci else f" · 95% {ci[0] * 100:+.0f}% to {ci[1] * 100:+.0f}%"}</div></div>
<div class="panel stat"><div class="k">Hit rate</div><div class="n">{pct(s.get('hit_rate'))}</div><div class="s">of trades won when the crowds split by 10+ pts</div></div>
<div class="panel stat"><div class="k">$1 a trade since {esc(eq[0]['date'] if eq else '—')}</div><div class="n {'pos' if eq and eq[-1]['cumulative'] > 0 else 'neg'}">{'—' if not eq else f"${eq[-1]['cumulative']:+.0f}"}</div><div class="s">cumulative, before fees and size limits</div></div>
</div>"""


def _score(v: Any) -> str:
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return "—"


def uw_section(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    def money(v: Any) -> str:
        try:
            x = float(v or 0)
        except (TypeError, ValueError):
            return "—"
        if x <= 0:
            return "—"
        return f"${x / 1e6:.1f}M" if x >= 1e6 else f"${x / 1e3:.0f}K"

    body = "".join(
        f"<tr><td>{esc(r.get('market') or '')}<div class='meta'>{esc(r.get('category') or '')} · {esc(r.get('outcome') or '')}</div></td>"
        f"<td class='tn'>{pct(float(r['price'])) if r.get('price') not in (None, '') else '—'}</td>"
        f"<td class='tn'>{_score(r.get('unusual_score'))}</td><td class='tn'>{money(r.get('smart_volume'))}</td>"
        f"<td class='tn'>{r.get('insiders') or 0}{'' if not r.get('insider_usd') else ' · ' + money(r.get('insider_usd'))}</td>"
        f"<td>{esc(', '.join(t.replace('_', ' ') for t in r.get('tags') or []))}</td></tr>"
        for r in rows
    )
    return f"""<h2>What Unusual Whales sees on Polymarket</h2><p class="note">Unusual Predictions: markets with unusual activity right now, the money from
traders with a profitable record, and wallets that look like they know something. From <code>/api/predictions/unusual</code>.</p>
<div class="panel tablewrap" style="margin-top:14px;padding:4px 8px"><table><thead><tr><th style="min-width:300px">Market</th><th class="tn">Price</th><th class="tn">Unusual</th><th class="tn">Smart money</th><th class="tn">Possible insiders</th><th>Signals</th></tr></thead><tbody>{body}</tbody></table></div>"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    t = service.today()
    rec = service.track_record()
    s = rec["score"]
    priced = t.get("priced", [])
    split = [c for c in priced if abs(c.get("gap") or 0) >= 0.095][:12]
    rest = [c for c in priced if c not in split][:12]
    earnings = [c for c in t.get("other", []) if c["kind"] == "earnings_beat"][:9]
    grid = lambda cards: '<div class="grid">' + "".join(card_html(c) for c in cards) + "</div>"
    disagree = grid(split) if split else '<div class="panel empty">No 10-point disagreements on the open markets right now.</div>'
    return page(
        "Today",
        f"""<div class="kicker">Polymarket vs the options market</div>
<h1>Two crowds bet on the same stock question. <span class="pmc">One</span> is usually <span class="opc">closer</span>.</h1>
<p class="lede">Polymarket asks things like <em>"Will NVDA close above $210 on Friday?"</em>. The options market prices the same question with real money
but never says it out loud. Two Crowds works out the options market's probability from Unusual Whales implied volatility, shows where the two
crowds split, and scores both on every market that has resolved.</p>
{scoreboard(s)}{money_stats(s, rec)}
<h2>Where they split now</h2><p class="note">Open Polymarket stock questions where the two crowds are 10+ points apart, as of {esc(t.get('as_of') or '—')}.
The bar shows both probabilities; violet is Polymarket, amber is options.</p>
{disagree}
{'<h2>Where they roughly agree</h2>' + grid(rest) if rest else ''}
{uw_section(t.get('uw_unusual') or [])}
{'<h2>Earnings questions</h2><p class="note">Options can&#39;t price an earnings beat directly, so these show Polymarket&#39;s odds with the way big bought options bets lean.</p>' + grid(earnings) if earnings else ''}""",
        t.get("mode", "demo"),
    )


def equity_svg(eq: list[dict[str, Any]]) -> str:
    if len(eq) < 2:
        return ""
    w, h, pad = 760, 240, 40
    vals = [0.0] + [e["cumulative"] for e in eq]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    xs = [pad + i * (w - pad - 12) / (len(vals) - 1) for i in range(len(vals))]
    ys = [h - pad - (v - lo) / span * (h - pad - 16) for v in vals]
    zero = h - pad - (0 - lo) / span * (h - pad - 16)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{zero:.1f} " + pts + f" {xs[-1]:.1f},{zero:.1f}"
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#ffb020"><title>{esc(e["date"])}: {e["trades"]} trades, {e["day"]:+.2f} that day, {e["cumulative"]:+.2f} total</title></circle>'
        for x, y, e in zip(xs[1:], ys[1:], eq)
    )
    return f"""<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Cumulative profit from taking the options side, $1 a trade">
<defs><linearGradient id="eqg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ffb020" stop-opacity=".35"/><stop offset="1" stop-color="#ffb020" stop-opacity="0"/></linearGradient></defs>
<line x1="{pad}" y1="{zero:.1f}" x2="{w - 12}" y2="{zero:.1f}" stroke="#2a3042" stroke-dasharray="4 4"/>
<polygon points="{area}" fill="url(#eqg)"/><polyline points="{pts}" fill="none" stroke="#ffb020" stroke-width="2.5"/>{dots}
<text x="{pad - 6}" y="{ys[-1] + 4:.1f}" fill="#a9b0c2" font-size="11" text-anchor="end">${vals[-1]:+.0f}</text>
<text x="{pad - 6}" y="{zero + 4:.1f}" fill="#727a90" font-size="11" text-anchor="end">$0</text>
<text x="{pad}" y="{h - 12}" fill="#727a90" font-size="11">{esc(eq[0]['date'])}</text><text x="{w - 12}" y="{h - 12}" fill="#727a90" font-size="11" text-anchor="end">{esc(eq[-1]['date'])}</text></svg>"""


def calibration_svg(cal: dict[str, list[dict[str, float]]]) -> str:
    w, h, pad = 360, 300, 36

    def pt(x: float, y: float) -> tuple[float, float]:
        return pad + x * (w - pad - 10), h - pad - y * (h - pad - 10)

    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:420px" role="img" aria-label="Calibration: forecast against how often it happened">']
    x0, y0 = pt(0, 0)
    x1, y1 = pt(1, 1)
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#2a3042" stroke-dasharray="4 4"/>')
    for label, v in (("0%", 0), ("50%", 0.5), ("100%", 1)):
        x, y = pt(v, 0)
        parts.append(f'<text x="{x}" y="{h - 12}" font-size="11" text-anchor="middle" fill="#727a90">{label}</text>')
        x, y = pt(0, v)
        parts.append(f'<text x="{pad - 6}" y="{y + 4}" font-size="11" text-anchor="end" fill="#727a90">{label}</text>')
    for name, color in (("crowd", "#8b6dff"), ("options", "#ffb020")):
        pts = [pt(b["forecast"], b["happened"]) for b in cal.get(name, [])]
        if pts:
            parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>')
            for (x, y), b in zip(pts, cal[name]):
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.5 + min(6, b["n"] ** 0.5 / 3):.1f}" fill="{color}"><title>{name}: forecast {b["forecast"]:.0%}, happened {b["happened"]:.0%} ({b["n"]})</title></circle>')
    parts.append(f'<text x="{w / 2}" y="{h - 1}" font-size="11" text-anchor="middle" fill="#a9b0c2">forecast</text></svg>')
    return "".join(parts)


@app.get("/record", response_class=HTMLResponse)
def record(gap: float = 0.10) -> HTMLResponse:
    rec = service.track_record(gap)
    s = rec["score"]
    if not s["cases"]:
        return page("Track record", '<h1>Track record</h1><div class="empty">No resolved markets scored yet. Run <code>python -m twocrowds.cli backtest</code>.</div>', rec["mode"])
    ci = s.get("pnl_ci95")
    ci_txt = "" if not ci else f" (95% range {ci[0] * 100:+.1f}% to {ci[1] * 100:+.1f}%)"
    kinds = "".join(
        f"<tr><td>{esc(k.replace('_', ' '))}</td><td class='tn'>{v['cases']}</td><td class='tn'>{v['crowd_brier']:.3f}</td><td class='tn'>{v['options_brier']:.3f}</td>"
        f"<td class='tn'>{'—' if v['pnl_per_dollar'] is None else f'{v['pnl_per_dollar'] * 100:+.1f}%'}</td><td class='tn'>{v['trades']}</td></tr>"
        for k, v in rec["by_kind"].items()
    )
    rows = "".join(
        f"<tr><td>{esc(r['question'])}</td><td class='tn'>{pct(r['crowd_prob'])}</td><td class='tn'>{pct(r['options_prob'])}</td>"
        f"<td class='{'won' if r['outcome'] else 'lost'}'>{'Yes' if r['outcome'] else 'No'}</td>"
        f"<td>{'Options' if abs(r['options_prob'] - r['outcome']) < abs(r['crowd_prob'] - r['outcome']) else 'Polymarket'}</td></tr>"
        for r in rec["biggest_disagreements"]
    )
    return page(
        "Track record",
        f"""<div class="kicker">Every resolved market · {s['days']} trading days</div><h1>Which crowd forecasts better?</h1>
<p class="lede">Both forecasts are taken at the same moment, 4pm New York the trading day before: Polymarket's last price, and the options market's probability
from that close and Unusual Whales implied volatility. Then each is scored against what happened (Brier score: 0 is perfect, 0.25 is a coin flip).</p>
{scoreboard(s)}{money_stats(s, rec)}
<h2>Taking the options side, day by day</h2><p class="note">$1 on the options crowd's side on Polymarket every time the two split by {gap * 100:.0f}+ points, after a 1¢ cost.
Rules fixed before the first run. 95% range from resampling by day: {'' if not ci else f"{ci[0] * 100:+.1f}% to {ci[1] * 100:+.1f}% per trade"}.</p>
<div class="panel" style="margin-top:14px;padding:16px">{equity_svg(rec.get('equity') or [])}</div>
<h2>Calibration</h2><p class="note">When a crowd says 70%, does it happen 70% of the time? The dashed line is perfect; dot size is the number of markets.</p>
<div class="panel" style="margin-top:14px;padding:16px">{calibration_svg(rec['calibration'])}<div class="legend"><span><b style="background:var(--pm)"></b>Polymarket</span><span><b style="background:var(--op)"></b>Options</span></div></div>
<h2>By kind of question</h2><div class="panel tablewrap" style="margin-top:14px;padding:4px 8px"><table><thead><tr><th>Question</th><th class="tn">Markets</th><th class="tn">Polymarket Brier</th><th class="tn">Options Brier</th><th class="tn">Options-side return</th><th class="tn">Trades</th></tr></thead><tbody>{kinds}</tbody></table></div>
<h2>Biggest disagreements</h2><div class="panel tablewrap" style="margin-top:14px;padding:4px 8px"><table><thead><tr><th>Question</th><th class="tn">Polymarket</th><th class="tn">Options</th><th>Happened?</th><th>Closer</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">Try another threshold with <code>?gap=0.20</code>. Strikes on the same day move together, so the sample is the {s['days']} days more than the {s['cases']:,} markets.
Real fills, Polymarket fees and size limits vary.</p>""",
        rec["mode"],
    )


@app.get("/how", response_class=HTMLResponse)
def how() -> HTMLResponse:
    return page(
        "How it works",
        """<div class="kicker">Method</div><h1>How it works</h1>
<div class="steps"><div class="panel"><b>01</b><p class="q"> Find questions the options market can price</p><p>Polymarket lists daily ladders such as <em>Will NVIDIA (NVDA) close above $205 on October 23?</em>
and <em>Micron (MU) Up or Down on October 23?</em>. Two Crowds reads them from Polymarket's public API and parses the stock, level and date.</p></div>
<div class="panel"><b>02</b><p class="q"> Ask the options market the same question</p><p>Options are priced on a model where the chance a stock closes above a level K
is N(d2), with d2 = (ln(S/K) − σ²T/2) / (σ√T). S is the stock price, T the time left and σ the implied volatility for that horizon from Unusual Whales
(<code>/api/stock/{ticker}/interpolated-iv</code>). That gives the options crowd's own probability for the exact Polymarket question.</p></div>
<div class="panel"><b>03</b><p class="q"> Add what Unusual Whales sees on both sides</p><p>For the prediction market: Unusual Predictions flags
(<code>/api/predictions/unusual</code>, smart money, possible insiders, contrarian whales). For the stock: which way big options bets bought at the ask lean
(<code>/api/option-trades/flow-alerts</code>).</p></div>
<div class="panel"><b>04</b><p class="q"> Keep score</p><p>Every resolved market is scored for both crowds with the Brier score, from forecasts taken at the same moment, 4pm New York the
day before. The record also tests a simple rule: when the crowds disagree by 10+ points, buy the options crowd's side on Polymarket.</p></div></div>
<h2>Ask it from Claude</h2><p>Every number here is also an MCP tool. <a href="/ask">Try the tools and connect Claude →</a></p>
<h2>Limits</h2><ul class="note"><li>Implied volatility is at the money; far-from-the-money strikes carry skew this ignores, so the options probability is less exact there.</li>
<li>Strikes on the same day are correlated; the sample is the number of days more than the number of markets.</li>
<li>Polymarket prices are last trades, hourly, and can be thin.</li></ul>""",
        service.mode(),
    )


ASK_CSS = """
.ask{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:12px;margin-top:22px}
.prompts{display:flex;flex-direction:column;gap:8px}
.prompt{all:unset;cursor:pointer;display:block;padding:14px 16px;border-radius:12px;background:var(--panel);border:1px solid var(--line);color:var(--ink);font-weight:500;line-height:1.35}
.prompt:hover,.prompt.on{border-color:var(--op);background:var(--panel2)}.prompt small{display:block;color:var(--ink3);font:12px "JetBrains Mono",monospace;margin-top:6px}
.form{padding:14px 16px;display:grid;grid-template-columns:1fr 1fr;gap:8px}.form label{font-size:12px;color:var(--ink3);display:flex;flex-direction:column;gap:4px}
.form input{background:#0b0e14;border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:8px 10px;font:14px "JetBrains Mono",monospace}
.form button{grid-column:1/-1;background:var(--op);color:#1b1300;border:0;border-radius:9px;padding:10px;font-weight:700;cursor:pointer}
.console{min-height:420px;display:flex;flex-direction:column;overflow:hidden}
.console .head{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--line);font:12.5px "JetBrains Mono",monospace;color:var(--ink3)}
.console .head i{width:9px;height:9px;border-radius:50%;background:#2b3142}.console .head i:nth-child(1){background:var(--pm)}.console .head i:nth-child(2){background:var(--op)}
.console .body{padding:16px 18px;display:flex;flex-direction:column;gap:12px}
.call{font:13px "JetBrains Mono",monospace;color:var(--op)}.call b{color:var(--ink)}.call span{color:var(--ink3)}
.answer{font-size:16px;line-height:1.5}.answer .hlp{color:var(--pm);font-weight:700}.answer .hlo{color:var(--op);font-weight:700}
.rows{display:flex;flex-direction:column;gap:6px}.rowc{display:grid;grid-template-columns:minmax(0,1fr) 58px 58px 70px;gap:10px;align-items:center;padding:9px 12px;border-radius:9px;background:var(--panel2);font-size:14px}
.rowc .tn{font-size:13.5px}.rowc .pmv{color:var(--pm)}.rowc .opv{color:var(--op)}
.connect{margin-top:12px;padding:16px 18px}.seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;margin-bottom:10px}
.seg button{all:unset;cursor:pointer;padding:6px 14px;font:13px "JetBrains Mono",monospace;color:var(--ink2)}.seg button.on{background:var(--panel2);color:var(--ink)}
.cmd{display:flex;gap:8px;align-items:center}.cmd code{flex:1;padding:10px 12px;overflow-x:auto;white-space:nowrap}
.tools{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:12px}.tool{padding:12px 14px}.tool .sig{font:13px "JetBrains Mono",monospace;color:var(--op)}.tool p{margin:6px 0 0;color:var(--ink2);font-size:13.5px}
details{margin-top:4px}summary{cursor:pointer;color:var(--ink3);font:12.5px "JetBrains Mono",monospace}details pre{max-height:260px;margin-top:8px}
@media(max-width:820px){.ask{grid-template-columns:1fr}}
"""

ASK_JS = """
const $ = (s) => document.querySelector(s);
const pct = (x) => x == null ? '—' : Math.round(x * 100) + '%';
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function run(kind, btn, args) {
  document.querySelectorAll('.prompt').forEach((b) => b.classList.toggle('on', b === btn));
  const body = $('#out');
  const calls = { today: 'two_crowds_today(limit=5)', record: 'two_crowds_track_record(gap=0.10)',
    implied: `implied_probability(ticker="${args?.ticker}", level=${args?.level}, event_date="${args?.date}")` };
  body.innerHTML = `<div class="call">→ <b>${esc(calls[kind])}</b> <span>running…</span></div>`;
  const url = kind === 'today' ? '/api/today' : kind === 'record' ? '/api/record' :
    `/api/implied?ticker=${encodeURIComponent(args.ticker)}&level=${encodeURIComponent(args.level)}&date=${encodeURIComponent(args.date)}`;
  const t0 = performance.now();
  let data;
  try { const r = await fetch(url); data = await r.json(); if (!r.ok) throw new Error(data.detail || data.error || r.status); }
  catch (e) { body.innerHTML = `<div class="call">→ <b>${esc(calls[kind])}</b></div><div class="answer">Couldn't run it: ${esc(e.message)}</div>`; return; }
  const ms = Math.round(performance.now() - t0);
  let html = '';
  if (kind === 'today') {
    const top = data.priced.slice(0, 5);
    html = `<div class="answer">The biggest splits right now, of ${data.priced.length} open questions:</div><div class="rows">` +
      top.map((c) => `<div class="rowc"><span>${esc(c.question)}</span><span class="tn pmv">${pct(c.crowd_prob)}</span><span class="tn opv">${pct(c.options_prob)}</span><span class="tn">${c.gap > 0 ? '+' : ''}${Math.round(c.gap * 100)} pts</span></div>`).join('') + '</div>';
  } else if (kind === 'record') {
    const s = data.score;
    html = `<div class="answer">Over <b>${s.cases.toLocaleString()}</b> resolved markets, options scored <span class="hlo">${s.options_brier.toFixed(3)}</span> against Polymarket's <span class="hlp">${s.crowd_brier.toFixed(3)}</span> (Brier, lower is better). When they split by 10+ points, options were closer in <b>${s.options_closer} of ${s.disagreements}</b>, and taking the options side returned <b>${(s.pnl_per_dollar * 100).toFixed(1)}%</b> per $1 over ${s.trades} trades.</div>`;
  } else {
    html = `<div class="answer">The options market puts ${esc(data.ticker)} ${data.direction} <b>$${data.level}</b> at the close on ${esc(data.event_date)} at <span class="hlo">${pct(data.probability)}</span>. Last price $${Number(data.spot).toFixed(2)}, implied volatility ${(data.implied_volatility * 100).toFixed(0)}%, ${data.trading_days} trading day${data.trading_days === 1 ? '' : 's'} left.</div>`;
  }
  body.innerHTML = `<div class="call">→ <b>${esc(calls[kind])}</b> <span>${ms} ms</span></div>${html}<details><summary>raw result</summary><pre>${esc(JSON.stringify(kind === 'today' ? {...data, priced: data.priced.slice(0, 5), other: undefined, uw_unusual: undefined} : kind === 'record' ? data.score : data, null, 2))}</pre></details>`;
}
document.querySelectorAll('[data-run]').forEach((b) => b.addEventListener('click', () => run(b.dataset.run, b)));
$('#implied').addEventListener('submit', (e) => { e.preventDefault(); const f = new FormData(e.target);
  run('implied', null, { ticker: f.get('ticker'), level: f.get('level'), date: f.get('date') }); });
document.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('.seg button').forEach((x) => x.classList.toggle('on', x === b));
  $('#cmd').textContent = b.dataset.cmd; }));
"""


@app.get("/ask", response_class=HTMLResponse)
def ask(request: Request) -> HTMLResponse:
    base = str(request.base_url).rstrip("/")
    http_cmd = f"claude mcp add --transport http two-crowds {base}/mcp-server/mcp"
    stdio_cmd = "claude mcp add two-crowds -- python -m twocrowds.cli mcp"
    from datetime import date, timedelta

    nxt = date.today() + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    live = service.mode() == "live"
    tools = [
        ("two_crowds_today(limit)", "Open Polymarket stock questions priced by both crowds, biggest splits first."),
        ("two_crowds_track_record(gap)", "Brier scores, how often options were closer, and the options-side return."),
        ("implied_probability(ticker, level, event_date)", "What options imply for any stock closing above a level on a date."),
        ("two_crowds_market(market_id)", "One market: both probabilities, and the outcome once resolved."),
    ]
    return page(
        "Ask",
        f"""<style>{ASK_CSS}</style><div class="kicker">MCP server · 4 read-only tools</div>
<h1>Ask where the crowds split.</h1>
<p class="lede">Two Crowds is an MCP server, so Claude (or any MCP client) can call the same numbers this site shows. Pick a question to see the tool call
and what comes back.</p>
<div class="ask">
<div class="prompts">
<button class="prompt" data-run="today">Where do Polymarket and options disagree right now?<small>two_crowds_today</small></button>
<button class="prompt" data-run="record">Which crowd is usually right?<small>two_crowds_track_record</small></button>
<form class="panel form" id="implied"><label>Ticker<input name="ticker" value="NVDA"></label><label>Closes above $<input name="level" value="215"></label>
<label style="grid-column:1/-1">On<input name="date" type="date" value="{nxt.isoformat()}"></label>
<button type="submit">{'What do options imply?' if live else 'What do options imply? (needs a UW key)'}</button></form>
</div>
<section class="panel console"><div class="head"><i></i><i></i><i></i>two-crowds · mcp</div><div class="body" id="out">
<div class="answer" style="color:var(--ink3)">Pick a question on the left.</div></div></section>
</div>
<h2>Connect Claude</h2>
<div class="panel connect"><div class="seg"><button class="on" data-cmd="{esc(http_cmd)}">HTTP</button><button data-cmd="{esc(stdio_cmd)}">stdio</button></div>
<div class="cmd"><code id="cmd">{esc(http_cmd)}</code></div>
<p class="note" style="margin:10px 0 0">Then ask Claude things like "where do the crowds split today?". The Claude skill in <code>skill/SKILL.md</code> also pulls live flow
and prediction-market data from the Unusual Whales MCP server.</p></div>
<h2>The tools</h2><div class="tools">{''.join(f'<div class="panel tool"><div class="sig">{esc(sig)}</div><p>{esc(d)}</p></div>' for sig, d in tools)}</div>
<script>{ASK_JS}</script>""",
        service.mode(),
    )


# ---- JSON API -------------------------------------------------------------


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(service.status())


@app.get("/api/today")
def api_today() -> JSONResponse:
    return JSONResponse(service.today())


@app.get("/api/record")
def api_record(gap: float = 0.10) -> JSONResponse:
    return JSONResponse(service.track_record(gap))


@app.get("/api/market/{market_id}")
def api_market(market_id: str) -> JSONResponse:
    m = service.market(market_id)
    if not m:
        raise HTTPException(404, f"No market {market_id}")
    return JSONResponse(m)


@app.get("/api/implied")
def api_implied(ticker: str, level: float, date: str, direction: str = "above") -> JSONResponse:
    if service.mode() != "live":
        raise HTTPException(503, "Needs UW_API_KEY")
    out = service.implied_probability(ticker, level, date, direction)
    return JSONResponse(out, status_code=400 if "error" in out else 200)
