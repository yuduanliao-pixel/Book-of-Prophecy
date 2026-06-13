#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""京房納甲六爻 — 離線排盤執行檔（進入點）。

功能：互動輸入占問、自動系統時間起卦、可手動指定時間、可手動輸入銅錢結果。
僅做「起卦＋裝卦＋排盤顯示」，不含問題精煉、斷卦與結論。
亦支援命令列參數供進階/自動化使用。
"""
import argparse
import datetime
import json
import os
import sys

# ── 讓 engine 套件可被匯入（原始碼執行 / PyInstaller 凍結皆可）──
if getattr(sys, "frozen", False):
    _BASE = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from engine import cast, divination as dv, render  # noqa: E402
from engine.ganzhi import DAY_BOUNDARY_POLICIES  # noqa: E402


def _setup_console():
    """Windows 主控台改用 UTF-8，避免中文亂碼。"""
    try:
        if os.name == "nt":
            os.system("")  # 啟用 ANSI
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            sys.stdin.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
    except Exception:
        pass


CATEGORIES = list(dv.CATEGORY_TO_YONGSHEN.keys())


def _parse_time(s: str):
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            t = datetime.datetime.strptime(s, fmt)
            return (t.year, t.month, t.day, t.hour, t.minute)
        except ValueError:
            continue
    raise ValueError("時間格式須為 YYYY-MM-DD HH:MM")


def _now_tuple():
    t = datetime.datetime.now()
    return (t.year, t.month, t.day, t.hour, t.minute)


# ───────────────────────── 互動模式 ─────────────────────────
def _ask(prompt, default=None):
    suffix = f"（預設 {default}）" if default is not None else ""
    val = input(f"{prompt}{suffix}：").strip()
    return val if val else (default if default is not None else "")


def _ask_choice(prompt, options, default_idx=0):
    print(prompt)
    for i, o in enumerate(options, 1):
        mark = "（預設）" if i - 1 == default_idx else ""
        print(f"  {i}. {o}{mark}")
    raw = input("請輸入編號：").strip()
    if not raw:
        return default_idx
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    print("  輸入無效，採用預設。")
    return default_idx


def _ask_manual_coins():
    print("\n手動輸入擲幣結果（由下而上，初爻→上爻）。")
    print("每爻輸入三枚錢面，可用：背/字、b/z、3/2、陽/陰，連寫或空白分隔（例：背 字 字 或 背字字）。")
    rounds = []
    names = ["初", "二", "三", "四", "五", "上"]
    i = 0
    while i < 6:
        raw = input(f"  {names[i]}爻：")
        try:
            rounds.append(cast.make_line(cast.parse_faces(raw)))
            i += 1
        except ValueError as e:
            print(f"    {e}")
    return rounds


def interactive(args):
    print("═" * 60)
    print("　京房納甲六爻　離線排盤工具")
    print("═" * 60)
    question = _ask("請輸入占問", default="（未填）")

    # 時間
    mode = _ask_choice("\n起卦時間：", ["使用目前系統時間", "手動指定時間"], 0)
    if mode == 1:
        while True:
            try:
                when = _parse_time(_ask("輸入時間 YYYY-MM-DD HH:MM"))
                break
            except ValueError as e:
                print(f"  {e}")
    else:
        when = _now_tuple()

    # 換日策略
    bidx = _ask_choice("\n換日策略：",
                       ["子初換日(23時起算次日)", "子正換日(00時)", "夜子時分日"], 0)
    boundary = DAY_BOUNDARY_POLICIES[bidx]

    # 起卦方式
    cmode = _ask_choice("\n起卦方式：", ["程式自動擲幣（密碼學亂數）", "手動輸入銅錢結果"], 0)
    rounds = _ask_manual_coins() if cmode == 1 else cast.cast_hexagram()

    # 占問類別（用神標示，可略）
    cidx = _ask_choice("\n占問類別（用於標示用神候選，可選 0 略過）：",
                       ["（略過）"] + CATEGORIES, 0)
    category = CATEGORIES[cidx - 1] if cidx >= 1 else None

    chart = dv.build_chart(question, when, rounds, day_boundary=boundary, category=category)
    print("\n" + render.render_text(chart))
    _maybe_export_interactive(chart)


def _maybe_export_interactive(chart):
    ans = input("\n是否匯出排盤？(t=純文字 / j=JSON / 直接 Enter 略過)：").strip().lower()
    if ans in ("t", "j"):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if ans == "t":
            path = f"paipan_{stamp}.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(render.render_text(chart))
        else:
            path = f"paipan_{stamp}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(chart, f, ensure_ascii=False, indent=2)
        print(f"已匯出：{os.path.abspath(path)}")
    try:
        input("\n按 Enter 結束…")
    except EOFError:
        pass


# ───────────────────────── 命令列模式 ─────────────────────────
def cli(args):
    try:
        when = _parse_time(args.time) if args.time else _now_tuple()
    except ValueError as e:
        raise SystemExit(f"時間格式錯誤：{e}")
    if args.manual:
        try:
            rounds = cast.parse_manual_spec(args.manual)
        except ValueError as e:
            raise SystemExit(f"錢面輸入錯誤：{e}")
    else:
        rounds = cast.cast_hexagram()
    category = dv.resolve_category(args.category)
    if args.category and category is None:
        raise SystemExit(
            "未知類別：可用 財/官/父/子/兄/世（或完整類別字串，見 --help）")
    chart = dv.build_chart(args.question or "（未填）", when, rounds,
                           day_boundary=args.boundary, category=category)
    if args.export == "json":
        print(json.dumps(chart, ensure_ascii=False, indent=2))
    else:
        print(render.render_text(chart))


def main():
    _setup_console()
    p = argparse.ArgumentParser(
        description="京房納甲六爻 離線排盤（不含斷卦）")
    p.add_argument("-q", "--question", help="占問內容")
    p.add_argument("-t", "--time", help="指定時間 YYYY-MM-DD HH:MM（預設系統時間）")
    p.add_argument("-m", "--manual",
                   help="手動錢面，6 組以 ; 分隔（由下而上），每組三枚如 背字字；例："
                        "'背背字;背背背;背字字;背字字;背字字;背字字'")
    p.add_argument("-c", "--category",
                   help="占問類別（標示用神候選）。簡寫：財/官/父/子/兄/世，"
                        "或完整字串如 財運/求財/投資/生意")
    p.add_argument("-b", "--boundary", default="zi_initial_23",
                   choices=list(DAY_BOUNDARY_POLICIES), help="換日策略")
    p.add_argument("-e", "--export", choices=["text", "json"], default="text",
                   help="輸出格式（命令列模式）")
    p.add_argument("--no-interactive", action="store_true",
                   help="不進入互動選單，直接依參數輸出")
    args = p.parse_args()

    # 有參數 → 命令列模式；無參數且為互動終端 → 互動選單；
    # 無參數且非互動終端（被管線/重導向）→ 直接命令列（自動起卦），避免卡在等待輸入。
    has_args = bool(args.no_interactive or args.question or args.manual or args.time)
    is_tty = sys.stdin.isatty()
    if has_args or not is_tty:
        cli(args)
    else:
        try:
            interactive(args)
        except (KeyboardInterrupt, EOFError):
            print("\n已取消。")


if __name__ == "__main__":
    main()
