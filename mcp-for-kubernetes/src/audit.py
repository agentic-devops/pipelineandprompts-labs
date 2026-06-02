# audit.py — structured audit logging for every MCP tool call
import logging
import json
from datetime import datetime, timezone

audit_logger = logging.getLogger("mcp.audit")


def log_tool_call(tool: str, inputs: dict, session_id: str = "unknown") -> None:
    """
    Emit a structured audit log entry for every tool invocation.
    In production, configure this logger to write to a dedicated audit sink.
    """
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "inputs": inputs,
        "session_id": session_id  # AUTHOR: replace default with real session identity
    }))
