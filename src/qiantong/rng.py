"""尽量真随机的随机数源。

熵来源：
1. 操作系统熵池（os.urandom → getrandom/getentropy），由硬件噪声、中断时序等持续补充；
2. 用户按下空格那一刻的纳秒级时间戳（人手的抖动本身也是一份熵）。

两者拼接后做 SHA-256，再用拒绝采样映射到 [0, n)，保证每个结果概率严格相等。
"""

import hashlib
import os
import time


def randbelow(n, moment_ns=None):
    """返回 [0, n) 内均匀分布的整数。moment_ns 为按键时刻，不传则取当前时刻。"""
    if n <= 0:
        raise ValueError("n 必须为正整数")
    if moment_ns is None:
        moment_ns = time.perf_counter_ns()
    stamp = moment_ns.to_bytes(16, "big", signed=True) + time.time_ns().to_bytes(16, "big")
    space = 1 << 256
    limit = space - space % n  # 超出 limit 的值丢弃，避免取模偏差
    counter = 0
    while True:
        digest = hashlib.sha256(os.urandom(32) + stamp + counter.to_bytes(4, "big")).digest()
        value = int.from_bytes(digest, "big")
        if value < limit:
            return value % n
        counter += 1


def coin(moment_ns=None):
    """抛一次：True 为阳，False 为阴。"""
    return randbelow(2, moment_ns) == 1
