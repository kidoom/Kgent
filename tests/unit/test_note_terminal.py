"""Tests for E5: NoteTool + TerminalTool."""

import os
import tempfile

import pytest

from kagent.tools.note_tool import NoteTool
from kagent.tools.terminal_tool import TerminalTool


# ── NoteTool ───────────────────────────────────────────────────────

class TestNoteTool:
    def test_create_and_read(self):
        """Create a note then read it back."""
        tool = NoteTool()
        r = tool.run({"action": "create", "title": "Test", "content": "Hello"})
        assert r.success is True
        note_id = r.metadata["id"]

        r = tool.run({"action": "read", "id": note_id})
        assert r.success is True
        assert "Hello" in r.content

    def test_update(self):
        """Update a note's content."""
        tool = NoteTool()
        r = tool.run({"action": "create", "title": "T", "content": "old"})
        note_id = r.metadata["id"]

        r = tool.run({"action": "update", "id": note_id, "content": "new"})
        assert r.success is True

        r = tool.run({"action": "read", "id": note_id})
        assert "new" in r.content

    def test_delete(self):
        """Delete a note."""
        tool = NoteTool()
        r = tool.run({"action": "create", "title": "T", "content": "x"})
        note_id = r.metadata["id"]

        r = tool.run({"action": "delete", "id": note_id})
        assert r.success is True

        r = tool.run({"action": "read", "id": note_id})
        assert r.success is False

    def test_list(self):
        """List all notes."""
        tool = NoteTool()
        tool.run({"action": "create", "title": "A", "content": "a"})
        tool.run({"action": "create", "title": "B", "content": "b"})

        r = tool.run({"action": "list"})
        assert r.success is True
        assert "A" in r.content
        assert "B" in r.content

    def test_list_empty(self):
        """List when no notes exist."""
        tool = NoteTool()
        r = tool.run({"action": "list"})
        assert r.success is True
        assert "没有" in r.content

    def test_read_nonexistent(self):
        """Read a nonexistent note returns error."""
        tool = NoteTool()
        r = tool.run({"action": "read", "id": "999"})
        assert r.success is False

    def test_invalid_action(self):
        """Unknown action returns error."""
        tool = NoteTool()
        r = tool.run({"action": "export"})
        assert r.success is False


# ── TerminalTool ────────────────────────────────────────────────────

class TestTerminalTool:
    def test_list_directory(self):
        """List files in a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            open(os.path.join(tmpdir, "a.txt"), "w").close()
            open(os.path.join(tmpdir, "b.txt"), "w").close()
            os.mkdir(os.path.join(tmpdir, "subdir"))

            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "list", "path": "."})
            assert r.success is True
            assert "a.txt" in r.content
            assert "b.txt" in r.content
            assert "subdir" in r.content

    def test_read_file(self):
        """Read a text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            with open(path, "w") as f:
                f.write("Hello, World!")

            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "read", "path": "test.txt"})
            assert r.success is True
            assert "Hello, World!" in r.content

    def test_read_nonexistent(self):
        """Read a nonexistent file returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "read", "path": "nope.txt"})
            assert r.success is False

    def test_path_escape_blocked(self):
        """Accessing files outside root_dir is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "read", "path": "../../../etc/passwd"})
            assert r.success is False
            assert "越界" in r.content or "error" in r.content.lower()

    def test_read_too_large(self):
        """Files over 10KB are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "big.txt")
            with open(path, "w") as f:
                f.write("x" * 20000)

            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "read", "path": "big.txt"})
            assert r.success is False
            assert "过大" in r.content

    def test_invalid_action(self):
        """Unknown action returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = TerminalTool(root_dir=tmpdir)
            r = tool.run({"action": "write"})
            assert r.success is False
