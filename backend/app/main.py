from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router, run_events
from app.core.errors import AppException, INTERNAL_ERROR, NOT_FOUND, PARAM_ERROR, status_for_error_code
from app.core.middleware import RequestIdMiddleware
from app.core.response import json_envelope
from app.db.init_db import init_db

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="A2 Automation Test Platform", version="0.1.0")
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router, prefix="/api")
    app.add_api_websocket_route("/ws/test-runs/{run_id}/events", run_events)

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return json_envelope(
            request,
            data={"details": exc.details} if exc.details else {},
            message=exc.message,
            code=exc.code,
            status_code=exc.status_code or status_for_error_code(exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            cleaned = dict(error)
            if "ctx" in cleaned:
                cleaned["ctx"] = {key: str(value) for key, value in (cleaned.get("ctx") or {}).items()}
            errors.append(cleaned)
        return json_envelope(
            request,
            data={"errors": errors},
            message="参数错误",
            code=PARAM_ERROR,
            status_code=400,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = NOT_FOUND if exc.status_code == 404 else PARAM_ERROR
        return json_envelope(request, data={}, message=str(exc.detail), code=code, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logging.getLogger("a2.error").exception("unhandled exception")
        return json_envelope(
            request,
            data={},
            message="Internal server error",
            code=INTERNAL_ERROR,
            status_code=500,
        )

    return app


app = create_app()
