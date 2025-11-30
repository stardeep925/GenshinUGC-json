## 成品关卡展示

> 以下关卡的平台路径由本项目生成的字典数据驱动，可在原神UGC「千星奇域」中直接游玩。
>
> 关卡名称：**失落乐章**
>
> 关卡 ID：`20033786150`
>
> 《失落乐章》是一款支持 1–8 人在线的多人对抗闯关玩法：在这个一切记忆都被记录于乐谱之中的世界里，来自深渊的噬谱之魔正吞噬乐章，使历史与情感逐渐归于寂静。玩家将被分配为守护原初乐谱的谱守者（A 方）或信奉遗忘的噬谱信徒（B 方），在悬浮于虚空的“乐章之路”上展开追逐博弈。A 方沿着由曲谱生成器不断铺设的 1×1×1 方块道路向终点前进，在有限复活次数内躲避坠落与敌方攻击，试图在终点奏响终章，唤回失落的乐章与记忆；B 方则乘坐并行飞艇，以远程打击、控制技能与地形破坏持续干扰推进，将倒下的 A 方逐步“转化”为同阵营同伴。最终，至少一名 A 方成功抵达终点，旋律将再度回响于世界；若所有 A 方被淘汰或尽数堕落为 B 方，世界将永远沉入无声的遗忘之中。

# 千星奇域音频量化字典生成工具


<div align="center">

![GenshinUGC-json](https://socialify.git.ci/stardeep925/GenshinUGC-json/image?description=1&font=KoHo&language=1&name=1&owner=1&pattern=Circuit%20Board&theme=Auto)

[![GitHub stars](https://img.shields.io/github/stars/stardeep925/GenshinUGC-json?style=flat-square)](https://github.com/stardeep925/GenshinUGC-json/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/stardeep925/GenshinUGC-json?style=flat-square)](https://github.com/stardeep925/GenshinUGC-json/network)
[![GitHub issues](https://img.shields.io/github/issues/stardeep925/GenshinUGC-json?style=flat-square)](https://github.com/stardeep925/GenshinUGC-json/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/stardeep925/GenshinUGC-json?style=flat-square)](https://github.com/stardeep925/GenshinUGC-json/pulls)

 [📦 项目仓库](https://github.com/stardeep925/GenshinUGC-json)

</div>

> 本工具用于将音频文件量化为符合「千星奇域」字典 JSON 格式的数据，并生成可直接加载至「千星沙箱」字典变量的资源。坐标仅作为数据存储载体，并不表示真实的空间坐标。

本项目以 `Vector3` 坐标列表作为**通用存储容器**承载量化后的数据，不赋予其真实三维空间含义。生成的 JSON 可直接作为「千星沙箱」中的字典变量导入和使用。

---

## 功能概览

- **目标用途**
  - 生成符合「千星沙箱」约定结构的 **Dict<Int32, Vector3List> JSON** 数据；
  - 将 **音频文件**（以及 MIDI 文件）量化为离散时间步上的数据片段，并封装为便于脚本或关卡逻辑访问的字典变量；
  - 使用 `Vector3(x,y,z)` 作为编码与存储载体，**不用于表示实际空间坐标**。

- **支持输入格式**
  - **MIDI**：`.mid` / `.midi`
  - **音频**：例如 `.m4a`（通过 `librosa` 加载，理论上支持多种常见音频格式）

- **时间轴量化**
  - 支持 `seconds` / `beats` / `ticks` 作为时间单位。
  - 可通过 `--quant-x` 或 `--subdiv` 控制时间步长。

- **数据生成逻辑（抽象描述）**
  - 将原始音频/MIDI 按时间切片，提取每个时间片上的特征信息（如事件、能量等级等）；
  - 将上述离散特征编码到 `x、y、z` 三个整型分量中：
    - `x`：计数或强度（例如平台数量、能量等级、音高编号等）；
    - `y`：分层/分轨标识（例如将音高区间或能量区间映射到 1~5 号轨道）；
    - `z`：时间步索引（在中心化与缩放后得到的离散时间坐标）；
  - 最终以 **Dict<Int32, Vector3List>** 形式写入 JSON 文件，供「千星沙箱」在运行时读取。

> 可以把整个流程理解为：**“音频/MIDI → 离散特征 → 编码到 Vector3 → 写入千星奇域字典 JSON”**。

---

## 安装与依赖

### 环境要求

- Python 3（推荐 3.8+）
- 能使用 `pip` 安装依赖

### 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

`requirements.txt` 中的主要依赖：

- `mido` – 解析 MIDI
- `librosa` / `audioread` / `soundfile` – 加载与分析音频
- `numpy` / `scipy` – 数值计算

---

## 快速上手

项目的命令行入口为 `midi_cli.py`，`midi.py` 对其进行了简单封装（调用 `midi_cli.main()`），便于直接执行。

### 1. 处理 MIDI 文件

```bash
python midi_cli.py -i 1.mid
```

默认行为：

- 时间单位：`seconds`
- 时间步长：自动（约 0.1s）
- 输出：在同目录生成 `1_xyz.json`
- 在终端打印一份中文统计报告（含颜色高亮）

### 2. 处理音频文件（推荐：秒级量化）

```bash
python midi_cli.py -i 1.m4a -x seconds --quant-x 0.2
```

该模式适用于将音频按时间片量化为字典数据的典型场景：

- 每 `0.2` 秒计算一次 RMS 能量
- 将能量映射为离散等级（例如 `0~15`），再映射到 `y` 轨道（1~5）
- 不再做按 `(y,z)` 的额外统计，而是直接将每个时间片的数据编码到 `Vector3` 中

### 3. 使用拍子/节拍为时间轴（适用于带节奏感的内容）

```bash
# MIDI：以拍为单位，每拍切 16 份
python midi_cli.py -i 1.mid -x beats --subdiv 16

# 音频：以节拍为单位（通过节拍检测估计 tempo）
python midi_cli.py -i 1.m4a -x beats --subdiv 32
```

---

## 命令行参数

由 `midi_cli.build_parser()` 定义：

- **`-i, --input`**  
  输入文件路径。若不指定，脚本会尝试使用当前目录下的 `1.mid`，不存在则报错。

- **`-x, --x-unit`**  
  时间单位，默认 `seconds`。可选：
  - `seconds`：以秒为单位
  - `beats`：以拍为单位
  - `ticks`：MIDI 原始 tick

- **`-o, --output`**  
  输出 JSON 路径。默认在输入文件同目录下生成 `<输入文件名去扩展>_xyz.json`。

- **`--quant-x` (float)**  
  显式指定时间步长：
  - `x-unit=seconds` 时：单位为秒（例如 `0.1` 表示 0.1 秒一格）
  - `x-unit=beats` 时：单位为拍
  - `x-unit=ticks` 时：单位为 tick

- **`--subdiv` (int)**  
  当 `x-unit=beats` 且未指定 `--quant-x` 时，表示“每拍切多少份”，默认 32。

- **`--max-jump` (int)**  
  用于可玩性分析（估算是否存在贯通路径），与字典数据本身无关。默认为 5。

---

## 导出 JSON 格式（千星奇域字典）

导出逻辑由 `io_utils.save_dictvec(coords, path)` 完成：

1. **内部坐标结构（中间表示）**

   ```python
   {
       "x": int,
       "y": int,
       "z": int,
       "t": float,
   }
   ```

   - `t` 为时间（秒），仅用于排序，不参与导出内容。

2. **Z 轴中心化与缩放**

   - 统计所有 `z` 的最小值和最大值
   - 以中点为中心线性缩放：
     - 若跨度 `span <= 1000`：不缩放
     - 否则将跨度压缩到约 1000
   - 将最终 `z` 限制到 `[-500, 499]` 范围内，保证兼容 3D 场景/沙箱中约定的取值区间

3. **输出为 Dict<Int32, Vector3List>**

   JSON 大致形态：

   ```json
   {
     "type": "Dict",
     "key_type": "Int32",
     "value_type": "Vector3List",
     "value": [
       {
         "key": { "param_type": "Int32", "value": "1" },
         "value": {
           "param_type": "Vector3List",
           "value": [
             "x1,y1,z1",
             "x2,y2,z2"
           ]
         }
       }
     ]
   }
   ```

   - 每个 `key`（1,2,3,...) 对应一个 `Vector3List`，内部是若干个 `"x,y,z"` 字符串。
   - 按 `z, x, y` 排序，并按 `per_list_limit`（默认 100）进行分块。

> 在「千星沙箱」中，可以将该 JSON 直接加载为字典变量，并通过脚本或逻辑读取各个 Vector3 条目，从而获取在音频量化阶段编码的节奏、能量、音高分层等信息。

---

## 处理流程与主要模块

- <details>
  <summary>🔧 处理流程示意（点击展开）</summary>

  <table>
  <tr>
  <td>

  ```mermaid
  graph TD
      A[输入文件 (MIDI / 音频)] --> B[解析与特征提取]
      B --> C[时间轴量化]
      C --> D[按 (y,z) 聚合与统计]
      D --> E[Dict<Int32, Vector3List> JSON 导出]
      E --> F[在千星奇域 / 千星沙箱中加载为字典变量]
  ```

  </td>
  </tr>
  </table>

  以上流程对应代码中的几个核心模块：`midi_reader.py` / `audio_reader.py` 完成解析与特征提取，`processing.py` 负责聚合统计，`io_utils.py` 负责导出 JSON，`midi_cli.py` 负责命令行参数解析与整体串联。

  </details>

- **`midi_cli.py`**  
  命令行入口与主流程：
  - 解析参数
  - 根据扩展名选择 MIDI 或音频处理函数
  - 调用处理链：读取 → 量化 → 聚合 → 导出 → 打印报告

- **`midi_reader.py`**  
  MIDI 解析与切片：
  - 使用 `mido` 读取事件和 tempo 信息
  - 计算 `note_on/note_off` 的起止时间（秒/拍/ticks）
  - 根据时间单位和步长把音符投影到离散时间步上

- **`audio_reader.py`**  
  音频读取与特征提取：
  - `seconds + quant_x` 模式：固定时间窗 RMS 能量 → 能量等级 → (x,y,z)
  - 其他模式：onset + beat + chroma → 近似主音高 → (x,y,z)

- **`processing.py`**  
  简单聚合函数 `aggregate_counts_by_yz`：
  - 将同一 `(y,z)` 上的多个事件统计为一条，`x` 表示计数。

- **`io_utils.py`**  
  - `save_dictvec`：导出为目标 JSON 结构（千星奇域字典）。
  - `compute_summary` / `format_summary_cn`：统计结果与中文摘要文本。

- **`midi.py`**  
  简单封装：`from midi_cli import main`，方便 `python midi.py` 直接运行。

---

## 作为库调用（可选）

除了命令行，你也可以在自己的 Python 脚本中直接调用：

```python
from midi_reader import midi_to_sliced_coords
from audio_reader import audio_to_sliced_coords
from processing import aggregate_counts_by_yz
from io_utils import save_dictvec, compute_summary, format_summary_cn
```

示例代码：

```python
coords_raw = audio_to_sliced_coords("1.m4a", x_unit="seconds", quant_x=0.2)
coords = aggregate_counts_by_yz(coords_raw)
save_dictvec(coords, "1_xyz.json")
summary = compute_summary(coords, coords_raw, max_jump=5)
print(format_summary_cn(summary))
```

---

## 注意事项

- Z 轴会被压缩到有限范围，超长音频/曲目在时间分辨率上会被适当压缩。
- 音频分析使用的是启发式方法（onset/chroma 或能量），并非精确的音符恢复。
- 终端彩色输出依赖 ANSI 转义序列，在部分 Windows 终端可能需要额外设置才能显示颜色。

