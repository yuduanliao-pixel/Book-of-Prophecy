"""京房裝卦：定宮→世應→納甲納支→五行→六親→六獸→伏神，並標旬空、旺衰、動變、伏吟反吟。"""
from __future__ import annotations

from . import constants as C
from . import bagua
from . import ganzhi as gz


def liuqin(my_wuxing: str, yao_wuxing: str) -> str:
    """以卦宮五行(my)為『我』，定爻之六親。"""
    if yao_wuxing == my_wuxing:
        return "兄弟"
    if C.WUXING_SHENG[yao_wuxing] == my_wuxing:   # 生我者
        return "父母"
    if C.WUXING_SHENG[my_wuxing] == yao_wuxing:   # 我生者
        return "子孫"
    if C.WUXING_KE[yao_wuxing] == my_wuxing:       # 剋我者
        return "官鬼"
    return "妻財"                                   # 我剋者


def _gan_zhi_for(lines, pos):
    """爻位 pos(1..6) 之 (納甲干, 納支)。lines 為六爻 tuple。"""
    low = bagua.lower_trigram(lines)
    up = bagua.upper_trigram(lines)
    if pos <= 3:
        gan = C.NAJIA_GAN[low][0]
        zhi = C.NAJIA_ZHI[low][0][pos - 1]
    else:
        gan = C.NAJIA_GAN[up][1]
        zhi = C.NAJIA_ZHI[up][1][pos - 4]
    return gan, zhi


def _yao_records(lines, palace_wuxing):
    """回傳六爻的納甲六親紀錄（pos 1..6）。"""
    recs = []
    for pos in range(1, 7):
        gan, zhi = _gan_zhi_for(lines, pos)
        wx = C.DIZHI_WUXING[zhi]
        recs.append({"pos": pos, "gan": gan, "zhi": zhi, "wuxing": wx,
                     "liuqin": liuqin(palace_wuxing, wx)})
    return recs


def zhuang(lines, moving, day_gan, day_zhi=None, month_branch=None, xunkong=None):
    """完整裝卦。

    lines/moving：本卦六爻與動爻旗標（bottom→top）。
    day_gan：日干（定六獸）。month_branch：月建地支（供旺衰/月破）。
    day_zhi/xunkong：可選，供日辰關係/旬空標記。
    回傳含本卦、變卦、互/錯/綜、世應、伏神之結構。
    """
    month_wuxing = C.DIZHI_WUXING[month_branch] if month_branch else None
    lines = tuple(lines)
    moving = tuple(moving)
    base = bagua.gua_full(lines)
    pw = base["palace_wuxing"]
    shi, ying = base["shi"], base["ying"]

    # 六獸（依日干起初爻）
    start = C.LIUSHOU_START[day_gan]
    liushou = [C.LIUSHOU[(start + i) % 6] for i in range(6)]

    # 變卦
    has_moving = any(moving)
    changed_lines = bagua.bian_gua(lines, moving) if has_moving else None
    changed = bagua.gua_full(changed_lines) if has_moving else None

    yaos = []
    base_recs = _yao_records(lines, pw)
    for pos in range(1, 7):
        rec = base_recs[pos - 1]
        zhi = rec["zhi"]
        wx = rec["wuxing"]
        item = {
            "pos": pos,
            "yinyang": lines[pos - 1],
            "liushou": liushou[pos - 1],
            "gan": rec["gan"], "zhi": zhi, "wuxing": wx,
            "liuqin": rec["liuqin"],
            "is_shi": pos == shi, "is_ying": pos == ying,
            "moving": moving[pos - 1],
            "is_kong": bool(xunkong and zhi in xunkong),
            "wangshuai": gz.wangshuai(wx, month_wuxing) if month_wuxing else None,
            "is_yuepo": bool(month_branch and C.LIUCHONG.get(month_branch) == zhi),
            "day_relation": gz.branch_relation(zhi, day_zhi) if day_zhi else "",
        }
        # 變爻（六親仍以本卦卦宮五行為準）
        if has_moving and moving[pos - 1]:
            cgan, czhi = _gan_zhi_for(changed_lines, pos)
            cwx = C.DIZHI_WUXING[czhi]
            mark = []
            if C.JINSHEN.get(zhi) == czhi:
                mark.append("化進神")
            if C.TUISHEN.get(zhi) == czhi:
                mark.append("化退神")
            if C.WUXING_SHENG[cwx] == wx:
                mark.append("回頭生")
            if C.WUXING_KE[cwx] == wx:
                mark.append("回頭剋")
            if xunkong and czhi in xunkong:
                mark.append("化空")
            if czhi == zhi:
                mark.append("伏吟")      # 化出之爻地支不變
            if C.LIUCHONG.get(zhi) == czhi:
                mark.append("反吟")      # 化出之爻與本爻相沖
            item["changed"] = {"gan": cgan, "zhi": czhi, "wuxing": cwx,
                               "liuqin": liuqin(pw, cwx), "marks": mark}
        yaos.append(item)

    # 伏神：本卦缺之六親，於本宮純卦同爻位取
    present = {y["liuqin"] for y in yaos}
    fushen = {}
    pure_lines = bagua._pure_lines(base["palace"])
    pure_recs = _yao_records(pure_lines, pw)
    for liuqin_name in ("父母", "兄弟", "子孫", "妻財", "官鬼"):
        if liuqin_name not in present:
            for r in pure_recs:
                if r["liuqin"] == liuqin_name:
                    fushen[r["pos"]] = {
                        "liuqin": liuqin_name, "gan": r["gan"], "zhi": r["zhi"],
                        "wuxing": r["wuxing"],
                        "is_kong": bool(xunkong and r["zhi"] in xunkong),
                    }

    # 內／外卦伏吟、反吟：該經卦有動爻，且其動爻全數伏吟（或全數反吟）
    fuyin, fanyin = [], []
    for label, positions in (("內卦", (1, 2, 3)), ("外卦", (4, 5, 6))):
        marks = [yaos[p - 1]["changed"]["marks"] for p in positions if "changed" in yaos[p - 1]]
        if marks and all("伏吟" in m for m in marks):
            fuyin.append(label)
        if marks and all("反吟" in m for m in marks):
            fanyin.append(label)

    return {
        "base": base,
        "changed": changed,
        "hu": bagua.gua_full(bagua.hu_gua(lines)),
        "cuo": bagua.gua_full(bagua.cuo_gua(lines)),
        "zong": bagua.gua_full(bagua.zong_gua(lines)),
        "yaos": yaos,           # pos 1..6（由下而上）
        "fushen": fushen,       # {爻位: 伏神資訊}
        "shi": shi, "ying": ying,
        "has_moving": has_moving,
        "fuyin": fuyin,         # 伏吟所在（"內卦"／"外卦"）
        "fanyin": fanyin,       # 反吟所在（爻反吟：動爻化出相沖）
    }
