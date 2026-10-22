"""签文数据：观音灵签与浅草寺观音百签，各 100 支。"""

import json
from importlib import resources

GUANYIN = "guanyin"
SENSOJI = "sensoji"


def load_lots(temple=GUANYIN):
    """读取指定寺庙的签文，按签号排序返回。"""
    text = resources.files("qiantong").joinpath(f"data/{temple}.json").read_text(encoding="utf-8")
    lots = json.loads(text)
    return sorted(lots, key=lambda lot: lot["number"])
