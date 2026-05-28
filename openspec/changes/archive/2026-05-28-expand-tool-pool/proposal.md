## Why

The current tool pool has 6 tools (todo_write, calculator, list_files, read_file, write_file, edit_file). This limits the agent to basic file CRUD and arithmetic. Common tasks like searching code, running tests, fetching docs, or checking git status require capabilities the agent doesn't have. Adding these tools dramatically increases what the agent can do without leaving its loop.

## What Changes

- Add `grep` tool: search file contents by regex pattern within the project directory
- Add `bash` tool: execute shell commands with timeout and output capture
- Add `web_fetch` tool: fetch a URL and return its text content
- Add `git_status` tool: show working tree status (staged, unstaged, untracked)
- Add `git_diff` tool: show diff of changes (staged or unstaged)
- Add `git_log` tool: show recent commit history

All new tools follow existing `Tool` protocol from `app/tools/base.py` and are registered in `build_tools()`.

## Capabilities

### New Capabilities
- `grep-search`: Regex-based file content search within project root
- `bash-execution`: Shell command execution with timeout and output capture
- `web-fetch`: HTTP GET to retrieve URL content as text
- `git-readonly`: Read-only git operations (status, diff, log)

### Modified Capabilities

(none)

## Impact

- `backend/app/tools/` — new tool modules added
- `backend/app/tools/registry.py` — register new tools in `build_tools()`
- `backend/app/tools/base.py` — no changes needed, existing `Tool` protocol sufficient
- Risk levels: grep=list_files risk, bash=high risk, web_fetch=medium, git tools=low
- No external dependencies required (grep uses `re`+`pathlib`, bash uses `subprocess`, web_fetch uses `urllib`, git uses `subprocess` calling `git`)
