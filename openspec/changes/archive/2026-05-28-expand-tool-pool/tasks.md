## 1. Grep Tool

- [x] 1.1 Create `backend/app/tools/grep.py` with `GrepTool` class following `ListFilesTool` pattern (project_root, safe_resolve, risk_level=low)
- [x] 1.2 Implement regex search with `re` module, recursive `pathlib` walk, file extension filtering via `glob`, and `max_results` limit
- [x] 1.3 Register `GrepTool` in `build_tools()` in `backend/app/tools/registry.py`
- [x] 1.4 Write tests in `tests/test_grep.py`: basic match, regex, glob filter, max_results, no matches, path safety

## 2. Bash Tool

- [x] 2.1 Create `backend/app/tools/bash.py` with `BashTool` class (risk_level=high, timeout param defaulting to 30s)
- [x] 2.2 Implement `asyncio.create_subprocess_exec` with `shell=True`, capture stdout+stderr, timeout via `asyncio.wait_for`
- [x] 2.3 Register `BashTool` in `build_tools()`
- [x] 2.4 Write tests in `tests/test_bash.py`: simple command, exit code, timeout, stderr capture

## 3. Web Fetch Tool

- [x] 3.1 Create `backend/app/tools/web_fetch.py` with `WebFetchTool` class (risk_level=medium)
- [x] 3.2 Implement `urllib.request.urlopen` with 15s timeout, 50KB body cap, HTML tag stripping, HTTP/HTTPS-only validation
- [x] 3.3 Register `WebFetchTool` in `build_tools()`
- [x] 3.4 Write tests in `tests/test_web_fetch.py`: fetch text, timeout, size cap, reject non-HTTP URL

## 4. Git Read-Only Tools

- [x] 4.1 Create `backend/app/tools/git_status.py` with `GitStatusTool` (risk_level=low, subprocess `git status --short`)
- [x] 4.2 Create `backend/app/tools/git_diff.py` with `GitDiffTool` (risk_level=low, `git diff` / `git diff --cached`)
- [x] 4.3 Create `backend/app/tools/git_log.py` with `GitLogTool` (risk_level=low, `git log --oneline -N`)
- [x] 4.4 Register all three git tools in `build_tools()`
- [x] 4.5 Write tests in `tests/test_git_tools.py`: status, diff staged/unstaged, log with count, not-a-git-repo error

## 5. Integration

- [x] 5.1 Verify all new tools appear in `build_tool_schemas()` output with correct schemas
- [x] 5.2 Verify risk levels: grep=low, bash=high, web_fetch=medium, git=low
- [x] 5.3 Run full test suite to confirm no regressions
