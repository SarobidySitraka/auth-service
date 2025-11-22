import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = settings.RATE_LIMIT_PER_MINUTE, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        now = time.time()

        # Nettoyer les anciennes requêtes
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.period
        ]

        # Vérifier la limite
        if len(self.requests[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Trop de requêtes. Réessayez plus tard."}
            )

        self.requests[client_ip].append(now)
        return await call_next(request)