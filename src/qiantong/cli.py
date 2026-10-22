"""命令行入口：掷筊三圣杯 → 摇签筒 → 出签解签。"""

import argparse
import os
import sys
import textwrap
import time
import unicodedata

from qiantong import __version__, japan, rng
from qiantong.keys import KeyReader
from qiantong.lots import GUANYIN, SENSOJI, load_lots

FRAME = 0.08  # 动画每帧秒数
THROWS = 3  # 需要连续圣杯的次数

ORDINALS = "一二三四五六七八九十"


class Quit(Exception):
    pass


# ---------- 终端输出 ----------

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
    """终端显示宽度：中文等全角字符占两格，忽略 ANSI 颜色码。"""
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
    """按显示宽度折行。"""
    lines, line = [], ""
    for ch in text:
        if width(line + ch) > cells:
            if ch in NO_LINE_START and len(line) > 1:
                lines.append(line[:-1])  # 标点不放行首：带上前一个字一起换行
                line = line[-1]
            else:
                lines.append(line)
                line = ""
        line += ch
    if line:
        lines.append(line)
    return lines


class Canvas:
    """原地重绘一块固定行数的区域，用于动画。"""

    def __init__(self):
        self.height = 0

    def draw(self, lines):
        out = []
        if self.height:
            out.append(f"\x1b[{self.height}F")  # 回到上次绘制区域的开头
        for line in lines:
            out.append("\x1b[2K" + line + "\n")
        extra = self.height - len(lines)
        if extra > 0:  # 新画面更矮：清掉多出的旧行再回来
            out.append("\x1b[2K\n" * extra + f"\x1b[{extra}F")
        sys.stdout.write("".join(out))
        sys.stdout.flush()
        self.height = len(lines)


def say(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


# ---------- 按键控制 ----------


def wait_space(keys, prompt):
    """提示后等待空格；q 或 Esc 退出。"""
    keys.flush()
    say(dim(prompt))
    while True:
        ch = keys.read()
        if ch == " ":
            return
        if ch in ("q", "Q", "\x1b"):
            raise Quit


def animate(keys, frame_fn):
    """反复绘制 frame_fn(i) 直到再按空格，返回按下那一刻的纳秒时间戳。"""
    canvas = Canvas()
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


# ---------- 掷筊 ----------


def verdict(a, b):
    if a != b:
        return red("一阴一阳 · 圣杯 ✓")
    if a:
        return dim("两阳 · 笑杯 ✗")
    return dim("两阴 · 阴杯 ✗")


# 月牙形筊杯，每个造型两行、每行 7 格。
# 平面朝上（两角朝上）为阳，凸面朝上（两角朝下）为阴。
MOON_UP = ("█▖   ▗█", " ▀███▀ ")
MOON_RIGHT = (" ▄██▀▀ ", " ▀██▄▄ ")
MOON_DOWN = (" ▄███▄ ", "█▘   ▝█")
MOON_LEFT = (" ▀▀██▄ ", " ▄▄██▀ ")
SPIN = [MOON_UP, MOON_RIGHT, MOON_DOWN, MOON_LEFT]  # 翻转一周
BLANK = (" " * 7, " " * 7)
AIR = 5  # 地面以上的行数
FLIGHT = [1, 2, 3, 3, 2, 1]  # 空中循环的高度（月牙底边所在行）


def moon(is_yang):
    """落定后的筊杯：阳红、阴金。"""
    art = MOON_UP if is_yang else MOON_DOWN
    return tuple((red if is_yang else gold)(row) for row in art)


def spinning(step):
    return tuple(gold(row) for row in SPIN[step % len(SPIN)])


def toss_scene(label, cells, status):
    """画一帧掷筊场景。cells 为两枚筊杯的 (高度, 造型)，高度 0 表示落在地上。"""
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
    """落定后收成两行的记录。"""
    ma, mb = moon(a), moon(b)
    names = "  ".join("⚊阳" if x else "⚋阴" for x in (a, b))
    return [
        f"  {label}   {ma[0]}  {mb[0]}   {verdict(a, b)}",
        f"           {ma[1]}  {mb[1]}   {dim(names)}",
    ]


def throw_once(keys, n):
    """一次掷筊：空格抛起翻滚，再按空格落地。返回是否圣杯。"""
    label = f"第{ORDINALS[n]}掷"
    wait_space(keys, f"按空格掷出第{ORDINALS[n]}次筊杯")

    def flying(i):
        return [(FLIGHT[(i + k * 3) % len(FLIGHT)], spinning(i + k * 2)) for k in range(2)]

    state = {}

    def frame(i):
        state["i"] = i
        return toss_scene(label, flying(i), dim("翻滚中…按空格落地"))

    moment, canvas = animate(keys, frame)
    a, b = rng.coin(moment), rng.coin(moment + 1)

    # 落地：从当前高度一格格掉下来，边掉边转，触地后弹一下再停稳
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


def ask_permission(keys):
    """连掷三次，必须三次都是圣杯才可求签。"""
    while True:
        say()
        say(gold("【掷筊请示】") + " 需连得三次圣杯（一阴一阳），方可求签")
        say(dim("  月牙两角朝上为阳，两角朝下为阴"))
        if all(throw_once(keys, n) for n in range(THROWS)):
            say()
            say(red("  三圣杯，菩萨应允。"))
            return
        say()
        say(dim("  未得三圣杯，菩萨未允。请静心默念所求之事，再来一次。"))


# ---------- 摇签 ----------


def tube_frame(i, label):
    shift = " " * (i % 4 if i % 4 < 3 else 1)  # 左右晃动
    sticks = "".join("╿" if (i + k) % 3 else "│" for k in range(7))
    return [
        f"    {shift} {sticks}",
        f"    {shift}┃{sticks}┃",
        f"    {shift}┃{label}┃",
        f"    {shift}┗━━━━━━━┛",
        f"      {dim('摇签中…按空格停止')}",
    ]


def pop_frames(label):
    """一支签从签筒里跳出来。"""
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


# ---------- 签文 ----------

LEVEL_COLOR = {
    "上签": red, "中签": gold, "下签": dim,
    "大吉": red, "吉": red, "半吉": gold, "小吉": gold, "末小吉": gold, "末吉": gold, "凶": dim,
}
INNER = 36  # 签文框内宽


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
            body.append(gold("  " + line))  # 逐句解说的诗句标题
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


# ---------- 主流程 ----------


def run(keys, temple, reason):
    lots = load_lots(temple)
    say()
    if temple == SENSOJI:
        say(red("  ⛩  浅草寺 观音百签 · おみくじ  ⛩"))
        if reason:
            say(dim(f"  {reason}，今日改求浅草寺的签。"))
        say(dim("  双手捧起签筒，心中默念所求之事。空格：开始 / 停止；q：退出"))
    else:
        say(red("  ☸  观音灵签  ☸"))
        say(dim("  心中默念姓名、住址与所求之事。空格：开始 / 停止；q：退出"))
    while True:
        if temple == SENSOJI:
            # 浅草寺不掷筊，直接摇六角签筒
            lot = draw_lot(keys, lots, " みくじ", "按空格摇动签筒")
            box = render_sensoji(lot)
        else:
            ask_permission(keys)
            lot = draw_lot(keys, lots, " 签 筒 ", "按空格开始摇签筒")
            box = render_lot(lot)
        say()
        for line in box:
            say("  " + line)
        say()
        wait_space(keys, "按空格再求一签，q 退出")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qiantong", description="命令行观音灵签：掷筊三圣杯，空格摇签。")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--temple",
        choices=("auto", GUANYIN, SENSOJI),
        default="auto",
        help="auto：在日本（系统语言或时区）用浅草寺签，否则用观音灵签（默认）",
    )
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print("qiantong 需要在交互式终端中运行。", file=sys.stderr)
        return 1

    reason = None
    if args.temple == "auto":
        reason = japan.detect()
        temple = SENSOJI if reason else GUANYIN
    else:
        temple = args.temple

    sys.stdout.write("\x1b[?25l")  # 隐藏光标
    try:
        with KeyReader() as keys:
            run(keys, temple, reason)
    except (Quit, KeyboardInterrupt):
        say()
        say(dim("  阿弥陀佛，善哉。"))
    finally:
        sys.stdout.write("\x1b[?25h")  # 恢复光标
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
