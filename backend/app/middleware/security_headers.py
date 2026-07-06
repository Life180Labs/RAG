"""Standard security response headers (HSTS + related).

Browsers only ever act on `Strict-Transport-Security` when a response was
received over an actual HTTPS connection, so sending it unconditionally
(including over plain HTTP in local dev) is harmless — it's simply ignored
there, the same reasoning frameworks like Django's SecurityMiddleware rely on.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
