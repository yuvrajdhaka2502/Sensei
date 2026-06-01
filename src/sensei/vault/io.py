from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path
from typing import Any

import frontmatter

from . import paths


@dataclass
class MarkdownDoc:
    path: Path
    metadata: dict[str, Any]
    body: str

    def dumps(self) -> str:
        post = frontmatter.Post(self.body, **self.metadata)
        return frontmatter.dumps(post) + "\n"


def _load(path: Path) -> MarkdownDoc:
    if not path.exists():
        return MarkdownDoc(path=path, metadata={}, body="")
    post = frontmatter.load(path)
    return MarkdownDoc(path=path, metadata=dict(post.metadata), body=post.content)


def _save(doc: MarkdownDoc) -> None:
    doc.path.parent.mkdir(parents=True, exist_ok=True)
    doc.path.write_text(doc.dumps(), encoding="utf-8")


# ---------- profile ----------

PROFILE_TEMPLATE_BODY = """\
## Goals

_Edit this section yourself. Lightweight, no per-task tagging._

## How to coach me

_Edit this section yourself. The AI reads it as instruction._
"""


def read_profile(vault_path: Path) -> MarkdownDoc:
    return _load(paths.profile_path(vault_path))


def write_profile(vault_path: Path, metadata: dict[str, Any], body: str | None = None) -> MarkdownDoc:
    existing = read_profile(vault_path)
    merged_meta = {**existing.metadata, **metadata}
    final_body = body if body is not None else (existing.body or PROFILE_TEMPLATE_BODY)
    doc = MarkdownDoc(path=paths.profile_path(vault_path), metadata=merged_meta, body=final_body)
    _save(doc)
    return doc


def profile_exists(vault_path: Path) -> bool:
    return paths.profile_path(vault_path).exists()


# ---------- user info ----------

def read_user_info(vault_path: Path) -> MarkdownDoc:
    return _load(paths.user_info_path(vault_path))


def write_user_info(vault_path: Path, body: str) -> MarkdownDoc:
    doc = MarkdownDoc(path=paths.user_info_path(vault_path), metadata={}, body=body.strip() + "\n")
    _save(doc)
    return doc


def user_info_exists(vault_path: Path) -> bool:
    return paths.user_info_path(vault_path).exists()


# ---------- pending tasks ----------

PENDING_TEMPLATE = "# Pending Tasks\n\n_Tasks carried over from previous days._\n"


def read_pending_tasks(vault_path: Path) -> list[str]:
    doc = _load(paths.pending_tasks_path(vault_path))
    if not doc.body.strip():
        return []
    return [line.lstrip("- ").strip() for line in doc.body.splitlines() if line.strip().startswith("- ")]


def write_pending_tasks(vault_path: Path, tasks: list[str]) -> None:
    body_lines = [PENDING_TEMPLATE.rstrip(), ""]
    for t in tasks:
        body_lines.append(f"- {t}")
    body = "\n".join(body_lines) + "\n"
    doc = MarkdownDoc(path=paths.pending_tasks_path(vault_path), metadata={}, body=body)
    _save(doc)


# ---------- daily ----------

DAILY_SECTION_MORNING = "## Morning Plan"
DAILY_SECTION_EVENING = "## Evening Review"


def read_daily(vault_path: Path, d: Date) -> MarkdownDoc:
    return _load(paths.daily_path(vault_path, d))


def ensure_daily(vault_path: Path, d: Date) -> MarkdownDoc:
    doc = read_daily(vault_path, d)
    if not doc.metadata:
        doc.metadata = {"date": d.isoformat()}
    doc.metadata.setdefault("date", d.isoformat())
    if not doc.body.strip():
        doc.body = f"# {d.isoformat()}\n"
    _save(doc)
    return doc


def update_daily_meta(vault_path: Path, d: Date, fields: dict[str, Any]) -> MarkdownDoc:
    doc = ensure_daily(vault_path, d)
    doc.metadata.update(fields)
    _save(doc)
    return doc


def set_daily_section(vault_path: Path, d: Date, heading: str, content: str) -> MarkdownDoc:
    """Replace (or append) a top-level `## Heading` section in the daily file."""
    doc = ensure_daily(vault_path, d)
    doc.body = _replace_or_append_section(doc.body, heading, content)
    _save(doc)
    return doc


def _replace_or_append_section(body: str, heading: str, new_content: str) -> str:
    heading_line = heading if heading.startswith("#") else f"## {heading}"
    pattern = re.compile(
        rf"(^{re.escape(heading_line)}\s*$)(.*?)(?=^##\s|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    block = f"{heading_line}\n{new_content.rstrip()}\n\n"
    if pattern.search(body):
        return pattern.sub(block, body)
    sep = "" if body.endswith("\n") else "\n"
    return f"{body}{sep}\n{block}"
