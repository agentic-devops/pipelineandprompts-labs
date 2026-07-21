"""
Demo MCP server standing in for openshift-mcp-sre-tools.

Implements the same four read-only tool names used in the article
(get_cluster_health, get_failing_pods, get_events, diagnose_crashloop)
but returns canned data instead of querying a real cluster. This is a
real MCP server over Streamable HTTP transport — n8n's MCP Client node
connects to it exactly as it would connect to the production server.

Transport note: this server uses Streamable HTTP, not SSE. The MCP spec
deprecated the HTTP+SSE transport in the 2025-03-26 revision in favor of
Streamable HTTP — SSE still works for backward compatibility, but new
servers shouldn't be built on it. If you're integrating against an
existing MCP server that only speaks SSE (older deployments still do),
swap the transport back with `mcp.run(transport="sse")` and adjust the
n8n credential accordingly.

To force the "full alert" branch of the workflow instead of the
"auto-resolved" branch, edit FAILING_PODS below to a non-empty list.

Tool schemas: every parameter below uses Annotated + Field to declare
type, bounds, and whether it's required. FastMCP turns these into the
JSON Schema advertised to the calling agent, so the agent can't invent
an out-of-range `limit` or omit a required `pod_name` — the MCP server
rejects the call before it reaches the handler. This is the schema
enforcement layer the article's determinism warning calls for.
"""
from datetime import datetime, timezone
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("openshift-sre-diagnostics-demo", host="0.0.0.0", port=8080)

# Edit this to change which branch the demo workflow takes.
FAILING_PODS = [
    {"name": "payment-api-7d4b8c6f5-x2k9m", "phase": "CrashLoopBackOff", "restarts": 5},
]

RECENT_EVENTS = [
    {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container"},
    {"type": "Warning", "reason": "Unhealthy", "message": "Readiness probe failed: HTTP probe failed with statuscode: 503"},
]


@mcp.tool()
def get_cluster_health(
    cluster: Annotated[
        str, Field(description="Cluster name to check", pattern=r"^[a-z0-9-]+$", default="default")
    ] = "default",
) -> dict:
    """Return overall cluster health summary (canned data)."""
    return {
        "cluster": cluster,
        "status": "degraded" if FAILING_PODS else "healthy",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_failing_pods(
    namespace: Annotated[
        str, Field(description="Kubernetes namespace to inspect", pattern=r"^[a-z0-9-]+$", default="production")
    ] = "production",
) -> dict:
    """Return pods currently failing or crash-looping in a namespace (canned data)."""
    return {
        "namespace": namespace,
        "failing_pods": FAILING_PODS,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_events(
    namespace: Annotated[
        str, Field(description="Kubernetes namespace to inspect", pattern=r"^[a-z0-9-]+$", default="production")
    ] = "production",
    limit: Annotated[
        int, Field(description="Max events to return", ge=1, le=100, default=50)
    ] = 50,
) -> dict:
    """Return recent Warning/Normal events for a namespace (canned data)."""
    events = RECENT_EVENTS if FAILING_PODS else []
    return {
        "namespace": namespace,
        "recent_events": events[:limit],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def diagnose_crashloop(
    pod_name: Annotated[
        str, Field(description="Exact pod name to diagnose (required — not inferred)", min_length=1)
    ],
    namespace: Annotated[
        str, Field(description="Kubernetes namespace to inspect", pattern=r"^[a-z0-9-]+$", default="production")
    ] = "production",
) -> dict:
    """Return a canned crash-loop diagnosis for a given pod (canned data)."""
    return {
        "pod_name": pod_name,
        "namespace": namespace,
        "likely_cause": "Readiness probe failing after container start — check startup dependency on downstream service.",
        "confidence": "low (demo diagnostic — not a real analysis)",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
