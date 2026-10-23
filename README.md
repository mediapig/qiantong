# qiantong · Guanyin fortune sticks in your terminal

Draw a Guanyin fortune stick (观音灵签) in the terminal: first ask for permission by tossing jiaobei blocks (掷筊), and once you get three holy tosses (圣杯) in a row, shake the lot tube and read your fortune poem and its interpretation.

The interface and the fortune texts are in Chinese.

## Installation

Requires Python 3.9+. No third-party dependencies.

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

At startup the program guesses where you are and picks the lots of that place. Three signals vote:

| Signal | Votes | Notes |
| --- | --- | --- |
| Time zone | 3 | Usually set automatically from your location, so the strongest hint. `UTC` and the like abstain. |
| IP country | 2 | Looked up via Cloudflare (`https://1.1.1.1/cdn-cgi/trace`, 2-second timeout). A VPN or proxy shows the exit country. Abstains if the lookup fails. |
| System language | 2 | Says who you are rather than where you are. macOS reads the system preferences, Windows the UI language, other systems `LANG` and related variables. Languages unrelated to a region, such as English, abstain. |

Each signal votes for Japan (Sensō-ji), Taiwan (Sixty Jiazi lots) or anywhere else (Guanyin lots). The place with the most votes wins; a tie goes to the signal ranked higher in the table. So the time zone decides as soon as one other signal agrees with it, while the IP and the language together outvote it. For example, a mainland visitor in Tokyo gets Sensō-ji lots, and a Japanese person living in Singapore gets Guanyin lots.

When the result is not Guanyin, the program tells you which signals decided it. A command-line tool has no access to GPS, so precise location is not used. Pass `--no-ip` to skip the IP lookup, or choose the lots explicitly:

```bash
qiantong --temple sensoji   # Sensō-ji
qiantong --temple taiwan    # Sixty Jiazi lots
qiantong --temple guanyin   # Guanyin
qiantong --no-ip            # decide from the time zone and language only
TZ=Asia/Tokyo qiantong      # pretend to be in Japan
TZ=Asia/Taipei qiantong     # pretend to be in Taiwan
```

## In Taiwan: Sixty Jiazi lots (六十甲子籤)

The Sixty Jiazi lots are used at nearly every Mazu temple in Taiwan. Each lot is named after a pair from the sexagenary cycle, from 甲子 to 癸亥, and shows its hexagram, element, poem, stories and answers for common questions (career, marriage, health, lost items…), in the original Traditional Chinese.

The jiaobei step stays, and follows the Taiwanese custom: after the stick pops out, toss once more to confirm it is the right one. Without a holy toss, the stick goes back into the tube and you shake again.

## In Japan: Sensō-ji fortunes

The 100 Kannon fortunes of Sensō-ji in Asakusa, Tokyo (ranks 大吉 / 吉 / 半吉 / 小吉 / 末小吉 / 末吉 / 凶). As at the temple, there is no jiaobei step: you go straight to the lot tube.

## Randomness

Every result is decided at the moment you press space to stop. The animation is only for show and has no effect on the outcome.

**Quantum random numbers by default.** At startup the program fetches 1024 bytes from the [quantum random number service of the OTH Regensburg Laboratory for Digitalisation](https://lfdr.de/QRNG/) into a pool, and fetches more when the pool runs out. The bytes are produced by ID Quantique's Quantis quantum random number hardware (a PCIe card), whose randomness comes from quantum physical processes.

**Local fallback.** If the service is unreachable, times out (3 seconds) or misbehaves, the program falls back to Python's standard `secrets` module, i.e. the operating system's cryptographic random number generator. After one failure it stays offline for the rest of the run so that draws never stall. The startup line tells you which source is in use.

Each draw takes 32 random bytes, appends the nanosecond timestamp of your key press, hashes them with SHA-256, and maps the result onto the target range by rejection sampling. Every lot therefore has a probability of exactly 1/100, and each block is yin or yang with probability exactly 1/2.

## Data sources

- Guanyin lots: from [yanxinyu777-beep/guanyin-lingqian-100](https://github.com/yanxinyu777-beep/guanyin-lingqian-100).
- Sixty Jiazi lots: from [DestinyLab/lottery-poetry-sixty-jiazi](https://github.com/DestinyLab/lottery-poetry-sixty-jiazi) (MIT License, by Lance He), converted from YAML to JSON.
- Sensō-ji Kannon lots (Chinese translation): from [Tamshen/senso-ji-stick-data](https://github.com/Tamshen/senso-ji-stick-data); the fortune entries of lots 6–9 were reformatted.

Guanyin lot texts vary slightly between regions. For entertainment and cultural interest only.

## License

The code is released under the [MIT License](https://github.com/mediapig/qiantong/blob/main/LICENSE): anyone may use, modify and distribute it freely.

The fortune data in `src/qiantong/data/` comes from the third-party repositories listed above, and its copyright remains with the original authors. The Sixty Jiazi data (`taiwan.json`) is under the MIT License of its source repository; the Guanyin and Sensō-ji data come without a license and are not covered by the MIT License of this project.
