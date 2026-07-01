from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppException, NOT_FOUND
from app.core.response import json_envelope
from app.models.entities import now_utc
from app.db.session import SessionLocal, get_db
from app.models import Artifact
from app.schemas.contracts import (
    DeviceCommandRequest,
    DeviceScanRequest,
    FlowRunRequest,
    LogcatSnapshotRequest,
    NameRequest,
    RunCancelRequest,
    RunCreateRequest,
    SmokeSuiteRunRequest,
    TestCaseCreateRequest,
)
from app.schemas.serializers import artifact_to_dict, command_to_dict, device_to_dict, test_case_to_dict, test_result_to_dict, test_run_to_dict
from app.services.commands import CommandService
from app.services.devices import DeviceService
from app.services.events import subscribe_run, unsubscribe_run
from app.services.smoke_suite import SmokeSuiteService
from app.services.test_cases import TestCaseService
from app.services.test_runs import TestRunService

router = APIRouter()
device_service = DeviceService()
command_service = CommandService(device_service=device_service)
test_case_service = TestCaseService()
test_run_service = TestRunService(command_service=command_service)
smoke_suite_service = SmokeSuiteService(test_case_service=test_case_service)


def _execute_run_in_background(run_id: int, payload: RunCreateRequest) -> None:
    with SessionLocal() as db:
        try:
            test_run_service.execute_queued(db, run_id, payload)
        except Exception:
            db.rollback()
            try:
                run = test_run_service.get_run(db, run_id)
                run.status = "failed"
                run.ended_at = now_utc()
                db.commit()
            except Exception:
                db.rollback()


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)):
    adb_info = device_service.health()
    db_ok = True
    db_message = ""
    try:
        db.execute(select(1))
    except Exception as exc:
        db_ok = False
        db_message = str(exc)
    Path(settings.artifact_root).mkdir(parents=True, exist_ok=True)
    return json_envelope(
        request,
        {
            "status": "ok" if db_ok else "degraded",
            "adbAvailable": adb_info.get("available", False),
            "adb": adb_info,
            "db": {"ok": db_ok, "message": db_message},
            "pythonVersion": __import__("sys").version.split()[0],
            "artifactRoot": str(settings.artifact_root),
        },
    )


@router.get("/devices")
def list_devices(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    devices = device_service.list_devices(db, status=status)
    return json_envelope(request, {"devices": [device_to_dict(device) for device in devices]})


@router.post("/devices/scan")
def scan_devices(request: Request, payload: DeviceScanRequest, db: Session = Depends(get_db)):
    devices = device_service.scan(db)
    db.commit()
    return json_envelope(request, {"devices": [device_to_dict(device) for device in devices]})


@router.get("/devices/{device_id}")
def get_device(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = device_service.get_device(db, device_id)
    return json_envelope(request, {"device": device_to_dict(device)})


@router.post("/devices/{device_id}/commands")
def execute_command(request: Request, device_id: int, payload: DeviceCommandRequest, db: Session = Depends(get_db)):
    command, artifacts = command_service.execute(db, device_id=device_id, request=payload)
    db.commit()
    return json_envelope(
        request,
        {
            "command": command_to_dict(command),
            "artifacts": [artifact_to_dict(artifact) for artifact in artifacts],
        },
    )


def _run_flow_payload(payload: FlowRunRequest, db: Session) -> dict:
    flow_id = payload.flowId or f"flow_{uuid.uuid4().hex}"
    started_at = now_utc()
    steps = []
    artifacts = []
    status = "success"
    failure_message = None

    for index, step in enumerate(payload.steps, start=1):
        step_artifacts = []
        command_dict = None
        step_result = {
            "index": index,
            "name": step.name,
            "action": step.action.value,
            "status": "running",
            "message": None,
            "command": None,
            "locatorMode": None,
            "pixelFallbackUsed": False,
            "artifacts": [],
        }
        try:
            command, command_artifacts = command_service.execute(db, device_id=payload.deviceId, request=step, source="flow")
            command_dict = command_to_dict(command)
            step_artifacts.extend(command_artifacts)
            step_result["status"] = command_dict["status"]
            step_result["message"] = command_dict.get("errorMessage") or "ok"
            step_result["command"] = command_dict
            step_result["locatorMode"] = command_dict.get("locatorMode")
            step_result["pixelFallbackUsed"] = command_dict.get("pixelFallbackUsed", False)
            if payload.captureAfterEachStep:
                try:
                    screenshot = command_service.capture_screenshot(db, device_id=payload.deviceId, name=f"{flow_id}_step_{index}_after")
                    step_artifacts.append(screenshot)
                except AppException as exc:
                    step_result["screenshotWarning"] = exc.message
        except AppException as exc:
            status = "failed"
            failure_message = exc.message
            step_result["status"] = "failed"
            step_result["message"] = exc.message
            step_result["error"] = {"code": exc.code, "message": exc.message, "details": exc.details}
            if payload.captureAfterEachStep:
                try:
                    screenshot = command_service.capture_screenshot(db, device_id=payload.deviceId, name=f"{flow_id}_step_{index}_failure")
                    step_artifacts.append(screenshot)
                except AppException as screenshot_exc:
                    step_result["screenshotWarning"] = screenshot_exc.message
        step_result["artifacts"] = [artifact_to_dict(artifact) for artifact in step_artifacts]
        artifacts.extend(step_artifacts)
        steps.append(step_result)
        if step_result["status"] != "success":
            break

    final_artifacts = []
    if payload.collectFinalEvidence:
        for collector in (
            lambda: command_service.capture_hierarchy(db, device_id=payload.deviceId, name=f"{flow_id}_final_hierarchy"),
            lambda: command_service.capture_logcat(db, device_id=payload.deviceId, duration_sec=3, name=f"{flow_id}_final_logcat"),
        ):
            try:
                final_artifacts.append(collector())
            except AppException:
                pass

    artifacts.extend(final_artifacts)
    ended_at = now_utc()
    passed_count = sum(1 for result in steps if result["status"] == "success")
    failed_count = sum(1 for result in steps if result["status"] != "success")
    pixel_fallback_count = sum(1 for result in steps if result["pixelFallbackUsed"])
    run = {
        "id": flow_id,
        "status": status,
        "deviceId": payload.deviceId,
        "totalCount": len(payload.steps),
        "passedCount": passed_count,
        "failedCount": failed_count,
        "pixelFallbackCount": pixel_fallback_count,
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat(),
        "message": failure_message or "flow completed",
    }
    report_payload = {
        "run": run,
        "steps": steps,
        "artifacts": [artifact_to_dict(artifact) for artifact in artifacts],
        "config": payload.config,
    }
    report = command_service.artifacts.save_json(
        db,
        payload=report_payload,
        device_id=payload.deviceId,
        name=f"{flow_id}_summary",
        meta={"flowId": flow_id, "flowName": payload.name},
    )
    artifacts.append(report)
    artifact_dicts = [artifact_to_dict(artifact) for artifact in artifacts]
    summary = {
        "flowId": flow_id,
        "name": payload.name,
        "deviceId": payload.deviceId,
        "status": status,
        "totalSteps": len(payload.steps),
        "completedSteps": passed_count,
        "failedSteps": failed_count,
        "startedAt": run["startedAt"],
        "endedAt": run["endedAt"],
        "message": run["message"],
    }
    db.commit()
    return {
        "run": run,
        "steps": steps,
        "artifacts": artifact_dicts,
        "summary": summary,
        "stepResults": steps,
    }


@router.post("/automation-flows/run")
def run_automation_flow(request: Request, payload: FlowRunRequest, db: Session = Depends(get_db)):
    return json_envelope(request, _run_flow_payload(payload, db))


@router.post("/flows/run")
def run_flow(request: Request, payload: FlowRunRequest, db: Session = Depends(get_db)):
    return json_envelope(request, _run_flow_payload(payload, db))


@router.post("/devices/{device_id}/screenshot")
def capture_screenshot(request: Request, device_id: int, payload: NameRequest | None = None, db: Session = Depends(get_db)):
    artifact = command_service.capture_screenshot(db, device_id=device_id, name=payload.name if payload else None)
    db.commit()
    return json_envelope(request, {"artifact": artifact_to_dict(artifact)})


@router.post("/devices/{device_id}/dump-hierarchy")
def capture_hierarchy(request: Request, device_id: int, payload: NameRequest | None = None, db: Session = Depends(get_db)):
    artifact = command_service.capture_hierarchy(db, device_id=device_id, name=payload.name if payload else None)
    db.commit()
    return json_envelope(request, {"artifact": artifact_to_dict(artifact)})


@router.post("/devices/{device_id}/logcat/snapshot")
def capture_logcat(request: Request, device_id: int, payload: LogcatSnapshotRequest, db: Session = Depends(get_db)):
    artifact = command_service.capture_logcat(
        db,
        device_id=device_id,
        duration_sec=payload.durationSec,
        buffers=payload.buffers,
    )
    db.commit()
    return json_envelope(request, {"artifact": artifact_to_dict(artifact)})


@router.get("/test-cases")
def list_test_cases(
    request: Request,
    type: str | None = None,
    tags: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db),
):
    cases = test_case_service.list_cases(db, type_=type, tags=tags, enabled=enabled)
    return json_envelope(request, {"cases": [test_case_to_dict(case) for case in cases]})


@router.post("/test-cases")
def create_test_case(request: Request, payload: TestCaseCreateRequest, db: Session = Depends(get_db)):
    case = test_case_service.create_case(db, payload)
    db.commit()
    return json_envelope(request, {"case": test_case_to_dict(case)}, status_code=201)


@router.get("/test-runs")
def list_test_runs(
    request: Request,
    status: str | None = None,
    deviceId: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    runs = test_run_service.list_runs(db, status=status, device_id=deviceId, limit=limit)
    return json_envelope(request, {"runs": [test_run_to_dict(run) for run in runs]})


@router.post("/test-runs")
def create_test_run(request: Request, payload: RunCreateRequest, db: Session = Depends(get_db)):
    run = test_run_service.create_and_execute(db, payload)
    db.commit()
    return json_envelope(request, {"run": test_run_to_dict(run)}, status_code=201)


@router.post("/test-runs/async")
def create_test_run_async(request: Request, payload: RunCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run = test_run_service.create_queued(db, payload)
    db.commit()
    background_tasks.add_task(_execute_run_in_background, run.id, payload)
    return json_envelope(request, {"run": test_run_to_dict(run), "monitorUrl": f"/runs/{run.id}"}, status_code=202)


@router.get("/smoke-suite/p0")
def get_p0_smoke_suite(request: Request, db: Session = Depends(get_db)):
    suite = smoke_suite_service.ensure_p0_suite(db)
    db.commit()
    return json_envelope(request, suite)


@router.post("/smoke-suite/p0/run")
def run_p0_smoke_suite(request: Request, payload: SmokeSuiteRunRequest, db: Session = Depends(get_db)):
    run, suite = smoke_suite_service.create_p0_run(db, payload, test_run_service)
    db.commit()
    return json_envelope(request, {"suite": suite, "run": test_run_to_dict(run)}, status_code=201)


@router.post("/smoke-suite/p0/run-async")
def run_p0_smoke_suite_async(request: Request, payload: SmokeSuiteRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    cases = smoke_suite_service.ensure_p0_cases(db)
    suite = smoke_suite_service.serialize_p0_suite(cases)
    if suite["pixelFallbackCount"] > 0 and payload.riskAccepted is not True:
        raise AppException(
            42201,
            "riskAccepted=true is required before running a suite with Pixel Fallback audit cases",
            422,
            details={
                "suiteId": "p0_smoke",
                "requiresRiskAcceptance": True,
                "pixelFallbackCount": suite["pixelFallbackCount"],
                "acceptanceNotes": suite["acceptanceNotes"],
            },
        )
    config = dict(payload.config or {})
    config.update(
        {
            "suiteId": suite["suite"]["id"],
            "suiteName": suite["suite"]["name"],
            "suiteTag": suite["suite"].get("tag"),
            "riskAccepted": payload.riskAccepted,
            "requiresRiskAcceptance": suite["requiresRiskAcceptance"],
            "acceptanceNotes": suite["acceptanceNotes"],
            "executionMode": "async",
        }
    )
    run_request = RunCreateRequest(deviceId=payload.deviceId, caseIds=suite["caseIds"], config=config)
    run = test_run_service.create_queued(db, run_request)
    db.commit()
    background_tasks.add_task(_execute_run_in_background, run.id, run_request)
    return json_envelope(request, {"suite": suite, "run": test_run_to_dict(run), "monitorUrl": f"/runs/{run.id}"}, status_code=202)


@router.get("/test-runs/{run_id}")
def get_test_run(request: Request, run_id: int, db: Session = Depends(get_db)):
    run = test_run_service.get_run(db, run_id)
    results = [test_result_to_dict(result) for result in run.results]
    artifacts = [artifact_to_dict(artifact) for artifact in run.artifacts]
    return json_envelope(request, {"run": test_run_to_dict(run), "results": results, "artifacts": artifacts})


@router.post("/test-runs/{run_id}/cancel")
def cancel_test_run(request: Request, run_id: int, payload: RunCancelRequest, db: Session = Depends(get_db)):
    run = test_run_service.cancel(db, run_id, payload.reason)
    db.commit()
    return json_envelope(request, {"run": test_run_to_dict(run)})


@router.get("/test-runs/{run_id}/artifacts")
def get_test_run_artifacts(request: Request, run_id: int, type: str | None = None, db: Session = Depends(get_db)):
    artifacts = test_run_service.artifacts_for_run(db, run_id, type_=type)
    return json_envelope(request, {"artifacts": [artifact_to_dict(artifact) for artifact in artifacts]})


@router.get("/artifacts")
def list_artifacts(
    request: Request,
    type: str | None = None,
    runId: int | None = None,
    deviceId: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(Artifact).order_by(Artifact.created_at.desc()).limit(limit)
    if type:
        query = query.where(Artifact.type == type)
    if runId:
        query = query.where(Artifact.run_id == runId)
    if deviceId:
        query = query.where(Artifact.device_id == deviceId)
    artifacts = list(db.scalars(query).all())
    return json_envelope(request, {"artifacts": [artifact_to_dict(artifact) for artifact in artifacts]})


@router.get("/artifacts/{artifact_id}")
def get_artifact(request: Request, artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise AppException(NOT_FOUND, "artifact not found", 404)
    return json_envelope(request, {"artifact": artifact_to_dict(artifact)})


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise AppException(NOT_FOUND, "artifact not found", 404)
    path = Path(artifact.path)
    if not path.exists() or not path.is_file():
        raise AppException(NOT_FOUND, "artifact file not found", 404)
    return FileResponse(path, media_type=artifact.mime_type, filename=path.name)


async def run_events(websocket: WebSocket, run_id: int):
    await websocket.accept()
    queue = subscribe_run(run_id)
    try:
        await websocket.send_text(json.dumps({"type": "connected", "runId": run_id}, ensure_ascii=False))
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_run(run_id, queue)
