"""卦象：六爻↔卦名、上下經卦、互/錯/綜/變卦推導、京房八宮生成。
卦以 6 元組表示，bottom→top（爻1…爻6），1=陽 0=陰。
"""
from __future__ import annotations

from . import constants as C


def lower_trigram(lines):
    return C.TRIGRAM_BY_BITS[tuple(lines[0:3])]


def upper_trigram(lines):
    return C.TRIGRAM_BY_BITS[tuple(lines[3:6])]


def hexagram_name(lines) -> str:
    return C.GUA64[upper_trigram(lines)][lower_trigram(lines)]


def bian_gua(lines, moving):
    """變卦：動爻陰陽反轉，靜爻不變。moving 為長度 6 之布林序列。"""
    return tuple(1 - lines[i] if moving[i] else lines[i] for i in range(6))


def hu_gua(lines):
    """互卦：下卦取爻2,3,4；上卦取爻3,4,5。"""
    return (lines[1], lines[2], lines[3], lines[2], lines[3], lines[4])


def cuo_gua(lines):
    """錯卦：六爻全部陰陽互換。"""
    return tuple(1 - x for x in lines)


def zong_gua(lines):
    """綜卦：六爻上下顛倒。"""
    return tuple(lines[5 - i] for i in range(6))


def _pure_lines(trigram_name):
    bits = C.TRIGRAMS[trigram_name]
    return tuple(bits) + tuple(bits)


def _build_palace_index():
    """建立 {六爻 tuple: (宮, 宮五行, 世代名, 世爻, 應爻)} 完整 64 卦對照。"""
    index = {}
    for palace in C.PALACE_ORDER:
        pure = _pure_lines(palace)
        for gen_name, flipset, shi, ying in C.PALACE_GENERATION:
            lines = list(pure)
            for pos in flipset:
                lines[pos - 1] ^= 1
            index[tuple(lines)] = (palace, C.PALACE_WUXING[palace], gen_name, shi, ying)
    return index


PALACE_INDEX = _build_palace_index()


def palace_info(lines):
    """回傳 (宮, 宮五行, 世代名, 世爻位, 應爻位)。"""
    return PALACE_INDEX[tuple(lines)]


def gua_full(lines):
    """卦的綜合描述。"""
    palace, pw, gen, shi, ying = palace_info(lines)
    low, up = lower_trigram(lines), upper_trigram(lines)
    return {
        "lines": tuple(lines),
        "name": hexagram_name(lines),
        "lower": low, "upper": up,
        "lower_symbol": C.TRIGRAM_SYMBOL[low], "upper_symbol": C.TRIGRAM_SYMBOL[up],
        "palace": palace, "palace_wuxing": pw,
        "generation": gen, "shi": shi, "ying": ying,
        "is_liuchong": hexagram_name(lines) in C.LIUCHONG_GUA,
        "is_liuhe": hexagram_name(lines) in C.LIUHE_GUA,
    }
