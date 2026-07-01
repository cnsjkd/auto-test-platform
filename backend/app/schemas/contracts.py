from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.errors import AppException, PARAM_ERROR, PIXEL_AUDIT_MISSING


class Action(StrEnum):
    semantic_click = "semantic_click"
    semantic_input = "semantic_input"
    semantic_assert = "semantic_assert"
    swipe = "swipe"
    keyevent = "keyevent"
    open_notification = "open_notification"
    open_quick_settings = "open_quick_settings"
    shell = "shell"
    pixel_tap = "pixel_tap"
    pixel_swipe = "pixel_swipe"
    screenshot = "screenshot"
    dump_hierarchy = "dump_hierarchy"
    logcat_snapshot = "logcat_snapshot"


PIXEL_ACTIONS = {Action.pixel_tap.value, Action.pixel_swipe.value}
SEMANTIC_ACTIONS = {Action.semantic_click.value, Action.semantic_input.value, Action.semantic_assert.value}
REQUIRED_PIXEL_FIELDS = [
    "pixelFallback",
    "fallbackReason",
    "riskNote",
    "improvementSuggestion",
    "x",
    "y",
    "screenWidth",
    "screenHeight",
    "orientation",
]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DeviceScanRequest(StrictBaseModel):
    refresh: bool = True


class NameRequest(StrictBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)


class LogcatSnapshotRequest(StrictBaseModel):
    durationSec: int = Field(default=3, ge=1, le=60)
    buffers: list[str] = Field(default_factory=lambda: ["main", "system", "crash"])


class DeviceCommandRequest(StrictBaseModel):
    action: Action
    selector: dict[str, Any] | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    timeoutSec: int = Field(default=30, ge=1, le=300)
    pixelFallback: bool | None = None
    fallbackReason: str | None = Field(default=None, min_length=1)
    riskNote: str | None = Field(default=None, min_length=1)
    improvementSuggestion: str | None = Field(default=None, min_length=1)
    x: int | None = None
    y: int | None = None
    screenWidth: int | None = None
    screenHeight: int | None = None
    orientation: Literal["portrait", "landscape"] | None = None

    @model_validator(mode="after")
    def validate_action_contract(self) -> "DeviceCommandRequest":
        action_value = self.action.value
        if action_value in SEMANTIC_ACTIONS and not self.selector:
            raise ValueError("selector is required for semantic actions")
        if action_value == Action.semantic_input.value and not str(self.params.get("text", "")):
            raise ValueError("params.text is required for semantic_input")
        if action_value == Action.keyevent.value and not str(self.params.get("key", "")):
            raise ValueError("params.key is required for keyevent")
        if action_value in PIXEL_ACTIONS:
            validate_pixel_audit_payload(self.model_dump(mode="python", by_alias=True))
        return self


class TestCaseCreateRequest(StrictBaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="manual", min_length=1, max_length=64)
    priority: str = Field(default="P2", min_length=1, max_length=32)
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="enabled", min_length=1, max_length=32)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    description: str | None = None

    @model_validator(mode="after")
    def validate_steps(self) -> "TestCaseCreateRequest":
        derive_pixel_fallback_stats(self.steps)
        return self


class RunCreateRequest(StrictBaseModel):
    deviceId: int | None = None
    caseIds: list[int] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class SmokeSuiteRunRequest(StrictBaseModel):
    deviceId: int
    riskAccepted: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class RunCancelRequest(StrictBaseModel):
    reason: str = Field(min_length=1, max_length=500)


def validate_pixel_audit_payload(payload: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_PIXEL_FIELDS if payload.get(field) in (None, "")]
    if missing or payload.get("pixelFallback") is not True:
        if "pixelFallback" not in missing and payload.get("pixelFallback") is not True:
            missing.insert(0, "pixelFallback")
        raise AppException(
            code=PIXEL_AUDIT_MISSING,
            message=f"像素兜底审计字段缺失: {', '.join(missing)}",
            status_code=400,
            details={"missing": missing},
        )
    screen_width = payload.get("screenWidth")
    screen_height = payload.get("screenHeight")
    x = payload.get("x")
    y = payload.get("y")
    if not isinstance(screen_width, int) or not isinstance(screen_height, int) or screen_width <= 0 or screen_height <= 0:
        raise AppException(PARAM_ERROR, "screenWidth/screenHeight must be positive integers", 400)
    if not isinstance(x, int) or not isinstance(y, int) or x < 0 or y < 0 or x >= screen_width or y >= screen_height:
        raise AppException(PARAM_ERROR, "x/y must be within screen bounds", 400)
    if payload.get("orientation") not in {"portrait", "landscape"}:
        raise AppException(PARAM_ERROR, "orientation must be portrait or landscape", 400)


def derive_pixel_fallback_stats(steps: list[dict[str, Any]]) -> tuple[bool, int]:
    count = 0
    for index, step in enumerate(steps):
        if "commandType" in step:
            raise ValueError("commandType is not allowed; use action")
        action = step.get("action")
        if action is None:
            raise ValueError(f"steps[{index}].action is required")
        if action not in {item.value for item in Action}:
            raise ValueError(f"steps[{index}].action is not supported")
        if action in PIXEL_ACTIONS:
            validate_pixel_audit_payload(step)
            count += 1
    return count > 0, count
