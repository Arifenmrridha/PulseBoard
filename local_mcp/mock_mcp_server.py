"""
Local Mock MCP Server — fully in-process, zero network/subprocess dependencies.

This module simulates the Model Context Protocol (MCP) tool-calling interface
entirely in memory. It replaces stdio subprocess MCP servers so the full
PulseBoard pipeline works completely offline without any external API keys,
Node.js runtime, or internet access.

Supported simulated MCP servers/tools:
  - slack   / post_message    → writes formatted report to local Slack log file
  - slack   / list_channels   → returns a mock channel list
  - sheets  / append_row      → appends a CSV row to a local audit sheet file
  - sheets  / read_rows       → reads rows from local audit sheet file

All tool responses follow the same dict contract as a real MCP ClientSession
call_tool response, so callers need no code changes to switch.
"""

import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PulseBoard.LocalMCP")

# ─────────────────────────────────────────────
# Local filesystem paths for simulated storage
# ─────────────────────────────────────────────
_SLACK_LOG_FILE = os.path.join("tools", "mock_slack_messages.jsonl")
_SHEETS_AUDIT_FILE = os.path.join("tools", "delivery_audit_log.csv")


# ═════════════════════════════════════════════
#  Core dispatcher
# ═════════════════════════════════════════════

async def call_tool(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Entry-point for all local MCP tool calls. Dispatches to the appropriate
    simulated tool handler based on server_name and tool_name.

    Args:
        server_name: The MCP server identifier (e.g. "slack", "sheets").
        tool_name:   The tool to invoke on that server (e.g. "post_message").
        arguments:   Key-value arguments passed to the tool.

    Returns:
        A dict with at least {"status": "success"|"error", "content": ...}.
    """
    key = f"{server_name}/{tool_name}"
    logger.debug("LocalMCP call: %s  args=%s", key, list(arguments.keys()))

    dispatch = {
        "slack/post_message": _slack_post_message,
        "slack/list_channels": _slack_list_channels,
        "sheets/append_row":  _sheets_append_row,
        "sheets/read_rows":   _sheets_read_rows,
    }

    handler = dispatch.get(key)
    if handler is None:
        msg = f"LocalMCP: unknown tool '{key}'. Available: {list(dispatch)}"
        logger.warning(msg)
        return {"status": "error", "content": msg}

    try:
        return await handler(arguments)
    except Exception as exc:
        logger.error("LocalMCP tool '%s' raised: %s", key, exc)
        return {"status": "error", "content": str(exc)}


# ═════════════════════════════════════════════
#  Slack simulation handlers
# ═════════════════════════════════════════════

async def _slack_post_message(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates posting a Slack message by appending it to a local JSONL log.
    In production this would call the real Slack MCP server's post_message tool.
    """
    channel = args.get("channel", "#general")
    text    = args.get("text", "")
    blocks  = args.get("blocks", [])

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "channel":   channel,
        "text":      text,
        "blocks":    blocks,
    }

    os.makedirs(os.path.dirname(_SLACK_LOG_FILE) or ".", exist_ok=True)
    with open(_SLACK_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    msg = (f"[LocalMCP/Slack] Message posted to {channel}. "
           f"Logged to {_SLACK_LOG_FILE}")
    logger.info(msg)
    return {"status": "success", "content": msg}


async def _slack_list_channels(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a mock list of Slack channels."""
    channels = [
        {"id": "C001", "name": "alerts",     "is_private": False},
        {"id": "C002", "name": "executive",  "is_private": True},
        {"id": "C003", "name": "engineering","is_private": False},
        {"id": "C004", "name": "general",    "is_private": False},
    ]
    return {"status": "success", "content": channels}


# ═════════════════════════════════════════════
#  Google Sheets simulation handlers
# ═════════════════════════════════════════════

async def _sheets_append_row(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates appending a row to a Google Sheet by writing to the local audit CSV.
    Expected args: {"row": [...values...], "headers": [...optional...]}
    """
    row     = args.get("row", [])
    headers = args.get("headers", [])

    os.makedirs(os.path.dirname(_SHEETS_AUDIT_FILE) or ".", exist_ok=True)
    file_exists = os.path.exists(_SHEETS_AUDIT_FILE)

    with open(_SHEETS_AUDIT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists and headers:
            writer.writerow(headers)
        writer.writerow(row)

    msg = f"[LocalMCP/Sheets] Row appended to {_SHEETS_AUDIT_FILE}"
    logger.info(msg)
    return {"status": "success", "content": msg}


async def _sheets_read_rows(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates reading rows from a Google Sheet by reading the local audit CSV.
    Returns up to `limit` rows (default 100).
    """
    limit = int(args.get("limit", 100))

    if not os.path.exists(_SHEETS_AUDIT_FILE):
        return {"status": "success", "content": []}

    rows: List[List[str]] = []
    with open(_SHEETS_AUDIT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            rows.append(row)

    return {"status": "success", "content": rows}
