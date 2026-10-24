"""Settings, read once from the environment (and a local .env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    uw_api_key: str | None
    db_path: Path
    # Demo mode serves the bundled sample data and makes no network calls.
    demo: bool
    uw_rpm: int

    @property
    def live(self) -> bool:
        return bool(self.uw_api_key) and not self.demo


def settings() -> Settings:
    key = os.environ.get("UW_API_KEY") or None
    return Settings(
        uw_api_key=key,
        db_path=Path(os.environ.get("TWO_CROWDS_DB", ROOT / "data" / "two-crowds.db")),
        demo=os.environ.get("TWO_CROWDS_DEMO", "").lower() in {"1", "true", "yes"} or not key,
        uw_rpm=int(os.environ.get("UW_RPM", "100")),
    )
