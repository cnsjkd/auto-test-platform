from __future__ import annotations

import html
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.errors import AppException, NOT_FOUND, RUN_NOT_EXECUTABLE
from app.models import Artifact, LocatorFallback, TestCase, TestResult, TestRun
from app.models.entities import now_utc
from app.schemas.contracts import DeviceCommandRequest, RunCreateRequest
from app.schemas.serializers import artifact_to_dict, test_result_to_dict as serialize_test_result, test_run_to_dict as serialize_test_run
from app.services.artifacts import ArtifactManager
from app.services.commands import CommandService
from app.services.events import record_event


__test__ = False


class TestRunService:
    def __init__(self, command_service: CommandService | None = None, artifact_manager: ArtifactManager | None = None) -> None:
        self.commands = command_service or CommandService()
        self.artifacts = artifact_manager or ArtifactManager()

    def list_runs(self, db: Session, *, status: str | None = None, device_id: int | None = None, limit: int = 50) -> list[TestRun]:
        query = select(TestRun).order_by(TestRun.created_at.desc()).limit(min(max(limit, 1), 200))
        if status:
            query = query.where(TestRun.status == status)
        if device_id:
            query = query.where(TestRun.device_id == device_id)
        return list(db.scalars(query).all())

    def get_run(self, db: Session, run_id: int) -> TestRun:
        run = db.get(TestRun, run_id)
        if not run:
            raise AppException(NOT_FOUND, "test run not found", 404)
        return run

    def create_and_execute(self, db: Session, request: RunCreateRequest) -> TestRun:
        if request.deviceId is None:
            raise AppException(RUN_NOT_EXECUTABLE, "deviceId is required for P0 execution", 422)
        if not request.caseIds:
            raise AppException(RUN_NOT_EXECUTABLE, "at least one test case is required", 422)
        cases = self._resolve_cases(db, request.caseIds)
        run = TestRun(
            status="running",
            device_id=request.deviceId,
            total_count=len(cases),
            started_at=now_utc(),
            config=request.config,
        )
        db.add(run)
        db.flush()
        record_event(db, run_id=run.id, device_id=run.device_id, category="run_started", message="test run started")
        for case in cases:
            if run.status == "canceled":
                run.skipped_count += 1
                continue
            result = self._execute_case(db, run, case)
            if result.status == "passed":
                run.passed_count += 1
            elif result.status == "failed":
                run.failed_count += 1
            else:
                run.skipped_count += 1
            db.flush()
        if run.status != "canceled":
            run.status = "failed" if run.failed_count else "passed"
        run.ended_at = now_utc()
        self._generate_reports(db, run)
        record_event(
            db,
            run_id=run.id,
            device_id=run.device_id,
            category="run_finished",
            message=f"test run finished with status {run.status}",
            payload=serialize_test_run(run),
        )
        db.flush()
        return run

    def create_queued(self, db: Session, request: RunCreateRequest) -> TestRun:
        if request.deviceId is None:
            raise AppException(RUN_NOT_EXECUTABLE, "deviceId is required for P0 execution", 422)
        if not request.caseIds:
            raise AppException(RUN_NOT_EXECUTABLE, "at least one test case is required", 422)
        cases = self._resolve_cases(db, request.caseIds)
        run = TestRun(
            status="queued",
            device_id=request.deviceId,
            total_count=len(cases),
            config=request.config,
        )
        db.add(run)
        db.flush()
        record_event(db, run_id=run.id, device_id=run.device_id, category="run_queued", message="test run queued")
        return run

    def execute_queued(self, db: Session, run_id: int, request: RunCreateRequest) -> TestRun:
        run = self.get_run(db, run_id)
        if request.deviceId is None:
            raise AppException(RUN_NOT_EXECUTABLE, "deviceId is required for P0 execution", 422)
        if not request.caseIds:
            raise AppException(RUN_NOT_EXECUTABLE, "at least one test case is required", 422)
        cases = self._resolve_cases(db, request.caseIds)
        if run.status not in {"queued", "running"}:
            raise AppException(RUN_NOT_EXECUTABLE, "test run is already finished", 422)
        run.status = "running"
        run.device_id = request.deviceId
        run.total_count = len(cases)
        run.passed_count = 0
        run.failed_count = 0
        run.skipped_count = 0
        run.started_at = now_utc()
        run.ended_at = None
        run.config = request.config
        db.flush()
        record_event(db, run_id=run.id, device_id=run.device_id, category="run_started", message="test run started")
        db.commit()
        for case in cases:
            db.refresh(run)
            if run.status == "canceled":
                run.skipped_count += 1
                db.flush()
                db.commit()
                continue
            result = self._execute_case(db, run, case)
            if result.status == "passed":
                run.passed_count += 1
            elif result.status == "failed":
                run.failed_count += 1
            else:
                run.skipped_count += 1
            db.flush()
            db.commit()
        db.refresh(run)
        if run.status != "canceled":
            run.status = "failed" if run.failed_count else "passed"
        run.ended_at = now_utc()
        self._generate_reports(db, run)
        record_event(
            db,
            run_id=run.id,
            device_id=run.device_id,
            category="run_finished",
            message=f"test run finished with status {run.status}",
            payload=serialize_test_run(run),
        )
        db.flush()
        db.commit()
        return run

    def cancel(self, db: Session, run_id: int, reason: str) -> TestRun:
        run = self.get_run(db, run_id)
        if run.status in {"passed", "failed", "canceled"}:
            raise AppException(RUN_NOT_EXECUTABLE, "test run is already finished", 422)
        run.status = "canceled"
        run.ended_at = now_utc()
        record_event(db, run_id=run.id, device_id=run.device_id, category="run_canceled", message=reason, level="warning")
        db.flush()
        return run

    def artifacts_for_run(self, db: Session, run_id: int, type_: str | None = None) -> list[Artifact]:
        self.get_run(db, run_id)
        query = select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at.desc())
        if type_:
            query = query.where(Artifact.type == type_)
        return list(db.scalars(query).all())

    def _resolve_cases(self, db: Session, case_ids: list[int]) -> list[TestCase]:
        if case_ids:
            cases = list(db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all())
            missing = set(case_ids) - {case.id for case in cases}
            if missing:
                raise AppException(NOT_FOUND, f"test cases not found: {sorted(missing)}", 404)
            return cases
        return list(db.scalars(select(TestCase).where(TestCase.status == "enabled").order_by(TestCase.id.asc())).all())

    def _execute_case(self, db: Session, run: TestRun, case: TestCase) -> TestResult:
        result = TestResult(
            run_id=run.id,
            case_id=case.id,
            device_id=run.device_id,
            status="running",
            pixel_fallback_used=False,
            started_at=now_utc(),
            raw={"caseName": case.name, "steps": []},
        )
        db.add(result)
        db.flush()
        record_event(db, run_id=run.id, device_id=run.device_id, category="case_started", message=case.name, payload={"caseId": case.id})
        started = time.perf_counter()
        try:
            if run.device_id is None:
                raise AppException(RUN_NOT_EXECUTABLE, "deviceId is required for P0 execution", 422)
            for index, step in enumerate(case.steps or []):
                action = step.get("action")
                request = DeviceCommandRequest.model_validate(step)
                command, artifacts = self.commands.execute(
                    db,
                    device_id=run.device_id,
                    request=request,
                    run_id=run.id,
                    result_id=result.id,
                    case_id=case.id,
                    source="test_run",
                )
                raw = dict(result.raw or {})
                steps = list(raw.get("steps") or [])
                step_detail = {
                    "index": index,
                    "action": action,
                    "commandId": command.id,
                    "status": command.status,
                    "artifactIds": [artifact.id for artifact in artifacts],
                }
                if action in {"pixel_tap", "pixel_swipe"}:
                    result.pixel_fallback_used = True
                    pixel_audit = self._pixel_audit_from_command(db, command)
                    step_detail["pixelAudit"] = pixel_audit
                    raw.setdefault("pixelAudit", pixel_audit)
                steps.append(step_detail)
                raw["steps"] = steps
                result.raw = raw
                flag_modified(result, "raw")
            result.status = "passed"
            result.message = "passed"
        except AppException as exc:
            result.status = "failed"
            result.error_code = exc.code
            result.message = exc.message
            result.raw.setdefault("failure", {"code": exc.code, "message": exc.message})
            if run.device_id is not None:
                self._collect_failure_evidence(db, run, result)
            record_event(
                db,
                run_id=run.id,
                device_id=run.device_id,
                category="case_failed",
                message=exc.message,
                level="error",
                payload={"caseId": case.id, "errorCode": exc.code},
            )
        except Exception as exc:
            result.status = "failed"
            result.error_code = 50001
            result.message = str(exc)
            result.raw.setdefault("failure", {"code": 50001, "message": str(exc)})
            if run.device_id is not None:
                self._collect_failure_evidence(db, run, result)
            record_event(db, run_id=run.id, device_id=run.device_id, category="case_failed", message=str(exc), level="error")
        finally:
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            result.ended_at = now_utc()
            record_event(
                db,
                run_id=run.id,
                device_id=run.device_id,
                category="case_finished",
                message=f"{case.name}: {result.status}",
                payload={"caseId": case.id, "resultId": result.id, "status": result.status},
            )
            db.flush()
        return result

    def _pixel_audit_from_command(self, db: Session, command) -> dict[str, Any]:
        fallback = db.get(LocatorFallback, command.locator_fallback_id) if command.locator_fallback_id else None
        if fallback:
            return {
                "pixelFallback": True,
                "fallbackReason": fallback.fallback_reason,
                "x": fallback.x,
                "y": fallback.y,
                "screenWidth": fallback.screen_width,
                "screenHeight": fallback.screen_height,
                "orientation": fallback.orientation,
                "riskNote": fallback.risk_note,
                "improvementSuggestion": fallback.improvement_suggestion,
            }
        response = command.response or {}
        pixel_audit = response.get("pixelAudit") if isinstance(response, dict) else None
        if isinstance(pixel_audit, dict):
            return pixel_audit
        params = command.params or {}
        return {
            "pixelFallback": True,
            "fallbackReason": str(params.get("fallbackReason") or ""),
            "x": int(params.get("x") or 0),
            "y": int(params.get("y") or 0),
            "screenWidth": int(params.get("screenWidth") or 0),
            "screenHeight": int(params.get("screenHeight") or 0),
            "orientation": str(params.get("orientation") or "portrait"),
            "riskNote": str(params.get("riskNote") or ""),
            "improvementSuggestion": str(params.get("improvementSuggestion") or ""),
        }

    def _collect_failure_evidence(self, db: Session, run: TestRun, result: TestResult) -> None:
        if run.device_id is None:
            return
        for collector in (
            lambda: self.commands.capture_screenshot(db, device_id=run.device_id or 0, run_id=run.id, result_id=result.id, name="run_failure_screenshot"),
            lambda: self.commands.capture_hierarchy(db, device_id=run.device_id or 0, run_id=run.id, result_id=result.id, name="run_failure_hierarchy"),
            lambda: self.commands.capture_logcat(db, device_id=run.device_id or 0, run_id=run.id, result_id=result.id, name="run_failure_logcat"),
        ):
            try:
                collector()
            except Exception:
                continue

    def _generate_reports(self, db: Session, run: TestRun) -> None:
        results = list(db.scalars(select(TestResult).where(TestResult.run_id == run.id)).all())
        artifacts = list(db.scalars(select(Artifact).where(Artifact.run_id == run.id)).all())
        payload: dict[str, Any] = {
            "run": serialize_test_run(run),
            "results": [serialize_test_result(result) for result in results],
            "artifacts": [artifact_to_dict(artifact) for artifact in artifacts],
        }
        json_artifact = self.artifacts.save_json(db, payload=payload, run_id=run.id, device_id=run.device_id, name=f"run_{run.id}_report")
        html_text = self._render_html_report(payload)
        html_artifact = self.artifacts.save_text(
            db,
            text=html_text,
            artifact_type="report_html",
            run_id=run.id,
            device_id=run.device_id,
            name=f"run_{run.id}_report",
        )
        run.report_path = html_artifact.path or json_artifact.path

    def _render_html_report(self, payload: dict[str, Any]) -> str:
        run = payload["run"]
        rows = []
        audit_items = []
        for result in payload["results"]:
            audit = result.get("pixelAudit") or {}
            coordinate = ""
            if audit:
                coordinate = (
                    f"x={audit.get('x', '')}, y={audit.get('y', '')}, "
                    f"screenWidth={audit.get('screenWidth', '')}, screenHeight={audit.get('screenHeight', '')}, "
                    f"orientation={audit.get('orientation', '')}"
                )
                audit_items.append(
                    "<section class=\"audit\">"
                    f"<h3>Result #{html.escape(str(result['id']))} Pixel Audit</h3>"
                    "<dl class=\"audit-grid\">"
                    f"<dt>fallbackReason</dt><dd>{html.escape(str(audit.get('fallbackReason', '')))}</dd>"
                    f"<dt>x</dt><dd>{html.escape(str(audit.get('x', '')))}</dd>"
                    f"<dt>y</dt><dd>{html.escape(str(audit.get('y', '')))}</dd>"
                    f"<dt>screenWidth</dt><dd>{html.escape(str(audit.get('screenWidth', '')))}</dd>"
                    f"<dt>screenHeight</dt><dd>{html.escape(str(audit.get('screenHeight', '')))}</dd>"
                    f"<dt>orientation</dt><dd>{html.escape(str(audit.get('orientation', '')))}</dd>"
                    f"<dt>riskNote</dt><dd>{html.escape(str(audit.get('riskNote', '')))}</dd>"
                    f"<dt>improvementSuggestion</dt><dd>{html.escape(str(audit.get('improvementSuggestion', '')))}</dd>"
                    "</dl></section>"
                )
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(result['id']))}</td>"
                f"<td>{html.escape(str(result['caseId']))}</td>"
                f"<td>{html.escape(str(result.get('caseName') or ''))}</td>"
                f"<td>{html.escape(str(result['status']))}</td>"
                f"<td>{html.escape(str(result.get('errorCode') or ''))}</td>"
                f"<td>{html.escape(str(result.get('message') or ''))}</td>"
                f"<td>{'yes' if result.get('pixelFallbackUsed') else 'no'}</td>"
                f"<td>{html.escape(str(audit.get('fallbackReason', '')))}</td>"
                f"<td>{html.escape(coordinate)}</td>"
                f"<td>{html.escape(str(audit.get('riskNote', '')))}</td>"
                f"<td>{html.escape(str(audit.get('improvementSuggestion', '')))}</td>"
                "</tr>"
            )
        artifact_items = [f"<li>{html.escape(a['type'])}: {html.escape(a['fileName'])}</li>" for a in payload["artifacts"]]
        audit_section = "".join(audit_items) if audit_items else "<p>No pixel fallback audit entries.</p>"
        return f"""<!doctype html>
<html lang=\"zh-CN\">
<head><meta charset=\"utf-8\"><title>A2 Test Run {run['id']} Report</title>
<style>body{{font-family:Arial,'Noto Sans SC',sans-serif;background:#0D1117;color:#F9FAFB;padding:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #374151;padding:8px;vertical-align:top}}.warn{{color:#D97706}}.audit{{border:1px solid #7F1D1D;background:#1F2937;margin:16px 0;padding:12px}}.audit-grid{{display:grid;grid-template-columns:220px 1fr;gap:8px}}dt{{color:#FCA5A5}}dd{{margin:0}}</style></head>
<body>
<h1>A2 Test Run #{html.escape(str(run['id']))}</h1>
<p>Status: <strong>{html.escape(str(run['status']))}</strong>; Device: {html.escape(str(run.get('deviceId')))}</p>
<p>Total: {run['totalCount']} Passed: {run['passedCount']} Failed: {run['failedCount']} Skipped: {run['skippedCount']}</p>
<h2>Results</h2>
<table><thead><tr><th>ID</th><th>Case</th><th>Case Name</th><th>Status</th><th>Error</th><th>Message</th><th>Pixel Fallback</th><th>fallbackReason</th><th>Coordinates / screenWidth / screenHeight</th><th>riskNote</th><th>improvementSuggestion</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Pixel Fallback Audit</h2>{audit_section}
<h2>Artifacts</h2><ul>{''.join(artifact_items)}</ul>
<p class=\"warn\">Pixel fallback entries must be reviewed for stability risk and testability improvement.</p>
</body></html>"""
