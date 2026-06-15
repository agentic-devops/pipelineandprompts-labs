# main.py — MCP server entry point
# Supports stdio (local) and HTTP/SSE (remote/cluster) transports.
import asyncio
import logging
import os
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
import uvicorn

from tools import register_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXPECTED_API_KEY = os.environ.get("MCP_API_KEY")
if not EXPECTED_API_KEY:
    raise RuntimeError("MCP_API_KEY environment variable not set — cannot start server")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Health endpoint is unauthenticated (required for k8s probes)
        if request.url.path == "/health":
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        if api_key != EXPECTED_API_KEY:
            return JSONResponse({"error": "Unauthorised"}, status_code=401)
        return await call_next(request)


server = Server("platform-mcp")
register_tools(server)

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
    middleware=[Middleware(APIKeyMiddleware)]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MCP_PORT", 8080)))
