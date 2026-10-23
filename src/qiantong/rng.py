"""Randomness that combines a remote quantum source with a local fallback.

Each draw takes 32 bytes, appends the nanosecond timestamp of the user's key press,
hashes them with SHA-256, and maps the result onto [0, n) by rejection sampling so that
every outcome has exactly the same probability.
"""

import hashlib
import json
import secrets
import time
import urllib.request

QRNG_URL = "https://lfdr.de/qrng_api/qrng?length={length}&format=HEX"
POOL_SIZE = 1024  # bytes requested from the service per fetch
TIMEOUT = 3
CHUNK = 32  # bytes consumed per draw

QUANTUM = "量子随机数"
LOCAL = "本机密码学随机数（Python secrets）"


def fetch_quantum(length):
    """Request quantum bytes; callers can replace this provider in tests."""
    with urllib.request.urlopen(QRNG_URL.format(length=length), timeout=TIMEOUT) as resp:
        data = bytes.fromhex(json.loads(resp.read())["qrn"])
    if len(data) != length:
        raise ValueError(f"expected {length} quantum random bytes, got {len(data)}")
    return data


class EntropySource:
    """Hand out quantum random bytes when possible, otherwise fall back to `secrets`."""

    def __init__(self, fetch=fetch_quantum):
        self.fetch = fetch
        self.pool = bytearray()
        self.offline = fetch is None  # after one failure stay offline, so draws do not stall for seconds
        self.error = None

    def refill(self):
        if self.offline:
            return
        try:
            self.pool += self.fetch(POOL_SIZE)
        except Exception as exc:  # any network, certificate or format problem falls back to local randomness
            self.offline = True
            self.error = exc

    def take(self, n):
        """Return (n random bytes, source label)."""
        if len(self.pool) < n:
            self.refill()
        if len(self.pool) >= n:
            chunk = bytes(self.pool[:n])
            del self.pool[:n]
            return chunk, QUANTUM
        return secrets.token_bytes(n), LOCAL


source = EntropySource()
last_source = None  # source of the most recent draw, for display


def warm_up():
    """Prefetch a batch of quantum bytes and return the source label."""
    source.refill()
    return QUANTUM if source.pool else LOCAL


def randbelow(n, moment_ns=None):
    """Return a uniformly distributed integer in [0, n).

    `moment_ns` is the key-press time; defaults to now.
    """
    global last_source
    if n <= 0:
        raise ValueError("n must be a positive integer")
    if moment_ns is None:
        moment_ns = time.perf_counter_ns()
    stamp = moment_ns.to_bytes(16, "big", signed=True) + time.time_ns().to_bytes(16, "big")
    space = 1 << 256
    limit = space - space % n  # discard values at or above limit to avoid modulo bias
    while True:
        chunk, last_source = source.take(CHUNK)
        value = int.from_bytes(hashlib.sha256(chunk + stamp).digest(), "big")
        if value < limit:
            return value % n


def coin(moment_ns=None):
    """Toss once: True is yang, False is yin."""
    return randbelow(2, moment_ns) == 1
