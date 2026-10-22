from collections import Counter

import pytest

from qiantong import japan, rng
from qiantong.cli import NO_LINE_START, render_lot, render_sensoji, width
from qiantong.lots import SENSOJI, load_lots


@pytest.fixture(autouse=True)
def offline_rng(monkeypatch):
    """Tests stay offline by default and use local randomness."""
    monkeypatch.setattr(rng, "source", rng.EntropySource(fetch=None))


def test_hundred_lots():
    lots = load_lots()
    assert [lot["number"] for lot in lots] == list(range(1, 101))
    for lot in lots:
        assert len(lot["poem"]) == 4
        assert lot["level"] in ("上签", "中签", "下签")


def test_randbelow_range_and_spread():
    counts = Counter(rng.randbelow(100) for _ in range(20000))
    assert set(counts) == set(range(100))
    assert min(counts.values()) > 100  # expected 200; just needs to be well above 0


def test_coin_is_balanced():
    yang = sum(rng.coin() for _ in range(10000))
    assert 4700 < yang < 5300


def test_lot_box_is_aligned():
    for lot in load_lots():
        lines = render_lot(lot)
        assert len({width(line) for line in lines}) == 1


def test_sensoji_lots():
    lots = load_lots(SENSOJI)
    assert [lot["number"] for lot in lots] == list(range(1, 101))
    for lot in lots:
        assert len(lot["poem"]) == 4
        assert all(len(line) == 5 for line in lot["poem"])
        assert lot["fortune"]


def test_sensoji_box_is_aligned():
    for lot in load_lots(SENSOJI):
        lines = render_sensoji(lot)
        assert len({width(line) for line in lines}) == 1
        for line in lines:
            text = line.strip("│ ")
            assert not (text and text[0] in NO_LINE_START)


def test_detect_japanese_language(monkeypatch):
    monkeypatch.setattr(japan, "_primary_language", lambda: "ja-JP")
    monkeypatch.setattr(japan, "_timezone", lambda: "Asia/Singapore")
    assert "日语" in japan.detect()


def test_detect_japan_timezone(monkeypatch):
    monkeypatch.setattr(japan, "_primary_language", lambda: "zh-Hans-CN")
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    assert "Asia/Tokyo" in japan.detect()


def test_detect_elsewhere(monkeypatch):
    monkeypatch.setattr(japan, "_primary_language", lambda: "en-US")
    monkeypatch.setenv("TZ", "Asia/Shanghai")
    assert japan.detect() is None


def test_quantum_bytes_are_used_first(monkeypatch):
    calls = []

    def fake_fetch(length):
        calls.append(length)
        return bytes(range(256)) * (length // 256)

    monkeypatch.setattr(rng, "source", rng.EntropySource(fetch=fake_fetch))
    assert rng.warm_up() == rng.QUANTUM
    rng.randbelow(100)
    assert rng.last_source == rng.QUANTUM
    assert len(rng.source.pool) == rng.POOL_SIZE - rng.CHUNK
    assert calls == [rng.POOL_SIZE]


def test_falls_back_when_quantum_service_fails(monkeypatch):
    calls = []

    def broken_fetch(length):
        calls.append(length)
        raise OSError("network unreachable")

    monkeypatch.setattr(rng, "source", rng.EntropySource(fetch=broken_fetch))
    assert rng.warm_up() == rng.LOCAL
    assert 0 <= rng.randbelow(100) < 100
    assert rng.last_source == rng.LOCAL
    assert calls == [rng.POOL_SIZE]  # no repeated network attempts after a failure
