# PMF 调度甘特图生成工具

这是一个用于生成 **PMF (Prediction Motion Field)** 模块调度甘特图的工具集，用于可视化模块调度时序、检测时间冲突，并生成汇总分析图。

---

## 项目结构

```
├── gantt_scheduler.py                    # 核心甘特图绘制脚本
├── process_excel_and_generate_gantts.py  # Excel批处理与汇总图生成脚本
├── tasks.csv                             # 示例任务CSV文件
├── PMF *.csv                             # PMF调度数据文件
└── README.md
```

---

## 脚本功能说明

### 1. `gantt_scheduler.py` - 核心甘特图绘制器

#### 功能概述
从CSV文件读取任务调度数据，生成带有多段时间区间的甘特图，支持交互刷新。

#### 命令行参数
```bash
python gantt_scheduler.py [--csv-file FILE] [--output FILE] [--save-only]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--csv-file` | 输入CSV文件路径 | `tasks.csv` |
| `--output` | 输出PNG文件名 | 从配置tile字段生成 |
| `--save-only` | 仅保存PNG，不显示窗口 | False |

#### CSV文件格式

```csv
tile,标题名称
x,X轴标签
y,Y轴标签
mode,pipe begin,input begin,input end,output begin,output end
PMF_F8_0,0,2,24,10,31
PMF_M8_0_c,22,24,46,32,53
...
```

**配置行（前3行）：**
- 第1行：`tile` - 图表标题
- 第2行：`x` - X轴标签（默认：Clock Cycles）
- 第3行：`y` - Y轴标签（默认：Modules/Tasks）

**任务数据列：**
| 列名 | 说明 |
|------|------|
| `mode` | 模块名称，格式如 `PMF_[F/M][Size]_[Index]_[a/b/c]` |
| `pipe begin` | 流水线开始时间 |
| `input begin` | 输入开始时间 |
| `input end` | 输入结束时间（支持相对时间，如 `a22` 表示相对于input begin+22） |
| `output begin` | 输出开始时间 |
| `output end` | 输出结束时间 |

#### 时间解析规则
- **绝对时间**: 直接填写数值，如 `46`
- **相对时间**: 以 `a` 开头，表示相对于前一阶段的偏移量，如 `a22` 表示前一阶段结束+22

#### 甘特图段落与颜色

```
┌─────────┬───────────┬────────────┬───────────┐
│  Pipe   │   Input   │ Transition │  Output   │
│ (灰色)  │  (绿色)   │   (灰色)   │  (橙色)   │
└─────────┴───────────┴────────────┴───────────┘
```

| 段落 | 颜色 | 含义 |
|------|------|------|
| **Pipe** | 灰色 | 流水线准备阶段（pipe_begin → input_begin） |
| **Input** | 绿色 | 数据输入阶段 |
| **Transition** | 灰色 | 过渡阶段（input_end → output_begin） |
| **Output** | 橙色 | 数据输出阶段 |

#### 核心绘图逻辑

1. **任务读取与解析**
   - 解析CSV配置和任务数据
   - 处理相对时间标记（`a` 前缀）
   - `pipe_end` 自动等于 `input_begin`

2. **冲突检测**
   - 检测不同PMF模块间的 **Input段重叠**
   - 检测相同Size模块的 **Output段重叠**
   - 控制台输出警告信息

3. **汇总行绘制**
   - `PMF_INPUT`: 汇总所有PMF任务的输入段
   - `PMF_OUTPUT`: 汇总所有PMF任务的输出段
   - 颜色根据模块类型区分（M8/F8/M16/F16/M32/F32）

4. **刷新功能**
   - 图表右下角有 "Refresh" 按钮
   - 点击后重新读取CSV并刷新图表

#### 颜色映射（PMF汇总行）

**Input 汇总颜色：**
| 模式 | 颜色 |
|------|------|
| M8 | lightgreen |
| F8 | limegreen |
| M16 | orange |
| F16 | darkorange |
| M32 | gold |
| F32 | tomato |

**Output 汇总颜色：**
| 模式 | 颜色 |
|------|------|
| M8 | tomato |
| F8 | crimson |
| M16 | darkorange |
| F16 | orange |
| M32 | gold |
| F32 | orangered |

---

### 2. `process_excel_and_generate_gantts.py` - 批处理与汇总脚本

#### 功能概述
批量处理Excel文件中的多个PMF sheet，生成单独甘特图及按Size/Round分组的汇总分析图。

#### 使用方法
```bash
python process_excel_and_generate_gantts.py
```

**前提条件：** 当前目录需存在 `mrg.xlsx` 文件

#### 核心函数详解

##### `read_tasks_from_csv(csv_file_path)`
从CSV文件读取任务和配置。

```python
# 返回值
(tasks, config)  # 任务列表 + 配置字典
```

**处理逻辑：**
1. 读取前3行作为配置（tile, x, y）
2. 第4行起作为任务数据
3. 解析时间字段，支持 `a` 前缀相对时间
4. 自动计算 `pipe_end = input_begin`

##### `get_round(sheet)` / `get_c(sheet)`
从Sheet名称解析round和c参数。

```python
get_round("PMF c0 round0")     # 返回 '0'
get_round("PMF c1 round0-3")   # 返回 '1'
get_c("PMF c0 round0")         # 返回 'c0'
get_c("PMF UV c1 round0-3")    # 返回 'c1'
```

##### `collect_pmf_tasks(csv_files, sheet_names)`
从多个CSV文件收集并增强PMF任务。

**处理逻辑：**
1. 遍历所有CSV文件
2. 过滤出 `PMF_` 开头的任务
3. 添加元数据：`sheet`, `round`, `c`, `uv`
4. 重命名mode：`{原mode}_{uv}_{c}_{round}`
5. 对于 `round0-3` 的sheet，复制任务为 round 0 和 round 1

```python
# 示例：原始 mode = "PMF_F8_0", sheet = "PMF UV c1 round0-3"
# 生成两个任务:
#   mode = "PMF_F8_0_UV_c1_0"  (round 0)
#   mode = "PMF_F8_0_UV_c1_1"  (round 1)
```

##### `clean_pmf_tasks(tasks)`
清理和调整PMF任务，核心业务逻辑函数。

**删除规则（`_a`/`_b` 后缀任务）：**

| 通道 | Size | 处理 |
|------|------|------|
| Y | 16/32/64 | 删除 `_a`, `_b` 任务 |
| UV | 8/16/32 | 删除 `_a`, `_b` 任务 |

**调整规则（`_c` 后缀任务）：**

| 通道 | Size | 处理 |
|------|------|------|
| Y | 16/32/64 | 调整输出时间 |
| UV | 8/16/32 | 调整输出时间 |

**时间调整公式：**
```python
new_output_begin = old_output_end + 2
new_output_end = (old_output_end - old_output_begin) + new_output_begin
```

##### `get_size(mode)`
从mode名称提取Size数值。

```python
get_size("PMF_F8_0")    # 返回 '8'
get_size("PMF_M16_0_c") # 返回 '16'
get_size("PMF_M32_a")   # 返回 '32'
```

**正则匹配：** `r'[MF](\d+)'` 提取F或M后面的数字

##### `find_overlaps(intervals)`
检测时间区间重叠。

```python
intervals = [(10, 30), (20, 40), (50, 60)]
find_overlaps(intervals)  # 返回 [(20, 30)] - 第1和第2个区间重叠部分
```

**算法：** 两两比较，`overlap = (max(start1,start2), min(end1,end2))`

##### `merge_intervals(intervals)`
合并重叠的时间区间。

```python
intervals = [(10, 30), (20, 40), (50, 60)]
merge_intervals(intervals)  # 返回 [(10, 40), (50, 60)]
```

##### `plot_single_summary(grouped, filename, title, xlim)`
绘制单个汇总图的核心函数。

**绘图逻辑：**
1. 按 `(size, uv)` 分组绘制
2. 每组一行，显示所有任务的输出段
3. 检测并用红色标记重叠区域
4. 最后添加 Summary 汇总行

**颜色规则：**
```python
color = 'moccasin' if uv == 'Y' else 'lightgreen'
```

**文字标注格式：**
```python
suffix = f"{task['uv']} {task['c']} {mode_short}"  # 如 "UV c1 F8_0"
```

##### `generate_summary_plot(tasks, sizes, r, xlim)`
生成指定Size和Round的汇总图。

```python
# 示例调用
generate_summary_plot(cleaned_tasks, ['8'], '0', (0, 200))
# 生成: PMF_Summary_8_round0.png
```

##### `main()`
主函数，协调整个处理流程。

---

#### 完整处理流程图

```
mrg.xlsx
    │
    ▼
┌─────────────────────────────────────┐
│  1. 加载 Excel (data_only=True)     │
│     获取计算后的单元格值             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. 筛选 PMF 开头的 Sheet           │
│     例: ["PMF c0 round0",           │
│          "PMF UV c1 round0-3", ...] │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  3. 每个 Sheet → CSV 文件           │
│     "PMF c0 round0" → "PMF c0 round0.csv" │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  4. 调用 gantt_scheduler.py         │
│     为每个 CSV 生成单独的 PNG       │
│     使用 --save-only 模式           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  5. collect_pmf_tasks()             │
│     收集所有 PMF 任务               │
│     添加元数据 (uv, c, round)       │
│     处理 round0-3 复制              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  6. clean_pmf_tasks()               │
│     删除 _a/_b 任务                 │
│     调整 _c 任务输出时间            │
│     仅保留 output 相关字段          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  7. 生成 8 个汇总图                 │
│     Size: 4, 8, 16, 32              │
│     Round: 0, 1                     │
│     共 4 × 2 = 8 个 PNG             │
└─────────────────────────────────────┘
```

#### Sheet 名称解析规则

| Sheet 名称特征 | 解析结果 |
|----------------|----------|
| 包含 `UV` | uv = 'UV' |
| 不含 `UV` | uv = 'Y' |
| 包含 `c0` | c = 'c0' |
| 包含 `c1` | c = 'c1' |
| 包含 `round0`（不含 `round0-3`） | round = '0' |
| 包含 `round0-3` 或其他 | round = '1'（会复制为 round 0 和 1） |

#### 任务清理逻辑详解

**为什么要删除 `_a`/`_b` 任务？**
- 对于较大的块（Y通道16/32/64，UV通道8/16/32），`_a` 和 `_b` 是中间计算步骤
- 在汇总图中只需要关注最终输出 `_c`

**为什么要调整 `_c` 任务时间？**
- `_c` 任务的实际输出发生在原始 `output_end` 之后
- 调整公式确保汇总图显示真实的输出时序

```python
# 调整示例
# 原始: output_begin=100, output_end=120
# 调整后: output_begin=122, output_end=142
# 公式: new_begin = 120 + 2 = 122
#       new_end = (120-100) + 122 = 142
```

#### 生成的汇总图

共生成 8 个汇总图，按 Size 和 Round 分组：

| 文件名 | 内容 | X轴范围 |
|--------|------|---------|
| `PMF_Summary_4_round0.png` | Size=4, Round 0 | 0-200 |
| `PMF_Summary_4_round1.png` | Size=4, Round 1 | 0-200 |
| `PMF_Summary_8_round0.png` | Size=8, Round 0 | 0-200 |
| `PMF_Summary_8_round1.png` | Size=8, Round 1 | 0-200 |
| `PMF_Summary_16_round0.png` | Size=16, Round 0 | 0-800 |
| `PMF_Summary_16_round1.png` | Size=16, Round 1 | 0-800 |
| `PMF_Summary_32_round0.png` | Size=32, Round 0 | 0-800 |
| `PMF_Summary_32_round1.png` | Size=32, Round 1 | 0-800 |

#### 汇总图特性

- **Y 通道任务**: 使用 moccasin（浅橙）色
- **UV 通道任务**: 使用 lightgreen（浅绿）色
- **重叠区域**: 使用 **红色** 高亮显示
- **Summary 行**: 灰色底，红色标记重叠

---

## 模块命名规范

模块名称格式：`PMF_[Type][Size]_[Index]_[Suffix]`

| 字段 | 说明 | 示例 |
|------|------|------|
| Type | F=Forward, M=Merge | F, M |
| Size | 块大小 | 8, 16, 32 |
| Index | 序号 | 0, 1, 2, 3 |
| Suffix | 子任务标识（可选） | a, b, c |

**示例：**
- `PMF_F8_0` → Forward 8x8 块，序号0
- `PMF_M16_0_c` → Merge 16x16 块，序号0，子任务c

---

## 依赖安装

```bash
pip install matplotlib numpy openpyxl
```

---

## 使用示例

### 生成单个甘特图
```bash
# 使用默认 tasks.csv
python gantt_scheduler.py

# 指定输入文件和输出文件
python gantt_scheduler.py --csv-file "PMF c0 round0.csv" --output result.png

# 仅保存，不显示窗口
python gantt_scheduler.py --csv-file data.csv --save-only
```

### 批量处理 Excel
```bash
# 确保 mrg.xlsx 存在于当前目录
python process_excel_and_generate_gantts.py
```

---

## 输出示例

### 单任务甘特图
- 每行显示一个模块的调度时序
- 顶部显示 PMF_INPUT 和 PMF_OUTPUT 汇总行
- X轴为时钟周期，带有关键时间点刻度
- 图例说明各颜色含义

### 汇总分析图
- 按 Size/UV 类型分行显示
- 每行内显示所有相关任务的输出段
- 红色高亮标记时间冲突区域
- 最后一行为 Summary 汇总

---

## 注意事项

1. CSV 文件需使用 **UTF-8** 编码
2. 时间值必须为整数（时钟周期数）
3. 相对时间使用 `a` 前缀（如 `a22`）
4. Excel 批处理要求文件名为 `mrg.xlsx`
5. Sheet 命名需遵循 `PMF*` 格式以被识别
