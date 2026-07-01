from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import SUCCESS


def envelope(data: Any | None = None, message: str = "", code: int = SUCCESS) -> dict[str, Any]:
    return {"code": code, "data": data if data is not None else {}, "message": message}


def json_envelope(
    request: Request | None,
    data: Any | None = None,
    message: str = "",
    code: int = SUCCESS,
    status_code: int = 200,
) -> JSONResponse:
    body = envelope(data=data, message=message, code=code)
    if request is not None and hasattr(request.state, "request_id"):
        body["requestId"] = request.state.request_id
    return JSONResponse(status_code=status_code, content=body)
