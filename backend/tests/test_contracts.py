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
    from app.main import create_app
    from app.db.init_db import init_db

    app = create_app()
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_health_does_not_crash_when_adb_missing_or_unavailable(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert "requestId" in payload
    assert payload["data"]["status"] in {"ok", "degraded"}
    assert "adbAvailable" in payload["data"]
    assert Path(payload["data"]["artifactRoot"]).exists()


def test_pixel_fallback_missing_audit_fields_returns_52003(client):
    response = client.post(
        "/api/test-cases",
        json={
            "name": "bad pixel case",
            "steps": [
                {
                    "action": "pixel_tap",
                    "pixelFallback": True,
                    "x": 10,
                    "y": 20,
                    "screenWidth": 100,
                    "screenHeight": 200,
                    "orientation": "portrait",
                }
            ],
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == 52003
    assert "fallbackReason" in payload["message"]


def test_test_case_derives_pixel_fallback_fields(client):
    response = client.post(
        "/api/test-cases",
        json={
            "name": "pixel audit case",
            "type": "ui",
            "priority": "P0",
            "tags": ["a2", "pixel"],
            "steps": [
                {"action": "screenshot"},
                {
                    "action": "pixel_tap",
                    "pixelFallback": True,
                    "fallbackReason": "控件未暴露 resource-id/content-desc",
                    "riskNote": "坐标依赖当前分辨率和方向，布局变化可能漂移",
                    "improvementSuggestion": "建议补充稳定 resource-id 或 content-desc",
                    "x": 10,
                    "y": 20,
                    "screenWidth": 100,
                    "screenHeight": 200,
                    "orientation": "portrait",
                },
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    case = payload["data"]["case"]
    assert case["hasPixelFallback"] is True
    assert case["pixelFallbackCount"] == 1
    assert case["steps"][1]["action"] == "pixel_tap"

    list_response = client.get("/api/test-cases")
    assert list_response.status_code == 200
    cases = list_response.json()["data"]["cases"]
    assert cases[0]["steps"]


def test_action_contract_rejects_command_type_and_keeps_action(client):
    bad = client.post(
        "/api/test-cases",
        json={
            "name": "legacy commandType case",
            "steps": [{"commandType": "screenshot"}],
        },
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == 40001

    good = client.post(
        "/api/test-cases",
        json={"name": "action case", "steps": [{"action": "screenshot"}]},
    )
    assert good.status_code == 201
    case = good.json()["data"]["case"]
    assert "commandType" not in str(case)
    assert case["steps"][0]["action"] == "screenshot"


def test_command_request_uses_action_field_not_command_type(client):
    response = client.post("/api/devices/999/commands", json={"commandType": "screenshot"})
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == 40001
    assert "action" in str(payload["data"]) or "Field required" in str(payload["data"])


def test_run_creation_requires_device_before_persisting(client):
    case_response = client.post(
        "/api/test-cases",
        json={"name": "run guard case", "steps": [{"action": "screenshot"}]},
    )
    assert case_response.status_code == 201
    case_id = case_response.json()["data"]["case"]["id"]

    response = client.post("/api/test-runs", json={"deviceId": None, "caseIds": [case_id], "config": {}})
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == 42201
    assert "deviceId" in payload["message"]

    runs_response = client.get("/api/test-runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["data"]["runs"] == []


class StubAdb:
    def __init__(self, results=None, *, screen=(100, 200)):
        self.results = list(results or [])
        self.calls = []
        self.screen = screen

    def _run_serial(self, serial, args, timeout=None, binary=False):
        self.calls.append({"serial": serial, "args": args, "timeout": timeout, "binary": binary})
        if not self.results:
            raise AssertionError(f"unexpected adb call: {args}")
        return self.results.pop(0)

    def wm_size(self, serial, timeout=10):
        width, height = self.screen
        return width, height, f"Physical size: {width}x{height}"

    def screenshot_png(self, serial, timeout=10):
        from app.adapters.adb import PNG_MAGIC

        return PNG_MAGIC + b"\r\nunchanged-binary-payload\r\n"

    def input_tap(self, serial, x, y, timeout=10):
        from app.adapters.adb import AdbResult

        self.calls.append({"serial": serial, "args": ["shell", "input", "tap", str(x), str(y)], "timeout": timeout, "binary": False})
        return AdbResult(ok=True, stdout="", stderr="", exit_code=0)

    def input_swipe(self, serial, x1, y1, x2, y2, duration_ms=300, timeout=10):
        from app.adapters.adb import AdbResult

        self.calls.append(
            {
                "serial": serial,
                "args": ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                "timeout": timeout,
                "binary": False,
            }
        )
        return AdbResult(ok=True, stdout="", stderr="", exit_code=0)


def _clear_app_modules():
    modules_to_clear = [name for name in sys.modules if name == "app" or name.startswith("app.")]
    for name in modules_to_clear:
        sys.modules.pop(name, None)


def _isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("A2_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("A2_ARTIFACT_ROOT", str(artifact_root))
    _clear_app_modules()

    from app.db.init_db import init_db
    from app.db.session import SessionLocal

    init_db()
    return SessionLocal, artifact_root


def test_screenshot_png_preserves_exec_out_bytes_and_rejects_non_standard_magic():
    from app.adapters.adb import AdbAdapter, AdbResult, PNG_MAGIC
    from app.core.errors import UI_AUTOMATION_FAILED, AppException

    raw_png = PNG_MAGIC + b"\r\nraw\r\nbytes"
    adapter = AdbAdapter.__new__(AdbAdapter)
    adapter.adb_path = "adb"
    stub = StubAdb([AdbResult(ok=True, stdout_bytes=raw_png, exit_code=0)])
    adapter._run_serial = stub._run_serial

    assert adapter.screenshot_png("A2") == raw_png
    assert stub.calls[0]["args"] == ["exec-out", "screencap", "-p"]
    assert stub.calls[0]["binary"] is True

    broken_png_after_crlf_rewrite = b"\x89PNG\n\x1a\nraw"
    bad_adapter = AdbAdapter.__new__(AdbAdapter)
    bad_adapter.adb_path = "adb"
    bad_stub = StubAdb([AdbResult(ok=True, stdout_bytes=broken_png_after_crlf_rewrite, exit_code=0)])
    bad_adapter._run_serial = bad_stub._run_serial

    with pytest.raises(AppException) as exc_info:
        bad_adapter.screenshot_png("A2")
    assert exc_info.value.code == UI_AUTOMATION_FAILED
    assert exc_info.value.details["expectedPngMagic"] == PNG_MAGIC.hex()
    assert exc_info.value.details["actualHeader"] == broken_png_after_crlf_rewrite[:8].hex()


def test_capture_screenshot_invalid_png_does_not_create_success_artifact(tmp_path, monkeypatch):
    SessionLocal, artifact_root = _isolated_db(tmp_path, monkeypatch)

    from sqlalchemy import select

    from app.adapters.adb import AdbAdapter, AdbResult
    from app.core.errors import AppException, UI_AUTOMATION_FAILED
    from app.models import Artifact, Device
    from app.services.artifacts import ArtifactManager
    from app.services.commands import CommandService
    from app.services.devices import DeviceService

    class BadPngAdb(AdbAdapter):
        def __init__(self):
            self.adb_path = "adb"
            self.calls = []

        def _run_serial(self, serial, args, timeout=None, binary=False):
            self.calls.append({"args": args, "binary": binary})
            return AdbResult(ok=True, stdout_bytes=b"\x89PNG\n\x1a\ncorrupted", exit_code=0)

    db = SessionLocal()
    try:
        device = Device(serial="A2", status="online", screen_width=100, screen_height=200)
        db.add(device)
        db.flush()
        adb = BadPngAdb()
        service = CommandService(adb=adb, device_service=DeviceService(adb), artifact_manager=ArtifactManager(root=artifact_root))

        with pytest.raises(AppException) as exc_info:
            service.capture_screenshot(db, device_id=device.id, name="broken")

        assert exc_info.value.code == UI_AUTOMATION_FAILED
        assert adb.calls == [{"args": ["exec-out", "screencap", "-p"], "binary": True}]
        assert list(db.scalars(select(Artifact)).all()) == []
        assert [path for path in artifact_root.rglob("*") if path.is_file()] == []
    finally:
        db.close()


def test_dump_hierarchy_uses_sdcard_file_readback_and_rejects_non_xml_artifact(tmp_path, monkeypatch):
    SessionLocal, artifact_root = _isolated_db(tmp_path, monkeypatch)

    from sqlalchemy import select

    from app.adapters.adb import AdbAdapter, AdbResult, UI_DUMP_REMOTE_PATH
    from app.core.errors import AppException, UI_AUTOMATION_FAILED
    from app.models import Artifact, Device
    from app.services.artifacts import ArtifactManager
    from app.services.commands import CommandService
    from app.services.devices import DeviceService

    class BadXmlAdb(AdbAdapter):
        def __init__(self):
            self.adb_path = "adb"
            self.calls = []
            self.results = [
                AdbResult(ok=True, stdout=f"UI hierchary dumped to: {UI_DUMP_REMOTE_PATH}", exit_code=0),
                AdbResult(ok=True, stdout_bytes="ERROR: could not get idle state 中文".encode("utf-8"), exit_code=0),
            ]

        def _run_serial(self, serial, args, timeout=None, binary=False):
            self.calls.append({"args": args, "binary": binary})
            return self.results.pop(0)

    db = SessionLocal()
    try:
        device = Device(serial="A2", status="online", screen_width=100, screen_height=200)
        db.add(device)
        db.flush()
        adb = BadXmlAdb()
        service = CommandService(adb=adb, device_service=DeviceService(adb), artifact_manager=ArtifactManager(root=artifact_root))

        with pytest.raises(AppException) as exc_info:
            service.capture_hierarchy(db, device_id=device.id, name="bad_xml")

        assert exc_info.value.code == UI_AUTOMATION_FAILED
        assert adb.calls == [
            {"args": ["shell", "uiautomator", "dump", UI_DUMP_REMOTE_PATH], "binary": False},
            {"args": ["exec-out", "cat", UI_DUMP_REMOTE_PATH], "binary": True},
        ]
        assert "/dev/tty" not in str(adb.calls)
        assert list(db.scalars(select(Artifact)).all()) == []
        assert [path for path in artifact_root.rglob("*") if path.is_file()] == []
    finally:
        db.close()


def test_pixel_audit_is_serialized_to_result_detail_and_reports(tmp_path, monkeypatch):
    import json

    SessionLocal, artifact_root = _isolated_db(tmp_path, monkeypatch)

    from sqlalchemy import select

    from app.models import Artifact, Device, TestCase, TestResult
    from app.schemas.contracts import RunCreateRequest
    from app.schemas.serializers import test_result_to_dict
    from app.services.artifacts import ArtifactManager
    from app.services.commands import CommandService
    from app.services.devices import DeviceService
    from app.services.test_runs import TestRunService

    pixel_step = {
        "action": "pixel_tap",
        "pixelFallback": True,
        "fallbackReason": "控件未暴露 resource-id/content-desc",
        "riskNote": "坐标依赖当前分辨率和方向，布局变化可能漂移",
        "improvementSuggestion": "建议补充稳定 resource-id 或 content-desc",
        "x": 10,
        "y": 20,
        "screenWidth": 100,
        "screenHeight": 200,
        "orientation": "portrait",
    }
    expected_audit = {
        "pixelFallback": True,
        "fallbackReason": pixel_step["fallbackReason"],
        "riskNote": pixel_step["riskNote"],
        "improvementSuggestion": pixel_step["improvementSuggestion"],
        "x": 10,
        "y": 20,
        "screenWidth": 100,
        "screenHeight": 200,
        "orientation": "portrait",
    }

    db = SessionLocal()
    try:
        device = Device(serial="A2", status="online", screen_width=100, screen_height=200)
        case = TestCase(name="pixel audit report case", type="ui", priority="P0", status="enabled", steps=[pixel_step], has_pixel_fallback=True, pixel_fallback_count=1)
        db.add_all([device, case])
        db.flush()

        adb = StubAdb(screen=(100, 200))
        artifacts = ArtifactManager(root=artifact_root)
        service = TestRunService(
            command_service=CommandService(adb=adb, device_service=DeviceService(adb), artifact_manager=artifacts),
            artifact_manager=artifacts,
        )
        run = service.create_and_execute(db, RunCreateRequest(deviceId=device.id, caseIds=[case.id], config={}))
        db.flush()

        result = db.scalar(select(TestResult).where(TestResult.run_id == run.id))
        assert result is not None
        assert result.status == "passed"
        assert result.pixel_fallback_used is True
        assert result.raw["pixelAudit"] == expected_audit
        assert result.raw["steps"][0]["pixelAudit"] == expected_audit
        assert test_result_to_dict(result)["pixelAudit"] == expected_audit

        json_artifact = db.scalar(select(Artifact).where(Artifact.run_id == run.id, Artifact.type == "report_json"))
        html_artifact = db.scalar(select(Artifact).where(Artifact.run_id == run.id, Artifact.type == "report_html"))
        assert json_artifact is not None
        assert html_artifact is not None

        report_payload = json.loads(Path(json_artifact.path).read_text(encoding="utf-8"))
        assert report_payload["results"][0]["pixelAudit"] == expected_audit
        assert report_payload["results"][0]["raw"]["steps"][0]["pixelAudit"] == expected_audit

        html_text = Path(html_artifact.path).read_text(encoding="utf-8")
        for required_text in [
            "Pixel Fallback Audit",
            "fallbackReason",
            "screenWidth",
            "screenHeight",
            "orientation",
            "riskNote",
            "improvementSuggestion",
            pixel_step["fallbackReason"],
            pixel_step["riskNote"],
            pixel_step["improvementSuggestion"],
        ]:
            assert required_text in html_text
    finally:
        db.close()


def test_adb_screenshot_preserves_standard_png_magic(monkeypatch):
    from app.adapters.adb import AdbAdapter, AdbResult, PNG_MAGIC

    adapter = AdbAdapter()
    monkeypatch.setattr(
        adapter,
        "_run_serial",
        lambda *args, **kwargs: AdbResult(ok=True, stdout_bytes=PNG_MAGIC + b"\r\nPNG_BINARY_PAYLOAD"),
    )

    png = adapter.screenshot_png("SERIAL")

    assert png.startswith(PNG_MAGIC)
    assert b"\r\nPNG_BINARY_PAYLOAD" in png


def test_adb_screenshot_rejects_non_png_header(monkeypatch):
    from app.adapters.adb import AdbAdapter, AdbResult
    from app.core.errors import AppException

    adapter = AdbAdapter()
    monkeypatch.setattr(adapter, "_run_serial", lambda *args, **kwargs: AdbResult(ok=True, stdout_bytes=b"not_png"))

    with pytest.raises(AppException) as exc_info:
        adapter.screenshot_png("SERIAL")

    assert exc_info.value.code == 52001
    assert "non-standard PNG" in exc_info.value.message


def test_adb_dump_hierarchy_reads_remote_xml_and_strips_prefix(monkeypatch):
    from app.adapters.adb import AdbAdapter, AdbResult

    calls = []
    adapter = AdbAdapter()

    def fake_run_serial(serial, args, timeout=None, binary=False):
        calls.append({"args": args, "binary": binary})
        if args[:3] == ["shell", "uiautomator", "dump"]:
            return AdbResult(ok=True, stdout="UI hierchary dumped to: /sdcard/window_dump.xml\n")
        if args[:2] == ["exec-out", "cat"]:
            return AdbResult(ok=True, stdout_bytes="noise before xml\n<?xml version='1.0'?><hierarchy text='中文' />\n".encode("utf-8"))
        return AdbResult(ok=False, stderr="unexpected command")

    monkeypatch.setattr(adapter, "_run_serial", fake_run_serial)

    xml = adapter.dump_hierarchy("SERIAL")

    assert calls[0] == {"args": ["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], "binary": False}
    assert calls[1] == {"args": ["exec-out", "cat", "/sdcard/window_dump.xml"], "binary": True}
    assert xml.startswith("<?xml")
    assert "<hierarchy" in xml
    assert "中文" in xml


def test_adb_dump_hierarchy_rejects_non_xml_readback(monkeypatch):
    from app.adapters.adb import AdbAdapter, AdbResult
    from app.core.errors import AppException

    adapter = AdbAdapter()

    def fake_run_serial(serial, args, timeout=None, binary=False):
        if args[:3] == ["shell", "uiautomator", "dump"]:
            return AdbResult(ok=True, stdout="UI hierchary dumped to: /sdcard/window_dump.xml")
        return AdbResult(ok=True, stdout_bytes="UI hierchary dumped to: /dev/tty".encode("utf-8"))

    monkeypatch.setattr(adapter, "_run_serial", fake_run_serial)

    with pytest.raises(AppException) as exc_info:
        adapter.dump_hierarchy("SERIAL")

    assert exc_info.value.code == 52001
    assert "did not contain XML" in exc_info.value.message


def test_pixel_audit_is_serialized_into_run_detail_and_html_report(client):
    from app.adapters.adb import PNG_MAGIC
    from app.db.session import SessionLocal
    from app.models import Device
    from app.models.entities import now_utc
    from app.services.commands import CommandService
    from app.services.devices import DeviceService
    from app.services.test_cases import TestCaseService
    from app.services.test_runs import TestRunService
    from app.schemas.contracts import RunCreateRequest, TestCaseCreateRequest
    from app.schemas.serializers import artifact_to_dict, test_result_to_dict

    class FakeResult:
        ok = True
        stdout = ""
        stderr = ""
        exit_code = 0

    class FakeAdb:
        def screenshot_png(self, serial, timeout=10):
            return PNG_MAGIC + b"FAKE_SCREENSHOT"

        def input_tap(self, serial, x, y, timeout=10):
            return FakeResult()

        def wm_size(self, serial, timeout=10):
            return 1200, 1920, "Physical size: 1200x1920"

    with SessionLocal() as db:
        device = Device(
            serial="FAKE_SERIAL",
            status="online",
            manufacturer="AISPEECH",
            model="AINOTE-A2",
            android_version="13",
            sdk_int="33",
            screen_width=1200,
            screen_height=1920,
            density="320",
            capabilities={"adb": {"adbState": "device"}},
            last_seen_at=now_utc(),
        )
        db.add(device)
        db.commit()
        db.refresh(device)

        case = TestCaseService().create_case(
            db,
            TestCaseCreateRequest.model_validate(
                {
                    "name": "pixel audit report case",
                    "type": "ui",
                    "priority": "P0",
                    "steps": [
                        {
                            "action": "pixel_tap",
                            "pixelFallback": True,
                            "fallbackReason": "控件未暴露稳定语义定位",
                            "riskNote": "坐标依赖当前 A2 分辨率与方向",
                            "improvementSuggestion": "补充 resource-id 或 content-desc",
                            "x": 100,
                            "y": 200,
                            "screenWidth": 1200,
                            "screenHeight": 1920,
                            "orientation": "portrait",
                        }
                    ],
                }
            ),
        )
        service = TestRunService(command_service=CommandService(adb=FakeAdb(), device_service=DeviceService(adb=FakeAdb())))
        run = service.create_and_execute(db, RunCreateRequest(deviceId=device.id, caseIds=[case.id], config={}))
        db.commit()
        db.refresh(run)

        result = run.results[0]
        serialized = test_result_to_dict(result)

        assert serialized["pixelFallbackUsed"] is True
        assert serialized["pixelAudit"]["fallbackReason"] == "控件未暴露稳定语义定位"
        assert serialized["pixelAudit"]["x"] == 100
        assert serialized["pixelAudit"]["screenWidth"] == 1200
        assert serialized["pixelAudit"]["riskNote"] == "坐标依赖当前 A2 分辨率与方向"
        assert serialized["raw"]["steps"][0]["pixelAudit"]["improvementSuggestion"] == "补充 resource-id 或 content-desc"

        html_artifact = next(artifact for artifact in run.artifacts if artifact.type == "report_html")
        json_artifact = next(artifact for artifact in run.artifacts if artifact.type == "report_json")
        html_text = Path(html_artifact.path).read_text(encoding="utf-8")
        json_text = Path(json_artifact.path).read_text(encoding="utf-8")

        assert artifact_to_dict(html_artifact)["mimeType"] == "text/html"
        assert "fallbackReason" in html_text
        assert "控件未暴露稳定语义定位" in html_text
        assert "screenWidth" in html_text
        assert "坐标依赖当前 A2 分辨率与方向" in html_text
        assert "pixelAudit" in json_text
        assert "补充 resource-id 或 content-desc" in json_text
