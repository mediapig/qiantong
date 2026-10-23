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


@pytest.fixture(autouse=True)
def no_ip_lookup(monkeypatch):
    """Tests never look up the public IP."""
    monkeypatch.setattr(region, "_country", lambda: None)


def fake_place(monkeypatch, tz, country, lang):
    monkeypatch.setenv("TZ", tz)
    monkeypatch.setattr(region, "_country", lambda: country)
    monkeypatch.setattr(region, "_primary_language", lambda: lang)


@pytest.mark.parametrize(
    "tz, country, lang, temple",
    [
        ("Asia/Tokyo", "JP", "zh-Hans-CN", SENSOJI),  # mainland tourist in Tokyo
        ("Asia/Singapore", "SG", "ja-JP", GUANYIN),  # Japanese living in Singapore
        ("Asia/Taipei", "SG", "zh-Hant-TW", TAIWAN),  # in Taipei behind a Singapore VPN
        ("Asia/Shanghai", "JP", "ja-JP", SENSOJI),  # Japanese in Shanghai on a Japan VPN
        ("UTC", "US", "ja-JP", GUANYIN),  # cloud box: tie goes to the IP
        ("UTC", None, "ja-JP", SENSOJI),  # only the language speaks
        ("UTC", None, "zh_TW.UTF-8", TAIWAN),
        ("Asia/Taipei", None, "en-US", TAIWAN),  # the time zone alone
        ("Asia/Hong_Kong", "HK", "zh-Hant-HK", GUANYIN),  # Hong Kong is not Taiwan
        ("UTC", None, "en-US", GUANYIN),  # nothing to go on
    ],
)
def test_detect(monkeypatch, tz, country, lang, temple):
    fake_place(monkeypatch, tz, country, lang)
    assert region.detect()[0] == temple


def test_detect_reason_lists_agreeing_signals(monkeypatch):
    fake_place(monkeypatch, "Asia/Taipei", "TW", "en-US")
    assert region.detect() == (TAIWAN, "时区为台湾（Asia/Taipei）、IP 位于台湾")


def test_detect_without_ip(monkeypatch):
    fake_place(monkeypatch, "UTC", "JP", "en-US")
    assert region.detect(use_ip=False) == (GUANYIN, None)
    assert region.detect()[0] == SENSOJI


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
