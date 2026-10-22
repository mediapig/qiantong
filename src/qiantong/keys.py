"""单键读取：不需要回车，支持超时轮询。"""

import os
import sys
import time

if os.name == "nt":
    import msvcrt

    class KeyReader:
        def __enter__(self):
            os.system("")  # 打开 Windows 终端的 ANSI 转义支持
            return self

        def __exit__(self, *exc):
            return False

        def read(self, timeout=None):
            """读一个按键；超时返回 None。"""
            deadline = None if timeout is None else time.monotonic() + timeout
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch == "\x03":
                        raise KeyboardInterrupt
                    return ch
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                time.sleep(0.01)

        def flush(self):
            while msvcrt.kbhit():
                msvcrt.getwch()

else:
    import select
    import termios
    import tty

    class KeyReader:
        def __enter__(self):
            self.fd = sys.stdin.fileno()
            self.saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)  # 关闭行缓冲和回显，保留 Ctrl-C
            return self

        def __exit__(self, *exc):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
            return False

        def read(self, timeout=None):
            """读一个按键；超时返回 None。"""
            ready, _, _ = select.select([self.fd], [], [], timeout)
            if not ready:
                return None
            return os.read(self.fd, 1).decode("utf-8", "ignore")

        def flush(self):
            termios.tcflush(self.fd, termios.TCIFLUSH)
