"""SQLite: a response cache for both APIs, plus live snapshots and backtest rows."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
create table if not exists http_cache (
  key text primary key,
  body text not null,
  fetched_at real not null
);
create table if not exists snapshots (
  id integer primary key autoincrement,
  taken_at text not null,
  market_id text not null,
  question text not null,
  ticker text,
  kind text not null,
  crowd_prob real,
  options_prob real,
  gap real,
  payload text not null
);
create index if not exists snapshots_market on snapshots (market_id, taken_at);
create table if not exists backtest (
  market_id text primary key,
  question text not null,
  ticker text not null,
  kind text not null,
  event_date text not null,
  strike real,
  crowd_prob real not null,
  options_prob real not null,
  outcome integer not null,
  payload text not null
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ---- cache -------------------------------------------------------------
    def cache_get(self, key: str, max_age: float | None) -> Any | None:
        row = self.db.execute("select body, fetched_at from http_cache where key = ?", (key,)).fetchone()
        if not row:
            return None
        if max_age is not None and time.time() - row["fetched_at"] > max_age:
            return None
        return json.loads(row["body"])

    def cache_put(self, key: str, body: Any) -> None:
        self.db.execute(
            "insert or replace into http_cache (key, body, fetched_at) values (?, ?, ?)",
            (key, json.dumps(body), time.time()),
        )
        self.db.commit()

    # ---- snapshots ---------------------------------------------------------
    def add_snapshot(self, row: dict[str, Any]) -> None:
        self.db.execute(
            "insert into snapshots (taken_at, market_id, question, ticker, kind, crowd_prob, options_prob, gap, payload)"
            " values (:taken_at, :market_id, :question, :ticker, :kind, :crowd_prob, :options_prob, :gap, :payload)",
            {**row, "payload": json.dumps(row.get("payload", {}))},
        )
        self.db.commit()

    # ---- backtest ----------------------------------------------------------
    def put_backtest(self, rows: list[dict[str, Any]]) -> None:
        self.db.executemany(
            "insert or replace into backtest (market_id, question, ticker, kind, event_date, strike, crowd_prob, options_prob, outcome, payload)"
            " values (:market_id, :question, :ticker, :kind, :event_date, :strike, :crowd_prob, :options_prob, :outcome, :payload)",
            [{**r, "payload": json.dumps(r.get("payload", {}))} for r in rows],
        )
        self.db.commit()

    def backtest_rows(self) -> list[dict[str, Any]]:
        rows = self.db.execute("select * from backtest order by event_date desc, ticker, strike").fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]
