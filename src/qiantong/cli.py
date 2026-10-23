"""Command-line entry: three holy jiaobei tosses → shake the lot tube → read the lot.

In Taiwan one more holy toss confirms the drawn stick; Sensō-ji skips the jiaobei entirely.
"""

import argparse
import os
import sys
import textwrap
import time
import unicodedata

from qiantong import __version__, region, rng
from qiantong.animation import AnsiAnimationBackend, AnimationBackend, create_backend
from qiantong.keys import KeyReader
from qiantong.lots import load_plugin_lots
from qiantong.plugins import discover, get as get_plugin, ids as plugin_ids

FRAME = 0.08  # seconds per animation frame
THROWS = 3  # consecutive holy tosses required

ORDINALS = "一二三四五六七八九十"


class Quit(Exception):
    pass


# ---------- terminal output ----------

COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(text, code):
    return f"\x1b[{code}m{text}\x1b[0m" if COLOR else text


def red(t):
    return paint(t, "1;31")


def gold(t):
    return paint(t, "1;33")


def dim(t):
    return paint(t, "2")


def width(text):
    """Display width in the terminal: wide CJK characters take two cells; ANSI codes take none."""
    total, i = 0, 0
    while i < len(text):
        if text[i] == "\x1b":
            i = text.index("m", i) + 1
            continue
        total += 2 if unicodedata.east_asian_width(text[i]) in "WF" else 1
        i += 1
    return total


NO_LINE_START = "，。、；：！？）」』”’"


def wrap_cjk(text, cells):
    """Wrap text by display width."""
    lines, line = [], ""
    for ch in text:
        if width(line + ch) > cells:
            if ch in NO_LINE_START and len(line) > 1:
                lines.append(line[:-1])  # never start a line with punctuation: carry the previous character along
                line = line[-1]
            else:
                lines.append(line)
                line = ""
        line += ch
    if line:
        lines.append(line)
    return lines


Canvas = AnsiAnimationBackend  # backwards-compatible name for callers of the CLI module


def say(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


# ---------- key control ----------


def wait_space(keys, prompt):
    """Show a prompt and wait for space; q or Esc quits."""
    keys.flush()
    say(dim(prompt))
    while True:
        ch = keys.read()
        if ch == " ":
            return
        if ch in ("q", "Q", "\x1b"):
            raise Quit


def animate(keys, frame_fn, backend=None):
    """Draw frames through an animation backend until space is pressed."""
    canvas = backend or create_backend()
    i = 0
    keys.flush()
    while True:
        canvas.draw(frame_fn(i))
        ch = keys.read(FRAME)
        if ch == " ":
            return time.perf_counter_ns(), canvas
        if ch in ("q", "Q", "\x1b"):
            raise Quit
        i += 1


# ---------- jiaobei tossing ----------


def verdict(a, b):
    if a != b:
        return red("一阴一阳 · 圣杯 ✓")
    if a:
        return dim("两阳 · 笑杯 ✗")
    return dim("两阴 · 阴杯 ✗")


# Crescent-shaped jiaobei blocks, each pose two rows of 7 cells.
# Flat side up (horns up) is yang; round side up (horns down) is yin.
MOON_UP = ("█▖   ▗█", " ▀███▀ ")
MOON_RIGHT = (" ▄██▀▀ ", " ▀██▄▄ ")
MOON_DOWN = (" ▄███▄ ", "█▘   ▝█")
MOON_LEFT = (" ▀▀██▄ ", " ▄▄██▀ ")
SPIN = [MOON_UP, MOON_RIGHT, MOON_DOWN, MOON_LEFT]  # one full flip
BLANK = (" " * 7, " " * 7)
AIR = 5  # rows above the ground
FLIGHT = [1, 2, 3, 3, 2, 1]  # looping flight heights (row of the crescent's lower edge)


def moon(is_yang):
    """A landed block: yang in red, yin in gold."""
    art = MOON_UP if is_yang else MOON_DOWN
    return tuple((red if is_yang else gold)(row) for row in art)


def spinning(step):
    return tuple(gold(row) for row in SPIN[step % len(SPIN)])


def toss_scene(label, cells, status):
    """Draw one frame of the toss. `cells` holds (height, pose) for both blocks; height 0 is on the ground."""
    rows = []
    for row in range(AIR - 1, -1, -1):
        parts = []
        for height, art in cells:
            if row == height + 1:
                parts.append(art[0])
            elif row == height:
                parts.append(art[1])
            else:
                parts.append(BLANK[0])
        rows.append("        " + "    ".join(parts))
    rows.append("      " + dim("─" * 25))
    rows.append(f"  {label}  {status}")
    return rows


def throw_record(label, a, b):
    """Two-line record left behind once the blocks have landed."""
    ma, mb = moon(a), moon(b)
    names = "  ".join("⚊阳" if x else "⚋阴" for x in (a, b))
    return [
        f"  {label}   {ma[0]}  {mb[0]}   {verdict(a, b)}",
        f"           {ma[1]}  {mb[1]}   {dim(names)}",
    ]


def throw_once(keys, label, prompt):
    """One toss: space throws the blocks, space again lands them. Return whether it is holy.

    `label` must be 6 cells wide so the two-line record stays aligned.
    """
    wait_space(keys, prompt)

    def flying(i):
        return [(FLIGHT[(i + k * 3) % len(FLIGHT)], spinning(i + k * 2)) for k in range(2)]

    state = {}

    def frame(i):
        state["i"] = i
        return toss_scene(label, flying(i), dim("翻滚中…按空格落地"))

    moment, canvas = animate(keys, frame)
    a, b = rng.coin(moment), rng.coin(moment + 1)

    # landing: fall one row at a time while spinning, bounce once, then settle
    i = state["i"]
    heights = [h for h, _ in flying(i)]
    spin = i
    while any(heights):
        spin += 1
        heights = [max(h - 1, 0) for h in heights]
        canvas.draw(toss_scene(label, [(h, spinning(spin + k * 2)) for k, h in enumerate(heights)], ""))
        time.sleep(FRAME)
    for bounce in (1, 0):
        spin += 1
        canvas.draw(toss_scene(label, [(bounce, spinning(spin + k * 2)) for k in range(2)], ""))
        time.sleep(FRAME * 1.5)

    canvas.draw(toss_scene(label, [(0, moon(a)), (0, moon(b))], verdict(a, b)))
    time.sleep(0.6)
    canvas.draw(throw_record(label, a, b))
    return a != b


def ask_permission(keys, deity):
    """Toss until three holy results in a row; only then may a lot be drawn."""
    while True:
        say()
        say(gold("【掷筊请示】") + " 需连得三次圣杯（一阴一阳），方可求签")
        say(dim("  月牙两角朝上为阳，两角朝下为阴"))
        tosses = (throw_once(keys, f"第{n}掷", f"按空格掷出第{n}次筊杯") for n in ORDINALS[:THROWS])
        if all(tosses):  # lazy: stop at the first toss that is not holy
            say()
            say(red(f"  三圣杯，{deity}应允。"))
            return
        say()
        say(dim(f"  未得三圣杯，{deity}未允。请静心默念所求之事，再来一次。"))


# ---------- shaking the lot tube ----------


def tube_frame(i, label):
    shift = " " * (i % 4 if i % 4 < 3 else 1)  # sway left and right
    sticks = "".join("╿" if (i + k) % 3 else "│" for k in range(7))
    return [
        f"    {shift} {sticks}",
        f"    {shift}┃{sticks}┃",
        f"    {shift}┃{label}┃",
        f"    {shift}┗━━━━━━━┛",
        f"      {dim('摇签中…按空格停止')}",
    ]


def pop_frames(label):
    """A stick pops out of the tube."""
    frames = []
    for rise in range(1, 4):
        top = ["" for _ in range(3 - rise)] + [f"          {red('┃')}" for _ in range(rise)]
        frames.append(
            top
            + [
                "      ╿╿╿╿╿╿╿",
                "     ┃╿╿╿╿╿╿╿┃",
                f"     ┃{label}┃",
                "     ┗━━━━━━━┛",
                "",
            ]
        )
    frames[-1][-1] = "      " + red("签已落出")
    return frames


def draw_lot(keys, lots, label, prompt):
    wait_space(keys, prompt)
    moment, canvas = animate(keys, lambda i: [""] * 3 + tube_frame(i, label))
    lot = lots[rng.randbelow(len(lots), moment)]
    for frame in pop_frames(label):
        canvas.draw(frame)
        time.sleep(0.25)
    return lot


def confirm_lot(keys, lots, label, deity):
    """Taiwanese custom: one more holy toss confirms the drawn stick; otherwise put it back and shake again."""
    prompt = "按空格开始摇签筒"
    while True:
        lot = draw_lot(keys, lots, label, prompt)
        say()
        say(gold("【掷筊确认】") + f" 请示{deity}是否为这支签，得一圣杯方可")
        if throw_once(keys, "确　认", "按空格掷筊确认"):
            return lot
        say(dim(f"  {deity}未允此签，把签放回签筒，重新摇签。"))
        prompt = "按空格重新摇签筒"


# ---------- lot text ----------

LEVEL_COLOR = {
    "上签": red, "中签": gold, "下签": dim,
    "上上签": red, "上吉签": red, "中吉签": gold, "中平签": gold, "下下签": dim,
    "大吉": red, "吉": red, "半吉": gold, "小吉": gold, "末小吉": gold, "末吉": gold, "凶": dim,
}
INNER = 36  # inner width of the lot box


def boxed(body, inner=INNER):
    out = ["╭" + "─" * (inner + 2) + "╮"]
    for line in body:
        out.append("│ " + line + " " * (inner - width(line)) + " │")
    out.append("╰" + "─" * (inner + 2) + "╯")
    return out


def render_lot(lot, inner=INNER):
    level = LEVEL_COLOR.get(lot["level"], str)(lot["level"])
    body = [
        red(f"观音灵签 · 第{lot['number']}签") + "  " + level,
        "典故：" + lot["story"],
        "",
        *[gold("  " + line) for line in lot["poem"]],
        "",
        "解曰：",
        *["  " + line for line in wrap_cjk(lot["interpretation"], inner - 2)],
    ]
    if lot.get("category"):
        body += ["", dim("宜问：" + lot["category"])]
    return boxed(body, inner)


def render_sensoji(lot, inner=INNER):
    level = LEVEL_COLOR.get(lot["level"], str)(lot["level"])
    poem = set(lot["poem"])
    body = [
        red(f"浅草寺 观音百签 · 第{lot['number']}番") + "  " + level,
        "",
        *[gold("  " + line) for line in lot["poem"]],
        "",
        "解说：",
    ]
    for line in lot["explanation"]:
        if line in poem or (len(line) == 5 and "，" not in line and "。" not in line):
            body.append(gold("  " + line))  # poem line heading its explanation
        else:
            body += ["    " + part for part in wrap_cjk(line, inner - 4)]
    body += ["", "运势："]
    for line in lot["fortune"]:
        body += ["  " + part for part in wrap_cjk(line, inner - 2)]
    if lot["note"]:
        body += [""] + ["  " + part for part in wrap_cjk(lot["note"], inner - 2)]
    if lot["level"] == "凶":
        body += ["", *[dim(part) for part in wrap_cjk("抽到凶签莫担心：把签纸系在寺内的架子上，厄运就留在寺里了。", inner)]]
    return boxed(body, inner)


def render_taiwan(lot, inner=INNER):
    body = [
        red(f"六十甲子签 · 第{lot['ordinal']}签") + "  " + gold(lot["name"]),
        "卦象：" + lot["gua"],
        *wrap_cjk(lot["element"], inner),
        "",
        *[gold("  " + line) for line in lot["poem"]],
        "",
        "典故：",
        *["  " + part for story in lot["story"] for part in wrap_cjk(story, inner - 2)],
        "",
        "签解：",
    ]
    # two items per line when both fit, otherwise one
    cells = [f"{key}：{value}" for key, value in lot["items"]]
    col = (inner - 2) // 2
    i = 0
    while i < len(cells):
        first = cells[i]
        if width(first) <= col - 2 and i + 1 < len(cells) and width(cells[i + 1]) <= col:
            body.append("  " + first + " " * (col - width(first)) + cells[i + 1])
            i += 2
        else:
            body += ["  " + part for part in wrap_cjk(first, inner - 2)]
            i += 1
    return boxed(body, inner)


def render_wongtaisin(lot, inner=INNER):
    level = LEVEL_COLOR.get(lot["level"], str)(lot["level"])
    body = [
        red(f"黄大仙灵签 · 第{lot['number']}签") + "  " + level,
        "签题：" + lot["name"],
        "",
        *[gold("  " + line) for line in lot["poem"]],
        "",
        "典故：" + lot["name"],
        "",
        *[dim("  " + part) for part in wrap_cjk("古签诗与历史签题来自黄大仙灵签传统资料，仅供文化体验。", inner - 2)],
    ]
    return boxed(body, inner)


def render_generic(lot, inner=INNER, title="灵签", labels=("签题：", "典故：", "解曰：")):
    """Render the common plugin contract used by independently mounted packs."""
    level = LEVEL_COLOR.get(lot.get("level", ""), str)(lot.get("level", ""))
    title = lot.get("title", title)
    body = [red(f"{title} · {lot['number']}") + "  " + level]
    if lot.get("name"):
        body.append(labels[0] + lot["name"])
    body += ["", *[gold("  " + line) for line in lot.get("poem", [])], ""]
    if lot.get("story"):
        body += [labels[1], *["  " + part for part in wrap_cjk(lot["story"], inner - 2)], ""]
    if lot.get("interpretation"):
        body += [labels[2], *["  " + part for part in wrap_cjk(lot["interpretation"], inner - 2)]]
    return boxed(body, inner)


def render_thai(lot, inner=INNER):
    return render_generic(lot, inner, "Thai Siam Si", ("ชื่อ: ", "เรื่อง: ", "คำแนะนำ: "))


def render_vietnamese(lot, inner=INNER):
    return render_generic(lot, inner, "Xin Xăm", ("Tên: ", "Ý nghĩa: ", "Lời khuyên: "))


def render_oracle(lot, inner=INNER):
    return render_generic(lot, inner, "English Oracle", ("Title: ", "Meaning:", "Reading:"))


def render_inari(lot, inner=INNER):
    return render_generic(lot, inner, "稲荷神社 おみくじ", ("題：", "由来：", "お告げ："))


RENDERERS = {
    "guanyin": render_lot,
    "sensoji": render_sensoji,
    "taiwan": render_taiwan,
    "wongtaisin": render_wongtaisin,
    "generic": render_generic,
    "thai": render_thai,
    "vietnamese": render_vietnamese,
    "oracle": render_oracle,
    "inari": render_inari,
}


# ---------- main flow ----------


def connect_entropy():
    """Prefetch quantum random bytes at startup and tell the user which source is in use."""
    sys.stdout.write(dim("  正在连接量子随机数服务…"))
    sys.stdout.flush()
    label = rng.warm_up()
    sys.stdout.write("\r\x1b[2K")
    if label == rng.QUANTUM:
        say(dim(f"  随机源：{label}"))
    else:
        say(dim(f"  量子随机数服务连不上，改用{label}"))


def run(keys, temple, reason):
    plugin = get_plugin(temple)
    lots = load_plugin_lots(plugin)
    say()
    say(red(plugin.title))
    if reason:
        say(dim(f"  {reason}，今日求{plugin.title.strip(' ⛩☯🏮☸')}。"))
    say(dim("  " + plugin.intro))
    connect_entropy()
    while True:
        if plugin.ritual == "direct":
            lot = draw_lot(keys, lots, plugin.label, plugin.draw_prompt)
        elif plugin.ritual == "confirm":
            ask_permission(keys, "妈祖")
            lot = confirm_lot(keys, lots, plugin.label, plugin.deity)
        else:
            ask_permission(keys, plugin.deity)
            lot = draw_lot(keys, lots, plugin.label, plugin.draw_prompt)
        renderer = plugin.render_lot if callable(plugin.render_lot) else RENDERERS[plugin.renderer]
        box = renderer(lot)
        say()
        for line in box:
            say("  " + line)
        say()
        wait_space(keys, "按空格再求一签，q 退出")


def main(argv=None):
    discover()
    parser = argparse.ArgumentParser(prog="qiantong", description="命令行求签：掷筊三圣杯，空格摇签。")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--temple",
        choices=("auto",) + plugin_ids(),
        default="auto",
        help="auto：综合时区、IP 和系统语言判断所在地区，日本用浅草寺签，台湾用六十甲子签，香港用黄大仙签，其他地方用观音灵签（默认）",
    )
    parser.add_argument("--no-ip", action="store_true", help="判断地区时不联网查询 IP")
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print("qiantong 需要在交互式终端中运行。", file=sys.stderr)
        return 1

    reason = None
    if args.temple == "auto":
        if not args.no_ip:
            sys.stdout.write(dim("  正在识别所在地区…"))
            sys.stdout.flush()
        temple, reason = region.detect(use_ip=not args.no_ip)
        sys.stdout.write("\r\x1b[2K")
    else:
        temple = args.temple

    sys.stdout.write("\x1b[?25l")  # hide cursor
    try:
        with KeyReader() as keys:
            run(keys, temple, reason)
    except (Quit, KeyboardInterrupt):
        say()
        say(dim("  " + get_plugin(temple).goodbye))
    finally:
        sys.stdout.write("\x1b[?25h")  # show cursor
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
