"""核心引擎驗收測試。執行：python -m pytest 或 python tests/test_engine.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import constants as C
from engine import ganzhi as gz
from engine import bagua
from engine import cast
from engine import zhuanggua as zg


def test_day_pillar_anchors():
    assert gz.compute_sizhu(2000, 1, 7, 12)["day_pillar"] == "甲子"
    assert gz.compute_sizhu(2000, 1, 1, 12)["day_pillar"] == "戊午"  # 修正：非甲辰
    assert gz.compute_sizhu(2026, 6, 13, 12)["day_pillar"] == "戊午"


def test_today_full():
    r = gz.compute_sizhu(2026, 6, 13, 14, 32)
    assert r["year_pillar"] == "丙午"
    assert r["month_pillar"] == "甲午"
    assert r["day_pillar"] == "戊午"
    assert r["hour_pillar"] == "己未"
    assert r["month_branch"] == "午" and r["month_wuxing"] == "火"
    assert r["xunkong"] == ("子", "丑")


def _boundary_pillars(year, term):
    """取引擎自算之節氣地方時刻，回傳該時刻前/後一分鐘之四柱（自洽測試，
    不依賴外部硬編碼分鐘，CSV 覆蓋或 VSOP 皆可）。"""
    import datetime
    from engine import solar_terms as st
    jd = st.term_local_jd(year, term, 8.0)
    y, mo, d, h, mi = st.gregorian_from_jd(jd)
    t = datetime.datetime(y, mo, d, h, mi)
    b = t - datetime.timedelta(minutes=1)
    a = t + datetime.timedelta(minutes=1)
    return (gz.compute_sizhu(b.year, b.month, b.day, b.hour, b.minute),
            gz.compute_sizhu(a.year, a.month, a.day, a.hour, a.minute))


def test_lichun_boundary():
    before, after = _boundary_pillars(2026, "立春")  # 立春換年又換月
    assert before["year_pillar"] == "乙巳" and before["month_branch"] == "丑"
    assert after["year_pillar"] == "丙午" and after["month_branch"] == "寅"


def test_mangzhong_boundary():
    before, after = _boundary_pillars(2026, "芒種")  # 芒種換月（巳→午）
    assert before["month_branch"] == "巳" and before["month_pillar"] == "癸巳"
    assert after["month_branch"] == "午" and after["month_pillar"] == "甲午"


def test_day_boundary():
    z23 = gz.compute_sizhu(2026, 6, 13, 23, 30, day_boundary="zi_initial_23")
    mid = gz.compute_sizhu(2026, 6, 13, 23, 30, day_boundary="midnight_00")
    assert z23["day_pillar"] == "己未"   # 進次日
    assert mid["day_pillar"] == "戊午"   # 不換


def test_xunkong():
    assert C.xunkong(0) == ("戌", "亥")    # 甲子旬
    assert C.xunkong(10) == ("申", "酉")   # 甲戌旬
    assert C.xunkong(54) == ("子", "丑")   # 甲寅旬（戊午）


def test_palace_index_complete():
    assert len(bagua.PALACE_INDEX) == 64
    # 火天大有 = 下乾(111)上離(101) → lines (1,1,1,1,0,1)
    assert bagua.hexagram_name((1, 1, 1, 1, 0, 1)) == "火天大有"
    # 但其屬乾宮歸魂：
    p = bagua.palace_info((1, 1, 1, 1, 0, 1))
    assert p[0] == "乾" and p[2] == "歸魂" and p[3] == 3
    # 山地剝 = 下坤(000)上艮(001) → (0,0,0,0,0,1)，乾宮五世
    assert bagua.hexagram_name((0, 0, 0, 0, 0, 1)) == "山地剝"
    assert bagua.palace_info((0, 0, 0, 0, 0, 1))[0:3] == ("乾", "金", "五世")
    # 地雷復 = 下震(100)上坤(000) → (1,0,0,0,0,0)，坤宮一世
    assert bagua.hexagram_name((1, 0, 0, 0, 0, 0)) == "地雷復"
    assert bagua.palace_info((1, 0, 0, 0, 0, 0))[0:3] == ("坤", "土", "一世")


def test_gua_transforms_gou():
    gou = (0, 1, 1, 1, 1, 1)  # 天風姤：下巽上乾
    assert bagua.hexagram_name(gou) == "天風姤"
    assert bagua.hexagram_name(bagua.hu_gua(gou)) == "乾為天"
    assert bagua.hexagram_name(bagua.cuo_gua(gou)) == "地雷復"
    assert bagua.hexagram_name(bagua.zong_gua(gou)) == "澤天夬"
    moving = (0, 1, 0, 0, 0, 0)  # 二爻動
    assert bagua.hexagram_name(bagua.bian_gua(gou, moving)) == "天山遯"


def test_zhuang_gou():
    gou = (0, 1, 1, 1, 1, 1)
    moving = (0, 0, 0, 0, 0, 0)
    res = zg.zhuang(gou, moving, day_gan="戊", day_zhi="午",
                    month_branch="午", xunkong=("子", "丑"))
    assert res["base"]["palace"] == "乾" and res["base"]["generation"] == "一世"
    assert res["shi"] == 1 and res["ying"] == 4
    expect = [
        (1, "父母", "辛", "丑", "土"),
        (2, "子孫", "辛", "亥", "水"),
        (3, "兄弟", "辛", "酉", "金"),
        (4, "官鬼", "壬", "午", "火"),
        (5, "兄弟", "壬", "申", "金"),
        (6, "父母", "壬", "戌", "土"),
    ]
    for y, (pos, lq, gan, zhi, wx) in zip(res["yaos"], expect):
        assert (y["pos"], y["liuqin"], y["gan"], y["zhi"], y["wuxing"]) == (pos, lq, gan, zhi, wx)
    # 妻財不上卦 → 伏神 妻財寅木 於二爻
    assert 2 in res["fushen"]
    assert res["fushen"][2]["liuqin"] == "妻財"
    assert res["fushen"][2]["zhi"] == "寅" and res["fushen"][2]["wuxing"] == "木"
    # 六獸：戊日起勾陳
    assert res["yaos"][0]["liushou"] == "勾陳"


def test_zhuang_moving_marks():
    gou = (0, 1, 1, 1, 1, 1)
    moving = (0, 1, 0, 0, 0, 0)  # 二爻動：亥水 → 遯之二爻
    res = zg.zhuang(gou, moving, day_gan="戊", month_branch="午", xunkong=("子", "丑"))
    assert res["changed"]["name"] == "天山遯"
    y2 = res["yaos"][1]
    assert y2["moving"] and "changed" in y2
    # 亥(水)化午(火)：午剋... 變爻午火, 本爻亥水 → 火被水剋?; 回頭? 午生? 檢查 marks 為 list
    assert isinstance(y2["changed"]["marks"], list)


def test_cast_distribution():
    import collections
    N = 60000
    cnt = collections.Counter()
    for _ in range(N):
        cnt[cast.cast_line()["name"]] += 1
    # 少陽=少陰≈3/8、老陽=老陰≈1/8，容差 ±0.02
    assert abs(cnt["少陽"] / N - 0.375) < 0.02
    assert abs(cnt["少陰"] / N - 0.375) < 0.02
    assert abs(cnt["老陽"] / N - 0.125) < 0.02
    assert abs(cnt["老陰"] / N - 0.125) < 0.02


def test_cast_face_values():
    assert cast.make_line(["背", "字", "字"])["name"] == "少陽"   # 1背=7
    assert cast.make_line(["背", "背", "字"])["name"] == "少陰"   # 2背=8
    assert cast.make_line(["背", "背", "背"])["name"] == "老陽"   # 3背=9
    assert cast.make_line(["字", "字", "字"])["name"] == "老陰"   # 0背=6


def test_gregorian_from_jd_rounding():
    """接近午夜的時刻四捨五入到分鐘時須正確進位到隔日（舊版會無限遞迴）。"""
    from engine import solar_terms as st
    for args in [(2026, 6, 13, 2, 19), (2000, 1, 1, 0, 0), (2024, 2, 29, 23, 59)]:
        y, m, d, h, mi = args
        assert st.gregorian_from_jd(st.jd_from_gregorian(y, m, d + (h * 60 + mi) / 1440.0)) == args
    late = (23 * 3600 + 59 * 60 + 45) / 86400.0                 # 23:59:45
    assert st.gregorian_from_jd(st.jd_from_gregorian(2026, 6, 13 + late)) == (2026, 6, 14, 0, 0)
    assert st.gregorian_from_jd(st.jd_from_gregorian(2026, 12, 31 + late)) == (2027, 1, 1, 0, 0)


def test_fuyin_fanyin_marks():
    # 火天大有 二、三爻動 → 火雷噬嗑：內卦乾化震，寅化寅、辰化辰 → 伏吟
    z = zg.zhuang((1, 1, 1, 1, 0, 1), (False, True, True, False, False, False),
                  day_gan="壬", day_zhi="寅", month_branch="亥", xunkong=("辰", "巳"))
    assert z["changed"]["name"] == "火雷噬嗑"
    assert "伏吟" in z["yaos"][1]["changed"]["marks"] and "伏吟" in z["yaos"][2]["changed"]["marks"]
    assert z["fuyin"] == ["內卦"] and z["fanyin"] == []
    # 坤為地 二、三爻動 → 內卦坤化巽：巳化亥、卯化酉 → 反吟
    z = zg.zhuang((0, 0, 0, 0, 0, 0), (False, True, True, False, False, False), day_gan="甲")
    assert "反吟" in z["yaos"][1]["changed"]["marks"] and "反吟" in z["yaos"][2]["changed"]["marks"]
    assert z["fanyin"] == ["內卦"] and z["fuyin"] == []
    # 一般動爻不標
    z = zg.zhuang((1, 1, 1, 1, 1, 1), (True, False, False, False, False, False), day_gan="甲")
    assert z["fuyin"] == [] and z["fanyin"] == []
    assert not {"伏吟", "反吟"} & set(z["yaos"][0]["changed"]["marks"])


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
