"""Fortune data: Guanyin lots and Sensō-ji (Asakusa) Kannon lots, 100 each."""

import json
from importlib import resources

GUANYIN = "guanyin"
SENSOJI = "sensoji"


def load_lots(temple=GUANYIN):
    """Load the lots of the given temple, sorted by number."""
    text = resources.files("qiantong").joinpath(f"data/{temple}.json").read_text(encoding="utf-8")
    lots = json.loads(text)
    return sorted(lots, key=lambda lot: lot["number"])
