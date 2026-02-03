"""
Rate Limiting Configuration

Uses slowapi to implement rate limiting for API endpoints.
Protects against abuse and ensures fair usage.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.config import settings


def get_real_client_ip(request: Request) -> str:
    """
    Get the real client IP address, handling proxies.

    Checks X-Forwarded-For header first (for reverse proxies like Railway/Vercel),
    then falls back to the direct client address.
    """
    # Check for forwarded header (common with reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2
        # The first one is the original client
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client address
    return get_remote_address(request)


# Create the limiter instance
# Uses in-memory storage by default (suitable for single-instance deployments)
# For multi-instance deployments, configure Redis storage
limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns a user-friendly JSON response.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down and try again later.",
            "retry_after": exc.detail,
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
        },
    )


def setup_rate_limiting(app):
    """
    Configure rate limiting for a FastAPI application.

    Call this in main.py to set up the middleware and exception handler.
    """
    if not settings.rate_limit_enabled:
        return

    # Add the limiter to app state (required by slowapi)
    app.state.limiter = limiter

    # Add the middleware
    app.add_middleware(SlowAPIMiddleware)

    # Add custom exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
