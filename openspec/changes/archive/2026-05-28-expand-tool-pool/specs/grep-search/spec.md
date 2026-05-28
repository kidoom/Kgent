## ADDED Requirements

### Requirement: Search file contents by regex pattern
The system SHALL provide a `grep` tool that searches file contents within the project directory using a Python regular expression pattern. The tool SHALL return matching lines with file paths and line numbers.

#### Scenario: Simple text match
- **WHEN** the agent calls `grep` with `pattern="TODO"` and `path="backend"`
- **THEN** the tool returns all lines containing "TODO" under `backend/`, formatted as `filepath:linenum: line_content`

#### Scenario: Regex pattern match
- **WHEN** the agent calls `grep` with `pattern="def\s+\w+"` and `path="backend/app/tools"`
- **THEN** the tool returns all lines matching the regex under the specified path

#### Scenario: No matches
- **WHEN** the agent calls `grep` with a pattern that matches nothing
- **THEN** the tool returns the string `<no matches>`

#### Scenario: Path safety enforcement
- **WHEN** the agent calls `grep` with `path="../../etc"`
- **THEN** the tool raises a ValueError rejecting the path

### Requirement: Configurable search parameters
The grep tool SHALL support optional `glob` parameter to filter by file extension, and `max_results` parameter to limit output size.

#### Scenario: Filter by file extension
- **WHEN** the agent calls `grep` with `pattern="import"` and `glob="*.py"`
- **THEN** the tool only searches `.py` files

#### Scenario: Limit results
- **WHEN** the agent calls `grep` with `max_results=20` and there are 100 matches
- **THEN** the tool returns only the first 20 matches

### Requirement: Risk level is low
The grep tool SHALL have risk_level `low` since it is read-only.

#### Scenario: Runs without permission prompt
- **WHEN** the agent calls `grep` under `risk_based` permission policy
- **THEN** the tool executes without requiring user approval
