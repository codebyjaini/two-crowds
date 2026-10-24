"""Turn a Polymarket question into something the options market can price."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}

# "Will NVIDIA (NVDA) close above $205 on October 23?"
CLOSE_ABOVE = re.compile(
    r"will\s+(?P<name>.+?)\s*\((?P<ticker>[A-Z.]{1,6})\)\s+(?:close|finish|end)\s+(?P<dir>above|below)\s+\$(?P<strike>[\d,]+(?:\.\d+)?)\s+on\s+(?P<month>[a-z]+)\s+(?P<day>\d{1,2})",
    re.I,
)
# "NVIDIA (NVDA) Up or Down on October 23?"
UP_DOWN = re.compile(r"^(?P<name>.+?)\s*\((?P<ticker>[A-Z.]{1,6})\)\s+up or down on\s+(?P<month>[a-z]+)\s+(?P<day>\d{1,2})", re.I)
# "Will Meta (META) beat quarterly earnings?"
EARNINGS = re.compile(r"will\s+(?P<name>.+?)\s*\((?P<ticker>[A-Z.]{1,6})\)\s+beat\s+quarterly\s+earnings", re.I)


@dataclass(frozen=True)
class Question:
    kind: str  # "close_above" | "close_below" | "up_down" | "earnings_beat"
    ticker: str
    name: str
    event_date: date | None
    strike: float | None = None

    @property
    def priceable(self) -> bool:
        """Options price a stock closing above or below a level directly."""
        return self.kind in {"close_above", "close_below", "up_down"} and self.event_date is not None


def _date(month: str, day: str, end_date: str | None) -> date | None:
    m = MONTHS.get(month.lower())
    if not m:
        return None
    year = datetime.fromisoformat(end_date.replace("Z", "+00:00")).year if end_date else date.today().year
    try:
        return date(year, m, int(day))
    except ValueError:
        return None


def parse(question: str, end_date: str | None = None) -> Question | None:
    q = question.strip()
    if m := CLOSE_ABOVE.search(q):
        kind = "close_above" if m["dir"].lower() == "above" else "close_below"
        return Question(kind, m["ticker"].upper(), m["name"].strip(), _date(m["month"], m["day"], end_date), float(m["strike"].replace(",", "")))
    if m := UP_DOWN.search(q):
        if "open" in q.lower().split("up or down")[0]:
            return None  # "Opens up or down" compares with the open, not the close: skip
        return Question("up_down", m["ticker"].upper(), m["name"].strip(), _date(m["month"], m["day"], end_date))
    if m := EARNINGS.search(q):
        ed = datetime.fromisoformat(end_date.replace("Z", "+00:00")).date() if end_date else None
        return Question("earnings_beat", m["ticker"].upper(), m["name"].strip(), ed)
    return None
