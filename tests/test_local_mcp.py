"""
Tests for local_mcp.mock_mcp_server — the in-process offline MCP simulation.
"""
import asyncio
import json
import os
import pytest

# ensure project root is on path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from local_mcp.mock_mcp_server import call_tool, _SLACK_LOG_FILE, _SHEETS_AUDIT_FILE


# ── helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    """Synchronous helper to drive async tests without pytest-asyncio dependency."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Slack tests ────────────────────────────────────────────────────────────────

def test_slack_post_message_creates_log(tmp_path, monkeypatch):
    """Posting a Slack message must create / append to the local JSONL log."""
    log_path = str(tmp_path / "slack.jsonl")
    monkeypatch.setattr("local_mcp.mock_mcp_server._SLACK_LOG_FILE", log_path)

    result = run(call_tool("slack", "post_message", {
        "channel": "#test",
        "text":    "Hello from pytest",
        "blocks":  [],
    }))

    assert result["status"] == "success"
    assert os.path.exists(log_path)

    with open(log_path, encoding="utf-8") as f:
        record = json.loads(f.readline())
    assert record["channel"] == "#test"
    assert record["text"]    == "Hello from pytest"


def test_slack_list_channels():
    """list_channels must return at least one channel entry."""
    result = run(call_tool("slack", "list_channels", {}))
    assert result["status"] == "success"
    channels = result["content"]
    assert isinstance(channels, list)
    assert len(channels) > 0
    # each channel has 'id' and 'name'
    assert all("id" in c and "name" in c for c in channels)


def test_unknown_tool_returns_error():
    """Calling a tool that doesn't exist must return status=error."""
    result = run(call_tool("slack", "nonexistent_tool", {}))
    assert result["status"] == "error"


def test_unknown_server_returns_error():
    """Calling an unknown server must return status=error."""
    result = run(call_tool("github", "create_issue", {"title": "x"}))
    assert result["status"] == "error"


# ── Sheets tests ───────────────────────────────────────────────────────────────

def test_sheets_append_and_read(tmp_path, monkeypatch):
    """Appending a row then reading it back must round-trip correctly."""
    csv_path = str(tmp_path / "audit.csv")
    monkeypatch.setattr("local_mcp.mock_mcp_server._SHEETS_AUDIT_FILE", csv_path)

    headers = ["timestamp", "recipient", "role", "status", "kpis"]
    row     = ["2026-07-01 00:00:00", "exec@co.com", "Executive", "ok", "revenue"]

    append_result = run(call_tool("sheets", "append_row", {
        "headers": headers,
        "row":     row,
    }))
    assert append_result["status"] == "success"

    read_result = run(call_tool("sheets", "read_rows", {"limit": 10}))
    assert read_result["status"] == "success"
    rows = read_result["content"]
    assert rows[0] == headers
    assert rows[1] == row
