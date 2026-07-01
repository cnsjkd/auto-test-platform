from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.adb import AdbAdapter, orientation_from_size
from app.adapters.uiautomator import Uiautomator2Adapter
from app.core.errors import AppException, PARAM_ERROR, SEMANTIC_LOCATOR_FAILED, UI_AUTOMATION_FAILED
from app.models import DeviceCommand, LocatorFallback
from app.models.entities import now_utc
from app.schemas.contracts import Action, DeviceCommandRequest, PIXEL_ACTIONS, validate_pixel_audit_payload
from app.schemas.serializers import artifact_to_dict
from app.services.artifacts import ArtifactManager
from app.services.devices import DeviceService
from app.services.events import record_event


class CommandService:
    def __init__(
        self,
        adb: AdbAdapter | None = None,
        ui: Uiautomator2Adapter | None = None,
        artifact_manager: ArtifactManager | None = None,
        device_service: DeviceService | None = None,
    ) -> None:
        self.adb = adb or AdbAdapter()
        self.ui = ui or Uiautomator2Adapter()
        self.artifacts = artifact_manager or ArtifactManager()
        self.devices = device_service or DeviceService(self.adb)

    def execute(
        self,
        db: Session,
        *,
        device_id: int,
        request: DeviceCommandRequest,
        run_id: int | None = None,
        result_id: int | None = None,
        case_id: int | None = None,
        source: str = "api",
    ) -> tuple[DeviceCommand, list]:
        device = self.devices.ensure_online(db, device_id)
        started = now_utc()
        command = DeviceCommand(
            device_id=device_id,
            run_id=run_id,
            result_id=result_id,
            case_id=case_id,
            command_type=request.action.value,
            source=source,
            params=request.params,
            selector=request.selector or {},
            status="running",
            locator_mode=self._locator_mode(request.action.value),
            pixel_fallback_used=request.action.value in PIXEL_ACTIONS,
            started_at=started,
        )
        db.add(command)
        db.flush()
        artifacts = []
        try:
            response = self._execute_action(db, device, request, command, artifacts, run_id, result_id, case_id)
            command.status = "success"
            command.response = response
            command.exit_code = 0
            command.ended_at = now_utc()
            record_event(
                db,
                category="device_command",
                message=f"action {request.action.value} completed",
                run_id=run_id,
                device_id=device_id,
                payload={"action": request.action.value, "commandId": command.id},
            )
        except AppException as exc:
            command.status = "failed"
            command.error_code = exc.code
            command.error_message = exc.message
            command.response = {"details": exc.details} if exc.details else {}
            command.exit_code = 1
            command.ended_at = now_utc()
            self._collect_failure_evidence(db, device, run_id, result_id, artifacts, exc.message)
            record_event(
                db,
                category="device_command_failed",
                message=exc.message,
                level="error",
                run_id=run_id,
                device_id=device_id,
                payload={"action": request.action.value, "commandId": command.id, "errorCode": exc.code},
            )
            db.flush()
            raise
        except Exception as exc:
            command.status = "failed"
            command.error_code = UI_AUTOMATION_FAILED
            command.error_message = str(exc)
            command.exit_code = 1
            command.ended_at = now_utc()
            self._collect_failure_evidence(db, device, run_id, result_id, artifacts, str(exc))
            db.flush()
            raise AppException(UI_AUTOMATION_FAILED, f"action execution failed: {exc}", 400) from exc
        db.flush()
        return command, artifacts

    def capture_screenshot(self, db: Session, *, device_id: int, name: str | None = None, run_id: int | None = None, result_id: int | None = None):
        device = self.devices.ensure_online(db, device_id)
        png = self.adb.screenshot_png(device.serial, timeout=10)
        artifact = self.artifacts.save_bytes(
            db,
            content=png,
            artifact_type="screenshot",
            run_id=run_id,
            result_id=result_id,
            device_id=device_id,
            name=name,
            meta={"serial": device.serial},
        )
        return artifact

    def capture_hierarchy(self, db: Session, *, device_id: int, name: str | None = None, run_id: int | None = None, result_id: int | None = None):
        device = self.devices.ensure_online(db, device_id)
        xml = self.adb.dump_hierarchy(device.serial, timeout=20)
        artifact = self.artifacts.save_text(
            db,
            text=xml,
            artifact_type="hierarchy",
            run_id=run_id,
            result_id=result_id,
            device_id=device_id,
            name=name,
            meta={"serial": device.serial},
        )
        return artifact

    def capture_logcat(self, db: Session, *, device_id: int, duration_sec: int = 3, buffers: list[str] | None = None, name: str | None = None, run_id: int | None = None, result_id: int | None = None):
        device = self.devices.ensure_online(db, device_id)
        text = self.adb.logcat_snapshot(device.serial, duration_sec=duration_sec, buffers=buffers, timeout=duration_sec + 10)
        artifact = self.artifacts.save_text(
            db,
            text=text,
            artifact_type="logcat",
            run_id=run_id,
            result_id=result_id,
            device_id=device_id,
            name=name,
            meta={"serial": device.serial, "durationSec": duration_sec, "buffers": buffers or []},
        )
        return artifact

    def _execute_action(
        self,
        db: Session,
        device,
        request: DeviceCommandRequest,
        command: DeviceCommand,
        artifacts: list,
        run_id: int | None,
        result_id: int | None,
        case_id: int | None,
    ) -> dict[str, Any]:
        action = request.action.value
        serial = device.serial
        if action == Action.screenshot.value:
            artifact = self.capture_screenshot(db, device_id=device.id, run_id=run_id, result_id=result_id)
            artifacts.append(artifact)
            return {"artifact": artifact_to_dict(artifact)}
        if action == Action.dump_hierarchy.value:
            artifact = self.capture_hierarchy(db, device_id=device.id, run_id=run_id, result_id=result_id)
            artifacts.append(artifact)
            return {"artifact": artifact_to_dict(artifact)}
        if action == Action.logcat_snapshot.value:
            artifact = self.capture_logcat(
                db,
                device_id=device.id,
                run_id=run_id,
                result_id=result_id,
                duration_sec=int(request.params.get("durationSec", 3)),
                buffers=request.params.get("buffers"),
            )
            artifacts.append(artifact)
            return {"artifact": artifact_to_dict(artifact)}
        if action in {Action.semantic_click.value, Action.semantic_input.value, Action.semantic_assert.value}:
            return self.ui.execute_semantic(serial, action, request.selector or {}, request.params, request.timeoutSec)
        if action == Action.keyevent.value:
            result = self.adb.input_keyevent(serial, str(request.params.get("key")), timeout=request.timeoutSec)
            self._raise_if_adb_failed(result, action)
            return {"stdout": result.stdout, "stderr": result.stderr}
        if action == Action.open_notification.value:
            result = self.adb.open_notification(serial, timeout=request.timeoutSec)
            self._raise_if_adb_failed(result, action)
            return {"stdout": result.stdout, "stderr": result.stderr}
        if action == Action.open_quick_settings.value:
            result = self.adb.open_quick_settings(serial, timeout=request.timeoutSec)
            self._raise_if_adb_failed(result, action)
            return {"stdout": result.stdout, "stderr": result.stderr}
        if action == Action.shell.value:
            result = self.adb.safe_shell(serial, str(request.params.get("command", "")), timeout=request.timeoutSec)
            self._raise_if_adb_failed(result, action)
            return {"stdout": result.stdout, "stderr": result.stderr, "exitCode": result.exit_code}
        if action == Action.swipe.value:
            result = self._execute_ratio_swipe(serial, request.params, request.timeoutSec)
            self._raise_if_adb_failed(result, action)
            return {"stdout": result.stdout, "stderr": result.stderr}
        if action in PIXEL_ACTIONS:
            return self._execute_pixel(db, device, request, command, artifacts, run_id, result_id, case_id)
        raise AppException(PARAM_ERROR, f"unsupported action: {action}", 400)

    def _execute_pixel(self, db: Session, device, request: DeviceCommandRequest, command: DeviceCommand, artifacts: list, run_id: int | None, result_id: int | None, case_id: int | None) -> dict[str, Any]:
        payload = request.model_dump(mode="python", by_alias=True)
        validate_pixel_audit_payload(payload)
        self.devices.refresh_device_screen(device)
        expected_orientation = orientation_from_size(device.screen_width, device.screen_height)
        if device.screen_width and device.screen_height:
            if payload["screenWidth"] != device.screen_width or payload["screenHeight"] != device.screen_height:
                raise AppException(
                    UI_AUTOMATION_FAILED,
                    "pixel fallback screen size mismatch with current device resolution",
                    400,
                    details={
                        "expected": {"screenWidth": device.screen_width, "screenHeight": device.screen_height},
                        "actual": {"screenWidth": payload["screenWidth"], "screenHeight": payload["screenHeight"]},
                    },
                )
        if expected_orientation and payload["orientation"] != expected_orientation:
            raise AppException(
                SEMANTIC_LOCATOR_FAILED,
                "pixel fallback orientation mismatch; semantic locator or updated coordinates required",
                400,
                details={"expectedOrientation": expected_orientation, "actualOrientation": payload["orientation"]},
            )
        before = self._best_effort_screenshot(db, device, run_id, result_id, "pixel_before")
        if before:
            artifacts.append(before)
        if request.action.value == Action.pixel_tap.value:
            result = self.adb.input_tap(device.serial, request.x or 0, request.y or 0, timeout=request.timeoutSec)
        else:
            params = request.params or {}
            x2 = int(params.get("x2", request.x or 0))
            y2 = int(params.get("y2", request.y or 0))
            duration_ms = int(params.get("durationMs", 300))
            result = self.adb.input_swipe(device.serial, request.x or 0, request.y or 0, x2, y2, duration_ms, timeout=request.timeoutSec)
        self._raise_if_adb_failed(result, request.action.value)
        time.sleep(0.1)
        after = self._best_effort_screenshot(db, device, run_id, result_id, "pixel_after")
        if after:
            artifacts.append(after)
        pixel_audit = {
            "pixelFallback": True,
            "fallbackReason": request.fallbackReason or "",
            "x": request.x or 0,
            "y": request.y or 0,
            "screenWidth": request.screenWidth or 0,
            "screenHeight": request.screenHeight or 0,
            "orientation": request.orientation or "portrait",
            "riskNote": request.riskNote or "",
            "improvementSuggestion": request.improvementSuggestion or "",
        }
        fallback = LocatorFallback(
            run_id=run_id,
            result_id=result_id,
            device_id=device.id,
            case_id=case_id,
            action=request.action.value,
            x=pixel_audit["x"],
            y=pixel_audit["y"],
            screen_width=pixel_audit["screenWidth"],
            screen_height=pixel_audit["screenHeight"],
            orientation=pixel_audit["orientation"],
            fallback_reason=pixel_audit["fallbackReason"],
            risk_note=pixel_audit["riskNote"],
            improvement_suggestion=pixel_audit["improvementSuggestion"],
            before_artifact_id=before.id if before else None,
            after_artifact_id=after.id if after else None,
            created_at=now_utc(),
        )
        db.add(fallback)
        db.flush()
        command.locator_fallback_id = fallback.id
        command.locator_mode = "pixel_fallback"
        record_event(
            db,
            category="pixel_fallback_used",
            message="pixel fallback used and audited",
            level="warning",
            run_id=run_id,
            device_id=device.id,
            payload={"action": request.action.value, **pixel_audit},
        )
        return {"fallbackId": fallback.id, "pixelAudit": pixel_audit, "stdout": result.stdout, "stderr": result.stderr}

    def _execute_ratio_swipe(self, serial: str, params: dict[str, Any], timeout: int):
        direction = str(params.get("direction", "up"))
        duration_ms = int(params.get("durationMs", 300))
        width = int(params.get("screenWidth", 1000))
        height = int(params.get("screenHeight", 1000))
        cx = width // 2
        cy = height // 2
        distance = int(min(width, height) * float(params.get("ratio", 0.4)))
        if direction == "up":
            return self.adb.input_swipe(serial, cx, cy + distance // 2, cx, cy - distance // 2, duration_ms, timeout)
        if direction == "down":
            return self.adb.input_swipe(serial, cx, cy - distance // 2, cx, cy + distance // 2, duration_ms, timeout)
        if direction == "left":
            return self.adb.input_swipe(serial, cx + distance // 2, cy, cx - distance // 2, cy, duration_ms, timeout)
        if direction == "right":
            return self.adb.input_swipe(serial, cx - distance // 2, cy, cx + distance // 2, cy, duration_ms, timeout)
        raise AppException(PARAM_ERROR, "params.direction must be up/down/left/right", 400)

    def _collect_failure_evidence(self, db: Session, device, run_id: int | None, result_id: int | None, artifacts: list, reason: str) -> None:
        for collector in (
            lambda: self._best_effort_screenshot(db, device, run_id, result_id, "failure_screenshot"),
            lambda: self._best_effort_hierarchy(db, device, run_id, result_id, "failure_hierarchy"),
            lambda: self._best_effort_logcat(db, device, run_id, result_id, "failure_logcat"),
        ):
            artifact = collector()
            if artifact:
                artifacts.append(artifact)

    def _best_effort_screenshot(self, db: Session, device, run_id, result_id, name):
        try:
            return self.capture_screenshot(db, device_id=device.id, run_id=run_id, result_id=result_id, name=name)
        except Exception:
            return None

    def _best_effort_hierarchy(self, db: Session, device, run_id, result_id, name):
        try:
            return self.capture_hierarchy(db, device_id=device.id, run_id=run_id, result_id=result_id, name=name)
        except Exception:
            return None

    def _best_effort_logcat(self, db: Session, device, run_id, result_id, name):
        try:
            return self.capture_logcat(db, device_id=device.id, run_id=run_id, result_id=result_id, name=name)
        except Exception:
            return None

    def _raise_if_adb_failed(self, result, action: str) -> None:
        if result.ok:
            return
        message = result.stderr or result.stdout or f"{action} failed"
        raise AppException(UI_AUTOMATION_FAILED, message, 400)

    def _locator_mode(self, action: str) -> str | None:
        if action in PIXEL_ACTIONS:
            return "pixel_fallback"
        if action.startswith("semantic_"):
            return "semantic"
        return "adb"
