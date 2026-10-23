"""Pick the temple from where we seem to be: system language first, then time zone.

Japan → Sensō-ji lots; Taiwan → Sixty Jiazi lots (六十甲子籤); anywhere else → Guanyin lots.
"""

import os
import re
import subprocess
import sys
import time

from qiantong.lots import GUANYIN, SENSOJI, TAIWAN

JAPAN_ZONES = ("Asia/Tokyo", "Japan")
TAIWAN_ZONES = ("Asia/Taipei", "ROC")


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

            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if langid & 0x3FF == 0x11:  # LANG_JAPANESE
                return "ja"
            if langid == 0x0404:  # Chinese (Traditional, Taiwan)
                return "zh-TW"
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


def _is_taiwanese(lang):
    """zh-Hant-TW, zh-TW, zh_TW.UTF-8 and the like."""
    tag = lang.split(".")[0].replace("_", "-").lower()
    return tag.startswith("zh") and tag.endswith("-tw")


def detect():
    """Return (temple, reason); reason is a Chinese phrase shown to the user, or None for the default."""
    lang = _primary_language()
    if lang.lower().startswith("ja"):
        return SENSOJI, f"系统语言为日语（{lang}）"
    if _is_taiwanese(lang):
        return TAIWAN, f"系统语言为台湾繁体中文（{lang}）"
    tz = _timezone()
    if tz in JAPAN_ZONES or tz.startswith("JST") or "Tokyo" in tz or "東京" in tz:
        return SENSOJI, f"时区为日本（{tz}）"
    if tz in TAIWAN_ZONES or "Taipei" in tz or "台北" in tz:
        return TAIWAN, f"时区为台湾（{tz}）"
    return GUANYIN, None
