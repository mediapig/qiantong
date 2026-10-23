from collections import Counter
from io import StringIO

import pytest

from qiantong import animation, location, plugins, region, rng
from qiantong.cli import (
    NO_LINE_START,
    RENDERERS,
    render_lot,
    render_sensoji,
    render_taiwan,
    render_wongtaisin,
    width,
)
from qiantong.lots import GUANYIN, SENSOJI, TAIWAN, WONGTAISIN, load_lots, load_plugin_lots


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


def test_wongtaisin_lots():
    lots = load_lots(WONGTAISIN)
    assert [lot["number"] for lot in lots] == list(range(1, 101))
    levels = {"上上签", "上吉签", "中吉签", "中平签", "下下签"}
    for lot in lots:
        assert len(lot["poem"]) == 4
        assert all(line for line in lot["poem"])
        assert lot["name"] and lot["level"] in levels


def test_wongtaisin_box_is_aligned():
    for lot in load_lots(WONGTAISIN):
        lines = render_wongtaisin(lot)
        assert len({width(line) for line in lines}) == 1


def test_every_mounted_plugin_has_data_and_renderer():
    plugins.discover()
    for plugin_id in plugins.ids():
        plugin = plugins.get(plugin_id)
        lots = load_plugin_lots(plugin)
        assert lots
        renderer = plugin.render_lot if callable(plugin.render_lot) else RENDERERS[plugin.renderer]
        assert renderer(lots[0])


@pytest.mark.parametrize(
    "lang, temple",
    [
        ("zh-TW", TAIWAN),
        ("zh-Hant-TW", TAIWAN),
        ("zh-HK", WONGTAISIN),
        ("zh-Hant-HK", WONGTAISIN),
        ("zh-SG", GUANYIN),
        ("zh-Hans-SG", GUANYIN),
        ("zh-MY", GUANYIN),
        ("zh-Hans-MY", GUANYIN),
    ],
)
def test_language_territory_routes(lang, temple):
    assert region._language_vote(lang)[0] == temple


def test_explicit_headless_location(monkeypatch):
    monkeypatch.setenv("QIANTONG_LOCATION", "22.30,114.20,50")
    assert location.current() == location.Location(22.3, 114.2, 50.0)


def test_invalid_explicit_location_is_ignored(monkeypatch):
    monkeypatch.setenv("QIANTONG_LOCATION", "not-a-coordinate")
    monkeypatch.setattr(location, "_macos_location", lambda: None)
    monkeypatch.setattr(location, "_gpsd_location", lambda: None)
    assert location.current() is None


def test_gpsd_tpv_location(monkeypatch):
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def settimeout(self, _):
            pass

        def sendall(self, _):
            pass

        def recv(self, _):
            if hasattr(self, "sent"):
                return b""
            self.sent = True
            return b'{"class":"TPV","mode":3,"lat":35.68,"lon":139.76,"epx":4,"epy":3}\n'

    monkeypatch.delenv("QIANTONG_LOCATION", raising=False)
    monkeypatch.setattr(location.socket, "create_connection", lambda *_args, **_kwargs: FakeSocket())
    assert location._gpsd_location() == location.Location(35.68, 139.76, 5.0)


def test_ansi_animation_backend_redraws_frames():
    output = StringIO()
    backend = animation.AnsiAnimationBackend(output)
    backend.draw(["first", "frame"])
    backend.draw(["second"])
    rendered = output.getvalue()
    assert "first" in rendered and "second" in rendered
    assert "\x1b[2F" in rendered  # second frame moves back over the first two lines


def test_plain_animation_backend_has_no_cursor_controls():
    output = StringIO()
    backend = animation.create_backend("plain", output)
    backend.draw(["first", "frame"])
    assert output.getvalue() == "first\nframe\n"


def test_animation_recommends_plain_on_low_memory(monkeypatch):
    monkeypatch.setenv("QIANTONG_ANIMATION", "auto")
    monkeypatch.setattr(animation, "_available_memory", lambda: 512 * 1024 * 1024)
    monkeypatch.setattr(animation.os, "cpu_count", lambda: 8)
    animation.recommended_backend.cache_clear()
    assert animation.recommended_backend() == "plain"
    animation.recommended_backend.cache_clear()


def test_animation_environment_override(monkeypatch):
    monkeypatch.setenv("QIANTONG_ANIMATION", "plain")
    animation.recommended_backend.cache_clear()
    assert animation.recommended_backend() == "plain"
    animation.recommended_backend.cache_clear()


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
        ("Asia/Hong_Kong", "HK", "zh-Hant-HK", WONGTAISIN),
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
