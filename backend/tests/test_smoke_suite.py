from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("A2_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("A2_ARTIFACT_ROOT", str(artifact_root))
    modules_to_clear = [name for name in sys.modules if name == "app" or name.startswith("app.")]
    for name in modules_to_clear:
        sys.modules.pop(name, None)
    from app.db.init_db import init_db
    from app.main import create_app

    app = create_app()
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_p0_smoke_suite_seed_is_idempotent(client):
    first = client.get("/api/smoke-suite/p0")
    second = client.get("/api/smoke-suite/p0")

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["suite"]["id"] == "p0_smoke"
    assert first_data["suite"]["name"] == "A2 P0 冒烟套件"
    assert first_data["suite"]["tag"] == "p0_smoke"
    assert first_data["ready"] is True
    assert first_data["caseCount"] == 7
    assert first_data["requiresRiskAcceptance"] is True
    assert first_data["acceptanceNotes"]
    assert len(first_data["cases"]) == 7
    assert len(second_data["cases"]) == 7
    assert second_data["caseIds"] == first_data["caseIds"]
    assert second_data["pixelFallbackCount"] == 1

    cases_response = client.get("/api/test-cases?tags=p0_smoke")
    assert cases_response.status_code == 200
    cases = cases_response.json()["data"]["cases"]
    assert len(cases) == 7
    assert sum(case["pixelFallbackCount"] for case in cases) == 1


def test_p0_smoke_suite_returns_case_ids_and_action_contract(client):
    response = client.get("/api/smoke-suite/p0")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["caseIds"] == [case["id"] for case in data["cases"]]
    assert data["caseCount"] == len(data["cases"])
    assert data["pixelFallbackCount"] == 1
    assert all("commandType" not in str(case["steps"]) for case in data["cases"])
    steps = [step for case in data["cases"] for step in case["steps"]]
    actions = [step["action"] for step in steps]
    assert {"screenshot", "dump_hierarchy", "logcat_snapshot", "open_notification", "open_quick_settings", "keyevent", "pixel_tap"}.issubset(set(actions))
    assert actions.count("screenshot") >= 5
    assert actions.count("dump_hierarchy") >= 3
    assert actions.count("logcat_snapshot") >= 2
    pixel_step = next(step for step in steps if step["action"] == "pixel_tap")
    for field in ["pixelFallback", "fallbackReason", "x", "y", "screenWidth", "screenHeight", "orientation", "riskNote", "improvementSuggestion"]:
        assert pixel_step[field] not in (None, "")
    assert pixel_step["pixelFallback"] is True
    assert pixel_step["screenWidth"] == 1200
    assert pixel_step["screenHeight"] == 1920
    assert pixel_step["orientation"] == "portrait"


def test_p0_smoke_suite_run_requires_risk_accepted(client):
    response = client.post("/api/smoke-suite/p0/run", json={"deviceId": 1, "riskAccepted": False})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == 42201
    assert "riskAccepted=true" in payload["message"]


def test_p0_smoke_suite_api_run_with_risk_accepted_uses_test_run_service(client):
    from app.api import routes
    from app.models import TestRun
    from app.models.entities import now_utc

    class FakeTestRunService:
        def __init__(self):
            self.requests = []

        def create_and_execute(self, db, request):
            self.requests.append(request)
            run = TestRun(
                status="passed",
                device_id=request.deviceId,
                total_count=len(request.caseIds),
                passed_count=len(request.caseIds),
                failed_count=0,
                skipped_count=0,
                started_at=now_utc(),
                ended_at=now_utc(),
                config=request.config,
            )
            db.add(run)
            db.flush()
            return run

    original_service = routes.test_run_service
    fake_run_service = FakeTestRunService()
    routes.test_run_service = fake_run_service
    try:
        response = client.post("/api/smoke-suite/p0/run", json={"deviceId": 42, "riskAccepted": True, "config": {"trigger": "api-test"}})
    finally:
        routes.test_run_service = original_service

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["suite"]["caseCount"] == 7
    assert data["suite"]["pixelFallbackCount"] == 1
    assert data["run"]["status"] == "passed"
    assert data["run"]["deviceId"] == 42
    assert len(fake_run_service.requests) == 1
    request = fake_run_service.requests[0]
    assert request.deviceId == 42
    assert request.caseIds == data["suite"]["caseIds"]
    assert request.config["suiteId"] == "p0_smoke"
    assert request.config["suiteName"] == "A2 P0 冒烟套件"
    assert request.config["riskAccepted"] is True
    assert request.config["trigger"] == "api-test"



def test_p0_smoke_suite_async_returns_queued_run_and_monitor_url(client):
    response = client.post("/api/smoke-suite/p0/run-async", json={"deviceId": 42, "riskAccepted": True, "config": {"trigger": "async-test"}})

    assert response.status_code == 202
    payload = response.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["suite"]["caseCount"] == 7
    assert data["run"]["status"] in {"queued", "running", "passed", "failed"}
    assert data["run"]["deviceId"] == 42
    assert data["monitorUrl"] == f"/runs/{data['run']['id']}"

    detail_response = client.get(f"/api/test-runs/{data['run']['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["run"]["id"] == data["run"]["id"]


def test_p0_smoke_suite_async_requires_risk_accepted(client):
    response = client.post("/api/smoke-suite/p0/run-async", json={"deviceId": 42, "riskAccepted": False})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == 42201
    assert payload["data"]["details"]["requiresRiskAcceptance"] is True


def test_p0_smoke_suite_success_run_uses_test_run_service(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("A2_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("A2_ARTIFACT_ROOT", str(artifact_root))
    modules_to_clear = [name for name in sys.modules if name == "app" or name.startswith("app.")]
    for name in modules_to_clear:
        sys.modules.pop(name, None)

    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.models import TestRun
    from app.models.entities import now_utc
    from app.schemas.contracts import SmokeSuiteRunRequest
    from app.services.smoke_suite import P0_SUITE_ID, P0_SUITE_NAME, P0_SUITE_TAG, SmokeSuiteService

    class FakeTestRunService:
        def __init__(self):
            self.requests = []

        def create_and_execute(self, db, request):
            self.requests.append(request)
            run = TestRun(
                status="passed",
                device_id=request.deviceId,
                total_count=len(request.caseIds),
                passed_count=len(request.caseIds),
                failed_count=0,
                skipped_count=0,
                started_at=now_utc(),
                ended_at=now_utc(),
                config=request.config,
            )
            db.add(run)
            db.flush()
            return run

    init_db()
    fake_run_service = FakeTestRunService()
    service = SmokeSuiteService(test_run_service=fake_run_service)

    with SessionLocal() as db:
        suite, run = service.run_p0_suite(db, SmokeSuiteRunRequest(deviceId=42, riskAccepted=True, config={"trigger": "unit"}))
        db.commit()

    assert len(fake_run_service.requests) == 1
    request = fake_run_service.requests[0]
    assert request.deviceId == 42
    assert request.caseIds == suite["caseIds"]
    assert request.config["suiteId"] == P0_SUITE_ID
    assert request.config["suiteName"] == P0_SUITE_NAME
    assert request.config["suiteTag"] == P0_SUITE_TAG
    assert request.config["riskAccepted"] is True
    assert request.config["trigger"] == "unit"
    assert run.status == "passed"
