"""判断当前环境是否在日本：系统语言是日语，或时区是日本。"""

import os
import re
import subprocess
import sys
import time

JAPAN_ZONES = ("Asia/Tokyo", "Japan")


def _primary_language():
    """系统首选语言，如 ja、zh-Hans-CN；取不到返回空串。"""
    if sys.platform == "darwin":
        # 终端里的 LANG 常常是 en_US，系统界面语言要从偏好设置读
        try:
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=2
            ).stdout
            # 输出形如 ( "ja-JP", "en-JP" )，第一项为首选语言
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
    """当前时区名，如 Asia/Tokyo、JST。"""
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
    """在日本则返回判断依据（一句中文），否则返回 None。"""
    lang = _primary_language()
    if lang.lower().startswith("ja"):
        return f"系统语言为日语（{lang}）"
    tz = _timezone()
    if tz in JAPAN_ZONES or tz.startswith("JST") or "Tokyo" in tz or "東京" in tz:
        return f"时区为日本（{tz}）"
    return None
