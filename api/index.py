"""Vercel serverless entry point: exposes the FastAPI app (ASGI) as the /api function.

Why the wrapper: depending on how Vercel forwards a rewritten request, the ASGI app can see the
original path (/api/health), the function path (/api/index.py) or even "/". vercel.json therefore
passes the original path as the query parameter `p`, and this wrapper rebuilds /api/<p> from it, so
routing works in every case. Visit /api/_debug to see exactly what the function received.
"""
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app as fastapi_app  # noqa: E402


class PathFix:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope["_orig_path"] = scope["path"]
            qs = scope.get("query_string", b"").decode()
            scope["_orig_query"] = qs
            pairs = parse_qsl(qs, keep_blank_values=True)
            p = [v for k, v in pairs if k == "p"]
            if p:  # path handed over by the vercel.json rewrite
                rest = [(k, v) for k, v in pairs if k != "p"]
                scope["path"] = "/api/" + p[0].lstrip("/")
                scope["raw_path"] = scope["path"].encode()
                scope["query_string"] = urlencode(rest).encode()
        await self.inner(scope, receive, send)


app = PathFix(fastapi_app)
