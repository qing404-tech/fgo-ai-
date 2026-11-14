# FGO 主线自动推进器

用摄像头式的「截图 + 模板识别 + 模拟点击」来推进 FGO 主线的桌面工具。纯本地运行，
不读取游戏内存、不修改客户端、不注入进程，游戏看到的就是一次普通的触摸。

- **图形界面**：实时画面、框选抓模板、坐标拾取、日志与流程统计、单步调试
- **命令行**：`run / check / shot`，可定时无人值守
- **内置模拟游戏（mock）**：没有游戏、没有模拟器也能把整条链路跑通、做回归测试
- **纯 numpy 视觉**：模板匹配是自带的 NCC（FFT + 积分图）实现，不需要装 OpenCV

> ⚠️ **风险提示**：使用自动化脚本违反 FGO 用户协议，可能导致账号被封。本项目仅供
> 单机推进、学习与自动化技术研究，使用风险自负。请勿用于账号交易、代练等行为。

![识别效果](docs/preview.png)

上图是内置 mock 演示时的识别结果：绿框是命中的模板（分数 1.00），左上角黄字是当前
判定的流程。真实游戏里换成你自己抓的模板即可。

---

## 1. 它能做什么

一条完整的「推主线」循环：

```
主界面 → 终端 → 主线关卡 → 关卡节点 → 编队 → 支援 → 战斗（技能/宝具/选卡）
      → 结算 → 剧情（自动跳过/推进）→ 下一关 → ……
```

同时具备这些能力（细节见第 5 节）：

- **战斗方案**：用 JSON 描述每回合开哪些技能、放哪些宝具、选什么卡，可导入/导出
- **刷本循环**：`loop.mode=farm` 反复刷同一关，而不是一直打新关卡
- **AP 管理**：按顺序吃苹果、限制本次最大消耗、统计 AP 用量
- **运行报告**：战斗场次 / 清理次数 / 苹果数 / 耗时写进 `logs/`
- **模板体检**：一键看所有模板在当前画面的分数，专门用来调阈值和抓错模板
- **界面自动识别**：给每一屏算指纹，自动认出「现在是哪一屏」，还能边跑边学（第 6 节）
- **一键检测画面**：截一张图就说清楚「现在是什么、能不能跑、缺什么」（第 6 节末尾）

同时处理这些打断：

| 场景 | 处理方式 |
| --- | --- |
| AP 不足 | 点「使用黄金果实」并确认（可配置成用圣晶石） |
| 升级 / 羁绊 / 获得道具弹窗 | 点确定，继续推进 |
| 剧情对话 | 连点推进；有「跳过」就先跳过再确认 |
| 战斗结算 | 点继续，进入下一关 |
| 连接错误 | 点重试 |
| 战斗不能（续关） | 默认放弃，回到关卡列表 |
| 陌生画面 | 点安全位置 + 返回键尝试退出，连续多次则暂停并保存截图报警 |

**做不到的**：自动抽卡、自动买卖、识别阵容强弱、自动换队伍（编队是固定队伍 +
好友支援）、跨服共用模板（每套 UI 抓一次模板即可）。

---

## 2. 环境准备

| 项目 | 要求 |
| --- | --- |
| 系统 | Windows 10 / 11（macOS、Linux 也能跑，需自行装 adb） |
| Python | 3.9+，自带 tkinter 即可 |
| 依赖 | `numpy`、`Pillow`（`pip install -r requirements.txt`） |
| 模拟器 | MuMu 12 / LDPlayer 9 / BlueStacks 5 / Nox 任选，**必须开启 ADB 调试** |
| 分辨率 | 建议 1280×720 或 1920×1080（16:9），**模板必须在同一分辨率下抓取** |

安装：

```bat
cd fgo_story_bot
pip install -r requirements.txt
```

如果 `python` 不在 PATH，把上面命令里的 `python` 换成你的解释器完整路径。

---

## 3. 快速开始（不碰游戏，先看效果）

```bat
python -m fgo_auto.cli run --mock
```

或者双击 **`启动界面.bat`** → 后端选「Mock 演示（无需游戏）」→ 点「连接设备」→ 点「开始」。

内置模拟游戏会自动生成一套模板（`templates/mock/`），你会看到界面实时识别画面、
点攻击、按颜色选卡（Buster 优先）、跳过剧情、用苹果恢复 AP、处理升级弹窗，
每清一个节点 `CLEARED` 数字 +1。

想验证代码是否健康：

```bat
python tests\test_core.py     # 32 项单元测试（匹配数值、颜色、模板、配置）
python tests\test_plan.py     # 30 项：战斗方案解析 / 运行报告
python tests\test_adbscan.py  # 39 项：ADB/模拟器探测、启动、尺寸校准
python tests\test_scene.py    # 38 项：界面指纹、相似度、自学习、引擎集成
python tests\test_diagnose.py # 23 项：画面自检（黑屏/白屏/未知画面/分辨率）
python tests\smoke.py         # 端到端：跑 mock，清 6 个以上节点并检查各流程命中
python tests\plan_smoke.py    # 战斗方案 / 刷本模式 / 模板体检联调（mock）
python tests\gui_smoke.py     # 界面冒烟：建窗、连 mock、跑几秒、停止、关闭
```

### 3.1 界面风格

默认是**深色工业风**（致敬明日方舟的视觉语言，但为原创实现，不使用游戏素材）：

| 元素 | 处理 |
| --- | --- |
| 配色 | 近黑底 `#0A0B0D`、面板 `#14171C`、细线 `#2B3038`、橙色强调 `#F2A33C` |
| 形状 | 全部直角；标题条用切角色块；画面区四角取景框；画布淡网格底纹 |
| 字体 | Bahnschrift SemiCondensed（拉丁/数字）、Microsoft YaHei UI（中文）、Consolas（日志/坐标） |
| 布局 | 标题条 → 设备两行 → 左预览 / 右面板 → 底部状态条；默认 1180×720，1366×768 屏也能完整显示 |

想改配色/字体只需编辑 `fgo_auto/theme.py`（`BG / ACCENT / LINE / TEXT` 等常量 + 字体函数），
不涉及任何业务逻辑。

### 3.2 模板抓取向导

「工具 → 模板抓取向导」：自动抓一张当前画面，用鼠标框住按钮，点「保存并下一个」，
它会按缺失清单依次提示下一张（已抓过的自动跳过）。抓的时候注意：

- 框选范围只包住按钮本身，不要带太多背景（背景会变，模板会失效）；
- 同一屏可以连续框多个按钮，抓完再切下一屏；
- 抓完重启任务，日志里的「缺 N 张模板」就会消失。

### 3.3 战斗策略（BBChannel 风格）

参考 BBChannel 的「操作序列 / 高级参数」思路，战斗方案（`--plan`）支持三类策略：

| 配置 | 说明 |
| --- | --- |
| `turns[].skills` | 按回合放技能，如 `["1-1","2-3"]` 表示 1 号从者 1 技能、2 号从者 3 技能 |
| `turns[].np` | 按回合放宝具，如 `[1]` 表示 1 号从者宝具 |
| `cards.policy` | 出卡策略：`priority`（按卡色优先）/ `same_color`（同色连携）/ `full_chain`（优先凑三连） |
| `cards.priority` | 卡色优先级，默认 `["buster","arts","quick"]` |
| `cards.per_turn` | 指定某回合必须出的卡色，如 `{"3": ["arts","arts","buster"]}` |

另外 `ap.wait_seconds`：苹果用完时不直接报错，而是等待 AP 回复（0 = 不等待，最大 1800 秒），
适合挂机；`runtime.skip_story` 控制是否自动跳过剧情。

### 3.4 流程调度规则

流程不是「从上往下碰运气」，而是有明确调度规则（`fgo_auto/engine.py`）：

| 规则 | 说明 |
| --- | --- |
| 优先级 `priority` | 数字大的先测。弹窗类（确认/升级/连接重试）高于页面类，避免被页面流程抢走 |
| 特异性 | 同优先级时，`detect` 条件更多（`all`+`any`+`none` 合计）的先测 |
| 提示 `hint` | 上次命中的流程只在「同优先级 + 同特异性」时提前，不再无条件置顶（旧版正是它让「跳过」压住「跳过确认」） |
| 动作防抖 | 执行动作后 0.6s 内不复用上一次识别结果，避免「刚点完跳过又按旧判定再点一次」 |
| 卡住升级 | 同一流程连续 `max_repeat` 次且画面几乎不变 → 执行 `alt_actions` 备用动作；再一轮仍无变化就停止并提示 |
| 未知界面 | 连续 5 次未识别且画面不变 → 存现场截图并停止，直接告诉你「这一屏还没有模板」 |
| 剧情开关 | `runtime.skip_story: false` 时自动停用「剧情跳过 / 跳过确认」，只推进对话 |

### 3.5 用打包好的 EXE（免安装）

`dist\FGO自动推主线.exe`（桌面上也放了一份）是**自带 Python 运行时**的单文件版，
目标机器不需要装 Python 或任何依赖：

| 项目 | 说明 |
| --- | --- |
| 首次启动 | 把运行环境解压到 `%LOCALAPPDATA%\FGOStoryBot`，约 6~10 秒；之后秒开 |
| 数据位置 | `config.json`、`templates\`、`logs\` 都在该目录下 |
| 重置 | 删掉该目录，或用 `FGO自动推主线.exe --reset` 启动 |
| 换目录 | 设置环境变量 `FGO_BOT_HOME` 指向别处（便携模式 / 多开） |
| 体积 | 约 35 MB，内含 Python 3.12 + numpy + Pillow + tkinter |

EXE 没有代码签名，Windows SmartScreen 可能提示「未知发布者」，点「更多信息 → 仍要运行」即可；
个别杀软对「自解压 + 启动脚本」敏感，如被拦截请加信任。

想重新打包（例如改了代码之后）：

```bat
powershell -ExecutionPolicy Bypass -File tools\build_exe.ps1
```

脚本会把精简后的运行时 + 应用压进 `payload.zip`，用 `tools\launcher.cs` 编译成 EXE，
产物是 `dist\FGO自动推主线.exe`。

图标是 `tools\app.ico`（内置的是一张原创的「金发蓝裙骑士少女」风格图，不使用官方美术素材）。
想换成自己的图：

```bat
python tools\make_icon.py --from D:\pics\your.png --preview docs\icon_preview.png
powershell -ExecutionPolicy Bypass -File tools\build_exe.ps1
```

Windows 可能缓存旧图标，替换后执行一次 `ie4uinit.exe -show`，或重启资源管理器。

---

## 4. 接入真实游戏

### 4.1 连接

**现在基本不用手填。** 启动模拟器（进到桌面）后，点界面顶部的「**自动检测**」：

- 自动找模拟器自带的 adb（包括装在 D:/E:/F: 盘的情况，走注册表 + 各驱动器扫描）；
- 自动判断厂商与端口（MuMu / 雷电 / BlueStacks / 夜神 / 逍遥），用厂商 CLI 或配置文件拿真实端口；
- 自动列出可用设备，标出分辨率、是否装了 FGO，双击选一个就连接并保存到 `config.json`；
- 下次启动会**静默自动探测**一次，直接把字段填好。

**模拟器没开也能一键拉起**：点「启动模拟器」（或检测不到设备时按提示确认），会调用厂商 CLI
启动实例，然后轮询等待设备就绪（默认最多 120 秒），成功后自动重新探测并连接。

模拟器里仍需打开 ADB 调试（这是一次性的）：

| 模拟器 | 开关位置 |
| --- | --- |
| MuMu 12 | 设置 → 其他 → 「ADB 调试」 |
| 雷电 9 | 设置 → 其他设置 → 「ADB 调试」→ 开启本地连接 |
| BlueStacks 5 | 设置 → 高级 → 「Android 调试桥」 |

检测不到时按顺序排查：

1. 模拟器是否**已经启动并进入桌面**（没启动时不会有设备，只能找到 adb）；
2. ADB 调试是否打开；
3. 安全软件是否拦了 adb / 自解压程序；
4. 命令行看细节：`python -m fgo_auto.cli devices`，会打印检测到的模拟器、adb 路径、端口和候选设备；
5. 实在不行再手填：「adb 路径」+「设备序列号」（MuMu 默认 `127.0.0.1:16384`，雷电 `127.0.0.1:5555`）。

连上后状态栏会显示 `已连接 adb:127.0.0.1:16384 1280x720`。

### 4.2 抓模板（只需要做一次）

模板 = 一小块截图，用来认得「这个按钮是什么」。**这是唯一需要手工的步骤**，
因为模板就是游戏 UI 本身，不能随代码分发。

操作：勾选「抓取模板模式」→ 在画面上框住按钮 → 输入下表里的名字 → 保存。

| 模板名 | 抓什么 | 必须 | 缺失后果 |
| --- | --- | --- | --- |
| `t_home` | 主界面稳定标识（如左下角终端图标、AP 条底色块） | 建议 | 从主界面开始的那一步走兜底坐标 |
| `t_terminal` | 主界面「终端」按钮 | 建议 | 用 `params.nav.terminal` 坐标 |
| `t_stage_select` | 关卡列表标题（「主线关卡」字样） | 建议 | 关卡列表页识别不到 |
| `t_stage_node` | 一个固定样式的关卡节点（别框数字/进度） | 建议 | 用 `params.nav.node` 坐标 |
| `t_party_start` | 编队界面的「出击」按钮 | 建议 | 用 `params.party_start` |
| `t_support_start` | 支援选择界面的「开始」按钮 | 建议 | 用 `params.support_start` |
| `t_attack` | 战斗界面红色「攻击」圆按钮 | **必须** | 战斗无法进行 |
| `t_cards` | 选卡界面标识（如「指令卡」标题） | 可选 | 点完攻击直接按坐标选卡 |
| `t_result_continue` | 结算界面「继续 / 下一关」 | **必须** | 战斗后卡在结算 |
| `t_dialog` | 剧情对话框的一小块特征（≤400×120） | 建议 | 剧情推进走兜底连点 |
| `t_skip` | 剧情右上角「跳过」 | 可选 | 只能逐句点，慢一些 |
| `t_skip_confirm` | 跳过确认弹窗的「确定」 | 可选 | 同上 |
| `t_ap_restore` | AP 不足弹窗标题 | 建议 | AP 不足时无法续战 |
| `t_use_apple` | 「使用黄金果实」按钮 | 建议 | 同上 |
| `t_levelup` | 升级弹窗标题 | 可选 | 卡在升级弹窗 |
| `t_confirm_ok` | 通用「确定」按钮 | 可选 | 部分弹窗卡住 |
| `t_conn_retry` | 连接错误「重试」 | 可选 | 断线后卡住 |
| `t_np` | 宝具按钮（`use_np` 打开时才需要） | 可选 | 不放宝具 |

抓取要点：

- **只框按钮/一小块特征**，宽度 100~400px 最合适；整屏面板（>900px）会变慢且易误判。
- 别框会变的东西：数字、HP 条、倒计时、角色立绘。
- 名字必须和上表一致（也可以用别的名字，但要同步改 `config.json` 里的流程）。
- 抓的时候画面要干净：不要半透明遮罩、不要鼠标悬停特效。
- 建议在**同一个分辨率**下抓全套；换分辨率（720p→1080p）要重抓。
- 日服/美服/韩服 UI 不同，各抓一套，放到不同目录再用 `templates.dir` 切换。

抓完点「缺失模板」能看到还差哪些、分别被哪个流程使用。

### 4.3 校准坐标（模板缺失时的兜底）

`config.json` 的 `params` 里都是 0~1 的归一化坐标（相对屏幕宽高），与分辨率无关。
勾选「坐标拾取」，在画面上点一下，坐标会复制到剪贴板，粘到 `params` 里即可。

需要校准的通常是：`dialog_tap`（剧情连点位置）、`popup_ok`（弹窗确定）、
`nav.terminal / nav.node`、`party_start`、`support_start`、`continue_decline`。

### 4.4 开跑

1. 先点「检测画面」：会截图并给出一份自检报告（黑屏/分辨率/界面指纹/模板命中/缺哪些模板）。
   报告说「可以直接跑」再继续；说没认出就按建议处理。
2. 勾「干跑（只识别不点击）」，看日志里的流程判定是否稳定（`▶ 流程「…」`）。
3. 取消干跑，点「开始」。
4. 想手动确认每一步：点「单步」，看画面上的绿框和右上角流程判定。
5. 出错会自动存图到 `logs/`，文件名带时间戳和原因（如 `unknown_1.png`）。

---

## 5. 战斗策略

### 5.1 战斗方案（推荐，bbchannel 风格）

用一份 JSON 描述「第几回合开哪些技能、放哪些宝具、选什么卡」，与画面识别解耦，
可以从外部工具生成后直接导入：

```json
{
  "name": "3T 周回",
  "cards": {
    "mode": "color",
    "priority": ["buster", "arts", "quick"],
    "per_turn": { "3": ["arts", "arts", "buster"] }
  },
  "turns": [
    { "turn": 1, "skills": ["1-1", "1-2", "2-1"], "np": [1] },
    { "turn": 2, "skills": ["3-1"], "np": [2] },
    { "turn": 3, "skills": [], "np": [] }
  ]
}
```

- 从者编号、技能位都从 **1** 开始；`"1-2"` = 1 号从者的第 2 个技能
  （也接受 `[1, 2]` 或 `{"servant": 1, "slot": 2}`）
- `np` 是本回合要放的宝具（从者编号）；`cards.per_turn` 指定该回合点哪三张卡
- 没写的回合 = 平砍

三种用法：

| 方式 | 做法 |
| --- | --- |
| 界面 | 工具 → 导入战斗方案…（选 JSON） |
| 配置 | `"battle": {"plan": "examples/plan_3t.json"}` |
| 命令行 | `python -m fgo_auto.cli run --plan examples\plan_3t.json` |

`examples/plan_3t.json` 可以直接改。注意：字段语义参考了 bbchannel 的作战脚本思路，
但**不保证与它的 JSON 逐字段兼容**，从 Chaldea 等工具转过来时可能需要一个中间脚本。

### 5.2 技能 / 宝具按钮怎么点

优先用模板，没有模板才用坐标：

| 按钮 | 模板名 | 坐标配置 |
| --- | --- | --- |
| 技能 | `t_skill_<从者>_<技能>`（如 `t_skill_2_1`） | `battle.skill_grid` |
| 宝具 | `t_np_<从者>`（如 `t_np_1`） | `battle.np_grid` |

```json
"skill_grid": {"x": [0.19, 0.30, 0.41], "y": [0.62, 0.72, 0.82]},
"np_grid":    {"x": [0.19, 0.30, 0.41], "y": 0.90}
```

即「x 是从者列、y 是技能行」。默认值是估算的，**第一次用请用坐标拾取校准**。

### 5.3 选卡

| 来源 | 行为 |
| --- | --- |
| 方案 `cards.per_turn` | 严格按指定卡色点，凑不齐的用剩下的卡补 |
| 方案 / 配置 `priority` | 按红 / 蓝 / 绿优先级排序 |
| `card_mode: "fixed"` | 永远从左到右，最稳，适合宝具队 |

颜色识别参数：`hsv`（H 是 0~360，不是 OpenCV 的 0~180）、`min_classify`（同色像素占比）、
`card_slots`（三张卡中心点）、`card_box`（单卡宽高）、`sample`（卡内取样区域）。

识别不出来时会自动退化为从左到右，不会卡死；要精调就用「模板体检」和日志里的
`选卡：颜色 [...]` 对照。

### 5.4 循环模式：推主线 / 刷本

```json
"loop": {"mode": "story"}
```

| `loop.mode` | 行为 |
| --- | --- |
| `story`（默认） | 每轮打「下一个新关卡」，适合推主线 |
| `farm` | 每轮打同一个关卡，适合刷素材 / 狗粮 |

`farm` 要指定刷哪一关，模板优先、坐标兜底：

```json
"loop": { "mode": "farm", "farm_node_tpl": "t_farm_node", "farm_node_point": [0.5, 0.45] }
```

### 5.5 AP 管理

AP 不足时按顺序尝试吃苹果，并统计消耗：

```json
"ap": {
  "apple_order": ["gold", "silver", "bronze", "quartz"],
  "apple_points": {"gold": [0.50, 0.42]},
  "apple_ap": {"gold": 40, "silver": 20, "bronze": 10, "quartz": 0},
  "max_per_run": 5,
  "keep_min": 20
}
```

- 有 `t_apple_<种类>` 模板就点模板，否则点 `apple_points` 里的坐标，再点确认
- `max_per_run`：本次最多吃几个（0 = 不限），到上限会停下来报错
- `apple_ap`：只用于统计（`summary.json` 里的 `ap_spent`）

### 5.6 运行报告

| 文件 | 内容 |
| --- | --- |
| `logs/report.jsonl` | 逐条事件（开战 / 结算 / 苹果 / 错误），可直接拿去做分析 |
| `logs/summary.json` | 本次汇总：战斗场次、清理次数、苹果数、AP 消耗、耗时、错误 |

「工具 → 运行摘要」可以直接看，状态栏也会实时显示战斗场次和苹果数。

### 5.7 模板体检

「工具 → 模板体检」会在当前画面上把**所有模板**跑一遍，列出分数 / 阈值 / 结论
（命中、分数够但颜色不符、临界、未命中），同时写 `logs/template_check.txt`。
调阈值、排查「为什么没识别到」时最省事。

---

## 6. 界面自动识别（场景指纹）

除了逐个模板匹配，工具还会给每一屏算一个「指纹」，直接判断当前是哪个界面。

- **指纹内容**：32×18 归一化灰度缩略图（布局）、24 段色相直方图（配色）、16×9 边缘密度（结构）、
  3×3 区块平均色、宽高比。一次比对约 0.2ms，不做 FFT，比模板扫描快一个数量级。
- **自学习**：某屏的模板命中分数 ≥ 0.95 时，自动把该画面记进 `scenes.json`（每个界面最多 6 个样本，
  几乎相同的样本去重）；也可以在「界面识别」页点「学习当前界面」手动补。
- **识别优先**：先认界面，认出来（≥ `scene.threshold` 且比第二名高 `scene.margin`）就直接执行对应流程；
  认不出再退回模板匹配——两条路互为兜底。
- **越用越快**：界面学过之后，那一屏不再做整帧模板扫描。mock 全流程耗时从 65s 降到 51s。

右侧「界面识别」页能看到：当前界面与相似度、已学界面与样本数、自动学习开关，以及
「学习当前界面 / 删除选中 / 清空全部 / 保存到磁盘」。

```json
"scene": {
  "enabled": true,
  "threshold": 0.88,
  "margin": 0.05,
  "auto_learn": true
}
```

```bat
python -m fgo_auto.cli scenes                    :: 查看学到的界面
python -m fgo_auto.cli scenes --forget 战斗回合   :: 删掉某一个
python -m fgo_auto.cli scenes --clear            :: 清空重学
```

注意：`scenes.json` 与**分辨率、模拟器渲染**相关（换分辨率建议清空重学）；它只负责「认界面」，
点哪里仍然由模板/坐标决定。

### 6.1 一键检测画面

界面左上角「检测画面」按钮（命令行 `python -m fgo_auto.cli probe`）会截图并做一次完整体检：

| 检查 | 说明 |
| --- | --- |
| 画面 | 实际尺寸、与期望分辨率是否一致、亮度/饱和度/均匀度 |
| 空白检测 | 全黑（没启动/锁屏/加载）、全白（启动页）、纯色（被遮罩） |
| 界面指纹 | 认成哪个界面、相似度、第二名、是否可信 |
| 模板流程 | 按模板命中了哪个流程、关键模板分数 |
| 模板库存 | 必需模板就绪几个、缺哪些 |
| 结论 | 一句话：能不能直接跑；不能跑时给出具体下一步 |

检测失败时还能在弹窗里「保存截图」「学习此界面」，方便把现场情况发出来排查。

---

## 7. 配置说明

`config.json` 首次运行时自动生成，只需要写想改的键（会深合并到默认值）。

### 7.1 设备与运行

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `device.backend` | `adb` | `adb` 或 `mock` |
| `device.adb_path` | `""` | 空 = 自动找 PATH / 常见模拟器目录 |
| `device.serial` | `""` | 空 = 用第一个在线设备；多开时填 `127.0.0.1:16384` |
| `device.connect` | `""` | 连接前先 `adb connect` 的目标 |
| `device.auto_detect` | `true` | 没填 adb/序列号时自动探测模拟器 |
| `device.auto_display` | `true` | 多显示器时自动抓「游戏所在屏」（MuMu 必需） |
| `device.display_id` | `""` | 手动指定显示器 uid，空 = 自动 |
| `device.auto_launch` | `false` | 检测到模拟器没启动时自动拉起 |
| `device.launch_wait` | `120` | 启动后等设备就绪的秒数 |
| `device.emulator_index` | `0` | 多开时用第几个实例 |
| `runtime.poll_interval` | `0.35` | 两轮识别之间的间隔（秒） |
| `runtime.dry_run` | `false` | 只识别不点击 |
| `runtime.humanize` | `true` | 点击抖动 + 随机延迟 |
| `runtime.tap_jitter` | `3` | 点击随机偏移（像素） |
| `runtime.click_delay` | `[0.05, 0.14]` | 每次点击后的随机停顿 |
| `runtime.max_unknown` | `10` | 连续识别失败多少次后停止 |
| `runtime.max_minutes` | `0` | 最长运行分钟，0 = 不限 |
| `runtime.max_steps` | `0` | 最多执行多少个流程，0 = 不限 |
| `runtime.save_debug_frames` | `true` | 异常时存截图到 `logs/` |
| `runtime.report` | `true` | 写 `logs/report.jsonl` 与 `summary.json` |

### 7.2 视觉

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `vision.min_score` | `0.86` | 匹配阈值；画面有滤镜/压缩就降到 0.80~0.84 |
| `vision.work_scale` | `0.35` | 粗扫分辨率比例；调大更准更慢 |
| `vision.color_tolerance` | `60` | 灰度匹配后允许的平均颜色差；0 = 关闭颜色校验 |
| `vision.scales` | `[1.0]` | 多尺度搜索，分辨率不一致时可用 `[0.9, 1.0, 1.1]` |

### 7.3 战斗 / 循环 / AP

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `battle.plan` | `""` | 战斗方案 JSON 路径，空 = 用旧技能轴 |
| `battle.card_mode` | `auto` | `auto` 按颜色 / `fixed` 从左到右 |
| `battle.priority` | `[buster, arts, quick]` | 卡色优先级 |
| `battle.skill_grid` | 见默认配置 | 技能按钮坐标（从者列 × 技能行） |
| `battle.np_grid` | 见默认配置 | 宝具按钮坐标 |
| `battle.skill_plan` | `{}` | 旧技能轴：`{"1": [[x,y], ...]}` |
| `loop.mode` | `story` | `story` 推主线 / `farm` 刷同一关 |
| `loop.farm_node_tpl` | `""` | 刷本要点的关卡模板 |
| `loop.farm_node_point` | `""` | 刷本关卡坐标（模板缺失时用） |
| `ap.apple_order` | `[gold, silver, bronze, quartz]` | 吃苹果的优先顺序 |
| `ap.apple_points` | `{}` | 各苹果按钮坐标 |
| `ap.apple_ap` | 全 0 | 各苹果的 AP 值（只用于统计） |
| `ap.max_per_run` | `0` | 本次最多吃几个，0 = 不限 |
| `ap.keep_min` | `0` | 保留 AP 下限 |
| `scene.enabled` | `true` | 启用界面指纹识别 |
| `scene.threshold` | `0.88` | 认定同一界面的相似度阈值 |
| `scene.margin` | `0.05` | 还需比第二名高多少才算可信 |
| `scene.auto_learn` | `true` | 模板高置信命中时自动学习界面 |

### 7.4 流程（flows）

每个流程 = 一个「看到什么 → 做什么」规则：

```json
{
  "name": "AP不足",
  "cooldown": 2.0,
  "detect": { "any": ["t_ap_restore"] },
  "actions": [
    { "if": { "tpl": "t_use_apple",
              "then": [{ "tap": "t_use_apple" }, { "wait": 1.5 },
                       { "tap_xy": "popup_ok" }],
              "else": [{ "error": "AP 不足且找不到苹果按钮" }] } }
  ]
}
```

- `detect`：`any`（任一命中）/ `all`（全部命中）/ `none`（一个都不能命中）/ `min_score`
- 流程**从上到下**匹配，命中第一个就执行，所以「弹窗/异常」要放前面，通用「确认」放后面
- `cooldown`：同一流程多快可以再次触发，防止连点

支持的动作：

| 动作 | 说明 |
| --- | --- |
| `{"tap": "t_x"}` | 按模板点击；加 `"fallback": "params键"` 在模板缺失时用坐标；`"timeout": 3` 等它出现 |
| `{"tap_xy": [0.5, 0.9]}` | 按坐标点击（≤1 视为归一化，字符串视为 `params` 里的键） |
| `{"wait": 0.8}` | 等待（秒） |
| `{"wait_tpl": {"tpl": "t_x", "timeout": 8}}` | 等某个模板出现 |
| `{"swipe": {"from": [0.5,0.8], "to": [0.5,0.2], "ms": 300}}` | 滑动 |
| `{"tap_until_gone": {"tpl": "t_dialog", "point": "dialog_tap", "interval": 0.45, "max": 400, "until_any": ["t_stage_select"]}}` | 连点直到某模板消失或出现别的模板（剧情推进核心） |
| `{"tap_points_until": {"points": "nav.chapter", "until_any": ["t_stage_node"]}}` | 依次尝试多个坐标 |
| `{"if": {"tpl": "t_x", "then": [...], "else": [...]}}` | 条件分支 |
| `{"repeat": {"times": 3, "actions": [...]}}` | 重复 |
| `{"call": "battle_attack"}` | 调用内置策略（`battle_attack` / `pick_cards` / `use_skills` / `reset_battle` / `wait_battle_idle`） |
| `{"log": "文字"}` / `{"error": "文字"}` | 写日志 / 立即报错停止 |
| `{"back": true}` / `{"screenshot": "tag"}` | 返回键 / 存调试图 |

**加一个「每日任务」流程**的示例：在 `flows` 里加

```json
{
  "name": "每日任务",
  "cooldown": 5,
  "detect": { "any": ["t_daily_banner"] },
  "actions": [{ "tap": "t_daily_banner" }, { "wait": 2 }]
}
```

然后抓一张 `t_daily_banner` 模板即可，不用改代码。

---

## 8. 命令行

```bat
python -m fgo_auto.cli run --mock                       :: mock 演示
python -m fgo_auto.cli run                              :: 连真机跑
python -m fgo_auto.cli run --mode farm --plan examples\plan_3t.json
python -m fgo_auto.cli run --dry-run --minutes 5        :: 干跑 5 分钟，验证识别
python -m fgo_auto.cli devices                          :: 自动探测模拟器 / adb / 设备
python -m fgo_auto.cli devices --launch                 :: 没设备时启动模拟器并等待
python -m fgo_auto.cli scenes                           :: 查看学到的界面指纹
python -m fgo_auto.cli probe                            :: 检测当前画面（自检报告）
python -m fgo_auto.cli probe --save logs\now.png        :: 自检并保存截图
python -m fgo_auto.cli check                            :: 检查模板/配置，列出缺失
python -m fgo_auto.cli shot logs\now.png                :: 截图验证连接
python -m fgo_auto.cli run --backend adb --steps 200
```

`Ctrl+C` 可安全中断。

---

## 9. 目录结构

```
fgo_story_bot/
├── run_gui.py               # 界面入口
├── 启动界面.bat             # 双击启动（自动找 python）
├── dist/
│   └── FGO自动推主线.exe    # 单文件版（自带运行时，免安装）
├── tools/
│   ├── build_exe.ps1        # 重新打包 EXE
│   ├── launcher.cs          # EXE 启动器源码（自解压 + 启动）
│   ├── make_icon.py         # 生成图标（也可把自己的图片转成 .ico）
│   └── app.ico              # 当前图标
├── config.json              # 配置（首次运行生成）
├── scenes.json              # 界面指纹库（自动学习，可删）
├── requirements.txt
├── fgo_auto/
│   ├── config.py            # 默认配置 + 深合并
│   ├── device.py            # ADB 设备层（自动找 adb / 连模拟器）
│   ├── adbscan.py           # 模拟器 / adb / 端口自动探测
│   ├── scene.py             # 界面指纹识别与自学习
│   ├── diagnose.py          # 画面自检（检测画面 / probe）
│   ├── theme.py             # 界面主题（深色工业风）
│   ├── vision.py            # 模板匹配（NCC / FFT / 积分图）
│   ├── templates.py         # 模板仓库与依赖分析
│   ├── actions.py           # 动作解释器 + 苹果/选关/结算策略
│   ├── plan.py              # 战斗方案（JSON）
│   ├── report.py            # 运行报告（jsonl + summary）
│   ├── battle.py            # 技能、宝具、选卡
│   ├── engine.py            # 主循环：识别 → 执行 → 恢复
│   ├── fakegame.py          # 内置模拟游戏（mock）
│   ├── gui.py               # Tkinter 界面
│   └── cli.py               # 命令行
├── templates/               # 模板 PNG（mock 的在 templates/mock）
├── logs/                    # 运行日志 + 异常截图
├── docs/preview.png         # 识别效果示意图
├── examples/plan_3t.json    # 战斗方案示例
└── tests/
    ├── test_core.py         # 单元测试（视觉/颜色/模板/配置）
    ├── test_plan.py         # 战斗方案 / 报告单元测试
    ├── smoke.py             # 端到端 mock 测试
    ├── plan_smoke.py        # 方案 / 刷本 / 体检联调
    ├── gui_smoke.py         # 界面冒烟测试
    └── diag_scores.py       # 每个界面所有模板的分数诊断
```

---

## 10. 已知限制

- **固定阵容**：只点「出击」，不会自动换从者、换礼装、换御主礼装。
- **战斗策略简单**：按配置开技能、放宝具、按颜色/顺序选卡；不计算伤害、不判断敌方职阶、
  不会根据血量调整目标。
- **依赖模板**：换服务器（国服/日服/美服）、换语言、换分辨率、换 UI 版本都要重抓模板；
  流程逻辑本身通用。
- **不处理所有弹窗**：活动广告、公告、强制更新等少见弹窗可能触发「未识别画面」，
  靠恢复动作点安全位置，连续失败会停下来报警。
- **需要模拟器可调试**：iOS 真机、未开 ADB 的模拟器无法使用。
- **自动启动依赖厂商 CLI**：MuMu 用 `MuMuManager`、雷电用 `ldconsole`、BlueStacks 用 `HD-Player`；
  个别老版本命令不同，失败时会在日志里打出实际执行的命令，可改用配置里的坐标/手动启动。

---

## 11. 常见问题

**连不上 / `unauthorized`**
模拟器没开 ADB 调试，或 adb 版本冲突。先关掉其他 adb 程序（Android Studio、其他脚本），
用模拟器自带的 adb 路径，再 `adb kill-server` 后重连。`unauthorized` 需要在模拟器里
弹出的授权框点「允许」。

**点「自动检测」找不到设备**
先确认模拟器已经启动并进入桌面（只是装了但没启动，只能找到 adb，不会有设备）。仍不行就跑
`python -m fgo_auto.cli devices`：它会列出「检测到哪个模拟器、adb 在哪、试过哪些端口、有没有设备」。
如果安全软件拦了 adb，把模拟器目录加入白名单；实在不行手填 adb 路径 + `127.0.0.1:16384`。

**双击后界面一闪就退 / 完全没反应**
先看 `%LOCALAPPDATA%\FGOStoryBot.launcher.log`：
- 没有这个文件 → EXE 根本没被执行，多半是安全软件拦截，加白名单或改用 `启动界面.bat`；
- 有日志且写着「2.5 秒内退出」→ 界面进程崩溃，常见原因是**游戏覆盖层软件**（游戏加加 / GAMEPP、
  录屏、悬浮窗、某些输入法皮肤）注入到 pythonw 里；退出这类软件再试；
- 也可以试 `FGO自动推主线.exe --reset`，强制重新解压运行环境；
- 启动日志里若出现「检测到覆盖层软件：GamePPLite.exe」，说明游戏加加正在注入界面进程，
  退出它（或关掉「游戏内覆盖」）再试；实在不行卸载 `D:\GamePPLite`。

**MuMu 抓到的画面是桌面 / 黑屏，不是游戏**
MuMu 15 同时存在多个虚拟屏（mumuscreen000/002/003/004），默认 `screencap` 抓的是
0 号屏 = 安卓桌面。本工具会自动读 `dumpsys SurfaceFlinger` 的图层名，挑出含
`com.bilibili.fatego`（或 `com.tencent.tmgp.fgo`）的那个屏，并按内容丰富度打分。
日志里会写 `选屏: port=2 图层=... 细节=...`。想强制指定就在配置里填 `device.display_id`
（`adb shell dumpsys SurfaceFlinger --display-id` 里那串大数字）。

**日志里满屏「未识别画面」，不知道补哪张模板**
现在每次遇到没见过的界面，会打印「最接近的模板 + 分数」，并存进 `logs/unknown.jsonl`；
界面里「工具 → 未知界面记录」可以直接看清单。按分数最高的那个流程去抓模板即可。

**识别时好时坏**
把 `vision.min_score` 降到 0.80；确认模板是同一分辨率、同一画质下抓的；检查
`logs/unknown_*.png` 看当时画面。窗口有半透明遮罩或动画时，可以把模板的
`region` 限制到局部（`templates.json` 里配置）。

**总是「未识别画面」**
大概率是模板名和配置对不上，或者只抓了半个按钮。用「缺失模板」清单核对；
勾「干跑」+ 反复「单步」，看绿框位置对不对。

**战斗中卡住**
选卡坐标偏了：用「坐标拾取」确认 `battle.card_slots` 三个点是否落在卡片中心；
颜色识别不稳就改 `card_mode: "fixed"`。

**速度慢**
识别是 8~15ms/模板，1280×720 比 1920×1080 快约 2 倍；`poll_interval` 可以调大；
流程越靠前越省时间（把常用流程放前面）；模板别抓太大。

**换日服 / 换模拟器**
复制一份 `templates/` 目录改个名，配置里改 `templates.dir`，重新抓一套模板即可，
流程逻辑完全通用。

**多开模拟器**
每个实例的 `device.serial` 不同（`adb devices` 看），用不同 config 文件分别跑。

---

## 12. 实现说明（给想改代码的人）

- **识别**：`vision.Matcher` 用 FFT 算 NCC 分子、积分图算窗口方差，等价
  `cv2.TM_CCOEFF_NORMED`；先在 0.35 倍分辨率全帧粗扫取 top-3 候选，再在原分辨率
  小窗口内用「局部积分图 + 点积」精确评分。灰度匹配后再比对平均颜色，避免
  「同形状不同颜色」的按钮互相误判。
- **状态机**：没有硬编码的状态枚举，全靠 `config.json` 里的 `flows` 规则表；
  引擎每轮截一张图，按顺序问「这个流程的模板在不在」，命中就执行它的 `actions`。
- **容错**：同一画面复用上次识别结果；上次命中的流程优先复测；未知画面走
  `recovery` 动作（点安全点 → 返回键 → 连续失败则停）。
- **界面识别**：`scene.fingerprint()` 把整帧压成 5 组特征，相似度用「缩略图相关 + 平滑色相直方图
  交集 + 边缘相关 + 区块色指数衰减」加权；识别要求「够像」且「比第二名明显像」，避免相近界面误判。
  指纹不参与点击决策，只用于选流程，因此可以安全地边跑边学。
- **设备探测**：`adbscan` 不依赖写死的路径——注册表卸载项拿到安装目录（所以装在 F: 盘也能找到），
  目录扫描带深度/耗时上限，端口先问厂商 CLI（`MuMuManager info`、`bluestacks.conf`），
  拿不到再按厂商规律试，最后用 `pm list packages` 判断哪台装了 FGO。
- **战斗方案**：`plan.BattlePlan` 只描述「意图」（第几回合开什么、放什么、选什么卡），
  具体点哪里由 `battle.py` 决定：优先模板、退回坐标。因此同一份方案能跨分辨率使用。
- **报告**：`report.Report` 只记事件与计数，写盘失败也不影响主流程；战斗场次按
  「新一场第一回合选卡」统计，清理次数按结算界面统计。
- **和 bbchannel 的关系**：本项目的战斗方案参考了它「用 JSON 驱动战斗」的思路，
  但数据结构是重新设计的，**不是**它的脚本格式；刷本/AP/报告这些能力是对齐它的使用
  方式，实现细节各自独立。
- **测试**：`tests/smoke.py` 用 mock 游戏做端到端断言（至少清 6 个节点、覆盖
  AP 恢复/升级弹窗/选卡/剧情等流程），改代码后跑它最快；`tests/plan_smoke.py`
  额外覆盖战斗方案、刷本模式和模板体检。

---

## 13. 免责声明

本项目不包含任何游戏资源，模板需用户自行从自己的游戏画面截取。使用自动化工具
违反 FGO 用户协议，可能被官方判定违规并封禁账号，作者不承担任何后果。
请仅在单机环境学习自动化技术，不要用于商业代练、账号交易等用途。
