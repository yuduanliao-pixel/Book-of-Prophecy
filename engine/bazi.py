"""八字（四柱）排盤：四柱、十神、藏干、十二長生、納音、大運、流年。

只產生可驗證的排盤事實，不含喜忌、格局與吉凶判斷（交由斷盤者／LLM）。
四柱沿用 ganzhi.compute_sizhu：年以立春換、月以節換、日柱錨點 2000-01-07=甲子。
純標準庫，離線。
"""
from __future__ import annotations

import calendar as _cal
import datetime as _dt

from . import constants as C
from . import ganzhi as gz
from . import solar_terms as st

CHANGSHENG = ["長生", "沐浴", "冠帶", "臨官", "帝旺", "衰", "病", "死", "墓", "絕", "胎", "養"]
# 各天干「長生」所在地支；陽干順行、陰干逆行
_CHANGSHENG_START = {
    "甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
    "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯",
}
PILLAR_KEYS = ("year", "month", "day", "hour")
PILLAR_NAMES = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "時柱"}
DAYUN_COUNT = 8  # 排 8 步大運（80 年）


def shishen(day_gan: str, other_gan: str) -> str:
    """以日干為「我」，定另一天干的十神。"""
    me, other = C.TIANGAN_WUXING[day_gan], C.TIANGAN_WUXING[other_gan]
    same = C.gan_is_yang(day_gan) == C.gan_is_yang(other_gan)
    if other == me:
        return "比肩" if same else "劫財"
    if C.WUXING_SHENG[me] == other:      # 我生者
        return "食神" if same else "傷官"
    if C.WUXING_KE[me] == other:         # 我剋者
        return "偏財" if same else "正財"
    if C.WUXING_KE[other] == me:         # 剋我者
        return "七殺" if same else "正官"
    return "偏印" if same else "正印"    # 生我者


def dishi(gan: str, zhi: str) -> str:
    """天干在某地支的十二長生狀態。"""
    start = C.DIZHI.index(_CHANGSHENG_START[gan])
    z = C.DIZHI.index(zhi)
    offset = (z - start) % 12 if C.gan_is_yang(gan) else (start - z) % 12
    return CHANGSHENG[offset]


def _pillar(ganzhi: str, day_gan: str, is_day: bool = False) -> dict:
    gan, zhi = ganzhi[0], ganzhi[1]
    return {
        "ganzhi": ganzhi, "gan": gan, "zhi": zhi,
        "gan_wuxing": C.TIANGAN_WUXING[gan], "zhi_wuxing": C.DIZHI_WUXING[zhi],
        "shishen": "日主" if is_day else shishen(day_gan, gan),
        "canggan": [{"gan": g, "shishen": shishen(day_gan, g)} for g in C.CANGGAN[zhi]],
        "dishi": dishi(day_gan, zhi),
        "nayin": C.nayin(ganzhi),
    }


def _jie_points(year: int, tz_hours: float):
    """year-1 … year+1 三年內全部「節」的地方時 JD（遞增）。"""
    pts = []
    for y in (year - 1, year, year + 1):
        for name in st.JIE_TO_BRANCH:
            pts.append((st.term_local_jd(y, name, tz_hours), name))
    pts.sort()
    return pts


def _add_ymdh(dt: _dt.datetime, years: int, months: int, days: int, hours: int) -> _dt.datetime:
    total = dt.month - 1 + months
    y = dt.year + years + total // 12
    m = total % 12 + 1
    d = min(dt.day, _cal.monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=d) + _dt.timedelta(days=days, hours=hours)


def branch_relations(branch: str, others: dict) -> list:
    """地支 branch 與 others（{標籤: 地支}）的沖、合關係，回傳描述字串清單。"""
    out = []
    for label, z in others.items():
        if C.LIUCHONG.get(branch) == z:
            out.append(f"{branch}{z}沖（{label}）")
        elif C.LIUHE.get(branch) == z:
            out.append(f"{branch}{z}合（{label}）")
    return out


def combos(branches) -> list:
    """一組地支中成立的三合局、三會方。"""
    present = set(branches)
    out = []
    for group, wx in C.SANHE.items():
        if group <= present:
            out.append("".join(sorted(group, key=C.DIZHI.index)) + f"三合{wx}局")
    for group, wx in C.SANHUI.items():
        if group <= present:
            out.append("".join(sorted(group, key=C.DIZHI.index)) + f"三會{wx}方")
    return out


def normalize_gender(gender: str) -> str:
    g = str(gender).strip().lower()
    if g in ("男", "m", "male", "乾", "1"):
        return "男"
    if g in ("女", "f", "female", "坤", "0"):
        return "女"
    raise ValueError(f"性別須為 男/女：{gender}")


def build_bazi(year, month, day, hour, minute, gender, tz_hours: float = 8.0,
               day_boundary: str = "zi_initial_23", liunian_years=None) -> dict:
    """排八字。參數為出生地方民用時；gender 為 男/女。

    liunian_years：要列出的流年（西元年，以立春起算之干支年）清單，可 None。
    """
    gender = normalize_gender(gender)
    sz = gz.compute_sizhu(year, month, day, hour, minute, tz_hours=tz_hours,
                          day_boundary=day_boundary)
    day_gan = sz["day_gan"]
    gz_of = {"year": sz["year_pillar"], "month": sz["month_pillar"],
             "day": sz["day_pillar"], "hour": sz["hour_pillar"]}
    pillars = {k: _pillar(gz_of[k], day_gan, is_day=(k == "day")) for k in PILLAR_KEYS}
    natal_branches = {PILLAR_NAMES[k][0] + "支": pillars[k]["zhi"] for k in PILLAR_KEYS}

    # 五行統計：四干＋四支本氣
    wuxing_count = {wx: 0 for wx in "木火土金水"}
    for k in PILLAR_KEYS:
        wuxing_count[pillars[k]["gan_wuxing"]] += 1
        wuxing_count[pillars[k]["zhi_wuxing"]] += 1

    # 年柱所屬西元年（立春換年）
    pillar_year = year
    while C.ganzhi_name((pillar_year - 4) % 60) != sz["year_pillar"]:
        pillar_year -= 1

    # ── 大運：陽年男、陰年女順行，反之逆行；距節 3 日折 1 年 ──
    forward = C.gan_is_yang(sz["year_pillar"][0]) == (gender == "男")
    birth_jd = st.jd_from_gregorian(year, month, day + (hour * 60 + minute) / 1440.0)
    pts = _jie_points(year, tz_hours)
    prev_jie = max(p for p in pts if p[0] <= birth_jd)
    next_jie = min(p for p in pts if p[0] > birth_jd)
    span_days = (next_jie[0] - birth_jd) if forward else (birth_jd - prev_jie[0])
    minutes = int(round(span_days * 1440))
    s_years, rem = divmod(minutes, 4320)     # 3 日 = 1 年
    s_months, rem = divmod(rem, 360)         # 6 時 = 1 月
    s_days, rem = divmod(rem, 12)            # 12 分 = 1 日
    s_hours = rem * 2
    start_dt = _add_ymdh(_dt.datetime(year, month, day, hour, minute),
                         s_years, s_months, s_days, s_hours)

    month_index = C.ganzhi_index(sz["month_pillar"])
    dayun = []
    for i in range(1, DAYUN_COUNT + 1):
        gzname = C.ganzhi_name(month_index + (i if forward else -i))
        start_year = start_dt.year + (i - 1) * 10
        dayun.append({
            "index": i, "ganzhi": gzname,
            "shishen_gan": shishen(day_gan, gzname[0]),
            "shishen_zhi": shishen(day_gan, C.CANGGAN[gzname[1]][0]),
            "start_year": start_year, "end_year": start_year + 9,
            "start_age": start_year - pillar_year + 1,
            "end_age": start_year - pillar_year + 10,
            "relations": branch_relations(gzname[1], natal_branches),
            "combos": combos(list(natal_branches.values()) + [gzname[1]]),
        })

    # ── 流年 ──
    liunian = []
    for ly in (liunian_years or []):
        gzname = C.ganzhi_name((ly - 4) % 60)
        current = None
        for du in dayun:
            if du["start_year"] <= ly <= du["end_year"]:
                current = du
        others = dict(natal_branches)
        branches = list(natal_branches.values()) + [gzname[1]]
        if current:
            others["大運支"] = current["ganzhi"][1]
            branches.append(current["ganzhi"][1])
        liunian.append({
            "year": ly, "ganzhi": gzname, "age": ly - pillar_year + 1,
            "shishen_gan": shishen(day_gan, gzname[0]),
            "shishen_zhi": shishen(day_gan, C.CANGGAN[gzname[1]][0]),
            "dayun": current["ganzhi"] if current else None,
            "relations": branch_relations(gzname[1], others),
            "combos": combos(branches),
        })

    return {
        "system": "bazi",
        "input": {"year": year, "month": month, "day": day, "hour": hour, "minute": minute,
                  "gender": gender, "tz_hours": tz_hours, "day_boundary": day_boundary},
        "pillars": pillars,
        "day_master": {"gan": day_gan, "wuxing": C.TIANGAN_WUXING[day_gan],
                       "yinyang": "陽" if C.gan_is_yang(day_gan) else "陰"},
        "pillar_year": pillar_year,
        "month_branch": sz["month_branch"],
        "solar_term": sz["solar_term"], "solar_term_days_in": sz["solar_term_days_in"],
        "xunkong": list(sz["xunkong"]),
        "night_zi": sz["night_zi"],
        "wuxing_count": wuxing_count,
        "natal_combos": combos(natal_branches.values()),
        "dayun": {
            "forward": forward,
            "from_jie": (next_jie if forward else prev_jie)[1],
            "start_offset": {"years": s_years, "months": s_months, "days": s_days, "hours": s_hours},
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "list": dayun,
        },
        "liunian": liunian,
    }
