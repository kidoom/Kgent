#!/usr/bin/env python3
"""Generate a progress report from a DEV_SPEC.md.

Reads task statuses from the spec and prints a formatted progress report.

Usage:
    python progress_report.py <spec_file>

Example:
    python progress_report.py DEV_SPEC.md
"""

import argparse
import re
import sys
from pathlib import Path


def parse_tasks(content: str) -> list[dict]:
    """Parse all tasks with their status from the spec."""
    tasks = []
    # Match task rows in markdown tables: | A1 | task name | [x] | date | notes |
    row_pattern = re.compile(
        r"\|\s*([A-Z]\d+(?:\.\d+)?)\s*\|"  # task ID
        r"\s*(.+?)\s*\|"                      # task name
        r"\s*\[([ x~])\]\s*\|"               # status
        r"\s*(.*?)\s*\|"                      # date
        r"\s*(.*?)\s*\|"                      # notes
    )
    for m in row_pattern.finditer(content):
        status_char = m.group(3)
        status = {"x": "DONE", "~": "IN_PROGRESS", " ": "TODO"}[status_char]
        tasks.append({
            "id": m.group(1).strip(),
            "name": m.group(2).strip(),
            "status": status,
            "date": m.group(4).strip(),
            "notes": m.group(5).strip(),
        })
    return tasks


def get_phase(id_str: str) -> str:
    """Extract phase letter from task ID."""
    return re.match(r"([A-Z])", id_str).group(1)


def main():
    parser = argparse.ArgumentParser(description="Generate progress report")
    parser.add_argument("spec_file", help="Path to DEV_SPEC.md")
    args = parser.parse_args()

    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"ERROR: File not found: {spec_path}")
        sys.exit(1)

    content = spec_path.read_text(encoding="utf-8")
    tasks = parse_tasks(content)

    if not tasks:
        print("No tasks found in spec.")
        sys.exit(1)

    # Group by phase
    phases: dict[str, list[dict]] = {}
    for t in tasks:
        phase = get_phase(t["id"])
        phases.setdefault(phase, []).append(t)

    # Print report
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "DONE")
    wip = sum(1 for t in tasks if t["status"] == "IN_PROGRESS")
    todo = sum(1 for t in tasks if t["status"] == "TODO")

    print(f"{'='*60}")
    print(f"  SPEC PROGRESS REPORT")
    print(f"{'='*60}")
    print(f"  Total: {total}  |  Done: {done}  |  In Progress: {wip}  |  TODO: {todo}")
    pct = (done / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * done / total) if total > 0 else 0
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"  [{bar}] {pct:.0f}%")
    print(f"{'='*60}\n")

    for phase in sorted(phases.keys()):
        phase_tasks = phases[phase]
        phase_done = sum(1 for t in phase_tasks if t["status"] == "DONE")
        phase_total = len(phase_tasks)
        pct = phase_done / phase_total * 100 if phase_total else 0

        print(f"  Phase {phase}  [{phase_done}/{phase_total}]  ({pct:.0f}%)")
        print(f"  {'-'*50}")
        for t in phase_tasks:
            icon = {"DONE": "[x]", "IN_PROGRESS": "[~]", "TODO": "[ ]"}[t["status"]]
            date_str = f"  ({t['date']})" if t["date"] else ""
            print(f"    {icon} {t['id']:6s} {t['name']}{date_str}")
        print()

    # Show in-progress and next tasks
    in_progress = [t for t in tasks if t["status"] == "IN_PROGRESS"]
    next_up = [t for t in tasks if t["status"] == "TODO"]

    if in_progress:
        print(f"  [~] Currently in progress:")
        for t in in_progress:
            print(f"     - {t['id']}: {t['name']}")

    if next_up:
        print(f"\n  [ ] Next up:")
        for t in next_up[:3]:
            print(f"     - {t['id']}: {t['name']}")
        if len(next_up) > 3:
            print(f"     ... and {len(next_up) - 3} more")


if __name__ == "__main__":
    main()
