"""Tolerant Markdown-section parser for subagent final answer text."""

from __future__ import annotations

import re

from app.runtime.subagent import SubagentPayload

# Canonical section names and the payload field they map to.
_SECTION_FIELD_MAP: dict[str, str] = {
    "summary": "summary",
    "findings": "findings",
    "files": "files",
    "actions": "actions",
    "risks": "risks",
    "next steps": "next_steps",
}

# Matches a Markdown heading (## or #) followed by the section name.
_HEADING_RE = re.compile(r"^#{1,2}\s+(.+?)\s*$", re.MULTILINE)


def parse_payload(text: str) -> SubagentPayload:
    """Parse Markdown-section final answer text into a SubagentPayload.

    Tolerant behaviour:
    - Accepts # or ## headings with flexible casing/whitespace.
    - Missing optional sections yield empty lists.
    - If no Summary section is found, the entire text is used as summary
      and raw fallback.
    """
    if not text or not text.strip():
        return SubagentPayload(summary="", raw=text or "")

    headings: list[tuple[str, int, int]] = []  # (normalised_name, start, end)
    for m in _HEADING_RE.finditer(text):
        name = m.group(1).strip().lower()
        headings.append((name, m.start(), m.end()))

    # No recognised headings at all — treat whole text as unstructured.
    if not headings:
        return SubagentPayload(summary=text.strip(), raw=text)

    # Build (name, body) pairs for each heading.
    sections: list[tuple[str, str]] = []
    for i, (name, _start, body_start) in enumerate(headings):
        body_end = headings[i + 1][1] if i + 1 < len(headings) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((name, body))

    # Map canonical names to their body text.
    section_bodies: dict[str, str] = {}
    for name, body in sections:
        canonical = _SECTION_FIELD_MAP.get(name)
        if canonical:
            # First occurrence wins.
            if canonical not in section_bodies:
                section_bodies[canonical] = body

    # If no Summary heading found, use pre-heading text or whole text as summary.
    if "summary" not in section_bodies:
        first_heading_start = headings[0][1]
        pre = text[:first_heading_start].strip()
        section_bodies["summary"] = pre if pre else text.strip()

    summary = section_bodies["summary"]
    findings = _parse_bullet_list(section_bodies.get("findings", ""))
    files = _parse_bullet_list(section_bodies.get("files", ""))
    actions = _parse_bullet_list(section_bodies.get("actions", ""))
    risks = _parse_bullet_list(section_bodies.get("risks", ""))
    next_steps = _parse_bullet_list(section_bodies.get("next_steps", ""))

    return SubagentPayload(
        summary=summary,
        findings=findings,
        files=files,
        actions=actions,
        risks=risks,
        next_steps=next_steps,
        raw=text,
    )


def _parse_bullet_list(text: str) -> list[str]:
    """Extract bullet items from a section body.

    Accepts ``-``, ``*``, or ``1.`` prefixes.  Falls back to non-empty
    lines if no bullet pattern is found.
    """
    if not text:
        return []

    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Strip bullet prefix.
        m = re.match(r"^[-*]\s+|^\d+\.\s+", stripped)
        if m:
            item = stripped[m.end():].strip()
        else:
            item = stripped
        if item:
            items.append(item)
    return items
