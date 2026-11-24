"""排盤文字渲染（終端用，含 CJK 對齊）。供執行檔與 skill 共用。"""
from __future__ import annotations

import unicodedata

YANG_SYMBOL = "▅▅▅▅▅▅▅"
YIN_SYMBOL = "▅▅▅　▅▅▅"
YAO_POS_NAME = ["初", "二", "三", "四", "五", "上"]


def _w(s: str) -> int:
    """字串顯示寬度（East Asian Wide/Fullwidth=2，其餘=1）。"""
    width = 0
    for ch in s:
        if ch == "　":  # 全形空格
            width += 2
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _pad(s: str, width: int) -> str:
    """靠左補空白到指定顯示寬度。"""
    return s + " " * max(0, width - _w(s))


def _line_symbol(yinyang: int, moving: bool) -> str:
    sym = YANG_SYMBOL if yinyang == 1 else YIN_SYMBOL
    if moving:
        sym += " ○" if yinyang == 1 else " ✕"
    return sym


def _gua_line(label: str, g: dict) -> str:
    tag = []
    if g.get("is_liuchong"):
        tag.append("六沖")
    if g.get("is_liuhe"):
        tag.append("六合")
    tagstr = ("，" + "／".join(tag)) if tag else ""
    return (f"- {label}：{g['name']}（{g['palace']}宮{g['generation']}，屬{g['palace_wuxing']}；"
            f"{g['upper']}{g['upper_symbol']}上 {g['lower']}{g['lower_symbol']}下{tagstr}）")


def render_text(chart: dict) -> str:
    t = chart["time"]
    z = chart["zhuang"]
    out = []
    out.append("═" * 60)
    out.append("　京房納甲六爻　離線排盤")
    out.append("═" * 60)

    # 占問
    out.append(f"【占問】{chart['question'] or '（未填）'}")
    if chart.get("yongshen"):
        ys = chart["yongshen"]
        loc = "、".join(f"{p}爻" for p in ys["positions"]) or "不上卦"
        extra = ""
        if ys.get("fushen_positions"):
            extra = f"（伏於 {'、'.join(str(p)+'爻' for p in ys['fushen_positions'])}）"
        out.append(f"　　　　用神候選：{ys['type']}（{loc}）{extra}")

    # 起卦時間
    inp = t["input"]
    boundary_name = {"zi_initial_23": "子初換日(23時)",
                     "midnight_00": "子正換日(00時)",
                     "split_zi": "夜子時分日"}.get(inp["day_boundary"], inp["day_boundary"])
    nz = "（夜子時）" if t.get("night_zi") else ""
    out.append(
        f"【起卦時間】{inp['year']:04d}-{inp['month']:02d}-{inp['day']:02d} "
        f"{inp['hour']:02d}:{inp['minute']:02d}（UTC+{inp['tz_hours']:g}，{boundary_name}）{nz}")
    out.append(
        f"　　　　　　{t['year_pillar']}年　{t['month_pillar']}月　"
        f"{t['day_pillar']}日　{t['hour_pillar']}時")
    out.append(
        f"　　　　　　月令：{t['month_branch']}{t['month_wuxing']}"
        f"（{t['solar_term']}後第{t['solar_term_days_in']}天）　"
        f"旬空：{t['xunkong'][0]}{t['xunkong'][1]}")

    # 擲幣過程（由下而上）
    out.append("")
    out.append("【擲幣過程】（由下而上；字＝2＝陰，背＝3＝陽）")
    for i, r in enumerate(chart["rounds"]):
        coins = " ".join(r["coins"])
        out.append(
            f"　{YAO_POS_NAME[i]}爻：{coins}（{r['total']}）→ {r['name']} "
            f"{_line_symbol(r['yinyang'], r['moving'])}")

    # 卦象（條列）
    out.append("")
    out.append("【卦象】")
    out.append(_gua_line("本卦", z["base"]))
    if z["changed"]:
        out.append(_gua_line("變卦", z["changed"]))
    else:
        out.append("- 變卦：無（六爻安靜）")
    out.append(_gua_line("互卦", z["hu"]))
    out.append(_gua_line("錯卦", z["cuo"]))
    out.append(_gua_line("綜卦", z["zong"]))

    # 裝卦表（由上而下）
    out.append("")
    out.append("【裝卦表】（由上而下）")
    cols = [("爻位", 5), ("六神", 5), ("伏神", 11), ("六親", 5),
            ("干支五行", 11), ("旺衰", 5), ("世應", 5), ("動", 4), ("本卦", 12)]
    header = "".join(_pad(name, w) for name, w in cols)
    out.append("　" + header)
    out.append("　" + "─" * _w(header))
    for y in reversed(z["yaos"]):  # 上爻先
        pos = y["pos"]
        fu = z["fushen"].get(pos)
        fu_str = (f"{fu['liuqin']}{fu['gan']}{fu['zhi']}{fu['wuxing']}"
                  + ("空" if fu["is_kong"] else "")) if fu else ""
        najia = f"{y['gan']}{y['zhi']}{y['wuxing']}"
        shi_ying = "世" if y["is_shi"] else ("應" if y["is_ying"] else "")
        dong = ("○" if y["yinyang"] == 1 else "✕") if y["moving"] else ""
        ws = y["wangshuai"] or ""
        sym = _line_symbol(y["yinyang"], y["moving"])
        notes = []
        if y["is_kong"]:
            notes.append("空")
        if y["is_yuepo"]:
            notes.append("月破")
        if notes:
            sym += " 〔" + "／".join(notes) + "〕"
        if "changed" in y:
            ch = y["changed"]
            sym += f" →{ch['liuqin']}{ch['gan']}{ch['zhi']}{ch['wuxing']}"
            if ch["marks"]:
                sym += "(" + "／".join(ch["marks"]) + ")"
        row = [(YAO_POS_NAME[pos - 1] + "爻", 5), (y["liushou"], 5),
               (fu_str, 11), (y["liuqin"], 5), (najia, 8), (ws, 5),
               (shi_ying, 5), (dong, 4), (sym, 12)]
        out.append("　" + "".join(_pad(v, w) for v, w in row))

    # 補充：世應、動爻摘要、日辰關係
    out.append("")
    out.append("【補充】")
    shi_yao = z["yaos"][z["shi"] - 1]
    ying_yao = z["yaos"][z["ying"] - 1]
    out.append(f"- 世爻：{YAO_POS_NAME[z['shi']-1]}爻 {shi_yao['liuqin']}"
               f"{shi_yao['gan']}{shi_yao['zhi']}{shi_yao['wuxing']}　"
               f"應爻：{YAO_POS_NAME[z['ying']-1]}爻 {ying_yao['liuqin']}"
               f"{ying_yao['gan']}{ying_yao['zhi']}{ying_yao['wuxing']}")
    if chart["moving_summary"]:
        for m in chart["moving_summary"]:
            mk = ("，" + "／".join(m["marks"])) if m["marks"] else ""
            out.append(f"- 動爻：{YAO_POS_NAME[m['pos']-1]}爻 {m['liuqin']}{m['from']} "
                       f"→ {m['to_liuqin']}{m['to']}{mk}")
    else:
        out.append("- 動爻：無（六爻安靜，以靜論）")
    if z.get("fuyin"):
        out.append("- 伏吟：" + "、".join(z["fuyin"]) + "（動爻化出地支不變）")
    if z.get("fanyin"):
        out.append("- 反吟：" + "、".join(z["fanyin"]) + "（動爻化出與本爻相沖）")
    # 日辰與各爻關係
    rels = []
    for y in z["yaos"]:
        if y["day_relation"]:
            rels.append(f"{YAO_POS_NAME[y['pos']-1]}爻{y['zhi']}{y['day_relation']}日")
    if rels:
        out.append("- 日辰關係：" + "　".join(rels))

    out.append("")
    out.append(f"※ 排盤工具 v{chart['version']}　僅呈現卦象事實，不含斷卦與結論；"
               f"占卜結果僅供參考。")
    out.append("═" * 60)
    return "\n".join(out)
