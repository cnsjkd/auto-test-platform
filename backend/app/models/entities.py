from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("serial", name="uq_devices_serial"),
        Index("ix_devices_status", "status"),
        Index("ix_devices_model", "model"),
        Index("ix_devices_last_seen_at", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    android_version: Mapped[str | None] = mapped_column(String(64))
    sdk_int: Mapped[str | None] = mapped_column(String(32))
    screen_width: Mapped[int | None] = mapped_column(Integer)
    screen_height: Mapped[int | None] = mapped_column(Integer)
    density: Mapped[str | None] = mapped_column(String(64))
    capabilities: Mapped[dict | None] = mapped_column(JSON, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    commands: Mapped[list["DeviceCommand"]] = relationship(back_populates="device")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="device")
    runs: Mapped[list["TestRun"]] = relationship(back_populates="device")


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        Index("ix_test_cases_status", "status"),
        Index("ix_test_cases_priority", "priority"),
        Index("ix_test_cases_has_pixel_fallback", "has_pixel_fallback"),
        Index("ix_test_cases_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="P2")
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="enabled")
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    has_pixel_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pixel_fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    results: Mapped[list["TestResult"]] = relationship(back_populates="case")


class TestRun(Base):
    __tablename__ = "test_runs"
    __table_args__ = (
        Index("ix_test_runs_status", "status"),
        Index("ix_test_runs_device_id", "device_id"),
        Index("ix_test_runs_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_path: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    device: Mapped[Device | None] = relationship(back_populates="runs")
    results: Mapped[list["TestResult"]] = relationship(back_populates="run")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run")
    events: Mapped[list["PlatformEvent"]] = relationship(back_populates="run")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        Index("ix_test_results_run_id", "run_id"),
        Index("ix_test_results_case_id", "case_id"),
        Index("ix_test_results_device_id", "device_id"),
        Index("ix_test_results_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id"))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    locator_strategy: Mapped[str | None] = mapped_column(String(128))
    pixel_fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict | None] = mapped_column(JSON, default=dict)

    run: Mapped[TestRun] = relationship(back_populates="results")
    case: Mapped[TestCase | None] = relationship(back_populates="results")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="result")


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_run_id", "run_id"),
        Index("ix_artifacts_result_id", "result_id"),
        Index("ix_artifacts_device_id", "device_id"),
        Index("ix_artifacts_type", "type"),
        Index("ix_artifacts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("test_runs.id"))
    result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id"))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128))
    meta: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    run: Mapped[TestRun | None] = relationship(back_populates="artifacts")
    result: Mapped[TestResult | None] = relationship(back_populates="artifacts")
    device: Mapped[Device | None] = relationship(back_populates="artifacts")


class LocatorFallback(Base):
    __tablename__ = "locator_fallbacks"
    __table_args__ = (
        Index("ix_locator_fallbacks_run_id", "run_id"),
        Index("ix_locator_fallbacks_device_id", "device_id"),
        Index("ix_locator_fallbacks_case_id", "case_id"),
        Index("ix_locator_fallbacks_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("test_runs.id"))
    result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id"))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    screen_width: Mapped[int] = mapped_column(Integer, nullable=False)
    screen_height: Mapped[int] = mapped_column(Integer, nullable=False)
    orientation: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_note: Mapped[str] = mapped_column(Text, nullable=False)
    improvement_suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    before_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("artifacts.id"))
    after_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("artifacts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DeviceCommand(Base):
    __tablename__ = "device_commands"
    __table_args__ = (
        Index("ix_device_commands_device_id", "device_id"),
        Index("ix_device_commands_run_id", "run_id"),
        Index("ix_device_commands_result_id", "result_id"),
        Index("ix_device_commands_command_type", "command_type"),
        Index("ix_device_commands_status", "status"),
        Index("ix_device_commands_locator_fallback_id", "locator_fallback_id"),
        Index("ix_device_commands_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("test_runs.id"))
    result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id"))
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="api")
    params: Mapped[dict | None] = mapped_column(JSON, default=dict)
    response: Mapped[dict | None] = mapped_column(JSON, default=dict)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    locator_mode: Mapped[str | None] = mapped_column(String(64))
    selector: Mapped[dict | None] = mapped_column(JSON, default=dict)
    pixel_fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locator_fallback_id: Mapped[int | None] = mapped_column(ForeignKey("locator_fallbacks.id"))
    error_code: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device | None] = relationship(back_populates="commands")


class PlatformEvent(Base):
    __tablename__ = "platform_events"
    __table_args__ = (
        Index("ix_platform_events_run_id", "run_id"),
        Index("ix_platform_events_device_id", "device_id"),
        Index("ix_platform_events_level", "level"),
        Index("ix_platform_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("test_runs.id"))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    level: Mapped[str] = mapped_column(String(32), nullable=False, default="info")
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    run: Mapped[TestRun | None] = relationship(back_populates="events")
