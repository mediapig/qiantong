"""Terminal animation backends.

The fortune flow only needs a backend that can redraw a list of lines.  The
default implementation uses ANSI cursor movement; richer front ends can
implement ``AnimationBackend`` without touching randomness or ritual logic.
"""

import os
import sys
from functools import lru_cache


class AnimationBackend:
    """Small rendering contract used by the interactive animation loops."""

    def draw(self, lines):
        raise NotImplementedError

    def close(self):
        """Release resources held by a live backend."""


class AnsiAnimationBackend(AnimationBackend):
    """Redraw frames in place using standard ANSI terminal controls."""

    def __init__(self, output=None):
        self.output = output or sys.stdout
        self.height = 0

    def draw(self, lines):
        out = []
        if self.height:
            out.append(f"\x1b[{self.height}F")
        for line in lines:
            out.append("\x1b[2K" + line + "\n")
        extra = self.height - len(lines)
        if extra > 0:
            out.append("\x1b[2K\n" * extra + f"\x1b[{extra}F")
        self.output.write("".join(out))
        self.output.flush()
        self.height = len(lines)


class PlainAnimationBackend(AnimationBackend):
    """Portable fallback for terminals that do not support cursor controls."""

    def __init__(self, output=None):
        self.output = output or sys.stdout

    def draw(self, lines):
        self.output.write("\n".join(lines) + "\n")
        self.output.flush()


class RichAnimationBackend(AnimationBackend):
    """Optional live display powered by Rich."""

    def __init__(self, output=None):
        try:
            from rich.console import Console
            from rich.live import Live
        except ImportError as exc:
            raise RuntimeError("Rich animation requires the optional 'rich' package") from exc
        self.console = Console(file=output or sys.stdout, force_terminal=True)
        self.live = Live("", console=self.console, refresh_per_second=20, transient=False)
        self.live.start()

    def draw(self, lines):
        self.live.update("\n".join(lines), refresh=True)

    def close(self):
        if self.live is not None:
            self.live.stop()
            self.live = None


def _available_memory():
    """Return physical memory in bytes where the OS exposes it."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return pages * page_size
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _rich_available():
    try:
        import rich  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def recommended_backend():
    """Choose a backend once per process from the machine's available resources."""
    forced = os.environ.get("QIANTONG_ANIMATION", "auto").lower()
    if forced in ("plain", "ansi", "rich"):
        return forced
    cpu_count = os.cpu_count() or 1
    memory = _available_memory()
    low_memory = memory is not None and memory < 1024 * 1024 * 1024
    if cpu_count <= 1 or low_memory:
        return "plain"
    if cpu_count >= 4 and (memory is None or memory >= 4 * 1024 * 1024 * 1024) and _rich_available():
        return "rich"
    return "ansi"


def create_backend(name=None, output=None):
    """Create the configured or automatically selected animation backend."""
    name = (name or recommended_backend()).lower()
    if name == "plain":
        return PlainAnimationBackend(output)
    if name == "ansi":
        return AnsiAnimationBackend(output)
    if name == "rich":
        try:
            return RichAnimationBackend(output)
        except RuntimeError:
            return AnsiAnimationBackend(output)
    raise ValueError(f"unknown animation backend: {name}")
