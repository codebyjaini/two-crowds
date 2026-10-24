"""Command line: python -m twocrowds.cli {backtest,today,record,export-demo,serve,mcp}"""

from __future__ import annotations

import argparse
import json
import os

from . import service


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def main() -> None:
    ap = argparse.ArgumentParser(prog="two-crowds")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backtest", help="score both crowds on resolved Polymarket stock markets")
    b.add_argument("--pages", type=int, default=10, help="pages of 100 closed events to scan")
    sub.add_parser("today", help="today's open markets, priced by both crowds")
    r = sub.add_parser("record", help="print the track record")
    r.add_argument("--gap", type=float, default=0.10)
    sub.add_parser("export-demo", help="save the current data as data/demo.json")
    s = sub.add_parser("serve", help="run the dashboard")
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8040)))
    s.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    sub.add_parser("mcp", help="run the MCP server over stdio")
    args = ap.parse_args()

    if args.cmd == "backtest":
        print(json.dumps(service.run_backtest(args.pages), indent=1, default=str))
    elif args.cmd == "today":
        t = service.today()
        print(f"as of {t['as_of']} ({t['mode']})")
        for c in t["priced"][:30]:
            print(f"  {c['question'][:70]:70}  crowd {pct(c['crowd_prob']):>4}  options {pct(c['options_prob']):>4}  {c['verdict']}")
    elif args.cmd == "record":
        print(json.dumps(service.track_record(args.gap)["score"], indent=1, default=str))
    elif args.cmd == "export-demo":
        print(f"saved {service.export_demo()} resolved cases to data/demo.json")
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("twocrowds.web:app", host=args.host, port=args.port, proxy_headers=True, forwarded_allow_ips="*")
    elif args.cmd == "mcp":
        from .mcp_server import mcp

        mcp.run()


if __name__ == "__main__":
    main()
