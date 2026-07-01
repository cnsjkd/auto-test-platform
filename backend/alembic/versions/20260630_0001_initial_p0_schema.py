"""initial p0 schema

Revision ID: 20260630_0001
Revises:
Create Date: 2026-06-30 00:01:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260630_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("serial", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("android_version", sa.String(length=64), nullable=True),
        sa.Column("sdk_int", sa.String(length=32), nullable=True),
        sa.Column("screen_width", sa.Integer(), nullable=True),
        sa.Column("screen_height", sa.Integer(), nullable=True),
        sa.Column("density", sa.String(length=64), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("serial", name="uq_devices_serial"),
    )
    op.create_index("ix_devices_status", "devices", ["status"])
    op.create_index("ix_devices_model", "devices", ["model"])
    op.create_index("ix_devices_last_seen_at", "devices", ["last_seen_at"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("has_pixel_fallback", sa.Boolean(), nullable=False),
        sa.Column("pixel_fallback_count", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_cases_status", "test_cases", ["status"])
    op.create_index("ix_test_cases_priority", "test_cases", ["priority"])
    op.create_index("ix_test_cases_has_pixel_fallback", "test_cases", ["has_pixel_fallback"])
    op.create_index("ix_test_cases_updated_at", "test_cases", ["updated_at"])

    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_path", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_runs_status", "test_runs", ["status"])
    op.create_index("ix_test_runs_device_id", "test_runs", ["device_id"])
    op.create_index("ix_test_runs_started_at", "test_runs", ["started_at"])

    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("test_runs.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("test_cases.id"), nullable=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("locator_strategy", sa.String(length=128), nullable=True),
        sa.Column("pixel_fallback_used", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
    )
    op.create_index("ix_test_results_run_id", "test_results", ["run_id"])
    op.create_index("ix_test_results_case_id", "test_results", ["case_id"])
    op.create_index("ix_test_results_device_id", "test_results", ["device_id"])
    op.create_index("ix_test_results_status", "test_results", ["status"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("test_runs.id"), nullable=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("test_results.id"), nullable=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("ix_artifacts_result_id", "artifacts", ["result_id"])
    op.create_index("ix_artifacts_device_id", "artifacts", ["device_id"])
    op.create_index("ix_artifacts_type", "artifacts", ["type"])
    op.create_index("ix_artifacts_created_at", "artifacts", ["created_at"])

    op.create_table(
        "locator_fallbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("test_runs.id"), nullable=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("test_results.id"), nullable=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("test_cases.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("screen_width", sa.Integer(), nullable=False),
        sa.Column("screen_height", sa.Integer(), nullable=False),
        sa.Column("orientation", sa.String(length=32), nullable=False),
        sa.Column("fallback_reason", sa.Text(), nullable=False),
        sa.Column("risk_note", sa.Text(), nullable=False),
        sa.Column("improvement_suggestion", sa.Text(), nullable=False),
        sa.Column("before_artifact_id", sa.Integer(), sa.ForeignKey("artifacts.id"), nullable=True),
        sa.Column("after_artifact_id", sa.Integer(), sa.ForeignKey("artifacts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_locator_fallbacks_run_id", "locator_fallbacks", ["run_id"])
    op.create_index("ix_locator_fallbacks_device_id", "locator_fallbacks", ["device_id"])
    op.create_index("ix_locator_fallbacks_case_id", "locator_fallbacks", ["case_id"])
    op.create_index("ix_locator_fallbacks_created_at", "locator_fallbacks", ["created_at"])

    op.create_table(
        "device_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("test_runs.id"), nullable=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("test_results.id"), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("test_cases.id"), nullable=True),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locator_mode", sa.String(length=64), nullable=True),
        sa.Column("selector", sa.JSON(), nullable=True),
        sa.Column("pixel_fallback_used", sa.Boolean(), nullable=False),
        sa.Column("locator_fallback_id", sa.Integer(), sa.ForeignKey("locator_fallbacks.id"), nullable=True),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_device_commands_device_id", "device_commands", ["device_id"])
    op.create_index("ix_device_commands_run_id", "device_commands", ["run_id"])
    op.create_index("ix_device_commands_result_id", "device_commands", ["result_id"])
    op.create_index("ix_device_commands_command_type", "device_commands", ["command_type"])
    op.create_index("ix_device_commands_status", "device_commands", ["status"])
    op.create_index("ix_device_commands_locator_fallback_id", "device_commands", ["locator_fallback_id"])
    op.create_index("ix_device_commands_started_at", "device_commands", ["started_at"])

    op.create_table(
        "platform_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("test_runs.id"), nullable=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_platform_events_run_id", "platform_events", ["run_id"])
    op.create_index("ix_platform_events_device_id", "platform_events", ["device_id"])
    op.create_index("ix_platform_events_level", "platform_events", ["level"])
    op.create_index("ix_platform_events_created_at", "platform_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_platform_events_created_at", table_name="platform_events")
    op.drop_index("ix_platform_events_level", table_name="platform_events")
    op.drop_index("ix_platform_events_device_id", table_name="platform_events")
    op.drop_index("ix_platform_events_run_id", table_name="platform_events")
    op.drop_table("platform_events")

    op.drop_index("ix_device_commands_started_at", table_name="device_commands")
    op.drop_index("ix_device_commands_locator_fallback_id", table_name="device_commands")
    op.drop_index("ix_device_commands_status", table_name="device_commands")
    op.drop_index("ix_device_commands_command_type", table_name="device_commands")
    op.drop_index("ix_device_commands_result_id", table_name="device_commands")
    op.drop_index("ix_device_commands_run_id", table_name="device_commands")
    op.drop_index("ix_device_commands_device_id", table_name="device_commands")
    op.drop_table("device_commands")

    op.drop_index("ix_locator_fallbacks_created_at", table_name="locator_fallbacks")
    op.drop_index("ix_locator_fallbacks_case_id", table_name="locator_fallbacks")
    op.drop_index("ix_locator_fallbacks_device_id", table_name="locator_fallbacks")
    op.drop_index("ix_locator_fallbacks_run_id", table_name="locator_fallbacks")
    op.drop_table("locator_fallbacks")

    op.drop_index("ix_artifacts_created_at", table_name="artifacts")
    op.drop_index("ix_artifacts_type", table_name="artifacts")
    op.drop_index("ix_artifacts_device_id", table_name="artifacts")
    op.drop_index("ix_artifacts_result_id", table_name="artifacts")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_test_results_status", table_name="test_results")
    op.drop_index("ix_test_results_device_id", table_name="test_results")
    op.drop_index("ix_test_results_case_id", table_name="test_results")
    op.drop_index("ix_test_results_run_id", table_name="test_results")
    op.drop_table("test_results")

    op.drop_index("ix_test_runs_started_at", table_name="test_runs")
    op.drop_index("ix_test_runs_device_id", table_name="test_runs")
    op.drop_index("ix_test_runs_status", table_name="test_runs")
    op.drop_table("test_runs")

    op.drop_index("ix_test_cases_updated_at", table_name="test_cases")
    op.drop_index("ix_test_cases_has_pixel_fallback", table_name="test_cases")
    op.drop_index("ix_test_cases_priority", table_name="test_cases")
    op.drop_index("ix_test_cases_status", table_name="test_cases")
    op.drop_table("test_cases")

    op.drop_index("ix_devices_last_seen_at", table_name="devices")
    op.drop_index("ix_devices_model", table_name="devices")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_table("devices")
