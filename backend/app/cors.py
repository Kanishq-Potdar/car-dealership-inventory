"""Explicit browser-origin allowlist; authentication still runs on every API request."""
from urllib.parse import urlsplit

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import field_validator
from pydantic_settings import BaseSettings
from starlette.types import ASGIApp, Receive, Scope, Send

from app.database import DatabaseSettings


class CorsSettings(BaseSettings):
    model_config = DatabaseSettings.model_config
    cors_allowed_origins: list[str] = []

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, origins):
        result = []
        for origin in origins:
            origin = origin.strip()
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                    or "*" in origin or parsed.username is not None or parsed.password is not None
                    or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                    or "?" in origin or "#" in origin or any(char.isspace() for char in origin)):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without credentials or paths")
            # Validate the port as well; malformed configuration must fail at startup.
            parsed.port
            result.append(origin.rstrip("/"))
        return result


class _UnhandledExceptionMiddleware:
    """Catch unhandled exceptions and return a generic 500 response.

    This middleware must sit *inside* CORSMiddleware in the ASGI stack so
    that the CORS ``send`` wrapper can inject the ``Access-Control-Allow-Origin``
    header before the 500 response is delivered to the browser.  Starlette's
    built-in ``ServerErrorMiddleware`` is placed *outside* every user-added
    middleware, so any exception that reaches it bypasses CORS header injection.
    By catching the exception here, the JSONResponse flows through the
    CORSMiddleware ``send`` wrapper and receives the correct CORS headers.

    The response body is intentionally generic to avoid leaking server internals.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception:
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
            await response(scope, receive, send)


def configure_cors(app) -> None:
    # _UnhandledExceptionMiddleware is registered first so that Starlette places
    # it *inside* CORSMiddleware when it builds the middleware stack (Starlette
    # reverses the user_middleware list during build).  The resulting order is:
    #   ServerErrorMiddleware → CORSMiddleware → _UnhandledExceptionMiddleware → …
    # which ensures the 500 response flows through the CORS send wrapper.
    app.add_middleware(_UnhandledExceptionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CorsSettings().cors_allowed_origins,
        allow_credentials=False,  # JWTs use Authorization, not cross-site cookies.
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["WWW-Authenticate"],
    )
