## ADDED Requirements

### Requirement: Execute shell commands
The system SHALL provide a `bash` tool that executes an arbitrary shell command and returns its combined stdout and stderr output.

#### Scenario: Simple command
- **WHEN** the agent calls `bash` with `command="echo hello"`
- **THEN** the tool returns `hello\n`

#### Scenario: Command with stderr
- **WHEN** the agent calls `bash` with a command that writes to stderr
- **THEN** the tool returns combined stdout and stderr output

#### Scenario: Command failure
- **WHEN** the agent calls `bash` with a command that exits with non-zero code
- **THEN** the tool returns the output and includes the exit code in the result

### Requirement: Timeout protection
The bash tool SHALL enforce a configurable timeout (default 30 seconds) and kill the process if exceeded.

#### Scenario: Command exceeds timeout
- **WHEN** the agent calls `bash` with `command="sleep 60"` and default timeout
- **THEN** the tool kills the process and returns a timeout error message

#### Scenario: Custom timeout
- **WHEN** the agent calls `bash` with `command="pytest"` and `timeout=120`
- **THEN** the tool allows up to 120 seconds before timing out

### Requirement: Risk level is high
The bash tool SHALL have risk_level `high` since it can execute arbitrary commands.

#### Scenario: Requires approval in risk_based mode
- **WHEN** the agent calls `bash` under `risk_based` permission policy
- **THEN** the tool requires explicit user approval before execution

#### Scenario: Blocked in restricted policy
- **WHEN** the agent calls `bash` and user denies the permission request
- **THEN** the tool returns a permission denied error
