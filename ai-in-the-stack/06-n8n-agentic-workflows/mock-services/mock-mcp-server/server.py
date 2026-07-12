"""
Mock MCP server standing in for openshift-mcp-sre-tools.

Implements the same four read-only tool names used in the article
(get_cluster_health, get_failing_pods, get_events, diagnose_crashloop)
but returns canned data instead of querying a real cluster. This is a
real MCP server over SSE transport — n8n's MCP Client node connects to
it exactly as it would connect to the production server.

To force the "full alert" branch of the workflow instead of the
"auto-resolved" branch, edit FAILING_PODS below to a non-empty list.
"""
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("openshift-sre-diagnostics-mock", host="0.0.0.0", port=8080)

# Edit this to change which branch the demo workflow takes.
FAILING_PODS = [
    {"name": "payment-api-7d4b8c6f5-x2k9m", "phase": "CrashLoopBackOff", "restarts": 5},
]

RECENT_EVENTS = [
    {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container"},
    {"type": "Warning", "reason": "Unhealthy", "message": "Readiness probe failed: HTTP probe failed with statuscode: 503"},
]


@mcp.tool()
def get_cluster_health(cluster: str = "default") -> dict:
    """Return overall cluster health summary (mock data)."""
    return {
        "cluster": cluster,
        "status": "degraded" if FAILING_PODS else "healthy",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_failing_pods(namespace: str = "production") -> dict:
    """Return pods currently failing or crash-looping in a namespace (mock data)."""
    return {
        "namespace": namespace,
        "failing_pods": FAILING_PODS,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_events(namespace: str = "production") -> dict:
    """Return recent Warning/Normal events for a namespace (mock data)."""
    return {
        "namespace": namespace,
        "recent_events": RECENT_EVENTS if FAILING_PODS else [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def diagnose_crashloop(pod_name: str, namespace: str = "production") -> dict:
    """Return a canned crash-loop diagnosis for a given pod (mock data)."""
    return {
        "pod_name": pod_name,
        "namespace": namespace,
        "likely_cause": "Readiness probe failing after container start — check startup dependency on downstream service.",
        "confidence": "low (mock diagnostic — not a real analysis)",
    }


if __name__ == "__main__":
    mcp.run(transport="sse")
