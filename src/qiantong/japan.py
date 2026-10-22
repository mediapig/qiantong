"""Detect whether we are in Japan: Japanese system language or a Japanese time zone."""

import os
import re
import subprocess
import sys
import time

JAPAN_ZONES = ("Asia/Tokyo", "Japan")


def _primary_language():
    """Preferred system language such as ja or zh-Hans-CN; empty string if unknown."""
    if sys.platform == "darwin":
        # LANG in a terminal is often en_US; the UI language lives in the user defaults
        try:
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=2
            ).stdout
            # Output looks like ( "ja-JP", "en-JP" ); the first entry is the preferred language
            langs = re.findall(r"[A-Za-z][\w-]*", out)
            if langs:
                return langs[0]
        except (OSError, subprocess.SubprocessError):
            pass
    if os.name == "nt":
        try:
            import ctypes

            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x11:  # LANG_JAPANESE
                return "ja"
        except (AttributeError, OSError):
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(var):
            return os.environ[var]
    return ""


def _timezone():
    """Current time zone name, e.g. Asia/Tokyo or JST."""
    tz = os.environ.get("TZ", "").lstrip(":")
    if tz:
        return tz
    try:
        real = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in real:
            return real.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return time.tzname[0]


def detect():
    """Return the reason (a Chinese sentence shown to the user) if in Japan, else None."""
    lang = _primary_language()
    if lang.lower().startswith("ja"):
        return f"系统语言为日语（{lang}）"
    tz = _timezone()
    if tz in JAPAN_ZONES or tz.startswith("JST") or "Tokyo" in tz or "東京" in tz:
        return f"时区为日本（{tz}）"
    return None
