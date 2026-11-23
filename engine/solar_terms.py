"""二十四節氣天文計算（離線、純標準庫）。

採用 Jean Meeus《Astronomical Algorithms》之太陽視黃經低精度公式，
配合 ΔT（Espenak–Meeus）與時區換算，求解太陽視黃經等於 15° 倍數之時刻。
精度約 ±1–2 分鐘，足供起卦定月令、定年（立春換年）之用。
涵蓋約 1900–2100；CSV 權威值可於外層覆蓋（見 ganzhi 載入）。
"""
from __future__ import annotations

import csv
import math
import os
import sys

# 24 節氣：名稱 → 太陽視黃經（度）。每 15° 一節氣，春分 = 0°。
SOLAR_LONGITUDE = {
    "春分": 0, "清明": 15, "穀雨": 30, "立夏": 45, "小滿": 60, "芒種": 75,
    "夏至": 90, "小暑": 105, "大暑": 120, "立秋": 135, "處暑": 150, "白露": 165,
    "秋分": 180, "寒露": 195, "霜降": 210, "立冬": 225, "小雪": 240, "大雪": 255,
    "冬至": 270, "小寒": 285, "大寒": 300, "立春": 315, "雨水": 330, "驚蟄": 345,
}

# 各節氣於該西元年之概略（月, 日），僅作牛頓法初始猜測用。
_APPROX_DATE = {
    "春分": (3, 20), "清明": (4, 5), "穀雨": (4, 20), "立夏": (5, 5),
    "小滿": (5, 21), "芒種": (6, 6), "夏至": (6, 21), "小暑": (7, 7),
    "大暑": (7, 23), "立秋": (8, 7), "處暑": (8, 23), "白露": (9, 8),
    "秋分": (9, 23), "寒露": (10, 8), "霜降": (10, 23), "立冬": (11, 7),
    "小雪": (11, 22), "大雪": (12, 7), "冬至": (12, 22), "小寒": (1, 6),
    "大寒": (1, 20), "立春": (2, 4), "雨水": (2, 19), "驚蟄": (3, 6),
}

# 十二「節」（換月用）：名稱 → 月支 index（子=0 … 亥=11）。
JIE_TO_BRANCH = {
    "立春": 2, "驚蟄": 3, "清明": 4, "立夏": 5, "芒種": 6, "小暑": 7,
    "立秋": 8, "白露": 9, "寒露": 10, "立冬": 11, "大雪": 0, "小寒": 1,
}


def jd_from_gregorian(year: int, month: int, day: float) -> float:
    """西曆（含小數日）→ 儒略日 JD。day 可含小數（如 1.5 = 該日正午）。"""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1))
            + day + b - 1524.5)


def gregorian_from_jd(jd: float):
    """儒略日 JD → (year, month, day, hour, minute)。"""
    # 先四捨五入到整數分鐘再拆解，進位（含跨日）交給整數運算處理。
    total_minutes = math.floor((jd + 0.5) * 1440 + 0.5)
    z, minute_of_day = divmod(total_minutes, 1440)
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    hour, minute = divmod(minute_of_day, 60)
    return year, month, day, hour, minute


def delta_t_seconds(year: float) -> float:
    """ΔT = TT − UT（秒）。Espenak–Meeus 分段多項式，涵蓋約 1900–2150。"""
    y = year
    if 1900 <= y < 1920:
        t = y - 1900
        return (-2.79 + 1.494119 * t - 0.0598939 * t**2
                + 0.0061966 * t**3 - 0.000197 * t**4)
    if 1920 <= y < 1941:
        t = y - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    if 1941 <= y < 1961:
        t = y - 1950
        return 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    if 1961 <= y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    if 1986 <= y < 2005:
        t = y - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3
                + 0.000651814 * t**4 + 0.00002373599 * t**5)
    if 2005 <= y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    if 2050 <= y < 2150:
        return -20 + 32 * ((y - 1820) / 100) ** 2 - 0.5628 * (2150 - y)
    # 範圍外通用拋物線
    u = (y - 1820) / 100
    return -20 + 32 * u * u


# 截斷式 VSOP87D 地球日心黃經序列（A·cos(B+Cτ)），A:1e-8 rad，C:rad/千年。
# 取自 Meeus《Astronomical Algorithms》附錄之 VSOP87 摘要，截斷至約 0.001°。
_EARTH_L0 = [
    (175347046, 0.0, 0.0), (3341656, 4.6692568, 6283.0758500),
    (34894, 4.62610, 12566.15170), (3497, 2.7441, 5753.3849),
    (3418, 2.8289, 3.5231), (3136, 3.6277, 77713.7715),
    (2676, 4.4181, 7860.4194), (2343, 6.1352, 3930.2097),
    (1324, 0.7425, 11506.7698), (1273, 2.0371, 529.6910),
    (1199, 1.1096, 1577.3435), (990, 5.233, 5884.927),
    (902, 2.045, 26.298), (857, 3.508, 398.149),
    (780, 1.179, 5223.694), (753, 2.533, 5507.553),
    (505, 4.583, 18849.228), (492, 4.205, 775.523),
    (357, 2.920, 0.067), (317, 5.849, 11790.629),
    (284, 1.899, 796.298), (271, 0.315, 10977.079),
    (243, 0.345, 5486.778), (206, 4.806, 2544.314),
    (205, 1.869, 5573.143), (202, 2.458, 6069.777),
]
_EARTH_L1 = [
    (628331966747, 0.0, 0.0), (206059, 2.678235, 6283.075850),
    (4303, 2.6351, 12566.1517), (425, 1.590, 3.523),
    (119, 5.796, 26.298), (109, 2.966, 1577.344),
    (93, 2.59, 18849.23), (72, 1.14, 529.69),
]
_EARTH_L2 = [
    (52919, 0.0, 0.0), (8720, 1.0721, 6283.0758),
    (309, 0.867, 12566.152),
]
_EARTH_L3 = [(289, 5.844, 6283.076)]


def _vsop_series(terms, tau):
    return sum(a * math.cos(b + c * tau) for a, b, c in terms)


def sun_apparent_longitude(jde: float) -> float:
    """太陽視黃經（度，0–360），含章動與光行差。截斷式 VSOP87，jde 為 TT。

    精度約 ±1–2 分鐘（與權威萬年曆對照）。
    """
    tau = (jde - 2451545.0) / 365250.0  # 千年
    l = (_vsop_series(_EARTH_L0, tau)
         + _vsop_series(_EARTH_L1, tau) * tau
         + _vsop_series(_EARTH_L2, tau) * tau ** 2
         + _vsop_series(_EARTH_L3, tau) * tau ** 3) * 1e-8  # 地球日心黃經(rad)
    theta = math.degrees(l) + 180.0  # 太陽地心幾何黃經
    t = (jde - 2451545.0) / 36525.0  # 世紀
    # VSOP87 → FK5 修正（對太陽僅常數項）
    theta -= 0.09033 / 3600.0
    # 章動（主要項，arcsec）
    omega = math.radians((125.04452 - 1934.136261 * t) % 360)
    l_sun = math.radians((280.4665 + 36000.7698 * t) % 360)
    l_moon = math.radians((218.3165 + 481267.8813 * t) % 360)
    d_psi = (-17.20 * math.sin(omega) - 1.32 * math.sin(2 * l_sun)
             - 0.23 * math.sin(2 * l_moon) + 0.21 * math.sin(2 * omega))
    # 光行差（R≈1.0，誤差 <0.4"）
    aberration = -20.4898
    lam = theta + (d_psi + aberration) / 3600.0
    return lam % 360


def _term_jd_tt(year: int, name: str) -> float:
    """求某西元年某節氣之 JD（TT 時間尺度）。"""
    target = SOLAR_LONGITUDE[name]
    m, d = _APPROX_DATE[name]
    jde = jd_from_gregorian(year, m, d + 0.5)  # 正午起算
    for _ in range(8):
        lam = sun_apparent_longitude(jde)
        diff = (target - lam + 180.0) % 360.0 - 180.0
        jde += 58.13 * math.sin(math.radians(diff))
        if abs(diff) < 1e-6:
            break
    return jde


def term_local(year: int, name: str, tz_hours: float = 8.0):
    """回傳該西元年某節氣之地方時刻 (year, month, day, hour, minute)。

    內部以 TT 求解，再扣 ΔT 得 UT，最後加時區得地方民用時。
    若 references/solar_terms_2020_2040.csv 有權威覆蓋值，優先採用。
    """
    return gregorian_from_jd(term_local_jd(year, name, tz_hours))


def term_local_jd(year: int, name: str, tz_hours: float = 8.0) -> float:
    """同 term_local，但回傳地方時對應之 JD（便於比較先後）。"""
    ref_jd = _reference_term_local_jd(year, name, tz_hours)
    if ref_jd is not None:
        return ref_jd
    jd_tt = _term_jd_tt(year, name)
    jd_ut = jd_tt - delta_t_seconds(year) / 86400.0
    return jd_ut + tz_hours / 24.0


_REFERENCE_TERMS = None


def _reference_key(year: int, name: str, tz_hours: float):
    return int(year), name, round(float(tz_hours), 2)


def _reference_csv_candidates():
    """可能的權威節氣覆蓋表位置（原始碼執行 / PyInstaller）。"""
    roots = []
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        roots.append(frozen_root)
    roots.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for root in roots:
        yield os.path.join(root, "references", "solar_terms_2020_2040.csv")


def _load_reference_terms():
    """載入可選權威節氣覆蓋表。

    CSV 欄位：year,name,local_time,tz_hours,source。
    local_time 格式：YYYY-MM-DD HH:MM；時間為指定時區的地方民用時。
    """
    global _REFERENCE_TERMS
    if _REFERENCE_TERMS is not None:
        return _REFERENCE_TERMS

    terms = {}
    for path in _reference_csv_candidates():
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(line for line in f if not line.lstrip().startswith("#")):
                if not row:
                    continue
                year_s = (row.get("year") or "").strip()
                name = (row.get("name") or "").strip()
                local_time = (row.get("local_time") or "").strip()
                if not year_s or not name or not local_time:
                    continue
                year = int(year_s)
                tz = float((row.get("tz_hours") or "8").strip())
                date_s, time_s = local_time.split()
                y_s, m_s, d_s = date_s.split("-")
                hh_s, mm_s = time_s.split(":")[:2]
                jd = jd_from_gregorian(
                    int(y_s), int(m_s),
                    int(d_s) + (int(hh_s) * 60 + int(mm_s)) / 1440.0,
                )
                terms[_reference_key(year, name, tz)] = jd
        break

    _REFERENCE_TERMS = terms
    return terms


def _reference_term_local_jd(year: int, name: str, tz_hours: float):
    return _load_reference_terms().get(_reference_key(year, name, tz_hours))


def month_branch_for(local_jd: float, year_hint: int, tz_hours: float = 8.0) -> int:
    """給定地方時 JD，回傳當下所屬「月支」index（子=0…亥=11，寅=2 為正月）。

    以十二節（立春…小寒）之地方時刻為界，取最後一個 ≤ local_jd 的節。
    """
    candidates = []  # (節氣地方時JD, 月支index)
    for y in (year_hint - 1, year_hint, year_hint + 1):
        for name, branch in JIE_TO_BRANCH.items():
            candidates.append((term_local_jd(y, name, tz_hours), branch))
    candidates.sort()
    chosen = candidates[0][1]
    for jd, branch in candidates:
        if jd <= local_jd:
            chosen = branch
        else:
            break
    return chosen


def current_solar_term(local_jd: float, year_hint: int, tz_hours: float = 8.0):
    """回傳 (節氣名稱, 該節氣地方時刻JD, 已過天數)；用於顯示『芒種第9天』之類。"""
    all_terms = []
    for y in (year_hint - 1, year_hint, year_hint + 1):
        for name in SOLAR_LONGITUDE:
            all_terms.append((term_local_jd(y, name, tz_hours), name))
    all_terms.sort()
    chosen = all_terms[0]
    for jd, name in all_terms:
        if jd <= local_jd:
            chosen = (jd, name)
        else:
            break
    import datetime as _dt
    ty, tm, td, *_ = gregorian_from_jd(chosen[0])
    cy, cm, cd, *_ = gregorian_from_jd(local_jd)
    days_in = (_dt.date(cy, cm, cd) - _dt.date(ty, tm, td)).days + 1
    return chosen[1], chosen[0], days_in
