"""紫微斗數排盤：命身宮、五行局、十四主星、十四輔星、生年四化、亮度、大限與流年。

只產生可驗證的排盤事實，不含格局與吉凶判斷（交由斷盤者／LLM）。
安星以農曆為準（engine.lunar）：年以正月初一換、閏月前半歸本月後半歸下月。
輔星僅排十四顆常用者（左右昌曲魁鉞、祿存羊陀、火鈴空劫、天馬），不含雜曜。
亮度（廟旺得利平不陷）各派有出入，本表採通行版本。純標準庫，離線。
"""
from __future__ import annotations

import datetime as _dt

from . import constants as C
from . import lunar as ln
from .bazi import normalize_gender

PALACE_NAMES = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄",
                "遷移", "僕役", "官祿", "田宅", "福德", "父母"]
HUA = ("祿", "權", "科", "忌")
JU_BY_WUXING = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}
JU_NAME = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}

# 紫微系（自紫微逆行之偏移）、天府系（自天府順行之偏移）
_ZIWEI_GROUP = (("紫微", 0), ("天機", -1), ("太陽", -3), ("武曲", -4), ("天同", -5), ("廉貞", -8))
_TIANFU_GROUP = (("天府", 0), ("太陰", 1), ("貪狼", 2), ("巨門", 3), ("天相", 4),
                 ("天梁", 5), ("七殺", 6), ("破軍", 10))
MAJOR_STARS = tuple(n for n, _ in _ZIWEI_GROUP + _TIANFU_GROUP)

# 十干四化：祿、權、科、忌
SIHUA = {
    "甲": ("廉貞", "破軍", "武曲", "太陽"), "乙": ("天機", "天梁", "紫微", "太陰"),
    "丙": ("天同", "天機", "文昌", "廉貞"), "丁": ("太陰", "天同", "天機", "巨門"),
    "戊": ("貪狼", "太陰", "右弼", "天機"), "己": ("武曲", "貪狼", "天梁", "文曲"),
    "庚": ("太陽", "武曲", "太陰", "天同"), "辛": ("巨門", "太陽", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左輔", "武曲"), "癸": ("破軍", "巨門", "太陰", "貪狼"),
}

# 年干 → 祿存所在地支（擎羊在其後一位、陀羅在其前一位）
_LUCUN = {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
          "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}
# 年干 → (天魁, 天鉞)
_KUIYUE = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
           "丙": "亥酉", "丁": "亥酉", "辛": "午寅", "壬": "卯巳", "癸": "卯巳"}
# 年支三合 → 天馬、(火星起子時宮, 鈴星起子時宮)
_TIANMA = {"寅午戌": "申", "申子辰": "寅", "巳酉丑": "亥", "亥卯未": "巳"}
_HUOLING = {"寅午戌": "丑卯", "申子辰": "寅戌", "巳酉丑": "卯戌", "亥卯未": "酉戌"}
# 命主（依命宮地支）、身主（依生年地支），順序：子丑寅卯辰巳午未申酉戌亥
_SOUL = ["貪狼", "巨門", "祿存", "文曲", "廉貞", "武曲", "破軍", "武曲", "廉貞", "文曲", "祿存", "巨門"]
_BODY = ["火星", "天相", "天梁", "天同", "文昌", "天機", "火星", "天相", "天梁", "天同", "文昌", "天機"]

# 星曜亮度，順序：子丑寅卯辰巳午未申酉戌亥（未列者不論亮度）
BRIGHTNESS = {
    "紫微": "平廟旺旺得旺廟廟旺旺得旺", "天機": "廟陷得旺利平廟陷得旺利平",
    "太陽": "陷不旺廟旺旺旺得得平不陷", "武曲": "旺廟得利廟平旺廟得利廟平",
    "天同": "旺不利平平廟陷不旺平平廟", "廉貞": "平利廟平利陷平利廟平利陷",
    "天府": "廟廟廟得廟得旺廟得旺廟得", "太陰": "廟廟旺陷陷陷不不利旺旺廟",
    "貪狼": "旺廟平利廟陷旺廟平利廟陷", "巨門": "旺不廟廟陷旺旺不廟廟陷旺",
    "天相": "廟廟廟陷得得廟得廟陷得得", "天梁": "廟旺廟廟廟陷廟旺陷得廟陷",
    "七殺": "旺廟廟旺廟平旺廟廟旺廟平", "破軍": "廟旺得陷旺平廟旺得陷旺平",
    "文昌": "得廟陷利得廟陷利得廟陷利", "文曲": "得廟平旺得廟陷旺得廟陷旺",
    "火星": "陷得廟利陷得廟利陷得廟利", "鈴星": "陷得廟利陷得廟利陷得廟利",
    "擎羊": "陷廟　陷廟　陷廟　陷廟　", "陀羅": "　廟陷　廟陷　廟陷　廟陷",
}


def _zi(branch: str) -> int:
    return C.DIZHI.index(branch)


def _group_of(branch: str, table: dict):
    for group, value in table.items():
        if branch in group:
            return value
    raise ValueError(branch)


def ziwei_position(ju: int, lunar_day: int) -> int:
    """紫微星所在地支 index（子=0）。依五行局數與農曆生日推算。"""
    q = -(-lunar_day // ju)          # 商數（無條件進位）
    x = q * ju - lunar_day           # 需補的日數
    pos = 2 + (q - 1)                # 自寅宮起數
    pos = pos + x if x % 2 == 0 else pos - x
    return pos % 12


def hour_index(hour: int) -> int:
    """時（0–23）→ 時辰 index（子=0…亥=11）；23 時與 0 時同屬子時。"""
    return ((hour + 1) // 2) % 12


def _brightness(star: str, branch_index: int):
    row = BRIGHTNESS.get(star)
    if not row:
        return None
    b = row[branch_index]
    return None if b == "　" else b


def _relative_names(ming_index: int) -> dict:
    """以某地支為命宮，回傳 {地支: 宮名}（十二宮逆布）。"""
    return {C.DIZHI[(ming_index - i) % 12]: PALACE_NAMES[i] for i in range(12)}


def build_ziwei(year, month, day, hour, minute, gender, day_boundary: str = "zi_initial_23",
                fix_leap: bool = True, horoscope_years=None) -> dict:
    """排紫微命盤。參數為出生地方民用時（西曆）；gender 為 男/女。

    day_boundary：23 時（晚子時）的處理。zi_initial_23 算次日子時；
        midnight_00／split_zi 算當日子時。
    fix_leap：閏月生人，十五日（含）前歸本月、十六日起歸下月；False 則一律歸本月。
    horoscope_years：要列出大限／流年資訊的農曆年（西元年數）清單，可 None。
    """
    gender = normalize_gender(gender)
    civil = _dt.date(year, month, day)
    if hour >= 23 and day_boundary == "zi_initial_23":
        civil += _dt.timedelta(days=1)
    h_idx = hour_index(hour)

    lunar = ln.solar_to_lunar(civil.year, civil.month, civil.day)
    shift = 1 if (lunar["is_leap"] and fix_leap and lunar["day"] > 15) else 0
    month_idx = (lunar["month"] - 1 + shift) % 12       # 正月=0
    year_gz = C.ganzhi_name((lunar["year"] - 4) % 60)
    year_gan, year_zhi = year_gz[0], year_gz[1]

    # ── 命宮、身宮（寅宮起正月，順數生月；逆數生時為命、順數生時為身）──
    ming = (2 + month_idx - h_idx) % 12
    shen = (2 + month_idx + h_idx) % 12

    # ── 十二宮天干（五虎遁）──
    yin_gan = ((C.TIANGAN.index(year_gan) % 5) * 2 + 2) % 10
    stem_of = {b: C.TIANGAN[(yin_gan + (b - 2) % 12) % 10] for b in range(12)}

    # ── 五行局（命宮干支納音）──
    ming_gz = stem_of[ming] + C.DIZHI[ming]
    ju = JU_BY_WUXING[C.nayin(ming_gz)[-1]]

    # ── 安星 ──
    stars = {b: {"major": [], "minor": []} for b in range(12)}
    zw = ziwei_position(ju, lunar["day"])
    tf = (4 - zw) % 12   # 天府與紫微以寅申線對稱
    for name, off in _ZIWEI_GROUP:
        stars[(zw + off) % 12]["major"].append(name)
    for name, off in _TIANFU_GROUP:
        stars[(tf + off) % 12]["major"].append(name)

    lucun = _zi(_LUCUN[year_gan])
    kui, yue = _KUIYUE[year_gan]
    huo0, ling0 = _group_of(year_zhi, _HUOLING)
    minor_pos = [
        ("左輔", (4 + month_idx) % 12), ("右弼", (10 - month_idx) % 12),
        ("文昌", (10 - h_idx) % 12), ("文曲", (4 + h_idx) % 12),
        ("天魁", _zi(kui)), ("天鉞", _zi(yue)),
        ("祿存", lucun), ("天馬", _zi(_group_of(year_zhi, _TIANMA))),
        ("擎羊", (lucun + 1) % 12), ("陀羅", (lucun - 1) % 12),
        ("火星", (_zi(huo0) + h_idx) % 12), ("鈴星", (_zi(ling0) + h_idx) % 12),
        ("地空", (11 - h_idx) % 12), ("地劫", (11 + h_idx) % 12),
    ]
    for name, pos in minor_pos:
        stars[pos]["minor"].append(name)

    natal_hua = dict(zip(SIHUA[year_gan], HUA))   # 星名 → 化X
    star_branch = {}
    for b in range(12):
        for name in stars[b]["major"] + stars[b]["minor"]:
            star_branch[name] = b

    # ── 大限：陽男陰女順行，陰男陽女逆行；自命宮起，起始歲數＝局數 ──
    forward = C.gan_is_yang(year_gan) == (gender == "男")
    decadal_of = {}
    for i in range(12):
        b = (ming + i) % 12 if forward else (ming - i) % 12
        decadal_of[b] = (ju + 10 * i, ju + 10 * i + 9)

    natal_names = _relative_names(ming)
    palaces = []
    for i in range(12):                      # 由命宮起，依十二宮次序
        b = (ming - i) % 12
        def _s(name):
            return {"name": name, "brightness": _brightness(name, b),
                    "hua": natal_hua.get(name)}
        palaces.append({
            "name": PALACE_NAMES[i], "branch": C.DIZHI[b], "stem": stem_of[b],
            "ganzhi": stem_of[b] + C.DIZHI[b], "is_body": b == shen,
            "major": [_s(n) for n in stars[b]["major"]],
            "minor": [_s(n) for n in stars[b]["minor"]],
            "decadal": {"start": decadal_of[b][0], "end": decadal_of[b][1]},
        })

    def _hua_landing(gan):
        """某天干四化所落之星與其本命宮位。"""
        out = []
        for hua, star in zip(HUA, SIHUA[gan]):
            b = star_branch.get(star)
            out.append({"hua": hua, "star": star,
                        "branch": C.DIZHI[b] if b is not None else None,
                        "natal_palace": natal_names[C.DIZHI[b]] if b is not None else None})
        return out

    horoscope = []
    for hy in (horoscope_years or []):
        age = hy - lunar["year"] + 1         # 虛歲（農曆年計）
        y_gz = C.ganzhi_name((hy - 4) % 60)
        y_ming = _zi(y_gz[1])                # 流年命宮＝流年地支所在宮
        item = {
            "year": hy, "age": age, "decadal": None,
            "yearly": {"ganzhi": y_gz, "branch": y_gz[1],
                       "natal_palace": natal_names[y_gz[1]],
                       "palace_names": _relative_names(y_ming),
                       "hua": _hua_landing(y_gz[0])},
        }
        for b, (start, end) in decadal_of.items():
            if start <= age <= end:
                item["decadal"] = {
                    "ganzhi": stem_of[b] + C.DIZHI[b], "branch": C.DIZHI[b],
                    "start": start, "end": end,
                    "natal_palace": natal_names[C.DIZHI[b]],
                    "palace_names": _relative_names(b),
                    "hua": _hua_landing(stem_of[b]),
                }
        horoscope.append(item)

    return {
        "system": "ziwei",
        "input": {"year": year, "month": month, "day": day, "hour": hour, "minute": minute,
                  "gender": gender, "day_boundary": day_boundary, "fix_leap": fix_leap},
        "lunar": {"year": lunar["year"], "month": lunar["month"], "day": lunar["day"],
                  "is_leap": lunar["is_leap"], "year_ganzhi": year_gz,
                  "text": f"{year_gz}年{ln.format_lunar(lunar)}",
                  "month_used": month_idx + 1},
        "hour_branch": C.DIZHI[h_idx],
        "yinyang_gender": ("陽" if C.gan_is_yang(year_gan) else "陰") + gender,
        "ming_branch": C.DIZHI[ming], "shen_branch": C.DIZHI[shen],
        "shen_palace": natal_names[C.DIZHI[shen]],
        "ju": ju, "ju_name": JU_NAME[ju],
        "soul_star": _SOUL[ming], "body_star": _BODY[_zi(year_zhi)],
        "natal_hua": _hua_landing(year_gan),
        "decadal_forward": forward,
        "palaces": palaces,
        "horoscope": horoscope,
    }
