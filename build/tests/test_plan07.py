"""Plan 07: bottle shells cut from the sheet, counter picks, burger layers and the E06 parity check."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from liquid import burger as burger_mod
from liquid import counter as counter_mod
from liquid import scene as scene_mod
from liquid import shells as shells_mod
from liquid.common import Issues

SHIP = Path(__file__).resolve().parents[2]


def real_scene():
    return json.loads((SHIP / "content" / "scene.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ shells

def _sheet(path: Path):
    """A black sheet with a solid green bottle shape and a clear glass outline."""
    im = Image.new("RGB", (400, 300), (0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([60, 40, 120, 250], fill=(30, 120, 40))              # opaque bottle
    d.rectangle([230, 60, 330, 250], outline=(235, 235, 235), width=2)  # glass: only its outline is lit
    im.save(path)


def _cfg():
    return {"version": 1, "source": "shells-sheet", "shells": {
        "sake": {"cell": 1, "mode": "opaque", "crop": [50, 30, 130, 260], "labelSheet": [66, 120, 114, 200], "labelBlend": "multiply"},
        "spirits": {"cell": 2, "mode": "glass", "crop": [220, 50, 340, 260], "labelSheet": [250, 130, 310, 200], "labelBlend": "normal"},
        "liqueur": {"cell": 2, "mode": "glass", "tintAmber": True, "liquidTop": 0.2, "crop": [220, 50, 340, 260],
                    "labelSheet": [250, 130, 310, 200], "labelBlend": "normal"},
    }}


def test_shells_are_cut_clean_translucent_and_the_sheet_is_never_published(tmp_path):
    src, docs, cache = tmp_path / "scene", tmp_path / "docs", tmp_path / "c.json"
    src.mkdir()
    _sheet(src / "shells-sheet.png")
    info, _, stats = scene_mod.convert(src, docs, cache, shells_cfg=_cfg())
    assert set(info["shells"]) == {"sake", "spirits", "liqueur"} and stats["encoded"] == 6
    out = docs / "img" / "scene"
    with Image.open(out / "shell-sake@2x.webp") as im:
        assert im.mode == "RGBA" and im.size == (80, 230) and not im.getexif()
        a = np.asarray(im)[..., 3]
    assert a[2, 2] == 0 and a[-3, 3] == 0                              # corners are transparent: the black is gone
    assert a[115, 40] == 255                                           # the body is solid
    with Image.open(out / "shell-sake@1x.webp") as im:
        assert im.size == (40, 115)
    # clear glass keeps partial transparency: the empty middle is almost see-through, the lit rim is not
    with Image.open(out / "shell-spirits@2x.webp") as im:
        g = np.asarray(im)[..., 3]
    assert g[100, 60] < 40 and g[10, 60] > 180
    # liqueur is the same glass with an amber fill: more opaque and warmer in the liquid
    with Image.open(out / "shell-liqueur@2x.webp") as im:
        l = np.asarray(im)
    assert l[150, 60, 3] > g[150, 60] + 60 and l[150, 60, 0] > l[150, 60, 2]
    # the label rectangle comes out as fractions of the shell, the sake one multiplies, and the originals stay out of docs
    sake = info["shells"]["sake"]
    assert sake["labelRect"] == [0.2, 0.3913, 0.6, 0.3478] and sake["labelBlend"] == "multiply"
    assert not list(docs.rglob("shells-sheet*"))
    _, _, again = scene_mod.convert(src, docs, cache, shells_cfg=_cfg())
    assert again["encoded"] == 0 and again["skipped"] == 6


def test_shells_polygon_is_trusted_over_the_picture(tmp_path):
    cfg = _cfg()["shells"]["sake"]
    cfg["maskPolygon"] = [[10, 10], [70, 10], [70, 100], [10, 100]]
    _sheet(tmp_path / "s.png")
    with Image.open(tmp_path / "s.png") as im:
        out = np.asarray(shells_mod.cut_cell(im.convert("RGB"), cfg))
    assert out[50, 40, 3] > 200 and out[150, 40, 3] == 0              # the hand-made polygon wins: the lower body is cut


# ------------------------------------------------------------------ counter picks

def _drink(i, name, cat="sake", styles=(), story="", abv=15.0, fav=False, visits=None, typ=None):
    return {"id": f"d{i}", "name": name, "category": cat, "sub": "x", "styles": list(styles), "story": story, "abv": abv,
            "favourite": fav, "visits": visits or [{"date": None, "_row": i}],
            "detail": {"Other Detail": {"Type": typ}} if typ else {}}


CFG = {"keywords": {"spring": ["haru"], "summer": ["yuzu", "Lager"], "autumn": ["aki", "kimoto"], "winter": ["Stout/Porter"]},
       "summerAbvMax": 13, "recentWindow": 3, "maxPerCategory": 2, "pins": {}, "exclude": []}


def test_new_arrivals_rank_by_latest_occasion_with_ties_to_the_later_row():
    ds = [_drink(1, "A", visits=[{"date": "2026-10-01", "_row": 2}]),
          _drink(2, "B", visits=[{"date": "2026-10-01", "_row": 9}]),            # same day, later row: ahead of A
          _drink(3, "C", visits=[{"date": "2026-01-01", "_row": 3}, {"date": "2026-10-20", "_row": 30}]),   # a repeat visit
          _drink(4, "D"), _drink(5, "E"), _drink(6, "F")]
    got = [d["id"] for d in counter_mod.rank_recent(ds)]
    assert got[:3] == ["d3", "d2", "d1"] and len(set(got)) == len(got)
    c, _ = counter_mod.build_counter(ds, {}, CFG, Issues())
    assert [x["id"] for x in c["newArrivals"]] == got[:5]


def test_season_picks_match_whole_words_cap_categories_and_honour_pins_and_exclude():
    ds = [_drink(1, "Akita Honjozo"),                                         # 'aki' must not match inside 'Akita'
          _drink(2, "Aki Kimoto", fav=True), _drink(3, "Kimoto Two"), _drink(4, "Kimoto Three"),
          _drink(5, "Kimoto Beer", cat="beer"), _drink(6, "Plain", abv=16), _drink(7, "Light", cat="wine", abv=11),
          _drink(8, "Stout", cat="beer", typ="Stout"), _drink(9, "Pale", styles=["Haru nigori"])]
    issues = Issues()
    picks = counter_mod.season_picks(ds, {}, CFG, issues)
    autumn = [p[0]["id"] for p in picks["autumn"]]
    assert "d1" not in autumn[:4] and autumn[0] == "d2"                       # the favourite match leads
    assert sum(1 for p in picks["autumn"] if p[0]["category"] == "sake") <= 3  # 2 matches + a filler at most; cap is 2 first
    assert [p[0]["id"] for p in picks["autumn"][:4]].count("d3") <= 1
    assert "ABV 11%" in next(p for p in picks["summer"] if p[0]["id"] == "d7")[2]     # low ABV counts as a summer match
    assert "d8" in [p[0]["id"] for p in picks["winter"]]                       # 'Stout/Porter' is two keywords
    assert all(len(picks[s]) == 5 for s in counter_mod.SEASONS)
    cfg = {**CFG, "pins": {"autumn": ["d6", "nope"]}, "exclude": ["d2"]}
    issues = Issues()
    picks = counter_mod.season_picks(ds, {}, cfg, issues)
    ids = [p[0]["id"] for p in picks["autumn"]]
    assert ids[0] == "d6" and "d2" not in ids and any(i["code"] == "W22" for i in issues.items)


def test_seasonal_config_is_validated():
    ok = Issues()
    cfg = json.loads((SHIP / "content" / "seasonal.json").read_text(encoding="utf-8"))
    assert counter_mod.validate_seasonal(cfg, ok) and not ok.errors
    bad = Issues()
    assert not counter_mod.validate_seasonal({"keywords": {"spring": []}, "maxPerCategory": 0}, bad)
    assert all(e["code"] == "E04" for e in bad.errors) and len(bad.errors) == 2


# ------------------------------------------------------------------ burger

def _burger_src(path: Path):
    im = Image.new("RGB", (300, 400), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, col in enumerate([(200, 120, 40), (60, 160, 50), (130, 60, 40), (220, 170, 90)]):
        d.rectangle([60, 40 + i * 80, 240, 40 + i * 80 + 76], fill=col)
    im.save(path)


def _burger_cfg():
    return {"source": "burger", "options": [{"key": k, "label": k.title()} for k in ("bar", "shelves", "makers", "about")],
            "cuts": [[[0, 118], [300, 118]], [[0, 198], [300, 198]], [[0, 278], [300, 278]]],
            "plateSplit": [[40, 280], [260, 280], [260, 360], [40, 360]],
            "mask": {"splitY": 400, "thresholdTop": 16, "thresholdBottom": 46, "plate": {"cx": 150, "cy": 340, "rx": 130, "ry": 30},
                     "burgerX": [20, 280], "plateTop": 380, "bunX": [20, 280], "bunBottom": 380}}


def test_burger_splits_into_one_layer_per_option_in_order(tmp_path):
    _burger_src(tmp_path / "burger.png")
    cfg = _burger_cfg()
    assert burger_mod.validate(cfg, Issues())
    res = burger_mod.cut(tmp_path / "burger.png", cfg)
    assert len(res["layers"]) == 4
    tops = [bb[1] for bb, _ in res["layers"]]
    assert tops == sorted(tops) and tops[0] <= 45 and 195 <= tops[2] <= 202   # top first, cut where the cuts are
    assert [round(c) for c in res["centres"]] == sorted(round(c) for c in res["centres"])
    # layers never overlap by more than the 1 px that hides the seam
    (_, _, _, b0), (_, y1, _, _) = res["layers"][0][0], res["layers"][1][0]
    assert b0 - y1 <= 2
    files = {f"layer{i}": {"1x": f"a{i}", "2x": f"b{i}"} for i in range(4)} | {"plate": {"1x": "p", "2x": "q"}}
    m = burger_mod.manifest(res, cfg, files)
    assert [l["key"] for l in m["layers"]] == ["bar", "shelves", "makers", "about"] and m["layers"][0]["cy"] < m["layers"][3]["cy"]
    for bad in ({"cuts": cfg["cuts"][:2]}, {"cuts": [cfg["cuts"][1], cfg["cuts"][0], cfg["cuts"][2]]}, {"options": cfg["options"][:1]}):
        issues = Issues()
        assert not burger_mod.validate({**cfg, **bad}, issues) and issues.errors


# ------------------------------------------------------------------ parity (E06) and the real plates

def test_e06_fails_when_bar_tall_exists_without_phone_values():
    manifest = real_scene()
    info = {"plates": {"wide": {}, "tall": {}}}
    ok = Issues()
    assert scene_mod.check_parity(manifest, info, ok) and not ok.errors
    del manifest["plates"]["tall"]["counter"]
    bad = Issues()
    assert not scene_mod.check_parity(manifest, info, bad) and [e["code"] for e in bad.errors] == ["E06"]
    none = Issues()                                                         # no tall plate yet: nothing to enforce
    assert scene_mod.check_parity(manifest, {"plates": {"wide": {}}}, none) and not none.errors


def test_real_scene_has_matching_desktop_and_phone_features_and_valid_content():
    m = real_scene()
    issues = Issues()
    assert scene_mod.validate_manifest(m, issues) and not issues.errors
    wide, tall = m["plates"]["wide"]["counter"], m["plates"]["tall"]["counter"]
    assert set(wide) - {"shelfX"} <= set(tall) | {"mode"}                   # every desktop counter value has a phone value
    assert len(m["plates"]["tall"]["shelves"]) == 3 and tall["mode"] == "tabs"
    cfg = json.loads((SHIP / "content" / "burger.json").read_text(encoding="utf-8"))
    assert burger_mod.validate(cfg, Issues())


# ------------------------------------------------------------------ chalkboards (sections 9 and 10)

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _blend(fg, bg, a):
    return tuple(f * a + b * (1 - a) for f, b in zip(fg, bg))


def _lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_chalk_on_slate_is_readable_at_every_size_and_state():
    css = (SHIP / "docs" / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    chalk = _rgb(re.search(r"--chalk:\s*(#[0-9a-fA-F]{6})", css).group(1))
    glow = _rgb(re.search(r"--glow:\s*(#[0-9a-fA-F]{6})", css).group(1))
    slate = _rgb(re.search(r"#262a28", css).group(0))
    # the faint chalk smudges lighten the slate a little: test against the worst case, the strongest smudge (6%)
    worst = _blend(chalk, slate, 0.06)
    cases = {"chalk (L, M and S boards)": 1.0, "Soon at 65%": 0.65, "counts at 70%": 0.7, "inactive tab at 75%": 0.75,
             "unavailable tag at 55%": 0.55}
    small = _blend(chalk, slate, 0.03)                          # S boards carry half-strength smudges (peak 3%)
    for name, alpha in cases.items():
        for ground, label in ((slate, "slate"), (worst if alpha > 0.55 else small, "slate with smudge")):
            r = _ratio(_blend(chalk, ground, alpha), ground)
            assert r >= 4.5, f"{name} on {label}: {r:.2f}:1"
    for ground in (slate, worst):
        assert _ratio(glow, ground) >= 4.5
        for body in ("#e6dfd3", "#d2c8b8"):                                     # About body text and credits
            assert _ratio(_rgb(body), ground) >= 4.5
    assert re.search(r"font-family: 'Kalam'; font-style: normal; font-weight: 700", css) and "fonts.googleapis" not in css


def test_kalam_is_self_hosted_with_its_licence():
    fonts = SHIP / "docs" / "assets" / "fonts"
    for w in (400, 700):
        for sub in ("latin", "latin-ext"):
            assert (fonts / f"Kalam-{w}-{sub}.woff2").read_bytes()[:4] == b"wOF2"
    assert "Indian Type Foundry" in (fonts / "OFL-kalam.txt").read_text(encoding="utf-8")
    html = (SHIP / "docs" / "index.html").read_text(encoding="utf-8")
    assert "fonts.googleapis" not in html and "fonts.gstatic" not in html


def test_browser_smoke_test_passes_at_all_four_sizes():
    """Real browser: tags, captions, counter bottles, the burger boards at opacity 1 after a real open (tools/smoke.py)."""
    sys.path.insert(0, str(SHIP / "build" / "tools"))
    import smoke
    if not smoke.edge_path():
        pytest.skip("no Edge or Chrome to run the smoke test")
    with smoke.Server() as srv:
        for w, h in smoke.SIZES:
            res = smoke.check_size(srv.port, w, h)
            assert res["ok"], f"{w}x{h}: {res['problems'][:5]}"


# ------------------------------------------------------------------ Plan 08: the inner pages in a real browser

def test_phase_2_inner_pages_smoke_in_a_scratch_copy():
    """Builds Phase 2 in a scratch copy outside Ship/ and checks every inner page type at the four sizes (tools/smoke.py)."""
    sys.path.insert(0, str(SHIP / "build" / "tools"))
    import smoke
    pytest.importorskip("websockets")
    if not smoke.edge_path():
        pytest.skip("no Edge or Chrome to run the smoke test")
    if not (SHIP.parent / "Drinks Ledger.xlsx").exists():
        pytest.skip("real ledger not available")
    docs = smoke.make_preview()
    assert docs is not None
    smoke.DOCS = docs
    import smoke_inner
    with smoke.Server() as srv:
        problems, _ = smoke_inner.run(f"http://127.0.0.1:{srv.port}")
        smoke.DOCS = SHIP / "docs"
    assert not problems, problems[:8]
