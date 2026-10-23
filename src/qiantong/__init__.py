"""Guanyin fortune sticks (观音灵签) in the terminal."""

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("qiantong")
except (ImportError, PackageNotFoundError):
    # Source checkouts before installation still have a useful version.
    __version__ = "0.1.3"
