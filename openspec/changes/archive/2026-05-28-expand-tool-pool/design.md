## Context

Kgent's tool pool currently has 6 tools: todo_write, calculator, list_files, read_file, write_file, edit_file. All follow the `Tool` protocol in `app/tools/base.py` — a class with `name`, `description`, `input_schema`, `risk_level` attributes and an async `call(input) -> str` method. Tools are registered in `build_tools()` in `app/tools/registry.py` and use `safe_resolve()` from `app/tools/path_safety.py` for path-based operations.

The agent cannot search code, run commands, fetch web content, or inspect git state. These are the most common operations in a coding workflow.

## Goals / Non-Goals

**Goals:**
- Add grep, bash, web_fetch, and git read-only tools following existing patterns
- Each tool is a single file in `backend/app/tools/`
- Proper risk levels: grep=low, bash=high, web_fetch=medium, git=low
- Path safety for file-touching tools (grep uses same `safe_resolve` pattern)
- No new pip dependencies (stdlib only)

**Non-Goals:**
- Git write operations (commit, push, checkout) — too risky for layer 1
- Streaming output for long-running bash commands
- Persistent shell sessions (each bash call is independent)
- Web search (requires external API keys)

## Decisions

**1. grep: `re` + `pathlib` recursive walk, not subprocess `grep`**
- Portable across Windows/Linux/macOS without depending on external `grep` binary
- Consistent with existing tools that use `pathlib`
- Supports full Python regex syntax
- Alternative: subprocess `grep` — faster but not portable on Windows

**2. bash: `asyncio.create_subprocess_exec` with shell=True**
- The model needs to run arbitrary commands (pip install, pytest, git, etc.)
- `shell=True` required for pipes, redirects, chaining
- Timeout via `asyncio.wait_for` to prevent hangs
- Captures both stdout and stderr
- Risk level: `high` — requires `allow_all` or explicit approval

**3. web_fetch: `urllib.request` with size limit**
- stdlib only, no `requests`/`httpx` dependency
- Cap response body at 50KB to avoid flooding context
- Return plain text (strip HTML tags with simple regex)
- Timeout: 15 seconds

**4. git tools: subprocess `git` commands**
- Three read-only tools: status, diff, log
- All risk_level `low` — no mutations
- Thin wrappers around `git status --short`, `git diff`, `git log --oneline -20`
- Fail gracefully if not a git repo

**5. All tools registered in `build_tools()` with existing pattern**
- No change to `Tool` protocol
- Each tool gets `project_root: Path` in `__init__` where needed

## Risks / Trade-offs

- **bash injection** → Mitigated by `high` risk level requiring explicit approval in interactive/risk_based modes. The model's input IS the command — no user template interpolation.
- **bash timeout** → Default 30s timeout. Long-running builds will be killed. User can adjust later.
- **web_fetch size limit** → 50KB cap may truncate large pages. Acceptable for doc lookup; full page scraping is a non-goal.
- **git not installed** → Tools raise clear error if `git` binary not found. Non-fatal to other tools.
