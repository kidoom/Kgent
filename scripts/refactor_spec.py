#!/usr/bin/env python3
"""One-shot refactor of DEV_spec.md into a 3-part, 20-chapter structure."""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(r"D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md")


def parse_chapters(text: str) -> dict[int, list[str]]:
    lines = text.splitlines()
    chapters: dict[int, list[str]] = {}
    current: int | None = None
    buf: list[str] = []
    for line in lines:
        m = re.match(r"^## (\d+)\.\s+(.+)$", line)
        if m:
            if current is not None:
                chapters[current] = buf
            current = int(m.group(1))
            buf = [line]
        elif current is not None:
            buf.append(line)
    if current is not None:
        chapters[current] = buf
    return chapters


def body(chapters: dict[int, list[str]], num: int) -> str:
    """Chapter body without the top ## header line."""
    raw = chapters[num]
    return "\n".join(raw[1:]).strip()


def split_at_subsection(chapter_body: str, subsection_prefix: str) -> tuple[str, str]:
    """Split chapter body at ### N.M subsection header."""
    idx = chapter_body.find(subsection_prefix)
    if idx == -1:
        return chapter_body.strip(), ""
    return chapter_body[:idx].strip(), chapter_body[idx:].strip()


def renumber_subsections(text: str, old_prefix: str, new_prefix: str) -> str:
    return text.replace(old_prefix, new_prefix)


def fix_refs(text: str) -> str:
    mapping = {
        "§21": "§17",
        "§15": "§15",
        "§14": "§14",
        "§6": "§6",
        "§7": "§7",
        "§17": "§12",
        "§20": "§19",
        "§18": "§20",
        "§22": "§18",
        "见 14.3": "见 §14.3",
        "（见 14.3）": "（见 §14.3）",
        "详见 §15。": "详见 §15。",
        "（见 §21）": "（见 §17）",
        "见 §21。": "见 §17。",
        "（V0.1.2+）": "（V0.1.2+，见 §15）",
        "（V0.1.3+）": "（V0.1.3+，见 §16）",
        "（V0.2+）": "（V0.2+，见 §18）",
    }
    # Old section references that changed
    old_to_new = {
        "§14 一致": "§14 一致",
        "与 §14 一致": "与 §14 一致",
    }
    result = text
    for old, new in old_to_new.items():
        result = result.replace(old, new)
    # Specific legacy refs
    result = result.replace("详见 §15。", "详见 §15。")
    result = result.replace("（见 §21）", "（见 §17）")
    result = result.replace("见 §21。", "见 §17。")
    result = result.replace("Debug CLI 已实现**，见 §21", "Debug CLI 已实现**，见 §17")
    result = result.replace("见 §21；", "见 §17；")
    result = result.replace("（见 §21）", "（见 §17）")
    result = result.replace("见 §21.", "见 §17.")
    return result


def build_part_a(ch: dict[int, list[str]]) -> str:
    # Merge §3 + §19 for chapter 3
    arch = body(ch, 3)
    mental = body(ch, 19)

    # Merge §11 + §12 + §13 for chapter 10
    runtime = "\n\n".join(
        [
            "### 10.1 串行执行\n\n" + body(ch, 11),
            "### 10.2 错误处理\n\n" + body(ch, 12),
            "### 10.3 安全边界\n\n" + body(ch, 13),
        ]
    )

    # §7 - update health JSON and step ref
    api = body(ch, 7)
    api = api.replace("详见 §15。", "详见 §15。")
    api = api.replace(
        '"model_client_ready": true\n}',
        '"model_client_ready": true,\n  "permission_mode": "risk_based",\n  "effective_permission_mode": "risk_based",\n  "tool_risks": {\n    "calculator": "low",\n    "list_files": "low",\n    "read_file": "medium"\n  }\n}',
        1,
    )
    api = api.replace("用于存活检查与配置探针（V0.1.3+）：", "用于存活检查与配置探针：")

    # §6 - add risk_level note
    tool = body(ch, 6)
    tool = tool.replace(
        "class Tool(Protocol):\n    name: str\n    description: str\n    input_schema: dict",
        'class Tool(Protocol):\n    name: str\n    description: str\n    input_schema: dict\n    risk_level: Literal["low", "medium", "high"]  # runtime-only，见 §18',
    )
    tool += "\n\n> V0.2 起 `risk_level` 为 runtime 元数据，**不**通过 `tool_to_schema()` 投影给模型。详见 §18。\n"

    # §4 - update directory tree
    modules = body(ch, 4)
    modules = modules.replace(
        "        prompts.py\n      tools/",
        "        prompts.py\n        permissions.py\n        session_store.py\n        model/\n      tools/",
    )
    modules = modules.replace(
        "        config.py\n    pyproject.toml",
        "        config.py\n      debug_cli.py\n    pyproject.toml",
    )
    modules = modules.replace("| `core/config.py` | 环境变量和运行配置 |", "| `core/config.py` | 环境变量和运行配置 |\n| `agent/permissions.py` | 工具权限策略（V0.2） |\n| `agent/session_store.py` | 进程内短期 session（V0.1.1） |\n| `debug_cli.py` | 终端可观测 debug REPL（V0.1.4） |")

    # §2 - update non-goals
    nongoals = body(ch, 2)
    nongoals = nongoals.replace("- 权限审批系统", "- 完整权限审批系统（V0.2 已实现 CLI 交互 + risk_based 策略，见 §18）")
    nongoals = nongoals.replace("- 复杂 Web 聊天 UI（**终端 debug CLI 已实现**，见 §21；与 Cursor/CC 级产品 UI 仍非目标）", "- 复杂 Web 聊天 UI（**终端 debug CLI 已实现**，见 §17；与 Cursor/CC 级产品 UI 仍非目标）")
    nongoals = nongoals.replace("这些能力留给 V0.2 之后逐步加入。", "其余能力见 §20 路线图，按版本逐步加入。")

    sections = [
        ("1. 目标", body(ch, 1)),
        ("2. 非目标", nongoals),
        (
            "3. 最小架构与核心心智模型",
            arch
            + "\n\n### 3.2 核心心智模型\n\n"
            + re.sub(r"^## \d+\.[^\n]*\n", "", mental, count=1),
        ),
        ("4. 模块划分", modules),
        ("5. Message 协议", body(ch, 5)),
        ("6. Tool 协议", tool),
        ("7. FastAPI API 设计", api),
        ("8. V0.1 内置工具", body(ch, 8)),
        ("9. Agent Loop 伪代码", body(ch, 9)),
        ("10. 运行时合约", runtime),
        ("11. 前端 V0.1 范围", body(ch, 10)),
        (
            "12. 验收标准",
            body(ch, 17)
            .replace("### 场景 1", "### 12.1 场景 1")
            .replace("### 场景 2", "### 12.2 场景 2")
            .replace("### 场景 3", "### 12.3 场景 3"),
        ),
    ]

    out = ["---", "", "## Part A — Stable Design（稳定设计契约）", ""]
    for title, content in sections:
        out.append(f"## {title}")
        out.append("")
        out.append(fix_refs(content))
        out.append("")
    return "\n".join(out)


def build_part_b(ch: dict[int, list[str]]) -> str:
    # §15 split: 15.4 plan→act goes to §17
    cc_full = body(ch, 15)
    cc_main, cc_plan = split_at_subsection(cc_full, "### 15.4 Debug 专用")
    cc_main = renumber_subsections(cc_main, "### 15.", "### 15.")
    cc_main = cc_main.replace("再进入 act（见 §21）。", "再进入 act（见 §17）。")

    v01_baseline = """> **版本状态：已完成** — 本章为设计追溯；具体实现见 §19 snapshot。

V0.1 基线能力（已在后续小版本中扩展）：

- FastAPI + 最小 model-tool-model loop
- 三类内置工具（calculator / list_files / read_file）
- 串行工具执行、错误回填、路径安全边界
- 伪代码见 §9；验收见 §12

> V0.1.1～V0.2 的增量能力各自独立成章（§14～§18），不在此重复。"""

    session = body(ch, 14)
    session = renumber_subsections(session, "### 14.", "### 14.")
    session = session.replace("# 22 passed", "# 41 passed（含 V0.2）")
    session = session.replace("**未纳入 V0.1.1（见 14.3）**", "**未纳入 V0.1.1（见 §14.3）**")

    prompt = body(ch, 16)
    prompt = renumber_subsections(prompt, "### 16.", "### 16.")

    debug = body(ch, 21)
    debug = renumber_subsections(debug, "### 21.", "### 17.")
    debug = debug.replace("与 §14 一致", "与 §14 一致")

    perm = body(ch, 22)
    perm = renumber_subsections(perm, "### 22.", "### 18.")
    perm = perm.replace('保持 §6"runtime', '保持 §6 "runtime')

    # Append plan→act from §15.4 to debug CLI chapter as §17.7
    if cc_plan:
        cc_plan = renumber_subsections(cc_plan, "### 15.4", "### 17.7")
        cc_plan = cc_plan.replace("（V0.1.4，仅 debug CLI）", "（仅 debug CLI）")
        debug = debug + "\n\n" + cc_plan

    sections = [
        ("13. V0.1 — 最小 Agent Loop", v01_baseline),
        ("14. V0.1.1 — 短期记忆 Session Store", session),
        ("15. V0.1.2 — CC 四相 Agent Loop", cc_main),
        ("16. V0.1.3 — Prompt 对齐与工程加固", prompt),
        ("17. V0.1.4 — Debug CLI 可观测性", debug),
        ("18. V0.2 — 工具权限层", perm),
    ]

    out = ["---", "", "## Part B — Version Log（版本变更日志）", ""]
    for title, content in sections:
        out.append(f"## {title}")
        out.append("")
        out.append(fix_refs(content))
        out.append("")
    return "\n".join(out)


def build_part_c(ch: dict[int, list[str]]) -> str:
    snapshot = body(ch, 20)
    snapshot = renumber_subsections(snapshot, "### 20.", "### 19.")
    snapshot = snapshot.replace("（见 §21）。", "（见 §17）。")
    snapshot = snapshot.replace(
        "These remain out of scope for the current V0.1 implementation:",
        "These remain out of scope（详见各版本章节的「不在范围」小节）：",
    )
    # Add test_permissions.py to file layout
    snapshot = snapshot.replace(
        "  test_debug_cli.py\n```",
        "  test_debug_cli.py\n  test_permissions.py\n```",
    )
    snapshot = snapshot.replace(
        "- [x] Health endpoint lists registered providers.",
        "- [x] Health endpoint lists registered providers.\n- [x] Permission layer tests (`tests/test_permissions.py`, 14 cases).",
    )

    roadmap = body(ch, 18)
    roadmap = roadmap.replace(
        "V0.1: FastAPI + 最小 agent loop + 串行工具调用 [done]",
        "V0.1:   FastAPI + 最小 agent loop + 串行工具调用          [done]  → §13",
    )
    roadmap = roadmap.replace(
        "V0.1.1: 短期记忆 session store（session_id -> messages[]） [done, 2026-05-19]",
        "V0.1.1: 短期记忆 session store                         [done]  → §14",
    )
    roadmap = roadmap.replace(
        "V0.1.2: CC 范式 think/call/observe/final agent loop [done, 2026-05-19]",
        "V0.1.2: CC 四相 think/call/observe/final             [done]  → §15",
    )
    roadmap = roadmap.replace(
        "V0.1.3: Prompt 对齐 + lifespan + AgentStep 校验 + session 截断 [done, 2026-05-19]",
        "V0.1.3: Prompt 对齐 + 工程加固                        [done]  → §16",
    )
    roadmap = roadmap.replace(
        "V0.1.4: Debug CLI 可观测性（交互 REPL、plan→act、compact trace）[done, 2026-05-19]",
        "V0.1.4: Debug CLI 可观测性                            [done]  → §17",
    )
    roadmap = roadmap.replace(
        "V0.2: 工具权限层 + read/write 风险分级 [done, 2026-05-19]",
        "V0.2:   工具权限层 + 风险分级                         [done]  → §18",
    )

    out = [
        "---",
        "",
        "## Part C — Snapshot & Roadmap（现状快照与路线）",
        "",
        "## 19. 当前实现状态",
        "",
        fix_refs(snapshot),
        "",
        "## 20. 后续版本路线",
        "",
        fix_refs(roadmap),
        "",
    ]
    return "\n".join(out)


def build_header() -> str:
    return """# Mini Agent DEV Spec

> Canonical path: `D:\\claude-code\\spec\\mini-agent-v0.1\\DEV_spec.md`（repo 内见 [`.spec-source`](.spec-source)）
>
> 最后更新：**2026-05-19** | 测试基线：**41 passed** | 最新版本：**V0.2**

---

## 文档结构

本 spec 分三段，避免「稳定设计 / 版本日志 / 现状快照」混编：

| Part | 章节 | 读什么时候 |
| --- | --- | --- |
| **A — Stable Design** | §1～§12 | 理解系统契约、协议、API、运行时规则 |
| **B — Version Log** | §13～§18 | 查某个版本做了什么、验收场景、进度表 |
| **C — Snapshot & Roadmap** | §19～§20 | 看仓库当前实现了什么、下一步去哪 |

### 目录

**Part A — Stable Design**
1. [目标](#1-目标)
2. [非目标](#2-非目标)
3. [最小架构与核心心智模型](#3-最小架构与核心心智模型)
4. [模块划分](#4-模块划分)
5. [Message 协议](#5-message-协议)
6. [Tool 协议](#6-tool-协议)
7. [FastAPI API 设计](#7-fastapi-api-设计)
8. [V0.1 内置工具](#8-v01-内置工具)
9. [Agent Loop 伪代码](#9-agent-loop-伪代码)
10. [运行时合约](#10-运行时合约)
11. [前端 V0.1 范围](#11-前端-v01-范围)
12. [验收标准](#12-验收标准)

**Part B — Version Log**
13. [V0.1 — 最小 Agent Loop](#13-v01--最小-agent-loop)
14. [V0.1.1 — 短期记忆 Session Store](#14-v011--短期记忆-session-store)
15. [V0.1.2 — CC 四相 Agent Loop](#15-v012--cc-四相-agent-loop)
16. [V0.1.3 — Prompt 对齐与工程加固](#16-v013--prompt-对齐与工程加固)
17. [V0.1.4 — Debug CLI 可观测性](#17-v014--debug-cli-可观测性)
18. [V0.2 — 工具权限层](#18-v02--工具权限层)

**Part C — Snapshot & Roadmap**
19. [当前实现状态](#19-当前实现状态)
20. [后续版本路线](#20-后续版本路线)

### 旧版章节对照（重构前 → 重构后）

| 旧 § | 新 § | 说明 |
| --- | --- | --- |
| §1～§10 | §1～§9, §11 | 稳定设计，顺序微调 |
| §11～§13 | §10 | 合并为「运行时合约」 |
| §14 | §14 | V0.1.1 session |
| §15 | §15 + §17.7 | CC 四相；plan→act 移入 Debug CLI 章 |
| §16 | §16 | V0.1.3 |
| §17 | §12 | 验收标准上移到 Part A |
| §18 | §20 | 路线图 |
| §19 | §3.2 | 心智模型并入架构章 |
| §20 | §19 | 实现状态 snapshot |
| §21 | §17 | Debug CLI |
| §22 | §18 | V0.2 权限层 |

---"""


def main() -> None:
    text = SPEC.read_text(encoding="utf-8")
    ch = parse_chapters(text)
    missing = set(range(1, 23)) - set(ch.keys())
    if missing:
        raise SystemExit(f"Missing chapters: {missing}")

    parts = [
        build_header(),
        build_part_a(ch),
        build_part_b(ch),
        build_part_c(ch),
    ]
    new_spec = "\n".join(parts).strip() + "\n"
    SPEC.write_text(new_spec, encoding="utf-8")
    print(f"Wrote refactored spec: {SPEC}")
    print(f"Lines: {len(new_spec.splitlines())}")


if __name__ == "__main__":
    main()
