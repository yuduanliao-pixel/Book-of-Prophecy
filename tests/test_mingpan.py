"""命盤（農曆／八字／紫微斗數）驗收測試。執行：python -m pytest 或 python tests/test_mingpan.py

fixtures/ 內的對照案例由兩套開源排盤庫產生（八字：lunar-javascript；紫微：iztro），
僅供比對用，引擎本身不依賴它們。詳見 docs/verification.md。
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import bazi, constants as C, lunar, mingpan, render_mingpan, ziwei

_FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _load(name):
    with open(os.path.join(_FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


# ── 農曆 ─────────────────────────────────────────────────
def test_lunar_known_dates():
    # 春節（正月初一）
    for y, m, d in [(1900, 1, 31), (2000, 2, 5), (2024, 2, 10), (2026, 2, 17)]:
        r = lunar.solar_to_lunar(y, m, d)
        assert (r["year"], r["month"], r["day"], r["is_leap"]) == (y, 1, 1, False)
    # 閏月：2023 年閏二月、2025 年閏六月
    assert lunar.leap_month(2023) == 2 and lunar.leap_month(2025) == 6
    r = lunar.solar_to_lunar(2023, 3, 22)
    assert (r["month"], r["day"], r["is_leap"]) == (2, 1, True)
    # 中秋（八月十五）
    assert lunar.solar_to_lunar(2025, 10, 6)["month"] == 8
    assert lunar.solar_to_lunar(2025, 10, 6)["day"] == 15
    assert lunar.format_lunar(lunar.solar_to_lunar(2023, 3, 22)) == "閏二月初一"


def test_lunar_roundtrip():
    d = datetime.date(1900, 1, 31)
    prev = None
    while d.year <= 2100:
        r = lunar.solar_to_lunar(d.year, d.month, d.day)
        assert lunar.lunar_to_solar(r["year"], r["month"], r["day"], r["is_leap"]) == d
        key = (r["year"], r["month"], r["is_leap"], r["day"])
        assert prev is None or key > prev or r["day"] == 1   # 日期單調
        prev = key
        d += datetime.timedelta(days=37)


def test_lunar_year_lengths():
    for y in range(lunar.MIN_YEAR, lunar.MAX_YEAR + 1):
        assert lunar.year_days(y) in (353, 354, 355, 383, 384, 385)


# ── 八字 ─────────────────────────────────────────────────
def test_shishen_and_dishi():
    assert bazi.shishen("甲", "甲") == "比肩" and bazi.shishen("甲", "乙") == "劫財"
    assert bazi.shishen("甲", "丙") == "食神" and bazi.shishen("甲", "丁") == "傷官"
    assert bazi.shishen("甲", "戊") == "偏財" and bazi.shishen("甲", "己") == "正財"
    assert bazi.shishen("甲", "庚") == "七殺" and bazi.shishen("甲", "辛") == "正官"
    assert bazi.shishen("甲", "壬") == "偏印" and bazi.shishen("甲", "癸") == "正印"
    assert bazi.dishi("甲", "亥") == "長生" and bazi.dishi("甲", "午") == "死"
    assert bazi.dishi("乙", "午") == "長生" and bazi.dishi("乙", "亥") == "死"   # 陰干逆行
    assert C.nayin("甲子") == "海中金" and C.nayin("癸亥") == "大海水"
    assert C.ganzhi_index("戊午") == 54


def test_bazi_dayun_direction():
    # 2000-06-15 為庚辰年（陽年）：男順、女逆
    m = bazi.build_bazi(2000, 6, 15, 10, 0, "男")
    f = bazi.build_bazi(2000, 6, 15, 10, 0, "女")
    assert m["pillars"]["year"]["ganzhi"] == "庚辰" and m["pillars"]["month"]["ganzhi"] == "壬午"
    assert m["dayun"]["forward"] and not f["dayun"]["forward"]
    assert m["dayun"]["list"][0]["ganzhi"] == "癸未" and f["dayun"]["list"][0]["ganzhi"] == "辛巳"
    # 順行距下一節（小暑）、逆行距上一節（芒種）
    assert m["dayun"]["from_jie"] == "小暑" and f["dayun"]["from_jie"] == "芒種"


def test_bazi_against_reference():
    cases = _load("bazi_cases.json")
    assert len(cases) >= 100
    for c in cases:
        y, m, d, h, mi, g = c["i"]
        r = bazi.build_bazi(y, m, d, h, mi, "男" if g else "女")
        P = r["pillars"]
        assert [P[k]["ganzhi"] for k in bazi.PILLAR_KEYS] == c["p"], c["i"]
        assert [P["year"]["shishen"], P["month"]["shishen"], P["hour"]["shishen"]] == c["sg"], c["i"]
        assert ["".join(x["gan"] for x in P[k]["canggan"]) for k in bazi.PILLAR_KEYS] == c["hg"], c["i"]
        assert [",".join(x["shishen"] for x in P[k]["canggan"]) for k in bazi.PILLAR_KEYS] == c["sz"], c["i"]
        assert [P[k]["dishi"] for k in bazi.PILLAR_KEYS] == c["ds"], c["i"]
        assert [P[k]["nayin"] for k in bazi.PILLAR_KEYS] == c["ny"], c["i"]
        assert "".join(r["xunkong"]) == c["xk"], c["i"]
        D = r["dayun"]
        assert int(D["forward"]) == c["fw"], c["i"]
        o = D["start_offset"]
        mine = o["years"] * 4320 + o["months"] * 360 + o["days"] * 12 + o["hours"] // 2
        ref = c["st"][0] * 4320 + c["st"][1] * 360 + c["st"][2] * 12 + c["st"][3] // 2
        assert abs(mine - ref) <= 3, c["i"]            # 節氣時刻容許 ±3 分鐘
        assert [x["ganzhi"] for x in D["list"]] == [x[0] for x in c["dy"]], c["i"]
        gap = abs((datetime.date.fromisoformat(D["start_date"])
                   - datetime.date.fromisoformat(c["ss"])).days)
        assert gap <= 1, c["i"]
        if gap == 0:
            assert [x["start_year"] for x in D["list"]] == [x[1] for x in c["dy"]], c["i"]


def test_bazi_night_zi_against_reference():
    """23 時出生、日柱算當日的兩種策略：四柱對照（時干以次日日干起）。"""
    cases = _load("bazi_night_zi.json")
    assert len(cases) >= 50
    for c in cases:
        for policy in ("midnight_00", "split_zi"):
            r = bazi.build_bazi(*c["i"], "男", day_boundary=policy)
            assert [r["pillars"][k]["ganzhi"] for k in bazi.PILLAR_KEYS] == c["p"], (c["i"], policy)


# ── 紫微斗數 ─────────────────────────────────────────────
def test_ziwei_position_table():
    # 土五局：初一在午、初五在寅、廿一在戌；水二局：初一在丑、初二在寅
    z = lambda ju, day: C.DIZHI[ziwei.ziwei_position(ju, day)]
    assert z(5, 1) == "午" and z(5, 5) == "寅" and z(5, 21) == "戌"
    assert z(2, 1) == "丑" and z(2, 2) == "寅" and z(2, 30) == "辰"
    assert z(6, 1) == "酉" and z(6, 6) == "寅"


def test_ziwei_structure():
    r = ziwei.build_ziwei(1990, 5, 15, 8, 30, "女", horoscope_years=[2026])
    assert r["lunar"]["text"] == "庚午年四月廿一" and r["hour_branch"] == "辰"
    assert r["ming_branch"] == "丑" and r["shen_branch"] == "酉" and r["ju_name"] == "火六局"
    assert [p["name"] for p in r["palaces"]] == ziwei.PALACE_NAMES
    names = [s["name"] for p in r["palaces"] for s in p["major"]]
    assert sorted(names) == sorted(ziwei.MAJOR_STARS)           # 十四主星各出現一次
    assert sum(len(p["minor"]) for p in r["palaces"]) == 14
    # 庚年四化：陽武陰同
    assert [(x["hua"], x["star"]) for x in r["natal_hua"]] == [
        ("祿", "太陽"), ("權", "武曲"), ("科", "太陰"), ("忌", "天同")]
    assert not r["decadal_forward"]                               # 陽女逆行
    h = r["horoscope"][0]
    assert h["age"] == 37 and h["decadal"]["ganzhi"] == "丙戌" and h["yearly"]["ganzhi"] == "丙午"


def test_ziwei_late_zi_and_leap():
    # 晚子時：預設算次日；midnight_00 算當日
    a = ziwei.build_ziwei(2024, 2, 9, 23, 30, "男")              # 除夕 23:30 → 次日為甲辰年正月初一
    b = ziwei.build_ziwei(2024, 2, 9, 23, 30, "男", day_boundary="midnight_00")
    assert a["lunar"]["year_ganzhi"] == "甲辰" and a["lunar"]["day"] == 1
    assert b["lunar"]["year_ganzhi"] == "癸卯" and b["lunar"]["month"] == 12
    # 閏月：十五日（含）前歸本月，十六日起歸下月
    early = ziwei.build_ziwei(2023, 3, 30, 12, 0, "女")          # 閏二月初九
    late = ziwei.build_ziwei(2023, 4, 10, 12, 0, "女")           # 閏二月二十
    assert early["lunar"]["is_leap"] and early["lunar"]["month_used"] == 2
    assert late["lunar"]["is_leap"] and late["lunar"]["month_used"] == 3
    assert ziwei.build_ziwei(2023, 4, 10, 12, 0, "女", fix_leap=False)["lunar"]["month_used"] == 2


def test_ziwei_against_reference():
    cases = _load("ziwei_cases.json")
    assert len(cases) >= 100
    hours = [0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]       # 時辰索引 0–12 → 代表小時
    fmt = lambda xs: set(x["name"] + ":" + (x["brightness"] or "") + (":" + x["hua"] if x["hua"] else "")
                         for x in xs)
    for c in cases:
        y, m, d, ti, g = c["i"]
        e = c["h"]
        r = ziwei.build_ziwei(y, m, d, hours[ti], 0, "男" if g else "女", horoscope_years=[e["y"]])
        assert (r["ming_branch"], r["shen_branch"], r["ju_name"]) == (c["mb"], c["sb"], c["ju"]), c["i"]
        assert (r["soul_star"], r["body_star"]) == (c["so"], c["bo"]), c["i"]
        assert r["lunar"]["year_ganzhi"] == c["cd"][:2], c["i"]
        mine = {p["branch"]: p for p in r["palaces"]}
        for s in c["pal"]:
            gz, name, body, major, minor, rng = s.split("|")
            p = mine[gz[1]]
            assert (p["ganzhi"], p["name"], int(p["is_body"])) == (gz, name, int(body)), c["i"]
            assert fmt(p["major"]) == set(filter(None, major.split(";"))), (c["i"], gz)
            assert fmt(p["minor"]) == set(filter(None, minor.split(";"))), (c["i"], gz)
            assert f"{p['decadal']['start']}-{p['decadal']['end']}" == rng, (c["i"], gz)
        h = r["horoscope"][0]
        assert h["age"] == e["age"] and h["yearly"]["ganzhi"] == e["ygz"], c["i"]
        assert ",".join(x["star"] for x in h["yearly"]["hua"]) == e["ym"], c["i"]
        if h["decadal"]:                                          # 童限（未起運）不比對
            assert h["decadal"]["ganzhi"] == e["dgz"], c["i"]
            assert ",".join(x["star"] for x in h["decadal"]["hua"]) == e["dm"], c["i"]


# ── 組裝與渲染 ───────────────────────────────────────────
def test_mingpan_build_and_render():
    mp = mingpan.build_mingpan((1990, 5, 15, 8, 30), "f", years=[2027, 2026, 2026])
    assert mp["years"] == [2026, 2027] and mp["birth"]["gender"] == "女"
    assert [x["year"] for x in mp["bazi"]["liunian"]] == [2026, 2027]
    text = render_mingpan.render_mingpan_text(mp)
    for token in ("【八字】", "【大運】", "【流年】", "【紫微斗數】", "【大限流年】", "火六局"):
        assert token in text
    only = mingpan.build_mingpan((1990, 5, 15, 8, 30), "女", systems=("bazi",))
    assert "ziwei" not in only and "【紫微斗數】" not in render_mingpan.render_mingpan_text(only)
    json.dumps(mp, ensure_ascii=False)                            # 可序列化


def test_mingpan_rejects_bad_input():
    for bad in (lambda: mingpan.build_mingpan((1990, 5, 15, 8, 30), "x"),
                lambda: mingpan.build_mingpan((1990, 5, 15, 8, 30), "男", systems=("tarot",)),
                lambda: ziwei.build_ziwei(1850, 5, 15, 8, 30, "男")):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("應拋出 ValueError")


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for f in funcs:
        try:
            f()
            print(f"PASS  {f.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {f.__name__}: {e!r}")
        except Exception as e:
            print(f"ERROR {f.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(funcs)} passed")
    sys.exit(0 if passed == len(funcs) else 1)
