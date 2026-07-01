from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel


def load_dotenv(base_dir: Path) -> None:
    for env_path in (base_dir.parent / ".env", base_dir / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break


class Settings(BaseModel):
    app_name: str = "A2 Automation Test Platform"
    api_prefix: str = "/api"
    base_dir: Path = Path(__file__).resolve().parents[2]
    database_url: str = ""
    artifact_root: Path = Path("")
    adb_timeout_sec: int = 30

    @classmethod
    def load(cls) -> "Settings":
        base_dir = Path(__file__).resolve().parents[2]
        load_dotenv(base_dir)
        database_url = os.getenv("A2_DB_URL", f"sqlite:///{base_dir / 'a2_automation.db'}")
        artifact_root = Path(os.getenv("A2_ARTIFACT_ROOT", str(base_dir / "artifacts"))).resolve()
        return cls(base_dir=base_dir, database_url=database_url, artifact_root=artifact_root)


settings = Settings.load()
