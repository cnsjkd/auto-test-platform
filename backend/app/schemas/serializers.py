from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.models import Artifact, Device, DeviceCommand, LocatorFallback, PlatformEvent, TestCase, TestResult, TestRun


def dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def device_to_dict(device: Device) -> dict[str, Any]:
    capabilities = device.capabilities or {}
    adb_detail = capabilities.get("adb") if isinstance(capabilities.get("adb"), dict) else {}
    battery_detail = capabilities.get("battery") if isinstance(capabilities.get("battery"), dict) else {}
    battery_level = battery_detail.get("level") or battery_detail.get("Level")
    return {
        "id": device.id,
        "serial": device.serial,
        "status": device.status,
        "manufacturer": device.manufacturer or "Unknown",
        "model": device.model or "Unknown",
        "androidVersion": device.android_version or "Unknown",
        "sdkInt": int(device.sdk_int) if str(device.sdk_int or "").isdigit() else 0,
        "screenWidth": device.screen_width or 0,
        "screenHeight": device.screen_height or 0,
        "density": int(device.density) if str(device.density or "").isdigit() else 0,
        "battery": int(battery_level) if str(battery_level or "").isdigit() else 0,
        "network": capabilities.get("network") or "Unknown",
        "storage": capabilities.get("storage") or "Unknown",
        "adbStatus": adb_detail.get("adbState") or device.status,
        "capabilities": capabilities,
        "lastSeenAt": dt(device.last_seen_at),
        "createdAt": dt(device.created_at),
        "updatedAt": dt(device.updated_at),
    }


def test_case_to_dict(case: TestCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "name": case.name,
        "type": case.type,
        "priority": case.priority,
        "tags": case.tags or [],
        "status": case.status,
        "steps": case.steps or [],
        "hasPixelFallback": case.has_pixel_fallback,
        "pixelFallbackCount": case.pixel_fallback_count,
        "description": case.description,
        "createdAt": dt(case.created_at),
        "updatedAt": dt(case.updated_at),
    }


def test_run_to_dict(run: TestRun) -> dict[str, Any]:
    pixel_fallback_count = 0
    try:
        pixel_fallback_count = sum(1 for result in (run.results or []) if result.pixel_fallback_used)
    except Exception:
        pixel_fallback_count = 0
    return {
        "id": run.id,
        "status": run.status,
        "deviceId": run.device_id,
        "deviceSerial": run.device.serial if run.device else None,
        "totalCount": run.total_count,
        "passedCount": run.passed_count,
        "failedCount": run.failed_count,
        "skippedCount": run.skipped_count,
        "pixelFallbackCount": pixel_fallback_count,
        "startedAt": dt(run.started_at),
        "endedAt": dt(run.ended_at),
        "reportPath": run.report_path,
        "config": run.config or {},
        "createdAt": dt(run.created_at),
        "updatedAt": dt(run.updated_at),
    }


def test_result_to_dict(result: TestResult) -> dict[str, Any]:
    raw = result.raw or {}
    return {
        "id": result.id,
        "runId": result.run_id,
        "caseId": result.case_id,
        "caseName": raw.get("caseName") or (result.case.name if result.case else None),
        "deviceId": result.device_id,
        "status": result.status,
        "durationMs": result.duration_ms,
        "errorCode": result.error_code,
        "message": result.message,
        "locatorStrategy": result.locator_strategy or ("pixel_fallback" if result.pixel_fallback_used else "system"),
        "pixelFallbackUsed": result.pixel_fallback_used,
        "pixelAudit": raw.get("pixelAudit"),
        "startedAt": dt(result.started_at),
        "endedAt": dt(result.ended_at),
        "raw": raw,
    }


def artifact_to_dict(artifact: Artifact) -> dict[str, Any]:
    path = Path(artifact.path)
    return {
        "id": artifact.id,
        "runId": artifact.run_id,
        "resultId": artifact.result_id,
        "deviceId": artifact.device_id,
        "type": artifact.type,
        "path": artifact.path,
        "fileName": path.name,
        "mimeType": artifact.mime_type,
        "sizeBytes": artifact.size_bytes,
        "checksum": artifact.checksum,
        "meta": artifact.meta or {},
        "createdAt": dt(artifact.created_at),
    }


def command_to_dict(command: DeviceCommand) -> dict[str, Any]:
    return {
        "id": command.id,
        "deviceId": command.device_id,
        "runId": command.run_id,
        "resultId": command.result_id,
        "caseId": command.case_id,
        "action": command.command_type,
        "source": command.source,
        "params": command.params or {},
        "response": command.response or {},
        "exitCode": command.exit_code,
        "status": command.status,
        "locatorMode": command.locator_mode,
        "selector": command.selector or {},
        "pixelFallbackUsed": command.pixel_fallback_used,
        "locatorFallbackId": command.locator_fallback_id,
        "errorCode": command.error_code,
        "errorMessage": command.error_message,
        "startedAt": dt(command.started_at),
        "endedAt": dt(command.ended_at),
    }


def locator_fallback_to_dict(fallback: LocatorFallback) -> dict[str, Any]:
    return {
        "id": fallback.id,
        "runId": fallback.run_id,
        "resultId": fallback.result_id,
        "deviceId": fallback.device_id,
        "caseId": fallback.case_id,
        "action": fallback.action,
        "x": fallback.x,
        "y": fallback.y,
        "screenWidth": fallback.screen_width,
        "screenHeight": fallback.screen_height,
        "orientation": fallback.orientation,
        "fallbackReason": fallback.fallback_reason,
        "riskNote": fallback.risk_note,
        "improvementSuggestion": fallback.improvement_suggestion,
        "beforeArtifactId": fallback.before_artifact_id,
        "afterArtifactId": fallback.after_artifact_id,
        "createdAt": dt(fallback.created_at),
    }


def platform_event_to_dict(event: PlatformEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "runId": event.run_id,
        "deviceId": event.device_id,
        "level": event.level,
        "category": event.category,
        "message": event.message,
        "payload": event.payload or {},
        "createdAt": dt(event.created_at),
    }
