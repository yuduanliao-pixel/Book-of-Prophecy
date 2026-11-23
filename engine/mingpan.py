"""命盤組裝器：把八字與紫微斗數排盤整合成單一結構，供 CLI 與 skill 使用。

與六爻（divination.build_chart）互相獨立：六爻看「此刻問此事」，命盤看出生時間。
"""
from __future__ import annotations

from . import bazi
from . import ziwei
from .divination import VERSION

SYSTEMS = ("bazi", "ziwei")


def build_mingpan(when, gender, systems=SYSTEMS, years=None, tz_hours: float = 8.0,
                  day_boundary: str = "zi_initial_23", fix_leap: bool = True) -> dict:
    """排命盤。

    when: (year, month, day, hour, minute) 出生地方民用時（西曆）。
    gender: 男/女。systems: 要排的系統（bazi、ziwei）。
    years: 要列出的流年（西元年）清單，同時用於八字流年與紫微大限流年。
    """
    y, mo, d, h, mi = when
    unknown = [s for s in systems if s not in SYSTEMS]
    if unknown:
        raise ValueError(f"未知系統：{unknown}")
    years = sorted(set(years or []))
    out = {
        "version": VERSION,
        "birth": {"year": y, "month": mo, "day": d, "hour": h, "minute": mi,
                  "gender": bazi.normalize_gender(gender), "tz_hours": tz_hours,
                  "day_boundary": day_boundary},
        "years": years,
    }
    if "bazi" in systems:
        out["bazi"] = bazi.build_bazi(y, mo, d, h, mi, gender, tz_hours=tz_hours,
                                      day_boundary=day_boundary, liunian_years=years)
    if "ziwei" in systems:
        out["ziwei"] = ziwei.build_ziwei(y, mo, d, h, mi, gender, day_boundary=day_boundary,
                                         fix_leap=fix_leap, horoscope_years=years)
    return out
