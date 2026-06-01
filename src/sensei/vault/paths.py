from datetime import date as Date
from pathlib import Path


def vault_root(vault_path: Path) -> Path:
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


def daily_dir(vault_path: Path) -> Path:
    p = vault_root(vault_path) / "daily"
    p.mkdir(exist_ok=True)
    return p


def weekly_dir(vault_path: Path) -> Path:
    p = vault_root(vault_path) / "weekly"
    p.mkdir(exist_ok=True)
    return p


def conversations_dir(vault_path: Path) -> Path:
    p = vault_root(vault_path) / "conversations"
    p.mkdir(exist_ok=True)
    return p


def profile_path(vault_path: Path) -> Path:
    return vault_root(vault_path) / "_user_profile.md"


def pending_tasks_path(vault_path: Path) -> Path:
    return vault_root(vault_path) / "_pending_tasks.md"


def user_info_path(vault_path: Path) -> Path:
    return vault_root(vault_path) / "_user_info.md"


def daily_path(vault_path: Path, d: Date) -> Path:
    return daily_dir(vault_path) / f"{d.isoformat()}.md"


def weekly_path_for(vault_path: Path, d: Date) -> Path:
    iso_year, iso_week, _ = d.isocalendar()
    return weekly_dir(vault_path) / f"{iso_year}-W{iso_week:02d}.md"
