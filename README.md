# qiantong · 命令行观音灵签

在终端里求一支观音灵签：先掷筊请示，连得三次圣杯后摇签筒出签，最后显示签诗与解签。

## 安装

需要 Python 3.9+，无第三方依赖。

```bash
# 推荐：装成独立命令
uv tool install git+https://github.com/mediapig/qiantong.git
# 或
pipx install git+https://github.com/mediapig/qiantong.git

# 本地开发
pip install -e .
```

安装后可用 `qiantong` 或 `chouqian` 启动。

## 玩法

| 按键 | 作用 |
| --- | --- |
| 空格 | 开始 / 停止（按一次开始，再按一次停止） |
| q / Esc / Ctrl-C | 退出 |

1. **掷筊请示**：每掷一次，空格开始翻滚，再按空格落地，得到两枚爻：
   - 一阴一阳：圣杯 ✓
   - 两阳：笑杯 ✗
   - 两阴：阴杯 ✗

   必须连续三次都是圣杯，才可求签；中途失败就从第一掷重来。
2. **摇签**：空格开始摇签筒，再按空格停下，一支签跳出。
3. **解签**：显示签号、吉凶、典故、签诗、解曰。

## 在日本：浅草寺观音百签

如果检测到以下任一情况，签会换成东京浅草寺的观音百签（大吉 / 吉 / 半吉 / 小吉 / 末小吉 / 末吉 / 凶），并且跳过掷筊，直接摇签：

- 系统首选语言是日语（macOS 读系统偏好设置，Windows 读界面语言，其他系统读 `LANG` 等环境变量）；
- 时区是日本（`Asia/Tokyo`、`Japan`、JST）。

也可以手动指定：

```bash
qiantong --temple sensoji   # 浅草寺
qiantong --temple guanyin   # 观音灵签
TZ=Asia/Tokyo qiantong      # 模拟人在日本
```

命令行工具拿不到 GPS 定位，所以不按地理位置判断。

## 随机性

结果都在按下“停止”空格的那一刻决定，动画只是表现，与结果无关。

**默认用量子随机数。** 启动时向 [OTH Regensburg 数字化实验室的量子随机数服务](https://lfdr.de/QRNG/) 取 1024 字节存进缓冲池，用完再取。这些字节由 ID Quantique 的 Quantis 量子随机数硬件（PCIe 卡）产生，来源是量子物理过程本身的随机性。

**取不到就退回本机。** 断网、超时（3 秒）或服务异常时，改用 Python 标准库 `secrets`，也就是操作系统的密码学随机数。失败一次后，本次运行不再联网，免得每次抽签都卡住。启动时会写明这次用的是哪种随机源。

每次取 32 字节随机数，和按键时刻的纳秒级时间戳拼接，做 SHA-256，再用拒绝采样映射到目标范围。所以每支签的概率都严格是 1/100，每枚筊杯的阴阳各占 1/2。

## 签文来源

- 观音灵签：取自 [yanxinyu777-beep/guanyin-lingqian-100](https://github.com/yanxinyu777-beep/guanyin-lingqian-100)。
- 浅草寺观音百签（中文译文）：取自 [Tamshen/senso-ji-stick-data](https://github.com/Tamshen/senso-ji-stick-data)，第 6–9 签的运势条目整理过格式。

观音灵签各地版本的用字略有出入，仅供娱乐和传统文化参考。
