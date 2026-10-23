from collections import Counter

import pytest

from qiantong import region, rng
from qiantong.cli import NO_LINE_START, render_lot, render_sensoji, render_taiwan, width
from qiantong.lots import GUANYIN, SENSOJI, TAIWAN, load_lots


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


def test_taiwan_lots():
    lots = load_lots(TAIWAN)
    assert [lot["number"] for lot in lots] == list(range(1, 61))
    assert lots[0]["name"] == "甲子" and lots[-1]["name"] == "癸亥"
    for lot in lots:
        assert len(lot["poem"]) == 4
        assert all(len(line) == 7 for line in lot["poem"])
        assert lot["items"] and lot["story"]


def test_taiwan_box_is_aligned():
    for lot in load_lots(TAIWAN):
        lines = render_taiwan(lot)
        assert len({width(line) for line in lines}) == 1
        for line in lines:
            text = line.strip("│ ")
            assert not (text and text[0] in NO_LINE_START)


def fake_place(monkeypatch, lang, tz):
    monkeypatch.setattr(region, "_primary_language", lambda: lang)
    monkeypatch.setenv("TZ", tz)


def test_detect_japanese_language(monkeypatch):
    fake_place(monkeypatch, "ja-JP", "Asia/Singapore")
    temple, reason = region.detect()
    assert temple == SENSOJI and "日语" in reason


def test_detect_japan_timezone(monkeypatch):
    fake_place(monkeypatch, "zh-Hans-CN", "Asia/Tokyo")
    temple, reason = region.detect()
    assert temple == SENSOJI and "Asia/Tokyo" in reason


@pytest.mark.parametrize("lang", ["zh-Hant-TW", "zh-TW", "zh_TW.UTF-8"])
def test_detect_taiwanese_language(monkeypatch, lang):
    fake_place(monkeypatch, lang, "Asia/Singapore")
    assert region.detect()[0] == TAIWAN


def test_detect_taiwan_timezone(monkeypatch):
    fake_place(monkeypatch, "en-US", "Asia/Taipei")
    temple, reason = region.detect()
    assert temple == TAIWAN and "Asia/Taipei" in reason


def test_hong_kong_is_not_taiwan(monkeypatch):
    fake_place(monkeypatch, "zh-Hant-HK", "Asia/Hong_Kong")
    assert region.detect() == (GUANYIN, None)


def test_detect_elsewhere(monkeypatch):
    fake_place(monkeypatch, "en-US", "Asia/Shanghai")
    assert region.detect() == (GUANYIN, None)


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
