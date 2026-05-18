#!/usr/bin/env python3
"""Split a DEV_SPEC.md into per-section reference files for progressive disclosure.

Reads a DEV_SPEC.md and generates individual reference files under
.claude/skills/spec-orchestrator/references/ for each major section.

Usage:
    python sync_spec.py <spec_file> [--force]

Example:
    python sync_spec.py DEV_SPEC.md
    python sync_spec.py AGENT_FRAMEWORK_SPEC.md --force
"""

import argparse
import re
import sys
from pathlib import Path


SECTION_MAP = {
    "1": ("01-overview.md", "项目概述"),
    "2": ("02-features.md", "核心特性"),
    "3": ("03-tech-decisions.md", "技术选型"),
    "4": ("04-testing.md", "测试方案"),
    "5": ("05-architecture.md", "系统架构"),
    "6": ("06-schedule.md", "项目排期"),
}

# Patterns to match section headers like "## 1." or "## 1："
SECTION_HEADER = re.compile(r"^##\s+(\d+)[.．：:]\s*(.+)$", re.MULTILINE)


def split_sections(content: str) -> dict[str, str]:
    """Split content by ## N. section headers."""
    headers = list(SECTION_HEADER.finditer(content))
    sections = {}

    for i, match in enumerate(headers):
        section_num = match.group(1)
        start = match.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        sections[section_num] = content[start:end].strip()

    return sections


def main():
    parser = argparse.ArgumentParser(description="Sync DEV_SPEC.md to reference files")
    parser.add_argument("spec_file", help="Path to DEV_SPEC.md")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"ERROR: File not found: {spec_path}")
        sys.exit(1)

    content = spec_path.read_text(encoding="utf-8")
    sections = split_sections(content)

    if not sections:
        print("WARNING: No sections found (expected ## 1., ## 2., etc.)")
        sys.exit(1)

    # Determine output directory
    script_dir = Path(__file__).parent
    ref_dir = script_dir.parent / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)

    # Also check for auto-coder references dir
    auto_coder_ref = Path(".claude/skills/auto-coder/references")

    written = 0
    skipped = 0

    for num, (filename, label) in SECTION_MAP.items():
        if num not in sections:
            print(f"  SKIP  {filename} — section {num} ({label}) not found in spec")
            skipped += 1
            continue

        out_path = ref_dir / filename

        if out_path.exists() and not args.force:
            print(f"  SKIP  {filename} — already exists (use --force to overwrite)")
            skipped += 1
            continue

        out_path.write_text(sections[num], encoding="utf-8")
        print(f"  WRITE {filename} — {len(sections[num])} chars")
        written += 1

        # Also sync to auto-coder references if it exists
        if auto_coder_ref.exists():
            auto_path = auto_coder_ref / filename
            auto_path.write_text(sections[num], encoding="utf-8")

    print(f"\nDone: {written} written, {skipped} skipped")
    print(f"Reference files: {ref_dir}")


if __name__ == "__main__":
    main()
