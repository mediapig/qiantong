"""尽量真随机的随机数源。

熵来源（按优先级）：
1. 量子随机数：OTH Regensburg 数字化实验室的公开服务，由 ID Quantique Quantis 量子随机数硬件生成；
   启动时取一批存进缓冲池，用完再取；
2. 取不到量子随机数时（断网、超时、服务异常），改用 Python 标准库的密码学随机数 secrets。

每次取 32 字节，和用户按下空格那一刻的纳秒时间戳拼接后做 SHA-256，
再用拒绝采样映射到 [0, n)，保证每个结果概率严格相等。
"""

import hashlib
import json
import secrets
import time
import urllib.request

QRNG_URL = "https://lfdr.de/qrng_api/qrng?length={length}&format=HEX"
POOL_SIZE = 1024  # 每次向服务取的字节数
TIMEOUT = 3  # 秒
CHUNK = 32  # 每次取随机数消耗的字节数

QUANTUM = "量子随机数（ID Quantique 量子硬件 · lfdr.de）"
LOCAL = "本机密码学随机数（Python secrets）"


def fetch_quantum(length):
    """向量子随机数服务请求 length 个字节，失败时抛出异常。"""
    with urllib.request.urlopen(QRNG_URL.format(length=length), timeout=TIMEOUT) as resp:
        data = bytes.fromhex(json.loads(resp.read())["qrn"])
    if len(data) != length:
        raise ValueError(f"量子随机数长度不符：要 {length}，得 {len(data)}")
    return data


class EntropySource:
    """优先给出量子随机字节，取不到就退回 secrets。"""

    def __init__(self, fetch=fetch_quantum):
        self.fetch = fetch
        self.pool = bytearray()
        self.offline = fetch is None  # 一旦失败就不再联网，免得每次抽签都卡几秒
        self.error = None

    def refill(self):
        if self.offline:
            return
        try:
            self.pool += self.fetch(POOL_SIZE)
        except Exception as exc:  # 网络、证书、格式等任何问题都退回本机随机数
            self.offline = True
            self.error = exc

    def take(self, n):
        """返回 (n 个随机字节, 来源说明)。"""
        if len(self.pool) < n:
            self.refill()
        if len(self.pool) >= n:
            chunk = bytes(self.pool[:n])
            del self.pool[:n]
            return chunk, QUANTUM
        return secrets.token_bytes(n), LOCAL


source = EntropySource()
last_source = None  # 最近一次取随机数用的来源，供界面显示


def warm_up():
    """预先取一批量子随机数，返回当前来源说明。"""
    source.refill()
    return QUANTUM if source.pool else LOCAL


def randbelow(n, moment_ns=None):
    """返回 [0, n) 内均匀分布的整数。moment_ns 为按键时刻，不传则取当前时刻。"""
    global last_source
    if n <= 0:
        raise ValueError("n 必须为正整数")
    if moment_ns is None:
        moment_ns = time.perf_counter_ns()
    stamp = moment_ns.to_bytes(16, "big", signed=True) + time.time_ns().to_bytes(16, "big")
    space = 1 << 256
    limit = space - space % n  # 超出 limit 的值丢弃，避免取模偏差
    while True:
        chunk, last_source = source.take(CHUNK)
        value = int.from_bytes(hashlib.sha256(chunk + stamp).digest(), "big")
        if value < limit:
            return value % n


def coin(moment_ns=None):
    """抛一次：True 为阳，False 为阴。"""
    return randbelow(2, moment_ns) == 1
