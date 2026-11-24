"""命盤文字渲染（八字、紫微斗數）。供 CLI 與 skill 共用。"""
from __future__ import annotations

from .bazi import PILLAR_KEYS
from .render import _pad

_BOUNDARY_NAME = {"zi_initial_23": "子初換日(23時)", "midnight_00": "子正換日(00時)",
                  "split_zi": "夜子時分日"}
_RULE = "═" * 60


def _birth_line(b: dict) -> str:
    return (f"【出生】{b['year']:04d}-{b['month']:02d}-{b['day']:02d} "
            f"{b['hour']:02d}:{b['minute']:02d}（UTC+{b['tz_hours']:g}，"
            f"{_BOUNDARY_NAME.get(b['day_boundary'], b['day_boundary'])}）　{b['gender']}")


def render_bazi_text(bz: dict) -> list:
    P = bz["pillars"]
    out = ["【八字】"]

    def row(label, values, width=10):
        return "　" + _pad(label, 10) + "".join(_pad(v, width) for v in values)

    out.append(row("", ["年柱", "月柱", "日柱", "時柱"]))
    out.append(row("十神", [P[k]["shishen"] for k in PILLAR_KEYS]))
    out.append(row("天干", [P[k]["gan"] + P[k]["gan_wuxing"] for k in PILLAR_KEYS]))
    out.append(row("地支", [P[k]["zhi"] + P[k]["zhi_wuxing"] for k in PILLAR_KEYS]))
    out.append(row("藏干", ["".join(c["gan"] for c in P[k]["canggan"]) for k in PILLAR_KEYS]))
    out.append(row("十二長生", [P[k]["dishi"] for k in PILLAR_KEYS]))
    out.append(row("納音", [P[k]["nayin"] for k in PILLAR_KEYS]))
    for k, name in zip(PILLAR_KEYS, ("年支", "月支", "日支", "時支")):
        cg = "、".join(f"{c['gan']}{c['shishen']}" for c in P[k]["canggan"])
        out.append(f"　{name}{P[k]['zhi']}藏干十神：{cg}")
    dm = bz["day_master"]
    out.append(f"　日主：{dm['gan']}{dm['wuxing']}（{dm['yinyang']}）　月令：{bz['month_branch']}"
               f"（{bz['solar_term']}後第{bz['solar_term_days_in']}天）　旬空：{''.join(bz['xunkong'])}")
    wc = bz["wuxing_count"]
    out.append("　五行（四干＋四支本氣）：" + "　".join(f"{w}{wc[w]}" for w in "木火土金水"))
    if bz["natal_combos"]:
        out.append("　原局：" + "、".join(bz["natal_combos"]))

    D = bz["dayun"]
    so = D["start_offset"]
    out.append("")
    out.append(f"【大運】{'順' if D['forward'] else '逆'}行，以{D['from_jie']}為界；出生後 "
               f"{so['years']} 年 {so['months']} 個月 {so['days']} 天起運（約 {D['start_date']}）")
    for du in D["list"]:
        extra = "　".join(du["relations"] + du["combos"])
        out.append(f"　{du['index']}. {du['ganzhi']}（{du['shishen_gan']}／{du['shishen_zhi']}）"
                   f"{du['start_year']}–{du['end_year']}　虛歲 {du['start_age']}–{du['end_age']}"
                   + (f"　{extra}" if extra else ""))
    if bz["liunian"]:
        out.append("")
        out.append("【流年】（立春起算）")
        for ly in bz["liunian"]:
            extra = "　".join(ly["relations"] + ly["combos"])
            out.append(f"　{ly['year']} {ly['ganzhi']}（{ly['shishen_gan']}／{ly['shishen_zhi']}）"
                       f"虛歲 {ly['age']}　大運 {ly['dayun'] or '未起運'}"
                       + (f"　{extra}" if extra else ""))
    return out


def _stars(items) -> str:
    def one(s):
        t = s["name"]
        if s["brightness"]:
            t += f"({s['brightness']})"
        if s["hua"]:
            t += f"[化{s['hua']}]"
        return t
    return " ".join(one(s) for s in items) or "—"


def _hua_line(landings) -> str:
    return "　".join(f"{x['hua']}：{x['star']}（{x['natal_palace'] or '不在盤'}）" for x in landings)


def render_ziwei_text(zw: dict) -> list:
    L = zw["lunar"]
    out = ["【紫微斗數】"]
    out.append(f"　農曆：{L['text']}　{zw['hour_branch']}時　{zw['yinyang_gender']}"
               + (f"（閏月，作{L['month_used']}月論）" if L["is_leap"] else ""))
    out.append(f"　命宮在{zw['ming_branch']}　身宮在{zw['shen_branch']}（{zw['shen_palace']}）　"
               f"{zw['ju_name']}　命主{zw['soul_star']}　身主{zw['body_star']}")
    out.append("　生年四化　" + _hua_line(zw["natal_hua"]))
    out.append("")
    out.append(f"　宮位　　干支　主星｜輔星　　大限（虛歲，{'順' if zw['decadal_forward'] else '逆'}行）")
    for p in zw["palaces"]:
        name = p["name"] + ("·身" if p["is_body"] else "")
        out.append(f"　{_pad(name, 8)}{p['ganzhi']}　{_stars(p['major'])}｜{_stars(p['minor'])}"
                   f"　　{p['decadal']['start']}–{p['decadal']['end']}")
    if zw["horoscope"]:
        out.append("")
        out.append("【大限流年】（農曆年；四化後括號為該星所在本命宮）")
        for h in zw["horoscope"]:
            yr = h["yearly"]
            out.append(f"　{h['year']} {yr['ganzhi']}　虛歲 {h['age']}")
            de = h["decadal"]
            if de:
                out.append(f"　　大限 {de['ganzhi']}（{de['start']}–{de['end']}，命宮在本命{de['natal_palace']}）")
                out.append("　　　大限四化　" + _hua_line(de["hua"]))
            else:
                out.append("　　大限：未起運（童限）")
            out.append(f"　　流年命宮在{yr['branch']}（本命{yr['natal_palace']}）")
            out.append("　　　流年四化　" + _hua_line(yr["hua"]))
    return out


def render_mingpan_text(mp: dict) -> str:
    out = [_RULE, "　命盤排盤（八字／紫微斗數）", _RULE, _birth_line(mp["birth"]), ""]
    if "bazi" in mp:
        out += render_bazi_text(mp["bazi"]) + [""]
    if "ziwei" in mp:
        out += render_ziwei_text(mp["ziwei"]) + [""]
    out.append(f"※ 排盤工具 v{mp['version']}　僅呈現命盤事實，不含格局、喜忌與吉凶判斷；結果僅供參考。")
    out.append(_RULE)
    return "\n".join(out)
