from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.db.session import engine
from app.models import Base


def init_db() -> None:
    Path(settings.artifact_root).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
