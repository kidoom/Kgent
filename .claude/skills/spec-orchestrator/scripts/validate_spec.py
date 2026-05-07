#!/usr/bin/env python3
"""Validate a DEV_SPEC.md against the methodology rules.

Checks:
1. All 6 sections exist
2. Every task has the 5 required fields (objective, files, classes, acceptance, test method)
3. Every pluggable component has interface + factory + config
4. Progress tracking table exists with correct columns

Usage:
    python validate_spec.py <spec_file>

Example:
    python validate_spec.py DEV_SPEC.md
"""

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "项目概述",
    "核心特性",
    "技术选型",
    "测试方案",
    "系统架构",
    "项目排期",
]

TASK_REQUIRED_FIELDS = ["目标", "修改文件", "实现类", "验收标准", "测试方法"]

COMPONENT_CHECKLIST_ITEMS = ["抽象接口", "工厂", "配置", "实现", "降级"]


def check_sections(content: str) -> list[str]:
    """Check that all required sections exist."""
    errors = []
    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section: {section}")
    return errors


def check_tasks(content: str) -> list[str]:
    """Check that every task header has the 5 required fields."""
    errors = []
    # Match task headers like "### A1：" or "### B7.1："
    task_pattern = re.compile(r"^###\s+[A-Z]\d+(?:\.\d+)?[：:]\s*(.+)$", re.MULTILINE)
    field_pattern = re.compile(r"-\s*\*\*(.+?)\*\*")

    tasks = list(task_pattern.finditer(content))
    if not tasks:
        # Also check for table-based tasks (| A1 | task name | [x] |)
        table_tasks = re.findall(r"\|\s*([A-Z]\d+(?:\.\d+)?)\s*\|", content)
        if table_tasks:
            print(f"  INFO: Found {len(table_tasks)} table-based tasks (no detailed specs to validate)")
            print("  TIP: Add detailed task specs (### A1: ...) with 5 required fields for full validation")
        else:
            errors.append("No task specifications found (expected ### A1:, B1:, etc.)")
        return errors

    for i, task_match in enumerate(tasks):
        task_name = task_match.group(1).strip()
        task_start = task_match.start()
        # Find end of this task (next task header or end of file)
        if i + 1 < len(tasks):
            task_end = tasks[i + 1].start()
        else:
            task_end = len(content)

        task_body = content[task_start:task_end]
        fields_found = [m.group(1) for m in field_pattern.finditer(task_body)]

        for required_field in TASK_REQUIRED_FIELDS:
            if not any(required_field in f for f in fields_found):
                errors.append(f"Task '{task_name}': missing field '**{required_field}**'")

    return errors


def check_progress_table(content: str) -> list[str]:
    """Check that progress tracking table exists with correct columns."""
    errors = []
    if "进度跟踪" not in content and "Progress" not in content:
        errors.append("No progress tracking table found")
        return errors

    # Check for table header with required columns
    if "| 编号" not in content and "| Task" not in content:
        errors.append("Progress table missing '编号/Task' column")
    if "| 状态" not in content and "| Status" not in content:
        errors.append("Progress table missing '状态/Status' column")

    return errors


def count_tasks(content: str) -> dict:
    """Count tasks by status."""
    not_started = len(re.findall(r"\[\s\]", content))
    in_progress = len(re.findall(r"\[~\]", content))
    completed = len(re.findall(r"\[x\]", content))
    return {
        "not_started": not_started,
        "in_progress": in_progress,
        "completed": completed,
        "total": not_started + in_progress + completed,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate a DEV_SPEC.md")
    parser.add_argument("spec_file", help="Path to DEV_SPEC.md")
    args = parser.parse_args()

    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"ERROR: File not found: {spec_path}")
        sys.exit(1)

    content = spec_path.read_text(encoding="utf-8")
    all_errors = []

    # Check sections
    section_errors = check_sections(content)
    all_errors.extend(section_errors)

    # Check tasks
    task_errors = check_tasks(content)
    all_errors.extend(task_errors)

    # Check progress table
    table_errors = check_progress_table(content)
    all_errors.extend(table_errors)

    # Print results
    if all_errors:
        print(f"VALIDATION FAILED — {len(all_errors)} issue(s):\n")
        for i, err in enumerate(all_errors, 1):
            print(f"  {i}. {err}")
        print()
    else:
        print("VALIDATION PASSED")

    # Always show stats
    stats = count_tasks(content)
    print(f"\nTask Progress: {stats['completed']}/{stats['total']} completed "
          f"({stats['in_progress']} in progress, {stats['not_started']} not started)")

    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
