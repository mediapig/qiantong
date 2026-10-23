"""Pick the temple from where we seem to be.

Three signals vote, each for the temple of the region it points to:
- time zone (3 votes): usually set automatically from the location, so the strongest hint;
- IP country (2 votes): looked up online, but a VPN or proxy shows the exit country;
- system language (2 votes): says who the user is rather than where they are.

Japan → Sensō-ji lots; Taiwan → Sixty Jiazi lots (六十甲子籤); anywhere else → Guanyin lots.
A signal that says nothing about a place (UTC, English, a failed lookup) abstains.
"""

import os
import re
import subprocess
import sys
import time
import urllib.request

from qiantong.lots import GUANYIN, SENSOJI, TAIWAN

JAPAN_ZONES = ("Asia/Tokyo", "Japan")
TAIWAN_ZONES = ("Asia/Taipei", "ROC")
NEUTRAL_ZONES = ("Etc/", "UTC", "GMT", "Universal", "Zulu")

IP_URL = "https://1.1.1.1/cdn-cgi/trace"  # Cloudflare; the reply has a line like loc=TW
IP_TIMEOUT = 2  # seconds

COUNTRY_TEMPLE = {"JP": SENSOJI, "TW": TAIWAN}
COUNTRY_NAME = {"JP": "日本", "TW": "台湾"}

# (votes, rank used to break ties: time zone, then IP, then language)
TIME_ZONE = (3, 3)
IP = (2, 2)
LANGUAGE = (2, 1)


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
            if langid & 0x3FF == 0x04:  # other Chinese
                return "zh"
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


def _country():
    """Two-letter country code of our public IP, or None if the lookup fails."""
    try:
        with urllib.request.urlopen(IP_URL, timeout=IP_TIMEOUT) as resp:
            text = resp.read().decode("ascii", "ignore")
    except Exception:  # offline, timeout, blocked: this signal just abstains
        return None
    match = re.search(r"^loc=([A-Z]{2})$", text, re.M)
    return match[1] if match else None


def _zone_vote(tz):
    if tz in JAPAN_ZONES or tz.startswith("JST") or "Tokyo" in tz or "東京" in tz:
        return SENSOJI, f"时区为日本（{tz}）"
    if tz in TAIWAN_ZONES or "Taipei" in tz or "台北" in tz:
        return TAIWAN, f"时区为台湾（{tz}）"
    if "/" in tz and not tz.startswith(NEUTRAL_ZONES):  # a real place elsewhere, e.g. Asia/Singapore
        return GUANYIN, f"时区为 {tz}"
    return None  # UTC, or an ambiguous abbreviation such as CST


def _ip_vote(country):
    if not country or country in ("XX", "T1"):  # unknown, Tor
        return None
    if country in COUNTRY_TEMPLE:
        return COUNTRY_TEMPLE[country], f"IP 位于{COUNTRY_NAME[country]}"
    return GUANYIN, f"IP 位于 {country}"


def _language_vote(lang):
    tag = lang.split(".")[0].replace("_", "-").lower()
    if tag.startswith("ja"):
        return SENSOJI, f"系统语言为日语（{lang}）"
    if tag.startswith("zh") and tag.endswith("-tw"):
        return TAIWAN, f"系统语言为台湾繁体中文（{lang}）"
    if tag.startswith("zh"):
        return GUANYIN, f"系统语言为中文（{lang}）"
    return None  # English and the like say nothing about the temple


def detect(use_ip=True):
    """Return (temple, reason); reason is a Chinese phrase shown to the user, or None for the default."""
    signals = [
        (TIME_ZONE, _zone_vote(_timezone())),
        (IP, _ip_vote(_country()) if use_ip else None),
        (LANGUAGE, _language_vote(_primary_language())),
    ]
    score, rank, why = {}, {}, {}
    for (votes, order), vote in signals:
        if vote is None:
            continue
        temple, phrase = vote
        score[temple] = score.get(temple, 0) + votes
        rank[temple] = max(rank.get(temple, 0), order)
        why.setdefault(temple, []).append(phrase)
    if not score:
        return GUANYIN, None
    temple = max(score, key=lambda t: (score[t], rank[t]))
    if temple == GUANYIN:
        return GUANYIN, None
    return temple, "、".join(why[temple])
