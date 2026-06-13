"""起卦：三枚銅錢成爻（字=2陰 / 背=3陽，火珠林計數法）。
隨機採密碼學等級 secrets，禁止以一般 random 取代。
"""
from __future__ import annotations

import secrets

FACE_YANG = "背"   # 無字面＝陽＝3
FACE_YIN = "字"    # 有文字面＝陰＝2
FACE_VALUE = {FACE_YIN: 2, FACE_YANG: 3}

# 三錢總和 → (爻名, 陰陽, 是否動爻)
SUM_TO_YAO = {
    6: ("老陰", 0, True),    # 三字，交 ✕，變陽
    7: ("少陽", 1, False),   # 兩字一背
    8: ("少陰", 0, False),   # 一字兩背
    9: ("老陽", 1, True),    # 三背，重 ○，變陰
}


def toss_one() -> str:
    """擲一枚錢，回傳 '背'(陽) 或 '字'(陰)，各 50%。"""
    return FACE_YANG if secrets.randbits(1) else FACE_YIN


def make_line(coins):
    """由三枚錢面組成一爻。coins 為長度 3 之 ['背'/'字',...]。"""
    if len(coins) != 3 or any(c not in FACE_VALUE for c in coins):
        raise ValueError("每爻需三枚錢面，且只能為 '字' 或 '背'")
    total = sum(FACE_VALUE[c] for c in coins)
    name, yinyang, moving = SUM_TO_YAO[total]
    return {"coins": list(coins), "total": total,
            "name": name, "yinyang": yinyang, "moving": moving}


def cast_line():
    """自動擲一爻（CSPRNG）。"""
    return make_line([toss_one() for _ in range(3)])


def cast_hexagram():
    """自動起一卦：六輪，由下而上（rounds[0]=初爻 … rounds[5]=上爻）。"""
    return [cast_line() for _ in range(6)]


def manual_hexagram(rounds):
    """手動起卦：rounds 為 6 組（由下而上），每組三枚錢面 '字'/'背'。"""
    if len(rounds) != 6:
        raise ValueError("需六爻（由下而上）共 6 組")
    return [make_line(r) for r in rounds]


# 錢面同義詞（不含『正/反』，因現代硬幣正反面定義有歧義）
FACE_SYNONYMS = {"背": "背", "字": "字", "b": "背", "z": "字", "B": "背", "Z": "字",
                 "3": "背", "2": "字", "陽": "背", "陰": "字"}


def parse_faces(token: str):
    """解析單爻三枚錢面字串，支援 '背字字' 連寫或 '背 字 字' 空白分隔，
    及同義詞 b/z、3/2、陽/陰。回傳 ['背','字','字']。"""
    token = token.strip().replace("，", " ").replace(",", " ")
    parts = token.split() if " " in token else list(token)
    faces = [FACE_SYNONYMS.get(p) for p in parts]
    if len(faces) != 3 or any(f is None for f in faces):
        raise ValueError(f"無效錢面『{token}』；每爻需三枚，僅可為 字/背（或 b/z、3/2、陽/陰）")
    return faces


def parse_manual_spec(spec: str):
    """解析 '組1;組2;…;組6'（由下而上）→ 六爻成卦結果。"""
    groups = [g for g in spec.split(";")]
    if len(groups) != 6:
        raise ValueError("需 6 組（以 ; 分隔，由下而上）")
    return manual_hexagram([parse_faces(g) for g in groups])


def lines_and_moving(rounds):
    """由六爻成卦結果取出 (本卦 lines tuple, moving 布林序列)，皆 bottom→top。"""
    lines = tuple(r["yinyang"] for r in rounds)
    moving = tuple(r["moving"] for r in rounds)
    return lines, moving
