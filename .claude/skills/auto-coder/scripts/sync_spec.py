#!/usr/bin/env python3
"""
Spec Sync — splits the canonical DEV spec into chapter files under auto-coder/references/.

The spec path is read from (first match):
  1. <repo>/.spec-source
  2. KGENT_SPEC_PATH environment variable
  3. D:\\claude-code\\spec\\mini-agent-v0.1\\DEV_spec.md

Usage:
    python scripts/sync_spec.py [--force]
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import List, NamedTuple, Tuple


class Chapter(NamedTuple):
    number: int
    cn_title: str
    filename: str
    start_line: int
    end_line: int
    line_count: int


DEFAULT_SPEC_PATH = Path(r"D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md")

# Chapter number -> English slug (encoding-independent)
NUMBER_SLUG_MAP = {
    1: "overview",
    2: "features",
    3: "tech-stack",
    4: "testing",
    5: "architecture",
    6: "schedule",
    7: "future",
}


def resolve_dev_spec(repo_root: Path) -> Path:
    config_file = repo_root / ".spec-source"
    if config_file.exists():
        raw = config_file.read_text(encoding="utf-8").strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                path = (repo_root / path).resolve()
            return path

    env_path = os.environ.get("KGENT_SPEC_PATH")
    if env_path:
        return Path(env_path)

    return DEFAULT_SPEC_PATH


def _slug(chapter_num: int, title: str) -> str:
    if chapter_num in NUMBER_SLUG_MAP:
        return NUMBER_SLUG_MAP[chapter_num]
    clean = re.sub(r"[^\w]+", "-", title, flags=re.ASCII).strip("-").lower()
    return clean or f"chapter-{chapter_num}"


def detect_chapters(content: str) -> List[Chapter]:
    lines = content.split("\n")
    starts: List[Tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^## (\d+)\.\s+(.+)$", line)
        if m:
            starts.append((int(m.group(1)), m.group(2).strip(), i))
    if not starts:
        raise ValueError("No chapters found. Expected '## N. Title'")
    chapters = []
    for idx, (num, title, start) in enumerate(starts):
        end = starts[idx + 1][2] if idx + 1 < len(starts) else len(lines)
        chapters.append(
            Chapter(num, title, f"{num:02d}-{_slug(num, title)}.md", start, end, end - start)
        )
    return chapters


def sync(force: bool = False) -> None:
    skill_dir = Path(__file__).parent.parent
    repo_root = skill_dir.parent.parent.parent
    dev_spec = resolve_dev_spec(repo_root)
    specs_dir = skill_dir / "references"
    hash_file = skill_dir / ".spec_hash"

    if not dev_spec.exists():
        print(f"ERROR: {dev_spec} not found")
        sys.exit(1)

    current_hash = hashlib.sha256(dev_spec.read_bytes()).hexdigest()
    if not force and hash_file.exists() and hash_file.read_text().strip() == current_hash:
        print(f"specs up-to-date ({dev_spec})")
        return

    content = dev_spec.read_text(encoding="utf-8")
    chapters = detect_chapters(content)
    lines = content.split("\n")

    specs_dir.mkdir(parents=True, exist_ok=True)

    old = {f.name for f in specs_dir.glob("*.md")}
    new = {ch.filename for ch in chapters}
    for filename in old - new:
        (specs_dir / filename).unlink()

    for ch in chapters:
        (specs_dir / ch.filename).write_text(
            "\n".join(lines[ch.start_line : ch.end_line]),
            encoding="utf-8",
        )

    hash_file.write_text(current_hash)
    print(f"synced {len(chapters)} chapters from {dev_spec}")


if __name__ == "__main__":
    sync(force="--force" in sys.argv)
