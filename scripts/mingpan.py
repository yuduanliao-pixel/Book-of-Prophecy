#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill 工具：八字＋紫微斗數排盤，輸出結構化命盤（JSON）供 LLM 合參。

由 SKILL.md 的「命盤合參」流程呼叫。僅標準庫，任何 python3 皆可執行；
排盤為確定性引擎，格局、喜忌與吉凶判斷交給 LLM。
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import mingpan, render_mingpan  # noqa: E402
from engine.ganzhi import DAY_BOUNDARY_POLICIES  # noqa: E402


def _parse_birth(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y%m%d %H:%M"):
        try:
            t = datetime.datetime.strptime(s.strip(), fmt)
            return (t.year, t.month, t.day, t.hour, t.minute)
        except ValueError:
            continue
    raise SystemExit("出生時間格式須為 YYYY-MM-DD HH:MM（西曆、出生地民用時）")


def _parse_years(s):
    """接受 2027、2026-2029、2026,2028 或其組合。"""
    years = set()
    for part in s.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, b = (int(x) for x in part.split("-", 1))
                if b < a or b - a > 120:
                    raise ValueError
                years.update(range(a, b + 1))
            else:
                years.add(int(part))
        except ValueError:
            raise SystemExit(f"流年格式錯誤：{part}（例：2027 或 2026-2029）")
    return sorted(years)


def main():
    p = argparse.ArgumentParser(description="八字／紫微斗數排盤（輸出 JSON 供合參）")
    p.add_argument("-b", "--birth", required=True, help="出生時間 YYYY-MM-DD HH:MM（西曆）")
    p.add_argument("-g", "--gender", required=True, help="性別：男/女（或 m/f）")
    p.add_argument("-s", "--system", choices=["bazi", "ziwei", "both"], default="both")
    p.add_argument("-y", "--years", help="要列出的流年，如 2026-2029（預設今年起三年）")
    p.add_argument("--tz", type=float, default=8.0, help="出生地時區（UTC 偏移，預設 8）")
    p.add_argument("--boundary", default="zi_initial_23", choices=list(DAY_BOUNDARY_POLICIES),
                   help="晚子時（23 時）換日策略")
    p.add_argument("--no-fix-leap", action="store_true",
                   help="紫微：閏月一律歸本月（預設十六日起歸下月）")
    p.add_argument("-f", "--format", choices=["json", "text", "both"], default="json")
    args = p.parse_args()

    when = _parse_birth(args.birth)
    if args.years:
        years = _parse_years(args.years)
    else:
        this_year = datetime.date.today().year
        years = [this_year, this_year + 1, this_year + 2]
    systems = mingpan.SYSTEMS if args.system == "both" else (args.system,)
    try:
        mp = mingpan.build_mingpan(when, args.gender, systems=systems, years=years,
                                   tz_hours=args.tz, day_boundary=args.boundary,
                                   fix_leap=not args.no_fix_leap)
    except ValueError as e:
        raise SystemExit(f"排盤失敗：{e}")

    if args.format in ("text", "both"):
        print(render_mingpan.render_mingpan_text(mp))
        if args.format == "both":
            print("\n----- JSON -----")
    if args.format in ("json", "both"):
        print(json.dumps(mp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
