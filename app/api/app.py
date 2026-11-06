"""FastAPI application factory for SMOXI HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.deps import bind_container
from app.api.errors import error_body
from app.api.v1.router import router as v1_router
from app.config.settings import get_settings
from app.core.container import ServiceContainer


def create_api_app(container: ServiceContainer | None = None) -> FastAPI:
    """Build versioned REST API sharing desktop services."""
    settings = get_settings()
    resolved = container or ServiceContainer.create()
    bind_container(resolved)

    app = FastAPI(
        title="SMOXI Service API",
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        _ = request
        return error_body(
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
            status_code=422,
        )

    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
    return app
