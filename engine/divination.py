"""排盤組裝器：把時間、起卦、裝卦整合成單一結構（chart）。
此結構同時供：①離線執行檔渲染 ②skill 輸出 JSON 交 LLM 斷卦。
"""
from __future__ import annotations

from . import cast
from . import ganzhi as gz
from . import zhuanggua as zg

VERSION = "1.1.1"

# 占問類別 → 用神六親（供補充標示，不作斷卦）
CATEGORY_TO_YONGSHEN = {
    "財運/求財/投資/生意": "妻財",
    "求職/官司/疾病/功名": "官鬼",
    "文書/合約/考試/房產/長輩": "父母",
    "子女/晚輩/平安/醫藥": "子孫",
    "兄弟/朋友/合夥/競爭": "兄弟",
    "占自身整體吉凶": "世爻",
}

# 友善別名 → 正式類別鍵（CLI 可用簡寫，如 財/官/父/子/兄/世 或 wealth/career…）
CATEGORY_ALIASES = {
    "財": "財運/求財/投資/生意", "財運": "財運/求財/投資/生意", "wealth": "財運/求財/投資/生意",
    "官": "求職/官司/疾病/功名", "求職": "求職/官司/疾病/功名", "career": "求職/官司/疾病/功名",
    "父": "文書/合約/考試/房產/長輩", "文書": "文書/合約/考試/房產/長輩", "doc": "文書/合約/考試/房產/長輩",
    "子": "子女/晚輩/平安/醫藥", "子孫": "子女/晚輩/平安/醫藥", "child": "子女/晚輩/平安/醫藥",
    "兄": "兄弟/朋友/合夥/競爭", "兄弟": "兄弟/朋友/合夥/競爭", "peer": "兄弟/朋友/合夥/競爭",
    "世": "占自身整體吉凶", "自身": "占自身整體吉凶", "self": "占自身整體吉凶",
}


def resolve_category(s):
    """接受正式類別鍵或友善別名，回傳正式鍵；無法解析回傳 None。"""
    if not s:
        return None
    s = s.strip()
    if s in CATEGORY_TO_YONGSHEN:
        return s
    return CATEGORY_ALIASES.get(s)


def build_chart(question, when, rounds, tz_hours=8.0,
                day_boundary="zi_initial_23", category=None):
    """組裝排盤。

    question: 占問字串。
    when: (year, month, day, hour, minute) 地方民用時。
    rounds: 六爻成卦結果（cast.cast_hexagram / cast.manual_hexagram 之輸出）。
    category: 占問類別（CATEGORY_TO_YONGSHEN 之鍵），可 None。
    """
    y, mo, d, h, mi = when
    sizhu = gz.compute_sizhu(y, mo, d, h, mi, tz_hours=tz_hours,
                             day_boundary=day_boundary)
    lines, moving = cast.lines_and_moving(rounds)
    zhuang = zg.zhuang(lines, moving,
                       day_gan=sizhu["day_gan"], day_zhi=sizhu["day_zhi"],
                       month_branch=sizhu["month_branch"], xunkong=sizhu["xunkong"])

    # 用神標示（僅標示所臨之爻，不下吉凶）
    yongshen = None
    if category and category in CATEGORY_TO_YONGSHEN:
        target = CATEGORY_TO_YONGSHEN[category]
        if target == "世爻":
            yongshen = {"category": category, "type": "世爻",
                        "positions": [zhuang["shi"]]}
        else:
            pos = [yy["pos"] for yy in zhuang["yaos"] if yy["liuqin"] == target]
            fu = [p for p, info in zhuang["fushen"].items() if info["liuqin"] == target]
            yongshen = {"category": category, "type": target,
                        "positions": pos, "fushen_positions": fu}

    # 動爻摘要
    moving_summary = []
    for yy in zhuang["yaos"]:
        if yy["moving"]:
            ch = yy.get("changed", {})
            moving_summary.append({
                "pos": yy["pos"], "liuqin": yy["liuqin"],
                "from": yy["gan"] + yy["zhi"],
                "to": ch.get("gan", "") + ch.get("zhi", ""),
                "to_liuqin": ch.get("liuqin", ""),
                "marks": ch.get("marks", []),
            })

    return {
        "version": VERSION,
        "question": question,
        "category": category,
        "time": sizhu,
        "rounds": rounds,          # 由下而上（rounds[0]=初爻）
        "zhuang": zhuang,
        "yongshen": yongshen,
        "moving_summary": moving_summary,
    }
