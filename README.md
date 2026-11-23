# 汽水音乐 安卓自动化脚本

![Platform](https://img.shields.io/badge/platform-Android-green)
![Framework](https://img.shields.io/badge/framework-AScript-blue)
![Based on](https://img.shields.io/badge/based%20on-iOS%20version-orange)
![Python](https://img.shields.io/badge/python-3.x-yellow)

基于 AScript 安卓引擎的自动化脚本，自动观看汽水音乐广告以获取免费听歌时长。

## 🚀 快速上手（最简四步）

1. **手机**：装 [AScript App](https://www.ascript.cn) → 开**无障碍**权限 → 开发者页打开**设备服务**（端口 9096）。
2. **电脑**：VS Code 装 **AScript 插件** → 把手机 IP 填进 `.vscode/settings.json` 的 `ascript.deviceId` → 手机电脑连**同一 WiFi**。
3. **运行**：VS Code 里点运行；或手机 AScript →「工程管理」→ 点**运行**，之后全自动循环领时长，额度用完自停。
4. **还不会？**：把本仓库链接直接发给你的 AI Agent（如 WorkBuddy），说一句「帮我部署」，它会自动拉代码、配环境、连手机并跑起来。

> 工程已上传手机时，可跳过第 1、2 步，直接在手机端点运行。详细配置见下方。

> ### 📌 来源声明
>
> **本项目改造自 [wei6718189/qishuiAScriptProject](https://github.com/wei6718189/qishuiAScriptProject)（iOS 版）**
>
> 原项目是 iOS 专用脚本，依赖 WebDriverAgent + `ascript.ios.*`。
> 本项目在其基础上完成 **Android 平台适配**，改写为 `ascript.android.*`，
> 原 iOS 代码完整保留在 [`__init___ios_backup.py`](./__init___ios_backup.py)。
>
> 感谢原作者 [@wei6718189](https://github.com/wei6718189) 的开源工作。

## 功能流程

```
启动 → 🔇 静音媒体音量 → 启动 App → 跳开屏广告 → 清弹窗 → 回到首页
    ↓
OCR 找广告入口「免费听」→ 进入广告
    ↓
（新版/一加：点歌曲卡片「免费听」；旧版/vivo：兜底点右上角「免」字坐标）
    ↓
┌──────────────────────────────────┐
│  等广告倒计时结束（最长 60s）      │
│         ↓                        │
│  点右上角「领取成功」              │
│         ↓                        │
│  弹窗点「领取奖励」→ 自动进下一轮  │
│         ↓                        │
│  成功次数 +1，重复循环             │
│                                  │
│  连续 10 轮没领到 → 自动退出       │
└──────────────────────────────────┘
    ↓
退出时 🔊 自动恢复原来的媒体音量
```

> 🔇 **静音广告**：脚本运行期间自动把媒体音量调到 0（铃声/来电/闹钟不受影响），退出时自动恢复原音量。不想静音把 `MUTE_ADS` 改成 `False` 即可。

## 运行环境

- **平台**：Android（实测 vivo V2055A / Android 14 / 1080×2400，一加 PJA110 / Android 16 / 1240×2772）
- **AScript App**：4.0.17+，运行模式「无障碍模式」
- **必需权限**：辅助功能（无障碍）、录屏授权、悬浮窗
- **OCR 引擎**：paddle（百度 PP-OCR V5，默认）或 mlkit（谷歌，更快）

## 项目结构

```
qishuiAScriptProject/
├── __init__.py              # 安卓版主入口（AScript 工程约定，必须叫这个名字）
├── __init___ios_backup.py   # 原 iOS 版脚本备份
├── res/img/                 # 图标与模板图（安卓版基本用不到）
├── .vscode/settings.json    # 平台 / 设备地址 / Python 路径
└── .trae/rules/ascript.md   # AScript AI 编码规则
```

## 快速开始

### 1. 手机端

1. 装 AScript App，开启**无障碍**权限
2. 进 App 的「开发者」页，开启**设备服务**（默认端口 9096）
3. 记下手机局域网 IP，如 `192.168.1.100`

### 2. 电脑端

1. 装 VS Code + AScript 插件
2. 确认 `uvx --version` 可用
3. 把手机 IP 填进 `.vscode/settings.json` 的 `ascript.deviceId`
4. 手机和电脑连同一个 WiFi

> `.vscode/settings.json` 里的 `192.168.1.100:9096` 是占位示例，请换成你自己手机的 IP 和端口。

### 3. 运行

在 VS Code 里用 AScript 插件运行工程，或让 AI 调用 `run_project`。

## 让它自己跑（无人值守）

脚本本身已经是全自动的（`AUTO_CLICK_MIAN = True`），启动后不用管。要彻底脱离电脑，按下面三步做。

### 第一步：手机端直接运行

1. 手机打开 **AScript App**
2. 进「**工程管理**」→ 找到 `qishuiAScriptProject`
3. 点 **运行**

工程已经上传到手机了，不需要电脑参与。运行后手机会自己找广告入口、看广告、领奖励，一直循环到当日额度用完（连续 10 轮没领到就自动退出）。

### 第二步：系统设置防中断

这几个设置不做，跑几分钟就会被系统掐掉：

| 设置项 | 路径（vivo 为例） | 作用 |
|--------|------------------|------|
| 电池优化白名单 | 设置 → 电池 → 后台耗电管理 → AScript → 允许后台高耗电 | 防止后台被杀 |
| 自启动 | 设置 → 应用管理 → AScript → 权限 → 自启动 | 允许后台存活 |
| 保持唤醒 | 开发者选项 → 不锁定屏幕（充电时） | 双保险 |

脚本内部已经调了 `Device.keep_screen_on()`，会保持屏幕常亮；每轮开始还会 `Device.wake_up()` 唤醒，所以息屏也能恢复。

### 第三步（可选）：打包成独立 APK

想更彻底、连 AScript App 都不用开：

1. AScript App → 首页找到「**打包独立程序**」
2. 选择 `qishuiAScriptProject` 工程
3. 生成 APK 并安装

打包后的 App 可以设桌面图标直接点、配合系统自启动实现开机跑。

### 定时每天跑

AScript 没有内置定时任务，用手机系统自带的能力：

- **vivo**：设置 → 快捷与辅助 → 自动任务 → 新建（定时启动指定应用）
- **第三方**：Tasker / MacroDroid 定时启动 AScript 并运行工程

## 关键配置

打开 `__init__.py` 头部：

| 常量 | 默认 | 说明 |
|------|------|------|
| `APP_PACKAGE` | `com.luna.music` | 安卓版汽水音乐包名 |
| `AUTO_CLICK_MIAN` | `True` | 是否自动点「免」字（False = 你手动点第一次） |
| `KEEP_SCREEN_ON` | `True` | 屏幕常亮，防息屏中断 |
| `AUTO_RESTART_APP` | `True` | 连续失败时自动重启 App 恢复 |
| `MUTE_ADS` | `True` | 运行时静音广告（只静音媒体音量，铃声/来电不受影响）；`False` = 保留声音 |
| `MUTE_RESTORE_VOLUME` | `True` | 退出时恢复静音前的媒体音量 |
| `MIAN_X_RATIO` | `0.937` | 兜底坐标：「免」字按钮相对屏幕 X 位置（OCR 未命中时用） |
| `MIAN_Y_RATIO` | `0.063` | 兜底坐标：「免」字按钮相对屏幕 Y 位置（OCR 未命中时用） |
| `OCR_ENGINE` | `"paddle"` | OCR 引擎，识别不准可换 `"mlkit"` |
| `LOOP_INTERVAL` | `3` | 每轮间隔秒数 |
| `MAX_LOOP_COUNT` | `100` | 最大循环次数（约 40 分钟） |
| `MAX_IDLE_ROUNDS` | `10` | 连续空跑多少轮退出（当日额度用完） |

## 与 iOS 版的主要差异

| 项目 | iOS 版 | 安卓版 |
|------|--------|--------|
| 模块前缀 | `ascript.ios.*` | `ascript.android.*` |
| 启动 App | `app_start(bundle_id=)` | `system.open(package)` |
| 包名 | `com.soda.music` | `com.luna.music` |
| 控件树 | WDA dump 不稳，走 OCR | 无障碍控件树，`Selector` 15ms 级 |
| 广告入口定位 | OCR | **OCR 找「免费听」优先 + 坐标兜底**（新版入口是文字按钮，旧版是图片） |
| 点击通道 | WDA（易被检测） | 无障碍（不被检测） |
| 屏幕尺寸 | `screen_size()` | `Device.display()` |

## 已知要点

1. **广告入口分两种版本**：
   - **新版/一加**：入口是歌曲卡片上的「免费听」文字按钮，OCR 可稳定识别（实测置信度 0.986），代码优先点它。
   - **旧版/vivo**：右上角「免」字是图片按钮，控件树 87 个节点都没有它、OCR 也识别不出（字体会被识别成乱码），用比例坐标 `(0.937W, 0.063H)` 兜底。
2. **倒计时文案**：`17秒后可领取奖励`，位于顶部 y≈40。
3. **领取弹窗**：显示「再看1个视频得 / 今日免费听」，绿色「领取奖励」按钮在屏幕中央偏下。
4. **广告底部有「立即下载」大按钮**：绝不能点，会跳到应用商店。代码里所有点击都限定在文字匹配上，不会误触。
5. **不要写 `if __name__ == "__main__"`**：AScript 工程入口约定不同，主体代码直接写在顶层，末尾 `main()` 就是入口。

## 广告中途的两种挽留弹窗（重点）

广告播放到一半会弹窗，**两种弹窗的正确操作完全相反**，点错就拿不到奖励：

### ① 短剧/视频广告的挽留弹窗 → 点「继续观看」

```
再看05秒继续解锁
   第24日免费听
┌─────────────────┐
│    继续观看      │  ← 绿色主按钮，点这个
└─────────────────┘
     坚持退出         ← 灰色小字，别点（放弃奖励）
```

实测坐标：`继续观看` @ (538, 1282) @ 1080×2400

### ② 直播形式广告的互动弹窗 → 点「退出」

```
继续互动还是退出？
5 秒后自动进入直播间
```

- 点「继续互动」→ 进直播间，**直播间不算广告时长**，白看
- 点「退出」→ 留在广告页，正常拿奖励

代码里的 `handle_live_prompt()` 专门处理这个：识别到 `继续互动 / 继续观看直播 / 进入直播间 / 秒后进入 / 自动进入 / 是否继续` 时，只点 `退出 / 退出互动 / 不感兴趣 / 取消 / 关闭`，**绝不点含「继续/进入」的按钮**。

### ③ 已经误入直播间 → 立即退出

代码里的 `handle_live_room()` 会检测 `更多直播 / 说点什么 / 在线观众` 等直播间特征，优先点右上角关闭按钮，兜底按返回键。

### 性能设计

直播互动弹窗只有 **5 秒**反应窗口，所以 `wait_ad_countdown()` 每轮**只做一次全屏 OCR**（`scan_screen_texts()`），在内存里按优先级匹配所有条件，而不是反复调用 `Ocr.find`。实测单次 `Ocr.find_all()`：paddle 约 0.8s，mlkit 约 0.4s。

> ⚠️ 踩坑：`Ocr.find_all()` 返回的是 **dict 列表**，而 `Ocr.paddleocr()` 返回的是 **OcrText 对象**，两种要分别处理，否则属性访问会全部拿到空值。

## 免责说明

脚本仅用于自动化观看广告领取官方免费权益，请遵守汽水音乐用户协议。每日有领取上限，连续 10 轮领不到会自动退出，不要反复空跑。

## 致谢

- 原项目：[wei6718189/qishuiAScriptProject](https://github.com/wei6718189/qishuiAScriptProject)（iOS 版）
- 自动化框架：[AScript](https://www.ascript.cn)（Python 移动端自动化引擎）

本项目在其基础上完成安卓平台适配，iOS 原版代码保留在 `__init___ios_backup.py`。

## 更新记录

### Android 适配版

- 模块从 `ascript.ios.*` 迁移到 `ascript.android.*`
- 包名改为安卓版 `com.luna.music`
- 「免」字按钮改用比例坐标定位（实测为图片按钮，无 text 属性）
- 利用无障碍控件树优先查找，OCR 作为兜底
- 新增屏幕常亮、自动唤醒、连续失败自动重启 App
- 新增 `AUTO_CLICK_MIAN` 全自动开关
- 实测环境：vivo V2055A / Android 14 / 1080×2400，连续多轮领取成功

### 新版界面适配（OCR 定位入口）

- `click_mian_button()` 改为优先 OCR 查找「免费听 / 免听 / 免费畅听」文字按钮，命中即点；未命中时回退到原比例坐标，兼容旧版
- 修复新版/一加机型上因入口位置变化而点进搜索页卡死的问题
- 新增实测环境：一加 PJA110 / Android 16 / 1240×2772，领奖循环正常

### 静音广告

- 新增 `MUTE_ADS`：脚本运行期间把媒体音量(type=3)调到 0，广告不再出声，铃声/来电/闹钟不受影响
- 新增 `MUTE_RESTORE_VOLUME`：退出时自动恢复静音前的媒体音量
- 通过 `ascript.android.media` 实现；老设备无该模块时自动跳过，不影响主流程

