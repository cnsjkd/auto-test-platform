from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.errors import ADB_UNAVAILABLE, AppException, PARAM_ERROR, UI_AUTOMATION_FAILED


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
UI_DUMP_REMOTE_PATH = "/sdcard/window_dump.xml"


@dataclass
class AdbResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    stdout_bytes: bytes | None = None


class AdbAdapter:
    def __init__(self) -> None:
        self.adb_path = shutil.which("adb")

    def is_available(self) -> bool:
        return self.adb_path is not None

    def version(self) -> dict:
        if not self.adb_path:
            return {"available": False, "version": None, "message": "adb not found in PATH"}
        result = self._run(["version"], timeout=5)
        return {
            "available": result.ok,
            "version": result.stdout.strip() if result.ok else None,
            "message": result.stderr.strip() if not result.ok else "",
        }

    def list_devices(self) -> list[dict]:
        if not self.adb_path:
            return []
        result = self._run(["devices", "-l"], timeout=10)
        if not result.ok:
            return []
        devices: list[dict] = []
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            detail = {"serial": serial, "adbState": state, "raw": line}
            for token in parts[2:]:
                if ":" in token:
                    key, value = token.split(":", 1)
                    detail[key] = value
            devices.append(detail)
        return devices

    def getprop(self, serial: str, prop: str | None = None, timeout: int = 10) -> AdbResult:
        args = ["shell", "getprop"]
        if prop:
            args.append(prop)
        return self._run_serial(serial, args, timeout=timeout)

    def wm_size(self, serial: str, timeout: int = 10) -> tuple[int | None, int | None, str]:
        result = self._run_serial(serial, ["shell", "wm", "size"], timeout=timeout)
        if not result.ok:
            return None, None, result.stderr or result.stdout
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", result.stdout)
        if not match:
            return None, None, result.stdout.strip()
        return int(match.group(1)), int(match.group(2)), result.stdout.strip()

    def wm_density(self, serial: str, timeout: int = 10) -> str | None:
        result = self._run_serial(serial, ["shell", "wm", "density"], timeout=timeout)
        if not result.ok:
            return None
        match = re.search(r"Physical density:\s*(\d+)", result.stdout)
        return match.group(1) if match else result.stdout.strip()

    def dumpsys_battery(self, serial: str, timeout: int = 10) -> dict:
        result = self._run_serial(serial, ["shell", "dumpsys", "battery"], timeout=timeout)
        if not result.ok:
            return {"available": False, "message": result.stderr or result.stdout}
        data: dict[str, str] = {"available": "true"}
        for line in result.stdout.splitlines():
            if ":" in line:
                key, value = line.strip().split(":", 1)
                data[key.strip()] = value.strip()
        return data

    def screenshot_png(self, serial: str, timeout: int = 10) -> bytes:
        result = self._run_serial(serial, ["exec-out", "screencap", "-p"], timeout=timeout, binary=True)
        if not result.ok or result.stdout_bytes is None:
            raise AppException(ADB_UNAVAILABLE, result.stderr or "screenshot failed", 503)
        if not result.stdout_bytes.startswith(PNG_MAGIC):
            header = result.stdout_bytes[:8].hex()
            raise AppException(
                UI_AUTOMATION_FAILED,
                f"screenshot failed: adb screencap returned non-standard PNG header {header}",
                400,
                details={"expectedPngMagic": PNG_MAGIC.hex(), "actualHeader": header},
            )
        return result.stdout_bytes

    def dump_hierarchy(self, serial: str, timeout: int = 20) -> str:
        dump_result = self._run_serial(serial, ["shell", "uiautomator", "dump", UI_DUMP_REMOTE_PATH], timeout=timeout)
        if not dump_result.ok:
            raise AppException(ADB_UNAVAILABLE, dump_result.stderr or dump_result.stdout or "uiautomator dump failed", 503)
        cat_result = self._run_serial(serial, ["exec-out", "cat", UI_DUMP_REMOTE_PATH], timeout=timeout, binary=True)
        if not cat_result.ok or cat_result.stdout_bytes is None:
            raise AppException(ADB_UNAVAILABLE, cat_result.stderr or cat_result.stdout or "uiautomator dump readback failed", 503)
        xml = cat_result.stdout_bytes.decode("utf-8", errors="replace").strip()
        if "<?xml" not in xml and "<hierarchy" not in xml:
            preview = xml[:200]
            raise AppException(
                UI_AUTOMATION_FAILED,
                "uiautomator dump readback did not contain XML hierarchy",
                400,
                details={"dumpOutput": dump_result.stdout.strip(), "readbackPreview": preview},
            )
        marker_candidates = [index for index in (xml.find("<?xml"), xml.find("<hierarchy")) if index >= 0]
        if marker_candidates:
            xml = xml[min(marker_candidates) :]
        return xml

    def logcat_snapshot(self, serial: str, duration_sec: int = 3, buffers: list[str] | None = None, timeout: int = 15) -> str:
        selected_buffers = buffers or ["main", "system", "crash"]
        args = ["logcat", "-d", "-v", "threadtime"]
        for buffer in selected_buffers:
            args.extend(["-b", buffer])
        result = self._run_serial(serial, args, timeout=max(timeout, duration_sec + 5))
        if not result.ok:
            raise AppException(ADB_UNAVAILABLE, result.stderr or "logcat snapshot failed", 503)
        return result.stdout

    def input_keyevent(self, serial: str, key: str, timeout: int = 10) -> AdbResult:
        return self._run_serial(serial, ["shell", "input", "keyevent", str(key)], timeout=timeout)

    def input_tap(self, serial: str, x: int, y: int, timeout: int = 10) -> AdbResult:
        return self._run_serial(serial, ["shell", "input", "tap", str(x), str(y)], timeout=timeout)

    def input_swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, timeout: int = 10) -> AdbResult:
        return self._run_serial(
            serial,
            ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
            timeout=timeout,
        )

    def open_notification(self, serial: str, timeout: int = 10) -> AdbResult:
        return self._run_serial(serial, ["shell", "cmd", "statusbar", "expand-notifications"], timeout=timeout)

    def open_quick_settings(self, serial: str, timeout: int = 10) -> AdbResult:
        return self._run_serial(serial, ["shell", "cmd", "statusbar", "expand-settings"], timeout=timeout)

    def safe_shell(self, serial: str, command: str, timeout: int = 10) -> AdbResult:
        tokens = shlex.split(command)
        if not tokens:
            raise AppException(PARAM_ERROR, "params.command is required for shell action", 400)
        allowed_prefixes = [
            ["getprop"],
            ["wm", "size"],
            ["wm", "density"],
            ["dumpsys", "battery"],
            ["input", "keyevent"],
            ["cmd", "statusbar", "expand-notifications"],
            ["cmd", "statusbar", "expand-settings"],
            ["uiautomator", "dump"],
            ["logcat", "-d"],
        ]
        if not any(tokens[: len(prefix)] == prefix for prefix in allowed_prefixes):
            raise AppException(PARAM_ERROR, "shell command is not in the P0 whitelist", 400)
        return self._run_serial(serial, ["shell", *tokens], timeout=timeout)

    def _run_serial(self, serial: str, args: list[str], timeout: int | None = None, binary: bool = False) -> AdbResult:
        return self._run(["-s", serial, *args], timeout=timeout, binary=binary)

    def _run(self, args: list[str], timeout: int | None = None, binary: bool = False) -> AdbResult:
        if not self.adb_path:
            return AdbResult(ok=False, stderr="adb not found in PATH", exit_code=127)
        try:
            completed = subprocess.run(
                [self.adb_path, *args],
                capture_output=True,
                timeout=timeout or settings.adb_timeout_sec,
                text=not binary,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AdbResult(ok=False, stderr=str(exc), exit_code=124, timed_out=True)
        if binary:
            stdout_bytes = completed.stdout if isinstance(completed.stdout, bytes) else b""
            stderr = completed.stderr.decode("utf-8", errors="replace") if isinstance(completed.stderr, bytes) else str(completed.stderr or "")
            return AdbResult(
                ok=completed.returncode == 0,
                stdout_bytes=stdout_bytes,
                stderr=stderr,
                exit_code=completed.returncode,
            )
        stdout = completed.stdout if isinstance(completed.stdout, str) else completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode("utf-8", errors="replace")
        if completed.returncode == 124:
            return AdbResult(ok=False, stdout=stdout, stderr=stderr, exit_code=124, timed_out=True)
        return AdbResult(ok=completed.returncode == 0, stdout=stdout, stderr=stderr, exit_code=completed.returncode)


def orientation_from_size(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    return "landscape" if width > height else "portrait"
