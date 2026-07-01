from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Artifact
from app.models.entities import now_utc


MIME_BY_TYPE = {
    "screenshot": "image/png",
    "pixel_audit": "image/png",
    "hierarchy": "application/xml",
    "logcat": "text/plain",
    "report_json": "application/json",
    "report_html": "text/html",
}


class ArtifactManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.artifact_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(
        self,
        db: Session,
        *,
        content: bytes,
        artifact_type: str,
        run_id: int | None = None,
        result_id: int | None = None,
        device_id: int | None = None,
        name: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Artifact:
        file_name = self._safe_name(name, artifact_type)
        path = self._build_path(run_id, artifact_type, file_name)
        path.write_bytes(content)
        return self._record(db, path, artifact_type, run_id, result_id, device_id, meta)

    def save_text(
        self,
        db: Session,
        *,
        text: str,
        artifact_type: str,
        run_id: int | None = None,
        result_id: int | None = None,
        device_id: int | None = None,
        name: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Artifact:
        extension = "html" if artifact_type == "report_html" else "json" if artifact_type == "report_json" else "txt"
        if artifact_type == "hierarchy":
            extension = "xml"
        file_name = self._safe_name(name, artifact_type, extension=extension)
        path = self._build_path(run_id, artifact_type, file_name)
        path.write_text(text, encoding="utf-8")
        return self._record(db, path, artifact_type, run_id, result_id, device_id, meta)

    def save_json(
        self,
        db: Session,
        *,
        payload: dict[str, Any],
        artifact_type: str = "report_json",
        run_id: int | None = None,
        result_id: int | None = None,
        device_id: int | None = None,
        name: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Artifact:
        return self.save_text(
            db,
            text=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            artifact_type=artifact_type,
            run_id=run_id,
            result_id=result_id,
            device_id=device_id,
            name=name,
            meta=meta,
        )

    def _record(
        self,
        db: Session,
        path: Path,
        artifact_type: str,
        run_id: int | None,
        result_id: int | None,
        device_id: int | None,
        meta: dict[str, Any] | None,
    ) -> Artifact:
        content = path.read_bytes()
        artifact = Artifact(
            run_id=run_id,
            result_id=result_id,
            device_id=device_id,
            type=artifact_type,
            path=str(path),
            mime_type=MIME_BY_TYPE.get(artifact_type, "application/octet-stream"),
            size_bytes=len(content),
            checksum=hashlib.sha256(content).hexdigest(),
            meta=meta or {},
            created_at=now_utc(),
        )
        db.add(artifact)
        db.flush()
        return artifact

    def _build_path(self, run_id: int | None, artifact_type: str, file_name: str) -> Path:
        date_part = datetime.now().strftime("%Y-%m-%d")
        run_part = str(run_id) if run_id is not None else "manual"
        directory = self.root / date_part / run_part / artifact_type
        directory.mkdir(parents=True, exist_ok=True)
        return directory / file_name

    def _safe_name(self, name: str | None, artifact_type: str, extension: str | None = None) -> str:
        suffix = extension or ("png" if artifact_type in {"screenshot", "pixel_audit"} else "txt")
        stem = name or f"{artifact_type}_{datetime.now().strftime('%H%M%S_%f')}"
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem).strip("_")
        if not safe:
            safe = artifact_type
        if not safe.endswith(f".{suffix}"):
            safe = f"{safe}.{suffix}"
        return safe
