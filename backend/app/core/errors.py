from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUCCESS = 0
PARAM_ERROR = 40001
NOT_FOUND = 40401
CONFLICT = 40901
RUN_NOT_EXECUTABLE = 42201
INTERNAL_ERROR = 50001
ADB_UNAVAILABLE = 51001
DEVICE_NOT_CONNECTED = 51002
DEVICE_UNAUTHORIZED = 51003
ADB_TIMEOUT = 51004
UI_AUTOMATION_FAILED = 52001
SEMANTIC_LOCATOR_FAILED = 52002
PIXEL_AUDIT_MISSING = 52003
REPORT_GENERATION_FAILED = 53001


@dataclass
class AppException(Exception):
    code: int
    message: str
    status_code: int = 400
    details: Any | None = None

    def __str__(self) -> str:
        return self.message


def status_for_error_code(code: int) -> int:
    if code == PARAM_ERROR:
        return 400
    if code == NOT_FOUND:
        return 404
    if code == CONFLICT:
        return 409
    if code == RUN_NOT_EXECUTABLE:
        return 422
    if code in (ADB_UNAVAILABLE, DEVICE_NOT_CONNECTED, DEVICE_UNAUTHORIZED, ADB_TIMEOUT):
        return 503
    if code in (UI_AUTOMATION_FAILED, SEMANTIC_LOCATOR_FAILED, PIXEL_AUDIT_MISSING):
        return 400
    return 500
