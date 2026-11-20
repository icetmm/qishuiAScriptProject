# -*- coding: utf-8 -*-
"""
汽水音乐 安卓自动化脚本 — 自动看广告获取免费听歌权益
=====================================================
改造自 iOS 版（原作者 wei6718189），适配 AScript 安卓引擎。

与 iOS 版的主要差异：
  1. 模块从 ascript.ios.* 换成 ascript.android.*
  2. 安卓有完整控件树，优先用 Selector 精确查找，OCR 兜底
  3. 包名改为安卓版汽水音乐 com.luna.music
  4. 点击走无障碍通道，不会被 App 检测（iOS 的 WDA 点击容易被拦截）

功能流程：
  启动 App → 跳开屏广告 → 清弹窗 → 等你手动进广告
  → 等倒计时结束 → 点「领取成功」→ 点「领取奖励」→ 自动进下一轮 → 循环
"""

import time
import traceback

# ============== 基础模块导入 ==============
from ascript.android import action, system  # type: ignore
from ascript.android.system import R, Device  # type: ignore
from ascript.android.screen import Ocr, FindImages  # type: ignore
from ascript.android.node import Selector  # type: ignore


# ============== 全局配置 ==============

APP_NAME = "汽水音乐"
APP_PACKAGE = "com.luna.music"      # 安卓版包名（iOS 是 com.soda.music）

# 主循环控制
MAX_LOOP_COUNT = 100                # 最大循环次数（防死循环）
LOOP_INTERVAL = 3                   # 每轮间隔秒数
MAX_IDLE_ROUNDS = 10                # 连续多少轮没领到就退出（当日额度用完）

# 无人值守相关
KEEP_SCREEN_ON = True               # 保持屏幕常亮，防止息屏中断
AUTO_RESTART_APP = True             # 连续失败时自动重启 App

# OCR 引擎：paddle=百度 PP-OCR V5（准） / mlkit=谷歌（快）
OCR_ENGINE = "paddle"

# "免"字按钮相对屏幕位置（实测 vivo V2055A 1080x2400：约 1012, 151）
MIAN_X_RATIO = 0.937
MIAN_Y_RATIO = 0.063

# 是否自动点"免"字进入广告
# True  = 全自动（脚本自己点，每轮都自动进广告）
# False = 半自动（你自己点第一次，之后脚本接管）
AUTO_CLICK_MIAN = True

# 运行时全局
SCREEN_W = 1080
SCREEN_H = 2400


# ============== 工具函数 ==============

def log(msg: str):
    """统一日志打印"""
    ts = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{ts}] {msg}")


def get_screen_size():
    """获取屏幕尺寸，多种方式兜底"""
    global SCREEN_W, SCREEN_H
    try:
        d = Device.display()
        w = int(getattr(d, "widthPixels", 0) or 0)
        h = int(getattr(d, "heightPixels", 0) or 0)
        if w > 0 and h > 0:
            return w, h
    except Exception as e:
        log(f"  Device.display() 取值失败: {e}")
    return SCREEN_W, SCREEN_H


def safe_click(x, y, desc=""):
    """安全点击：带日志 + 异常捕获"""
    try:
        log(f"点击 [{desc}] -> ({x}, {y})")
        action.click(int(x), int(y))
        time.sleep(0.6)
        return True
    except Exception as e:
        log(f"点击失败 [{desc}]: {e}")
        return False


def _node_bounds(node):
    """从控件节点上取边界 [l, t, r, b]，兼容多种属性名/返回类型"""
    for attr in ("bounds", "rect", "frame", "getBounds"):
        try:
            b = getattr(node, attr, None)
            if b is None:
                continue
            if callable(b):
                b = b()
            if isinstance(b, dict):
                l = b.get("left", b.get("l", 0))
                t = b.get("top", b.get("t", 0))
                r = b.get("right", b.get("r", 0))
                bo = b.get("bottom", b.get("b", 0))
                b = [l, t, r, bo]
            if b and len(b) == 4:
                return [int(v) for v in b]
        except Exception:
            continue
    return None


def ocr_find(text, rect=None, confidence=0.1):
    """
    查找文字，返回 dict 或 None。
    1) 先试控件树（安卓优势，15ms 级）
    2) 再试 OCR 带 rect
    3) 兜底：OCR 全屏找 + 手动按坐标过滤（部分场景 rect 参数不生效）
    """
    try:
        node = Selector().text(text).find()
        if node:
            b = _node_bounds(node)
            if b:
                cx = (b[0] + b[2]) // 2
                cy = (b[1] + b[3]) // 2
                return {"text": text, "center_x": cx, "center_y": cy,
                        "confidence": 1.0, "source": "selector", "node": node}
    except Exception:
        pass

    if rect:
        try:
            r = Ocr.find(text, rect=rect, confidence=confidence)
            if r:
                return r
        except Exception:
            pass

    try:
        r = Ocr.find(text, confidence=confidence)
        if r:
            if rect:
                cx = r.get("center_x", 0)
                cy = r.get("center_y", 0)
                if rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]:
                    return r
            else:
                return r
    except Exception as e:
        log(f"  OCR 查找 '{text}' 异常: {e}")
    return None


def ocr_exists(text, rect=None, confidence=0.1):
    """判断文字是否存在"""
    return ocr_find(text, rect=rect, confidence=confidence) is not None


def init_regions():
    """初始化屏幕尺寸"""
    global SCREEN_W, SCREEN_H
    SCREEN_W, SCREEN_H = get_screen_size()
    log(f"屏幕尺寸: {SCREEN_W} x {SCREEN_H}")


# ============== 阶段一：启动 App ==============

def launch_app() -> bool:
    """启动汽水音乐 App（安卓用 system.open 传包名）"""
    log("=" * 50)
    log("阶段一：启动汽水音乐 App")
    try:
        system.open(APP_PACKAGE)
        log("App 启动指令已发送")
        time.sleep(2.5)
        fg = ""
        try:
            fg = str(system.get_foreground_app() or "")
        except Exception:
            pass
        if fg:
            log(f"当前前台应用: {fg}")
        return True
    except Exception as e:
        log(f"启动 App 异常: {e}")
        return False


def click_mian_button() -> bool:
    """
    点击右上角"免"字按钮。
    实测该按钮是图片（无 text/desc 属性），OCR 也识别不出，只能用坐标。
    位置按屏幕百分比动态计算，适配不同分辨率。
    """
    x = int(SCREEN_W * MIAN_X_RATIO)
    y = int(SCREEN_H * MIAN_Y_RATIO)
    log(f"点击'免'字按钮（比例坐标）-> ({x}, {y})")
    return safe_click(x, y, "免字按钮")


# ============== 阶段二：开屏广告 & 弹窗清理 ==============

SPLASH_SKIP_KEYWORDS = ["跳过广告", "跳过"]

POPUP_KEYWORDS = [
    "续费会员", "会员享专属", "开通会员", "立即开通",
    "看视频领取", "领取更多时长", "看视频得",
]

CLOSE_KEYWORDS = [
    "关闭", "取消", "以后再说", "稍后", "暂不", "跳过", "我知道了",
]


def skip_splash_ad(timeout=5) -> bool:
    """跳过开屏广告（右上角区域轮询）"""
    log("阶段二：检测并跳过开屏广告")
    rect_skip = [int(SCREEN_W * 0.60), 0, SCREEN_W, int(SCREEN_H * 0.20)]
    deadline = time.time() + timeout
    scan = 0
    while time.time() < deadline:
        scan += 1
        for kw in SPLASH_SKIP_KEYWORDS:
            r = ocr_find(kw, rect=rect_skip)
            if r:
                log(f"  [扫描#{scan}] 命中开屏跳过: '{r.get('text')}'")
                safe_click(r["center_x"], r["center_y"], "跳过开屏广告")
                return True
        time.sleep(0.3)
    log(f"  扫描结束（{scan} 次），未检测到开屏广告")
    return False


def dismiss_popups(max_rounds=3) -> int:
    """清理各类弹窗（会员续费 / 看视频领时长 等）"""
    log("阶段二B：清理弹窗")
    closed = 0
    for _ in range(max_rounds):
        hit = False
        for kw in POPUP_KEYWORDS:
            if ocr_exists(kw):
                log(f"  检测到弹窗关键词: '{kw}'")
                hit = True
                break
        if not hit:
            break
        clicked = False
        for ck in CLOSE_KEYWORDS:
            r = ocr_find(ck)
            if r:
                safe_click(r["center_x"], r["center_y"], f"关闭弹窗({ck})")
                clicked = True
                closed += 1
                time.sleep(1)
                break
        if not clicked:
            log("  未找到关闭按钮，尝试点击屏幕上方空白区")
            safe_click(SCREEN_W // 2, int(SCREEN_H * 0.08), "空白区")
            time.sleep(1)
    log(f"  弹窗清理完成，共处理 {closed} 个")
    return closed


# ============== 阶段三：等"免"字按钮 ==============

def wait_for_mian_button(timeout=60, allow_mian=True) -> bool:
    """
    等待首页出现可领取广告的入口。
    "免"字是图片按钮，OCR 识别不出，这里通过首页特征文字判断。
    只检测不点击 —— 交给用户手动点，避免误触。
    """
    log("阶段三：等待首页加载完成")
    deadline = time.time() + timeout
    while time.time() < deadline:
        # 首页特征：底部导航有"发现"、"音乐"，或顶部有"模式探索"
        if ocr_exists("模式探索") or ocr_exists("发现") or ocr_exists("音乐"):
            log("  首页已就绪 → 请手动点右上角'免'字进入广告")
            return True
        time.sleep(1.5)
    log(f"  等待超时（{timeout}s），未确认首页")
    return False


# ============== 阶段四：等待广告倒计时结束 ==============

COUNTDOWN_KEYWORDS = ["秒后可领取", "秒后领取", "秒后关闭", "秒后获得"]

# ---- 直播形式广告的坑（实测用户反馈）----
# 1) 广告播放中途弹"继续互动 / 退出"选择，5 秒倒计时后自动进直播间
#    → 必须点"退出"，点"继续互动"就进直播间了
# 2) 已进入直播间 → 直播间不算广告时长，必须退出来才能继续看广告

# 进直播间前的互动弹窗特征词
LIVE_PROMPT_HINTS = [
    "继续互动", "继续观看直播", "进入直播间", "秒后进入", "自动进入", "是否继续",
]
# 退出类按钮（按优先级尝试，绝不点含"继续/进入"的按钮）
LIVE_EXIT_BUTTONS = [
    "退出互动", "退出直播间", "退出", "不感兴趣", "取消", "关闭",
]
# 已在直播间内的特征词（只保留高特异性的，避免误判）
LIVE_ROOM_HINTS = [
    "更多直播", "说点什么", "在线观众", "直播间人数",
]


def scan_screen_texts():
    """
    一次全屏 OCR，返回 [(text, cx, cy), ...]。
    比反复调用 Ocr.find 快很多 —— 直播广告只有 5 秒反应窗口，必须省时间。

    注意：Ocr.find_all() 返回的是 dict 列表，而 Ocr.paddleocr() 返回的是 OcrText 对象，
    这里两种都兼容，避免踩坑。
    """
    try:
        items = Ocr.find_all()
        if not items:
            return []
        out = []
        for it in items:
            try:
                if isinstance(it, dict):
                    txt = it.get("text", "") or ""
                    cx = it.get("center_x", 0) or 0
                    cy = it.get("center_y", 0) or 0
                else:
                    txt = getattr(it, "text", "") or ""
                    cx = getattr(it, "center_x", 0) or 0
                    cy = getattr(it, "center_y", 0) or 0
                if txt:
                    out.append((str(txt), int(cx), int(cy)))
            except Exception:
                continue
        return out
    except Exception as e:
        log(f"  全屏 OCR 异常: {e}")
        return []


def handle_live_prompt(texts) -> bool:
    """
    处理"继续互动 / 退出"弹窗（进直播间之前的拦截点）。
    在已识别的文字里找退出按钮，绝不点含"继续/进入"的。
    返回 True 表示已点击退出。
    """
    for btn in LIVE_EXIT_BUTTONS:
        for t, x, y in texts:
            if btn in t and "继续" not in t and "进入" not in t:
                log(f"    ⚠️  直播互动弹窗 → 点击退出 '{t}' @ ({x}, {y})")
                safe_click(x, y, f"退出直播广告({btn})")
                time.sleep(1.5)
                return True
    # 找不到退出按钮 → 返回键兜底
    log("    未找到退出按钮，按返回键兜底")
    try:
        action.Key.back()
        time.sleep(1.2)
        return True
    except Exception as e:
        log(f"    返回键异常: {e}")
    return False


def handle_live_room(texts) -> bool:
    """
    处理已进入直播间的情况：直播间不算广告时长，必须退出。
    优先点右上角关闭按钮，兜底按返回键。
    """
    for kw in ["关闭", "退出", "×", "✕"]:
        for t, x, y in texts:
            if kw in t and y < SCREEN_H * 0.20:
                log(f"    ⚠️  已在直播间 → 点击右上角 '{t}' @ ({x}, {y})")
                safe_click(x, y, f"关闭直播间({kw})")
                time.sleep(1.5)
                return True
    log("    未找到关闭按钮，按返回键兜底")
    try:
        action.Key.back()
        time.sleep(1.5)
        return True
    except Exception as e:
        log(f"    返回键异常: {e}")
    return False


def check_and_click_continue_watching(texts=None) -> bool:
    """
    检测并点击屏幕中间的"继续观看"。
    注意：
      - 只点中间区域，绝不点底部的广告下载按钮
      - 排除"继续观看直播"这类（点了会进直播间）
    """
    if texts is None:
        texts = scan_screen_texts()
    for t, x, y in texts:
        if "继续观看" not in t:
            continue
        if "直播" in t or "互动" in t:
            log(f"  跳过 '{t}'（直播相关，点了会进直播间）")
            continue
        if not (SCREEN_H * 0.25 <= y <= SCREEN_H * 0.68):
            continue
        log(f"  命中中间区'继续观看' → 点击恢复广告")
        if safe_click(x, y, "继续观看(中间区)"):
            time.sleep(2.5)
            return True
    return False


def wait_ad_countdown(timeout=30) -> bool:
    """
    等待广告倒计时结束，右上角出现"领取成功"。
    每轮只做一次全屏 OCR，本地按优先级匹配：
      1. "领取成功" → 成功
      2. 直播互动弹窗 → 选退出（否则 5 秒后自动进直播间）
      3. 已在直播间 → 退出（直播间不算广告时长）
      4. 倒计时文案 → 仅日志
      5. 中间"继续观看" → 点击恢复
    """
    log("阶段四：等待广告倒计时结束")
    deadline = time.time() + timeout
    checks = 0
    last_sec = -1

    while time.time() < deadline:
        checks += 1
        texts = scan_screen_texts()
        if not texts:
            time.sleep(0.5)
            continue
        joined = " | ".join(t for t, _, _ in texts)

        # 1) 最高优先：领取成功
        if "领取成功" in joined:
            log(f"  检测到'领取成功'（轮询 {checks} 次）")
            return True

        # 2) 直播互动弹窗（进直播间前拦截）
        if any(kw in joined for kw in LIVE_PROMPT_HINTS):
            log(f"  ⚠️  识别到直播互动弹窗（轮询 {checks} 次）")
            if handle_live_prompt(texts):
                continue

        # 3) 已在直播间
        if any(kw in joined for kw in LIVE_ROOM_HINTS):
            log(f"  ⚠️  识别到直播间界面（轮询 {checks} 次）")
            if handle_live_room(texts):
                continue

        # 4) 倒计时文案（仅日志）
        for t, x, y in texts:
            if "秒后" in t and y < SCREEN_H * 0.12:
                sec = None
                for ch in t:
                    if ch.isdigit():
                        sec = int(ch)
                        break
                if sec is not None and sec != last_sec:
                    log(f"  广告倒计时中... {t}")
                    last_sec = sec
                break

        # 5) 广告中途被关，尝试恢复
        check_and_click_continue_watching(texts)
        time.sleep(0.6)

    log(f"  等待超时（{timeout}s），'领取成功'未出现")
    return False


# ============== 阶段五：领取奖励 ==============

def claim_reward() -> int:
    """
    两步领取（实测汽水音乐安卓版流程）：
      步骤1：点右上角「领取成功」
      步骤2：弹窗出现「再看1个视频得 今日免费听」→ 点「领取奖励」→ 自动进下一轮广告
    返回 1=成功，0=失败
    """
    log("阶段五：领取奖励")

    # 步骤1：点右上角「领取成功」
    ok1 = False
    r = ocr_find("领取成功")
    if r and r.get("center_y", 0) < SCREEN_H * 0.25:
        if safe_click(r["center_x"], r["center_y"], "步骤1-领取成功"):
            ok1 = True
    if not ok1:
        log("  步骤1失败：未找到'领取成功'")
        return 0

    time.sleep(1.8)

    # 步骤2：点弹窗「领取奖励」
    for kw in ["领取奖励", "立即领取", "开心收下"]:
        r = ocr_find(kw)
        if r:
            if safe_click(r["center_x"], r["center_y"], f"步骤2-{kw}"):
                log("  ✅ 两步领取完成，自动进入下一轮")
                return 1

    log("  步骤2未命中'领取奖励'（可能已自动到账）")
    return 1


# ============== 主流程 ==============

def run_ad_loop() -> int:
    """
    核心循环：你手动进广告后，脚本负责
      等倒计时 → 点领取成功 → 点领取奖励 → 下一轮 → 循环
    """
    log("\n" + "#" * 60)
    log("🎯 进入核心广告领取循环")
    log("#" * 60)
    log("   ⚠️  请在手机上手动点一次右上角'免'字，脚本会自动接管后续所有轮次")
    success_count = 0
    round_idx = 0
    idle_count = 0

    while round_idx < MAX_LOOP_COUNT:
        round_idx += 1
        log(f"\n---- 第 {round_idx} 轮 ----")
        ensure_awake()

        # 第一轮给用户更长时间去点"免"字
        wait_sec = 60 if round_idx == 1 else 30
        got_ad = wait_ad_countdown(timeout=wait_sec)
        if not got_ad:
            idle_count += 1
            log(f"  本轮未检测到广告结束（连续 {idle_count}/{MAX_IDLE_ROUNDS}）")
            if idle_count >= MAX_IDLE_ROUNDS:
                log(f"  ⚠️  连续 {MAX_IDLE_ROUNDS} 轮无广告，可能当日额度已用完，退出")
                break
            # 前几轮失败：重新点"免"字再试
            if AUTO_CLICK_MIAN and idle_count <= 3:
                log("  尝试重新点'免'字进入广告")
                click_mian_button()
            # 连续失败较多：重启 App 清状态
            elif AUTO_RESTART_APP and idle_count % 3 == 0:
                log("  尝试重启 App 恢复状态")
                try:
                    system.open(APP_PACKAGE)
                    time.sleep(4)
                    ensure_home_page()
                except Exception as e:
                    log(f"  重启异常: {e}")
            time.sleep(3)
            continue

        res = claim_reward()
        if res == 1:
            success_count += 1
            idle_count = 0
            log(f"  ✅ 第 {round_idx} 轮成功，累计 {success_count} 次")
        else:
            idle_count += 1
            log(f"  ⚠️  第 {round_idx} 轮失败（连续 {idle_count}/{MAX_IDLE_ROUNDS}）")
            if idle_count >= MAX_IDLE_ROUNDS:
                log(f"  ⚠️  连续 {MAX_IDLE_ROUNDS} 轮失败，退出")
                break

        time.sleep(LOOP_INTERVAL)

    return success_count


def ensure_home_page(max_rounds=3) -> bool:
    """确保停在汽水音乐首页，不在就按返回键退出弹窗/广告页"""
    for i in range(max_rounds):
        if ocr_exists("模式探索") or ocr_exists("发现") or ocr_exists("音乐"):
            log("  已在首页")
            return True
        log(f"  未在首页，按返回键（{i + 1}/{max_rounds}）")
        try:
            action.Key.back()
        except Exception as e:
            log(f"  返回键异常: {e}")
            break
        time.sleep(1.5)
    return ocr_exists("模式探索") or ocr_exists("发现")


def setup_unattended():
    """无人值守设置：屏幕常亮 + 唤醒"""
    if not KEEP_SCREEN_ON:
        return
    try:
        Device.keep_screen_on()
        log("已开启屏幕常亮（防止息屏中断）")
    except Exception as e:
        log(f"屏幕常亮设置失败: {e}")
    try:
        Device.wake_up()
    except Exception:
        pass


def ensure_awake():
    """每轮开始前确保屏幕亮着"""
    try:
        Device.wake_up()
    except Exception:
        pass


def main():
    """脚本入口"""
    log("🎵 汽水音乐自动看广告脚本（安卓版）启动")
    log(f"   包名: {APP_PACKAGE} | OCR引擎: {OCR_ENGINE} | 自动点免字: {AUTO_CLICK_MIAN}")
    try:
        init_regions()
        try:
            Ocr.set_engine(OCR_ENGINE)
            log(f"OCR 引擎已设置为 {OCR_ENGINE}")
        except Exception as e:
            log(f"设置 OCR 引擎失败（用默认）: {e}")

        setup_unattended()

        if not launch_app():
            log("❌ 无法启动汽水音乐，脚本终止")
            return

        skip_splash_ad(timeout=6)
        dismiss_popups(max_rounds=3)

        if not ensure_home_page():
            log("  未能回到首页，重新启动 App 再试")
            try:
                system.open(APP_PACKAGE)
                time.sleep(4)
            except Exception as e:
                log(f"  重启异常: {e}")

        if AUTO_CLICK_MIAN:
            log("\n自动模式：脚本将自动点'免'字进入广告")
            click_mian_button()
            time.sleep(3.5)
        else:
            log("\n" + "=" * 50)
            log("✅ 准备工作完成，现在请你操作手机：")
            log("   1. 确保汽水音乐停在首页")
            log("   2. 手动点右上角'免'字（搜索框右边那个）")
            log("   3. 进入广告后不用管，脚本自动接管")
            log("=" * 50)

        total = run_ad_loop()

        log("=" * 60)
        log(f"✅ 脚本结束，共成功领取 {total} 次")

    except Exception as e:
        log(f"❌ 脚本异常: {e}")
        traceback.print_exc()
    finally:
        log("脚本退出")


# ============== 入口：AScript 工程约定顶层直接执行 ==============
main()
