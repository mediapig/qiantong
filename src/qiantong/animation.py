"""Terminal animation backends.

The fortune flow only needs a backend that can redraw a list of lines.  The
default implementation uses ANSI cursor movement; richer front ends can
implement ``AnimationBackend`` without touching randomness or ritual logic.
"""

import sys


class AnimationBackend:
    """Small rendering contract used by the interactive animation loops."""

    def draw(self, lines):
        raise NotImplementedError


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
