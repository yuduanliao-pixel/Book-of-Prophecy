"""農曆（陰陽合曆）換算：西曆 ↔ 農曆，涵蓋農曆 1900–2100 年。純標準庫，離線。

採查表法：每年一個整數，編碼該年各月大小與閏月（通行之 lunarInfo 編碼）。
    bit 16      閏月大小（1=30 天，0=29 天）
    bit 15..4   正月…十二月大小（1=30 天，0=29 天）
    bit 3..0    閏月月份（0=無閏月）
基準：1900-01-31 = 農曆庚子年正月初一。

資料由天文曆算生成，並與兩套獨立農曆表逐日比對（見 docs/verification.md）。
供紫微斗數安星使用；八字與六爻不依賴農曆（以節氣為準）。
"""
from __future__ import annotations

import datetime as _dt

MIN_YEAR = 1900
MAX_YEAR = 2100
_BASE_DATE = _dt.date(1900, 1, 31)  # 農曆 1900 年正月初一

_LUNAR_INFO = (
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,  # 1900
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,  # 1910
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,  # 1920
    0x06566, 0x0d4a0, 0x0ea50, 0x16a95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,  # 1930
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,  # 1940
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,  # 1950
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,  # 1960
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,  # 1970
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,  # 1980
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,  # 1990
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,  # 2000
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,  # 2010
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,  # 2020
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,  # 2030
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,  # 2040
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,  # 2050
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,  # 2060
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,  # 2070
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,  # 2080
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,  # 2090
    0x0d520,  # 2100
)

LUNAR_MONTH_NAMES = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "臘")
_DAY_PREFIX = ("初", "十", "廿", "三")
_DIGITS = "一二三四五六七八九十"


def leap_month(lunar_year: int) -> int:
    """該農曆年的閏月月份（1–12）；無閏月回傳 0。"""
    return _info(lunar_year) & 0xF


def leap_month_days(lunar_year: int) -> int:
    """該農曆年閏月天數；無閏月回傳 0。"""
    if not leap_month(lunar_year):
        return 0
    return 30 if _info(lunar_year) & 0x10000 else 29


def month_days(lunar_year: int, month: int) -> int:
    """該農曆年某（非閏）月的天數。"""
    if not 1 <= month <= 12:
        raise ValueError(f"農曆月份須為 1–12：{month}")
    return 30 if _info(lunar_year) & (0x8000 >> (month - 1)) else 29


def year_days(lunar_year: int) -> int:
    """該農曆年總天數。"""
    return sum(month_days(lunar_year, m) for m in range(1, 13)) + leap_month_days(lunar_year)


def _info(lunar_year: int) -> int:
    if not MIN_YEAR <= lunar_year <= MAX_YEAR:
        raise ValueError(f"農曆年份超出支援範圍 {MIN_YEAR}–{MAX_YEAR}：{lunar_year}")
    return _LUNAR_INFO[lunar_year - MIN_YEAR]


def _months_of(lunar_year: int):
    """依序產生 (月份, 是否閏月, 天數)。"""
    leap = leap_month(lunar_year)
    for m in range(1, 13):
        yield m, False, month_days(lunar_year, m)
        if m == leap:
            yield m, True, leap_month_days(lunar_year)


def solar_to_lunar(year: int, month: int, day: int) -> dict:
    """西曆日期 → 農曆。回傳 {year, month, day, is_leap, month_days}。

    year 為農曆年（正月初一換年），month 為 1–12，is_leap 表示是否閏月。
    """
    target = _dt.date(year, month, day)
    offset = (target - _BASE_DATE).days
    if offset < 0:
        raise ValueError("日期早於支援範圍（1900-01-31）")
    ly = MIN_YEAR
    while True:
        if ly > MAX_YEAR:
            raise ValueError("日期晚於支援範圍（農曆 2100 年底）")
        yd = year_days(ly)
        if offset < yd:
            break
        offset -= yd
        ly += 1
    for m, is_leap, days in _months_of(ly):
        if offset < days:
            return {"year": ly, "month": m, "day": offset + 1,
                    "is_leap": is_leap, "month_days": days}
        offset -= days
    raise AssertionError("unreachable")


def lunar_to_solar(lunar_year: int, month: int, day: int, is_leap: bool = False) -> _dt.date:
    """農曆 → 西曆日期。"""
    if is_leap and leap_month(lunar_year) != month:
        raise ValueError(f"農曆 {lunar_year} 年無閏{month}月")
    offset = sum(year_days(y) for y in range(MIN_YEAR, lunar_year))
    for m, leap_flag, days in _months_of(lunar_year):
        if m == month and leap_flag == is_leap:
            if not 1 <= day <= days:
                raise ValueError(f"該月只有 {days} 天：{day}")
            return _BASE_DATE + _dt.timedelta(days=offset + day - 1)
        offset += days
    raise ValueError(f"無效農曆月份：{month}")


def day_name(day: int) -> str:
    """農曆日名：初一…三十。"""
    if day == 10:
        return "初十"
    if day == 20:
        return "二十"
    if day == 30:
        return "三十"
    return _DAY_PREFIX[(day - 1) // 10] + _DIGITS[(day - 1) % 10]


def format_lunar(lunar: dict) -> str:
    """{year, month, day, is_leap} → 「閏四月初八」之類的字串（不含年）。"""
    return ("閏" if lunar["is_leap"] else "") + LUNAR_MONTH_NAMES[lunar["month"] - 1] + "月" + day_name(lunar["day"])
