# main.py — MCP server entry point
# Transport: HTTP+SSE (see README). Lab 06 n8n demo uses Streamable HTTP separately.
import logging
import os
from contextvars import ContextVar

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
import uvicorn

from tools import register_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXPECTED_API_KEY = os.environ.get("MCP_API_KEY")
if not EXPECTED_API_KEY:
    raise RuntimeError("MCP_API_KEY environment variable not set — cannot start server")

# Per-request session identity for audit + rate limiting
session_id_var: ContextVar[str] = ContextVar("session_id", default="anonymous")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Health endpoint is unauthenticated (required for k8s probes)
        if request.url.path == "/health":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if api_key != EXPECTED_API_KEY:
            return JSONResponse({"error": "Unauthorised"}, status_code=401)

        # Prefer explicit session header; fall back to API key suffix for multi-tenant demos
        session_id = request.headers.get("X-Session-Id") or f"key-{(api_key or '')[-8:]}"
        token = session_id_var.set(session_id)
        try:
            return await call_next(request)
        finally:
            session_id_var.reset(token)


server = Server("platform-mcp")
register_tools(server, session_id_var)

transport = SseServerTransport("/messages")


async def handle_sse(request):
    async with transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )


async def health(request):
    return Response(content="ok", status_code=200)


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/health", endpoint=health),
    ],
    middleware=[Middleware(APIKeyMiddleware)],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MCP_PORT", 8080)))
