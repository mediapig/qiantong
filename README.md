# qiantong · Guanyin fortune sticks in your terminal

Draw a Guanyin fortune stick (观音灵签) in the terminal: first ask for permission by tossing jiaobei blocks (掷筊), and once you get three holy tosses (圣杯) in a row, shake the lot tube and read your fortune poem and its interpretation.

The interface and the fortune texts are in Chinese.

## Installation

Requires Python 3.8+. Rich is installed automatically as a package dependency.

```bash
# Recommended: install as a standalone command
uv tool install qiantong
# or
pipx install qiantong
# or
pip install qiantong

# Latest code from GitHub
uv tool install git+https://github.com/mediapig/qiantong.git
```

After installing, run `qiantong` or `chouqian`.

To run the test suite:

```bash
pip install -e '.[test]'
pytest
```

GitHub Actions runs the test matrix on Ubuntu, macOS and Windows, checks the
wheel in a clean environment, and builds the macOS universal2 location helper.
Creating a `v*` tag starts the release workflow. Configure a PyPI Trusted
Publisher for this repository with the `pypi` environment before publishing.

At startup the program selects an animation backend from available resources: low-memory or single-core machines use plain output, ordinary machines use ANSI cursor controls, and machines with at least four cores and four GiB of memory use Rich Live. Rich is installed as part of the main package. Override the choice with `QIANTONG_ANIMATION=plain|ansi|rich`.

For serial consoles, older terminals or log output, use the portable line-by-line backend:

```bash
QIANTONG_ANIMATION=plain qiantong
```

On a capable machine, `QIANTONG_ANIMATION=rich qiantong` can be used to force Rich Live explicitly.

## How to play

| Key | Action |
| --- | --- |
| Space | Start / stop (press once to start, again to stop) |
| q / Esc / Ctrl-C | Quit |

1. **Ask with jiaobei (掷筊请示).** For each toss, press space to throw the two crescent-shaped blocks and press space again to land them. Each block lands yin or yang:
   - one yin, one yang: holy toss (圣杯) ✓
   - two yang: laughing toss (笑杯) ✗
   - two yin: yin toss (阴杯) ✗

   You need three holy tosses in a row before you may draw a lot. Any other result starts over from the first toss.
2. **Shake the tube (摇签).** Press space to start shaking and space again to stop. A stick pops out. Its number stays hidden until the result is shown.
3. **Read the lot (解签).** Shows the lot number, its rank, the story behind it, the poem and the interpretation.

## Which lots: where are you?

At startup the program guesses where you are and shows the lot choices available for that region. Three signals vote:

| Signal | Votes | Notes |
| --- | --- | --- |
| GPS | 5 | Uses the macOS Core Location helper, an explicit `QIANTONG_LOCATION`, or a local gpsd socket. Abstains when unavailable or too inaccurate. |
| Time zone | 3 | Usually set automatically from your location, so the strongest hint. `UTC` and the like abstain. |
| System language | 2 | Says who you are rather than where you are. `zh-TW` selects Taiwan Traditional Chinese, `zh-HK`/`zh-MO` selects Hong Kong Traditional Chinese, and `zh-SG`/`zh-MY` stays on Simplified Chinese. macOS reads the system preferences, Windows the UI language, other systems `LANG` and related variables. Languages unrelated to a region, such as English, abstain. |

Each signal votes for Japan (Sensō-ji), Taiwan (Sixty Jiazi lots), Hong Kong (Wong Tai Sin lots) or anywhere else (Guanyin lots). The place with the most votes wins; a tie goes to the signal ranked higher in the table. After the region is selected, the first page lets you choose its available thematic pack, such as Guanyin, Guandi, Yue Lao, Caishen or Wenchang, before the ritual starts.

The random engine is independent of the region router. Each fortune system is mounted as a plugin that supplies its data and ritual/presentation behavior. This keeps the core usable on desktops, servers, NAS systems and command-line routers.

### Third-party plugins

Plugins are discovered at startup through the Python entry-point group `qiantong.plugins`. A package can expose a `Plugin` object, a zero-argument factory, or a registrar that receives `register`; it may also provide its own `load_lots` and `render_lot` callables. The core application does not need to be edited when a new fortune system is installed.

On macOS, the universal2 Core Location helper is included in macOS builds of the package, so the first `qiantong` run asks for permission. If permission is denied or the helper is unavailable, the router falls back to time zone, IP and language. To build the helper locally, run `sh macos/LocationHelper/build.sh` on a Mac with Xcode command-line tools.

When the result is not Guanyin, the program tells you which signals decided it. Location is best-effort: a missing permission, GPS receiver or daemon never blocks a draw. On routers and NAS systems, set `QIANTONG_LOCATION=latitude,longitude[,accuracy]` or run gpsd with its standard local JSON socket. Choose the lots explicitly with `--temple`:

```bash
qiantong --temple sensoji   # Sensō-ji
qiantong --temple taiwan    # Sixty Jiazi lots
qiantong --temple guanyin   # Guanyin
qiantong --temple wongtaisin # Wong Tai Sin
qiantong --temple yuelao     # 月老姻缘签
qiantong --temple guandi     # 关帝灵签
qiantong --temple caishen   # 财神求财签
qiantong --temple wenchang  # 文昌学业签
qiantong --temple siamsi   # Thai Siam Si
qiantong --temple xinxam   # Vietnamese Xin Xăm
qiantong --temple oracle   # English Oracle
qiantong --temple inari    # Japanese Inari omikuji
qiantong --no-ip            # decide from the time zone and language only
TZ=Asia/Tokyo qiantong      # pretend to be in Japan
TZ=Asia/Taipei qiantong     # pretend to be in Taiwan
QIANTONG_LOCATION=22.3,114.2 qiantong  # provide a headless device location
```

## In Taiwan: Sixty Jiazi lots (六十甲子籤)

The Sixty Jiazi lots are used at nearly every Mazu temple in Taiwan. Each lot is named after a pair from the sexagenary cycle, from 甲子 to 癸亥, and shows its hexagram, element, poem, stories and answers for common questions (career, marriage, health, lost items…), in the original Traditional Chinese.

The jiaobei step stays, and follows the Taiwanese custom: after the stick pops out, toss once more to confirm it is the right one. Without a holy toss, the stick goes back into the tube and you shake again.

## In Japan: Sensō-ji fortunes

The 100 Kannon fortunes of Sensō-ji in Asakusa, Tokyo (ranks 大吉 / 吉 / 半吉 / 小吉 / 末小吉 / 末吉 / 凶). As at the temple, there is no jiaobei step: you go straight to the lot tube.

## In Hong Kong: Wong Tai Sin fortunes (黄大仙灵签)

The 100 traditional Wong Tai Sin lots associated with Sik Sik Yuen in Hong Kong. The program uses the same three holy jiaobei tosses as the Guanyin flow, then displays the lot title, grade and four-line poem in Traditional Chinese.

## Randomness

Every result is decided at the moment you press space to stop. The animation is only for show and has no effect on the outcome.

**Local cryptographic randomness.** Every draw uses Python's standard `secrets` module, backed by the operating system's cryptographic random number generator. The program does not contact a random-number service, so draws work offline and do not depend on a third-party endpoint.

Each draw takes 32 random bytes, appends the nanosecond timestamp of your key press, hashes them with SHA-256, and maps the result onto the target range by rejection sampling. Every lot therefore has a probability of exactly 1/100, and each block is yin or yang with probability exactly 1/2.

## Data sources

- Guanyin lots: from [yanxinyu777-beep/guanyin-lingqian-100](https://github.com/yanxinyu777-beep/guanyin-lingqian-100).
- Sixty Jiazi lots: from [DestinyLab/lottery-poetry-sixty-jiazi](https://github.com/DestinyLab/lottery-poetry-sixty-jiazi) (MIT License, by Lance He), converted from YAML to JSON.
- Sensō-ji Kannon lots (Chinese translation): from [Tamshen/senso-ji-stick-data](https://github.com/Tamshen/senso-ji-stick-data); the fortune entries of lots 6–9 were reformatted.
- Wong Tai Sin lots: from the [Kau Cim 100 public-domain reference dataset](https://www.kaucim.ai/reference/wong-tai-sin-kau-cim), checked against the Sik Sik Yuen Wong Tai Sin Temple stick enquiry.

Guanyin lot texts vary slightly between regions. For entertainment and cultural interest only.

## License

The code is released under the [MIT License](https://github.com/mediapig/qiantong/blob/main/LICENSE): anyone may use, modify and distribute it freely.

The fortune data in `src/qiantong/data/` comes from the third-party repositories listed above, and its copyright remains with the original authors. The Sixty Jiazi data (`taiwan.json`) is under the MIT License of its source repository; the Guanyin and Sensō-ji data come without a license and are not covered by the MIT License of this project.
