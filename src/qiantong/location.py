"""Optional operating-system location provider.

Location is deliberately best-effort. A missing helper, denied permission or
unavailable service returns ``None`` and never blocks the fortune flow.
"""

import json
import os
import platform
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    accuracy: Optional[float] = None


def _from_json(data):
    """Validate a provider response and turn it into a Location."""
    latitude = float(data["latitude"])
    longitude = float(data["longitude"])
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("coordinates out of range")
    accuracy = data.get("accuracy")
    return Location(latitude, longitude, float(accuracy) if accuracy is not None else None)


def _environment_location():
    """Read an explicit coordinate for appliances and headless deployments.

    This is useful when a router/NAS knows its location but has no location
    service. The value is intentionally opt-in: ``lat,lon[,accuracy]``.
    """
    value = os.environ.get("QIANTONG_LOCATION")
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) not in (2, 3):
        return None
    try:
        data = {"latitude": parts[0], "longitude": parts[1]}
        if len(parts) == 3 and parts[2]:
            data["accuracy"] = parts[2]
        return _from_json(data)
    except (TypeError, ValueError):
        return None


def _macos_helpers():
    configured = os.environ.get("QIANTONG_LOCATION_HELPER")
    if configured:
        yield Path(configured)
    yield Path(__file__).resolve().parent / "_macos/LocationHelper.app/Contents/MacOS/LocationHelper"
    root = Path(__file__).resolve().parents[2]
    yield root / "macos/LocationHelper.app/Contents/MacOS/LocationHelper"
    yield root / "macos/LocationHelper/.build/release/LocationHelper"


def _macos_location():
    for helper in _macos_helpers():
        if not helper.is_file():
            continue
        try:
            result = subprocess.run(
                [str(helper)], capture_output=True, text=True, timeout=12, check=False
            )
            if result.returncode:
                continue
            data = json.loads(result.stdout.strip().splitlines()[-1])
            return _from_json(data)
        except (OSError, ValueError, KeyError, json.JSONDecodeError, IndexError, subprocess.TimeoutExpired):
            continue
    return None


def _gpsd_location():
    """Read one 2D/3D fix from a local gpsd JSON socket.

    gpsd is optional and is deliberately contacted only when explicitly
    enabled or when its conventional local socket is reachable. No package or
    architecture-specific GPS code is bundled with qiantong.
    """
    host = os.environ.get("QIANTONG_GPSD_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("QIANTONG_GPSD_PORT", "2947"))
    except ValueError:
        return None
    timeout = float(os.environ.get("QIANTONG_GPSD_TIMEOUT", "0.8"))
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b'?WATCH={"enable":true,"json":true};\n')
            buffer = b""
            while len(buffer) < 64 * 1024:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                for line in buffer.splitlines():
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if message.get("class") != "TPV" or message.get("mode", 0) < 2:
                        continue
                    if "lat" not in message or "lon" not in message:
                        continue
                    accuracy = message.get("eph")
                    if accuracy is None and message.get("epx") is not None and message.get("epy") is not None:
                        accuracy = (float(message["epx"]) ** 2 + float(message["epy"]) ** 2) ** 0.5
                    return _from_json({"latitude": message["lat"], "longitude": message["lon"], "accuracy": accuracy})
                # Keep only an incomplete final line for the next recv.
                buffer = buffer.rsplit(b"\n", 1)[-1]
    except (OSError, ValueError, TypeError, socket.timeout):
        return None
    return None


def current():
    """Return the current OS location, or ``None`` when unavailable."""
    explicit = _environment_location()
    if explicit is not None:
        return explicit
    if platform.system() == "Darwin":
        location = _macos_location()
        if location is not None:
            return location
    return _gpsd_location()
