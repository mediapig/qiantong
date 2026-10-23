"""Mounted fortune-stick plugins.

The random engine and the region router do not know how a particular temple
works. A plugin only declares its data id, ritual flow and presentation hook.
New lots can be added by registering another plugin without changing the
randomness layer.
"""

from dataclasses import dataclass
from importlib import metadata


@dataclass(frozen=True)
class Plugin:
    id: str
    title: str
    deity: str
    ritual: str  # direct, permission, or confirm
    renderer: str
    label: str
    draw_prompt: str
    intro: str
    goodbye: str
    load_lots: object = None  # optional callable for a plugin-owned data source
    render_lot: object = None  # optional callable receiving (lot, inner)


_PLUGINS = {}
_DISCOVERED = False


def register(plugin):
    if plugin.id in _PLUGINS:
        raise ValueError(f"duplicate plugin id: {plugin.id}")
    _PLUGINS[plugin.id] = plugin
    return plugin


def get(plugin_id):
    try:
        return _PLUGINS[plugin_id]
    except KeyError as exc:
        raise ValueError(f"unknown fortune plugin: {plugin_id}") from exc


def ids():
    return tuple(_PLUGINS)


def discover():
    """Load third-party plugins declared through the standard entry-point API.

    An entry point may resolve to a ``Plugin`` instance, a zero-argument
    factory returning one, or a registrar accepting ``register``. Discovery
    is best-effort: a broken optional plugin must never prevent the built-in
    fortune systems from starting.
    """
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    try:
        entries = metadata.entry_points()
        if hasattr(entries, "select"):
            entries = entries.select(group="qiantong.plugins")
        else:  # Python 3.9/3.10 compatibility
            entries = entries.get("qiantong.plugins", ())
    except (ImportError, OSError, RuntimeError):
        return
    for entry in entries:
        try:
            loaded = entry.load()
            if isinstance(loaded, Plugin):
                register(loaded)
            elif callable(loaded):
                try:
                    result = loaded()
                except TypeError:
                    result = loaded(register)
                if isinstance(result, Plugin):
                    register(result)
        except Exception:
            # Optional integrations are isolated from the core application.
            continue


register(Plugin("guanyin", "  ☸  观音灵签  ☸", "菩萨", "permission", "guanyin", " 签 筒 ", "按空格开始摇签筒", "心中默念姓名、住址与所求之事。空格：开始 / 停止；q：退出", "阿弥陀佛，善哉。"))
register(Plugin("sensoji", "  ⛩  浅草寺 观音百签 · おみくじ  ⛩", "", "direct", "sensoji", " みくじ", "按空格摇动签筒", "双手捧起签筒，心中默念所求之事。空格：开始 / 停止；q：退出", "阿弥陀佛，善哉。"))
register(Plugin("taiwan", "  ☯  六十甲子签 · 妈祖灵签  ☯", "妈祖", "confirm", "taiwan", " 签 筒 ", "按空格开始摇签筒", "心中默念姓名、生辰、住址与所求之事。空格：开始 / 停止；q：退出", "妈祖保庇。"))
register(Plugin("wongtaisin", "  🏮  香港黄大仙灵签  🏮", "黄大仙", "permission", "wongtaisin", " 签 筒 ", "按空格开始摇签筒", "心中默念所求之事。空格：开始 / 停止；q：退出", "黄大仙保佑。"))
register(Plugin("yuelao", "  💞  月老姻缘签  💞", "月老", "permission", "generic", " 签 筒 ", "按空格开始摇签筒", "心中默念姓名与所求的缘分。空格：开始 / 停止；q：退出", "愿有情人终成眷属。"))
register(Plugin("guandi", "  🗡  关帝灵签  🗡", "关圣帝君", "permission", "generic", " 签 筒 ", "按空格开始摇签筒", "心中默念姓名、住址与所求之事。空格：开始 / 停止；q：退出", "愿你守正而行。"))
register(Plugin("caishen", "  🧧  财神求财签  🧧", "财神", "permission", "generic", " 签 筒 ", "按空格开始摇签筒", "心中默念事业、财务与经营所求之事。空格：开始 / 停止；q：退出", "财来有道，福自相随。"))
register(Plugin("wenchang", "  📚  文昌学业签  📚", "文昌帝君", "permission", "generic", " 签 筒 ", "按空格开始摇签筒", "心中默念学业、考试与进修所求之事。空格：开始 / 停止；q：退出", "愿你勤学有成。"))
register(Plugin("siamsi", "  🪷  Thai Siam Si  🪷", "", "direct", "thai", " SIAM SI ", "Press space to draw", "Hold your question in mind, then press space to draw a Thai fortune.", "May your path be kind."))
register(Plugin("xinxam", "  🪷  Việt Xin Xăm  🪷", "", "direct", "vietnamese", " XIN XĂM ", "Nhấn phím cách để rút quẻ", "Hãy tĩnh tâm và nghĩ về điều bạn muốn hỏi.", "Chúc bạn bình an."))
register(Plugin("oracle", "  ✦  English Oracle  ✦", "", "direct", "oracle", " ORACLE ", "Press space to draw", "Hold one clear question, then press space to draw.", "May the next step become clear."))
register(Plugin("inari", "  ⛩  稲荷神社 おみくじ  ⛩", "", "direct", "inari", " おみくじ ", "按空格抽签", "静心默念所求之事。空格：开始 / 停止；q：退出", "願いが道を照らします。"))
