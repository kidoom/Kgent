## ADDED Requirements

### Requirement: Show git working tree status
The system SHALL provide a `git_status` tool that shows the current working tree status (staged, unstaged, untracked files).

#### Scenario: Clean working tree
- **WHEN** the agent calls `git_status` on a clean repo
- **THEN** the tool returns "working tree clean"

#### Scenario: Modified files
- **WHEN** the agent calls `git_status` with staged and unstaged changes
- **THEN** the tool returns output equivalent to `git status --short`

### Requirement: Show git diff
The system SHALL provide a `git_diff` tool that shows the diff of changes.

#### Scenario: Unstaged changes
- **WHEN** the agent calls `git_diff` with no arguments
- **THEN** the tool returns the unstaged diff equivalent to `git diff`

#### Scenario: Staged changes
- **WHEN** the agent calls `git_diff` with `staged=true`
- **THEN** the tool returns the staged diff equivalent to `git diff --cached`

### Requirement: Show git log
The system SHALL provide a `git_log` tool that shows recent commit history.

#### Scenario: Default log
- **WHEN** the agent calls `git_log` with no arguments
- **THEN** the tool returns the last 20 commits in `oneline` format

#### Scenario: Custom count
- **WHEN** the agent calls `git_log` with `count=5`
- **THEN** the tool returns the last 5 commits

### Requirement: All git tools have low risk
All git read-only tools SHALL have risk_level `low`.

#### Scenario: Runs without permission prompt
- **WHEN** the agent calls any git tool under `risk_based` permission policy
- **THEN** the tool executes without requiring user approval

### Requirement: Graceful failure outside git repo
All git tools SHALL fail gracefully when called outside a git repository.

#### Scenario: Not a git repo
- **WHEN** the agent calls `git_status` in a non-git directory
- **THEN** the tool returns an error message "not a git repository"
