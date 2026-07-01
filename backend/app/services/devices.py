from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.adb import AdbAdapter, orientation_from_size
from app.core.errors import AppException, DEVICE_NOT_CONNECTED, DEVICE_UNAUTHORIZED, NOT_FOUND
from app.models import Device


class DeviceService:
    def __init__(self, adb: AdbAdapter | None = None) -> None:
        self.adb = adb or AdbAdapter()

    def health(self) -> dict[str, Any]:
        adb_info = self.adb.version()
        return adb_info

    def list_devices(self, db: Session, status: str | None = None) -> list[Device]:
        query = select(Device).order_by(Device.last_seen_at.desc().nullslast(), Device.id.desc())
        if status:
            query = query.where(Device.status == status)
        return list(db.scalars(query).all())

    def get_device(self, db: Session, device_id: int) -> Device:
        device = db.get(Device, device_id)
        if not device:
            raise AppException(NOT_FOUND, "device not found", 404)
        return device

    def scan(self, db: Session) -> list[Device]:
        if not self.adb.is_available():
            return []
        scanned = self.adb.list_devices()
        devices: list[Device] = []
        seen_serials: set[str] = set()
        for item in scanned:
            serial = item["serial"]
            seen_serials.add(serial)
            status = self._normalize_status(item.get("adbState", "unknown"))
            device = db.scalar(select(Device).where(Device.serial == serial))
            if device is None:
                device = Device(serial=serial)
                db.add(device)
            device.status = status
            device.last_seen_at = datetime.now(timezone.utc)
            device.capabilities = {"adb": item, "orientation": None, "battery": None, "network": None, "storage": None}
            if status == "online":
                self._hydrate_online_device(device)
            elif status == "unauthorized":
                device.capabilities = {
                    **(device.capabilities or {}),
                    "repairSuggestion": "设备未授权：请在 A2 上确认 USB 调试 RSA 授权弹窗后重新扫描。",
                }
            elif status == "offline":
                device.capabilities = {
                    **(device.capabilities or {}),
                    "repairSuggestion": "设备 offline：请检查 USB 线缆、重新插拔设备或重启 adb server。",
                }
            devices.append(device)
        db.flush()
        return devices

    def ensure_online(self, db: Session, device_id: int) -> Device:
        device = self.get_device(db, device_id)
        if device.status == "unauthorized":
            raise AppException(DEVICE_UNAUTHORIZED, "device is unauthorized; confirm USB debugging RSA prompt", 503)
        if device.status != "online":
            raise AppException(DEVICE_NOT_CONNECTED, "device is not online", 503)
        return device

    def refresh_device_screen(self, device: Device) -> None:
        if not device.serial or device.status != "online":
            return
        width, height, _ = self.adb.wm_size(device.serial)
        if width and height:
            device.screen_width = width
            device.screen_height = height
            capabilities = device.capabilities or {}
            capabilities["orientation"] = orientation_from_size(width, height)
            device.capabilities = capabilities

    def _hydrate_online_device(self, device: Device) -> None:
        serial = device.serial
        manufacturer = self.adb.getprop(serial, "ro.product.manufacturer")
        model = self.adb.getprop(serial, "ro.product.model")
        android_version = self.adb.getprop(serial, "ro.build.version.release")
        sdk_int = self.adb.getprop(serial, "ro.build.version.sdk")
        width, height, wm_raw = self.adb.wm_size(serial)
        density = self.adb.wm_density(serial)
        battery = self.adb.dumpsys_battery(serial)
        device.manufacturer = manufacturer.stdout.strip() if manufacturer.ok else None
        device.model = model.stdout.strip() if model.ok else None
        device.android_version = android_version.stdout.strip() if android_version.ok else None
        device.sdk_int = sdk_int.stdout.strip() if sdk_int.ok else None
        device.screen_width = width
        device.screen_height = height
        device.density = density
        device.capabilities = {
            **(device.capabilities or {}),
            "wmSizeRaw": wm_raw,
            "orientation": orientation_from_size(width, height),
            "battery": battery,
            "adbAvailable": True,
        }

    def _normalize_status(self, adb_state: str) -> str:
        if adb_state == "device":
            return "online"
        if adb_state in {"unauthorized", "offline"}:
            return adb_state
        return adb_state or "unknown"
