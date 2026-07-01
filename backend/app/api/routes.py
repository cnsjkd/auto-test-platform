from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppException, NOT_FOUND
from app.core.response import json_envelope
from app.db.session import get_db
from app.models import Artifact
from app.schemas.contracts import (
    DeviceCommandRequest,
    DeviceScanRequest,
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
