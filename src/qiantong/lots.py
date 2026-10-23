"""Fortune data: Guanyin lots and Sensō-ji (Asakusa) Kannon lots, 100 each; Taiwan's Sixty Jiazi lots, 60."""

import json
from pathlib import Path

GUANYIN = "guanyin"
SENSOJI = "sensoji"
TAIWAN = "taiwan"
WONGTAISIN = "wongtaisin"
YUELAO = "yuelao"
GUANDI = "guandi"


def load_lots(temple=GUANYIN):
    """Load the lots of the given temple, sorted by number."""
    text = (Path(__file__).resolve().parent / "data" / (temple + ".json")).read_text(encoding="utf-8")
    lots = json.loads(text)
    return sorted(lots, key=lambda lot: lot["number"])


def load_plugin_lots(plugin):
    """Load data from a plugin-owned callable or the built-in JSON bundle."""
    loader = getattr(plugin, "load_lots", None)
    lots = loader() if callable(loader) else load_lots(plugin.id)
    return sorted(lots, key=lambda lot: lot.get("number", lot.get("ordinal", 0)))
