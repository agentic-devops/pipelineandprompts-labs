# tools.py — MCP tool definitions and dispatch
# Tool descriptions are read by the LLM. Write them precisely.
from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import logging

from k8s_client import KubernetesClient
from audit import log_tool_call
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
k8s = KubernetesClient(in_cluster=True)
limiter = RateLimiter(calls_per_minute=60)


def register_tools(server: Server):

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="get_pod_status",
                description=(
                    "Get the current status of a specific Kubernetes pod, including phase, "
                    "readiness conditions, container states, and restart counts. "
                    "Use this when investigating why a specific pod is unhealthy or not ready."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "The Kubernetes namespace the pod is in"
                        },
                        "pod_name": {
                            "type": "string",
                            "description": "The exact name of the pod"
                        }
                    },
                    "required": ["namespace", "pod_name"]
                }
            ),
            Tool(
                name="list_failing_pods",
                description=(
                    "List all pods that are not in Running or Succeeded state across the cluster "
                    "or within a specific namespace. Use this as a first step when an incident "
                    "is reported and you need to identify which pods are affected."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Optional: filter to a specific namespace"
                        }
                    }
                }
            ),
            Tool(
                name="get_recent_events",
                description=(
                    "Retrieve recent Kubernetes events for a namespace, ordered by most recent first. "
                    "Events capture warnings, errors, and state changes. Use this to understand "
                    "what happened in the cluster leading up to an issue."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "The namespace to retrieve events from"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to return (default 20)",
                            "default": 20
                        }
                    },
                    "required": ["namespace"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        session_id = "default"  # AUTHOR: replace with real session identity from request context

        # Rate check before audit — fail fast, don't log rejected sessions
        if not limiter.is_allowed(session_id):
            return [TextContent(type="text", text="Rate limit exceeded for this session.")]

        log_tool_call(tool=name, inputs=arguments, session_id=session_id)

        try:
            if name == "get_pod_status":
                result = k8s.get_pod_status(
                    namespace=arguments["namespace"],
                    pod_name=arguments["pod_name"]
                )
            elif name == "list_failing_pods":
                result = k8s.list_failing_pods(
                    namespace=arguments.get("namespace")
                )
            elif name == "get_recent_events":
                result = k8s.get_recent_events(
                    namespace=arguments["namespace"],
                    limit=arguments.get("limit", 20)
                )
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Tool {name} failed: {str(e)}")
            return [TextContent(type="text", text=f"Tool execution failed: {str(e)}")]
