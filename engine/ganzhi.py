"""四柱干支換算：年（立春換）、月（節氣換）、日（錨點 2000-01-07=甲子）、時。
另含月令五行、旬空、旺相休囚死、地支生剋沖合判定。純標準庫，離線。
"""
from __future__ import annotations

import datetime as _dt

from . import constants as C
from . import solar_terms as st

# 日柱錨點：2000-01-07 = 甲子（干支序 0）。等價：2000-01-01 = 戊午(54)。
_DAY_ANCHOR = _dt.date(2000, 1, 7)

DAY_BOUNDARY_POLICIES = ("zi_initial_23", "midnight_00", "split_zi")


def _five_tiger_month_gan_base(year_gan_index: int) -> int:
    """五虎遁：年干 → 寅月之月干 index。"""
    return ((year_gan_index % 5) * 2 + 2) % 10


def _five_rat_hour_gan_base(day_gan_index: int) -> int:
    """五鼠遁：日干 → 子時之時干 index。"""
    return ((day_gan_index % 5) * 2) % 10


def wangshuai(yao_wuxing: str, month_wuxing: str) -> str:
    """爻五行對月令五行之旺相休囚死。"""
    if yao_wuxing == month_wuxing:
        return "旺"
    if C.WUXING_SHENG[month_wuxing] == yao_wuxing:
        return "相"   # 月令生爻
    if C.WUXING_SHENG[yao_wuxing] == month_wuxing:
        return "休"   # 爻生月令
    if C.WUXING_KE[yao_wuxing] == month_wuxing:
        return "囚"   # 爻剋月令
    return "死"        # 月令剋爻


def branch_relation(a: str, b: str) -> str:
    """地支 a 對 b 的關係（沖/合/同/無），供日辰、月破等判定。"""
    if a == b:
        return "同"
    if C.LIUCHONG.get(a) == b:
        return "沖"
    if C.LIUHE.get(a) == b:
        return "合"
    return ""


def compute_sizhu(year, month, day, hour=12, minute=0,
                  tz_hours: float = 8.0, day_boundary: str = "zi_initial_23"):
    """回傳四柱與相關資訊的 dict。

    參數為「地方民用時」。day_boundary 見 DAY_BOUNDARY_POLICIES。
    """
    if day_boundary not in DAY_BOUNDARY_POLICIES:
        raise ValueError(f"未知換日策略：{day_boundary}")

    civil_date = _dt.date(year, month, day)
    night_zi = False  # 夜子時旗標

    # ── 日柱（含換日策略）──
    day_offset_date = civil_date
    if hour >= 23:
        if day_boundary == "zi_initial_23":
            day_offset_date = civil_date + _dt.timedelta(days=1)
        elif day_boundary == "split_zi":
            night_zi = True  # 日柱不變，但標夜子時
        # midnight_00：23 點仍屬當日，日柱不變
    day_index = (day_offset_date - _DAY_ANCHOR).days % 60
    day_gan_i = day_index % 10
    day_zhi_i = day_index % 12

    # ── 起卦地方時對應 JD（供節氣判定）──
    local_jd = st.jd_from_gregorian(year, month, day + (hour * 60 + minute) / 1440.0)

    # ── 年柱（立春換年）──
    lichun_jd = st.term_local_jd(year, "立春", tz_hours)
    year_for_pillar = year if local_jd >= lichun_jd else year - 1
    year_index = (year_for_pillar - 4) % 60
    year_gan_i = year_index % 10
    year_zhi_i = year_index % 12

    # ── 月柱（節氣換月，五虎遁取月干）──
    month_branch_i = st.month_branch_for(local_jd, year, tz_hours)
    offset_from_yin = (month_branch_i - 2) % 12
    month_gan_i = (_five_tiger_month_gan_base(year_gan_i) + offset_from_yin) % 10

    # ── 時柱（五鼠遁）──
    # 23 時的子時屬次日之始：時干一律以「次日」日干起。
    # zi_initial_23 的日柱已進到次日；midnight_00／split_zi 日柱留在當日，
    # 故此處另取次日日干（如甲日 23:30 為丙子時，與次日 00:30 同柱）。
    hour_branch_i = ((hour + 1) // 2) % 12
    hour_day_gan_i = day_gan_i
    if hour >= 23 and day_boundary != "zi_initial_23":
        hour_day_gan_i = (day_gan_i + 1) % 10
    base_hour_gan = _five_rat_hour_gan_base(hour_day_gan_i)
    hour_gan_i = (base_hour_gan + hour_branch_i) % 10

    # ── 月令、旬空、節氣資訊 ──
    month_zhi = C.DIZHI[month_branch_i]
    month_wuxing = C.DIZHI_WUXING[month_zhi]
    kong1, kong2 = C.xunkong(day_index)
    term_name, term_jd, days_in = st.current_solar_term(local_jd, year, tz_hours)

    return {
        "input": {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute,
            "tz_hours": tz_hours, "day_boundary": day_boundary,
        },
        "year_pillar": C.ganzhi_name(year_index),
        "month_pillar": C.TIANGAN[month_gan_i] + month_zhi,
        "day_pillar": C.ganzhi_name(day_index),
        "hour_pillar": C.TIANGAN[hour_gan_i] + C.DIZHI[hour_branch_i],
        "day_gan": C.TIANGAN[day_gan_i],
        "day_zhi": C.DIZHI[day_zhi_i],
        "month_branch": month_zhi,
        "month_wuxing": month_wuxing,
        "day_index": day_index,
        "xunkong": (kong1, kong2),
        "solar_term": term_name,
        "solar_term_days_in": days_in,
        "night_zi": night_zi,
    }
