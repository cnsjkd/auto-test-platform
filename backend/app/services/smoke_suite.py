from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppException, RUN_NOT_EXECUTABLE
from app.models import TestCase, TestRun
from app.schemas.contracts import RunCreateRequest, SmokeSuiteRunRequest, TestCaseCreateRequest, derive_pixel_fallback_stats
from app.schemas.serializers import test_case_to_dict
from app.services.test_cases import TestCaseService
from app.services.test_runs import TestRunService

P0_SUITE_ID = "p0_smoke"
P0_SUITE_NAME = "A2 P0 冒烟套件"
P0_SUITE_TAG = "p0_smoke"
P0_SUITE_INTERNAL_TAG = f"suite:{P0_SUITE_ID}"
P0_SUITE_DESCRIPTION = "思必驰会议办公本 A2 Android 真机自动化平台 P0 冒烟用例库，覆盖 artifact 链路、基础安全动作和 Pixel Fallback 审计链路。"

ACCEPTANCE_NOTES = [
    "本套件包含 1 个 Pixel Fallback 审计链路验证用例。",
    "Pixel 坐标默认按 A2 1200x1920 portrait 设计，执行前需确认当前设备分辨率与方向一致。",
    "坐标点选择低风险左侧边缘空白区域，仅用于验证审计链路；稳定业务用例应优先补充 resource-id/content-desc 语义定位。",
]

COMMON_TAGS = ["a2", "p0", "smoke", P0_SUITE_TAG, P0_SUITE_INTERNAL_TAG]

P0_CASE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "slug": "screenshot-artifact",
        "name": "[P0 Smoke] 截图 artifact 链路",
        "description": "执行 screenshot，验证 PNG artifact 可采集、落库并进入运行报告。",
        "steps": [{"action": "screenshot", "timeoutSec": 10}],
    },
    {
        "slug": "dump-hierarchy-artifact",
        "name": "[P0 Smoke] UI XML artifact 链路",
        "description": "执行 dump_hierarchy，验证 UI XML artifact 可采集、落库并进入运行报告。",
        "steps": [{"action": "dump_hierarchy", "timeoutSec": 20}],
    },
    {
        "slug": "logcat-artifact",
        "name": "[P0 Smoke] logcat artifact 链路",
        "description": "执行 logcat_snapshot，验证 main/system/crash 日志 artifact 可采集、落库并进入运行报告。",
        "steps": [
            {
                "action": "logcat_snapshot",
                "params": {"durationSec": 3, "buffers": ["main", "system", "crash"]},
                "timeoutSec": 15,
            }
        ],
    },
    {
        "slug": "visible-notification-with-evidence",
        "name": "[P0 Smoke] 可见动作：通知栏展开并采证",
        "description": "从 HOME 开始展开通知栏，随后采集截图、UI XML 和 BACK 复位，用户可肉眼看到通知面板变化。",
        "steps": [
            {"action": "keyevent", "params": {"key": "HOME"}, "timeoutSec": 10},
            {"action": "open_notification", "timeoutSec": 10},
            {"action": "screenshot", "timeoutSec": 10},
            {"action": "dump_hierarchy", "timeoutSec": 20},
            {"action": "keyevent", "params": {"key": "BACK"}, "timeoutSec": 10},
        ],
    },
    {
        "slug": "visible-quick-settings-with-evidence",
        "name": "[P0 Smoke] 可见动作：快捷设置展开并采证",
        "description": "从 HOME 开始展开快捷设置，随后采集截图、UI XML 和 BACK 复位，用户可肉眼看到快捷设置面板变化。",
        "steps": [
            {"action": "keyevent", "params": {"key": "HOME"}, "timeoutSec": 10},
            {"action": "open_quick_settings", "timeoutSec": 10},
            {"action": "screenshot", "timeoutSec": 10},
            {"action": "dump_hierarchy", "timeoutSec": 20},
            {"action": "keyevent", "params": {"key": "BACK"}, "timeoutSec": 10},
        ],
    },
    {
        "slug": "visible-full-system-panel-flow",
        "name": "[P0 Smoke] 可见流程：HOME→通知栏→快捷设置→返回",
        "description": "连续执行 HOME、通知栏、快捷设置、BACK、BACK，并在关键节点截图采证，证明平台确实在操作真实 A2。",
        "steps": [
            {"action": "keyevent", "params": {"key": "HOME"}, "timeoutSec": 10},
            {"action": "screenshot", "timeoutSec": 10},
            {"action": "open_notification", "timeoutSec": 10},
            {"action": "screenshot", "timeoutSec": 10},
            {"action": "open_quick_settings", "timeoutSec": 10},
            {"action": "screenshot", "timeoutSec": 10},
            {"action": "keyevent", "params": {"key": "BACK"}, "timeoutSec": 10},
            {"action": "keyevent", "params": {"key": "BACK"}, "timeoutSec": 10},
            {"action": "logcat_snapshot", "params": {"durationSec": 3, "buffers": ["main", "system"]}, "timeoutSec": 15},
        ],
    },
    {
        "slug": "pixel-tap-audit",
        "name": "[P0 Smoke] Pixel Fallback 审计链路",
        "description": "执行低风险 pixel_tap，验证 Pixel Fallback 审计字段、截图前后证据和报告链路完整性。",
        "steps": [
            {
                "action": "pixel_tap",
                "timeoutSec": 10,
                "pixelFallback": True,
                "fallbackReason": "P0 冒烟验证 Pixel Fallback 审计链路，目标为 A2 1200x1920 portrait 左侧边缘空白点。",
                "x": 16,
                "y": 960,
                "screenWidth": 1200,
                "screenHeight": 1920,
                "orientation": "portrait",
                "riskNote": "坐标依赖当前 A2 分辨率与方向；点位位于左侧边缘空白区域，仅用于审计链路验证，页面布局变化仍可能导致轻微焦点变化。",
                "improvementSuggestion": "将审计占位坐标替换为稳定 resource-id/content-desc 或文本语义定位后再用于业务断言。",
            }
        ],
    },
]


class SmokeSuiteService:
    def __init__(self, test_case_service: TestCaseService | None = None, test_run_service: TestRunService | None = None) -> None:
        self.test_cases = test_case_service or TestCaseService()
        self.test_runs = test_run_service

    def ensure_p0_suite(self, db: Session) -> dict[str, Any]:
        cases = self.ensure_p0_cases(db)
        return self.serialize_p0_suite(cases)

    def get_p0_suite(self, db: Session) -> dict[str, Any]:
        return self.ensure_p0_suite(db)

    def create_p0_run(self, db: Session, payload: SmokeSuiteRunRequest, test_run_service: TestRunService | None = None) -> tuple[TestRun, dict[str, Any]]:
        cases = self.ensure_p0_cases(db)
        suite = self.serialize_p0_suite(cases)
        if suite["pixelFallbackCount"] > 0 and payload.riskAccepted is not True:
            raise AppException(
                RUN_NOT_EXECUTABLE,
                "riskAccepted=true is required before running a suite with Pixel Fallback audit cases",
                422,
                details={
                    "suiteId": P0_SUITE_ID,
                    "requiresRiskAcceptance": True,
                    "pixelFallbackCount": suite["pixelFallbackCount"],
                    "acceptanceNotes": ACCEPTANCE_NOTES,
                },
            )
        config = dict(payload.config or {})
        config.update(
            {
                "suiteId": P0_SUITE_ID,
                "suiteName": P0_SUITE_NAME,
                "suiteTag": P0_SUITE_TAG,
                "riskAccepted": payload.riskAccepted,
                "requiresRiskAcceptance": suite["requiresRiskAcceptance"],
                "acceptanceNotes": ACCEPTANCE_NOTES,
            }
        )
        runner = test_run_service or self.test_runs
        if runner is None:
            raise AppException(RUN_NOT_EXECUTABLE, "test run service is not configured", 422)
        run = runner.create_and_execute(
            db,
            RunCreateRequest(deviceId=payload.deviceId, caseIds=suite["caseIds"], config=config),
        )
        return run, suite

    def run_p0_suite(self, db: Session, payload: SmokeSuiteRunRequest) -> tuple[dict[str, Any], TestRun]:
        run, suite = self.create_p0_run(db, payload)
        return suite, run

    def run_payload(self, suite: dict[str, Any], run: TestRun) -> dict[str, Any]:
        from app.schemas.serializers import test_run_to_dict

        return {"suite": suite, "run": test_run_to_dict(run)}

    def ensure_p0_cases(self, db: Session) -> list[TestCase]:
        existing_cases = list(db.scalars(select(TestCase)).all())
        cases: list[TestCase] = []
        for definition in P0_CASE_DEFINITIONS:
            case = self._find_existing_case(existing_cases, definition)
            payload = self._case_payload(definition)
            if case is None:
                case = self.test_cases.create_case(db, TestCaseCreateRequest.model_validate(payload))
                existing_cases.append(case)
            else:
                self._sync_existing_case(case, payload)
            cases.append(case)
        db.flush()
        return cases

    def serialize_p0_suite(self, cases: list[TestCase]) -> dict[str, Any]:
        pixel_fallback_count = sum(int(case.pixel_fallback_count or 0) for case in cases)
        case_ids = [case.id for case in cases]
        return {
            "suite": {
                "id": P0_SUITE_ID,
                "name": P0_SUITE_NAME,
                "tag": P0_SUITE_TAG,
                "priority": "P0",
                "description": P0_SUITE_DESCRIPTION,
                "tags": COMMON_TAGS,
            },
            "ready": True,
            "cases": [test_case_to_dict(case) for case in cases],
            "caseIds": case_ids,
            "caseCount": len(cases),
            "pixelFallbackCount": pixel_fallback_count,
            "requiresRiskAcceptance": True,
            "acceptanceNotes": ACCEPTANCE_NOTES,
        }

    def _find_existing_case(self, cases: list[TestCase], definition: dict[str, Any]) -> TestCase | None:
        slug_tag = self._slug_tag(definition["slug"])
        for case in cases:
            tags = set(case.tags or [])
            if slug_tag in tags:
                return case
        for case in cases:
            if case.name == definition["name"]:
                return case
        return None

    def _case_payload(self, definition: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": definition["name"],
            "type": "smoke",
            "priority": "P0",
            "tags": [*COMMON_TAGS, self._slug_tag(definition["slug"])],
            "status": "enabled",
            "steps": deepcopy(definition["steps"]),
            "description": definition["description"],
        }

    def _sync_existing_case(self, case: TestCase, payload: dict[str, Any]) -> None:
        has_pixel_fallback, pixel_fallback_count = derive_pixel_fallback_stats(payload["steps"])
        case.name = payload["name"]
        case.type = payload["type"]
        case.priority = payload["priority"]
        case.tags = payload["tags"]
        case.status = payload["status"]
        case.steps = payload["steps"]
        case.description = payload["description"]
        case.has_pixel_fallback = has_pixel_fallback
        case.pixel_fallback_count = pixel_fallback_count

    def _slug_tag(self, slug: str) -> str:
        return f"{P0_SUITE_INTERNAL_TAG}:{slug}"
