## ADDED Requirements

### Requirement: Fetch URL content as text
The system SHALL provide a `web_fetch` tool that retrieves the content of a URL and returns it as plain text.

#### Scenario: Fetch a text page
- **WHEN** the agent calls `web_fetch` with `url="https://example.com"`
- **THEN** the tool returns the page content as text

#### Scenario: Fetch returns HTML stripped to text
- **WHEN** the agent calls `web_fetch` on an HTML page
- **THEN** the tool strips HTML tags and returns readable text content

### Requirement: Size and timeout limits
The web_fetch tool SHALL cap response body at 50KB and enforce a 15-second timeout.

#### Scenario: Large page truncated
- **WHEN** the agent calls `web_fetch` on a page larger than 50KB
- **THEN** the tool returns the first 50KB with a truncation notice

#### Scenario: Slow page times out
- **WHEN** the agent calls `web_fetch` on a URL that takes >15 seconds to respond
- **THEN** the tool returns a timeout error

### Requirement: Only HTTP/HTTPS URLs
The web_fetch tool SHALL only accept `http://` and `https://` URLs.

#### Scenario: Reject non-HTTP URL
- **WHEN** the agent calls `web_fetch` with `url="file:///etc/passwd"`
- **THEN** the tool raises a ValueError rejecting the URL scheme

### Requirement: Risk level is medium
The web_fetch tool SHALL have risk_level `medium` since it makes external network requests.

#### Scenario: Runs under allow_all policy
- **WHEN** the agent calls `web_fetch` under `allow_all` permission policy
- **THEN** the tool executes without requiring user approval
