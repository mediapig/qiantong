"""Single-key input without Enter, with optional timeout polling."""

import os
import sys
import time

if os.name == "nt":
    import msvcrt

    class KeyReader:
        def __enter__(self):
            os.system("")  # enable ANSI escape handling in the Windows console
            return self

        def __exit__(self, *exc):
            return False

        def read(self, timeout=None):
            """Read one key; return None on timeout."""
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
            tty.setcbreak(self.fd)  # no line buffering or echo, but keep Ctrl-C
            return self

        def __exit__(self, *exc):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
            return False

        def read(self, timeout=None):
            """Read one key; return None on timeout."""
            ready, _, _ = select.select([self.fd], [], [], timeout)
            if not ready:
                return None
            return os.read(self.fd, 1).decode("utf-8", "ignore")

        def flush(self):
            termios.tcflush(self.fd, termios.TCIFLUSH)
