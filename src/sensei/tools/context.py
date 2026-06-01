from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass
class ToolContext:
    user_id: str
    vault_path: Path
    db_path: Path
    tz: ZoneInfo

    def today(self) -> Date:
        return datetime.now(self.tz).date()
