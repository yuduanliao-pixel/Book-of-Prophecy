#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill 工具：起卦＋裝卦，輸出結構化排盤（JSON）供 LLM 斷卦。

由 SKILL.md 的流程呼叫。預設取系統時間、以 CSPRNG 自動擲幣。
僅標準庫，任何 python3 皆可執行；隨機與查表為確定性引擎，斷卦交給 LLM。
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import cast, divination as dv, render  # noqa: E402
from engine.ganzhi import DAY_BOUNDARY_POLICIES  # noqa: E402


def _now():
    t = datetime.datetime.now()
    return (t.year, t.month, t.day, t.hour, t.minute)


def _parse_time(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            t = datetime.datetime.strptime(s.strip(), fmt)
            return (t.year, t.month, t.day, t.hour, t.minute)
        except ValueError:
            continue
    raise SystemExit("時間格式須為 YYYY-MM-DD HH:MM")


def main():
    p = argparse.ArgumentParser(description="京房六爻起卦裝卦（輸出 JSON 供斷卦）")
    p.add_argument("-q", "--question", required=True, help="精煉後的占問")
    p.add_argument("-c", "--category",
                   help="占問類別（決定用神）。完整字串或簡寫 財/官/父/子/兄/世")
    p.add_argument("-t", "--time", help="指定時間 YYYY-MM-DD HH:MM（預設系統時間）")
    p.add_argument("-b", "--boundary", default="zi_initial_23",
                   choices=list(DAY_BOUNDARY_POLICIES))
    p.add_argument("-m", "--manual",
                   help="手動錢面 6 組以 ; 分隔（由下而上），每組三枚如 背字字")
    p.add_argument("-f", "--format", choices=["json", "text", "both"], default="json")
    args = p.parse_args()

    when = _parse_time(args.time) if args.time else _now()
    if args.manual:
        try:
            rounds = cast.parse_manual_spec(args.manual)
        except ValueError as e:
            raise SystemExit(f"錢面輸入錯誤：{e}")
    else:
        rounds = cast.cast_hexagram()

    category = dv.resolve_category(args.category)
    if args.category and category is None:
        raise SystemExit("未知類別：可用 財/官/父/子/兄/世 或完整類別字串")
    chart = dv.build_chart(args.question, when, rounds,
                           day_boundary=args.boundary, category=category)

    if args.format in ("text", "both"):
        print(render.render_text(chart))
        if args.format == "both":
            print("\n----- JSON -----")
    if args.format in ("json", "both"):
        print(json.dumps(chart, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
