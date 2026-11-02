"""Scene engine build step, pre-flight audit and contrast (Plan 01 sections 7.5 and 7.6)."""
import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

from fixture import make_project
from liquid import scene as scene_mod
from liquid.common import Issues
from liquid.pipeline import run

SHIP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SHIP / "build" / "tools"))


def manifest():
    m = json.loads((SHIP / "content" / "scene.json").read_text(encoding="utf-8"))
    m["shells"] = {"sake": {"labelRect": [0.17, 0.62, 0.66, 0.26]}}      # an individually delivered shell file (legacy path)
    return m


def shells_cfg():
    return json.loads((SHIP / "content" / "shells.json").read_text(encoding="utf-8"))


def test_scene_manifest_is_valid_and_bad_ones_are_rejected():
    issues = Issues()
    assert scene_mod.validate_manifest(manifest(), issues) and not issues.errors
    m = manifest()
    m["plates"]["wide"]["shelves"][0]["clear"] = 0.9          # taller than the shelf's own height
    del m["plates"]["tall"]["anchors"]["menu"]
    m["shells"]["sake"]["labelRect"] = [0.1, 0.2]
    bad = Issues()
    assert not scene_mod.validate_manifest(m, bad)
    assert len(bad.errors) == 3 and all(e["code"] == "E04" for e in bad.errors)


def test_shells_config_is_valid_and_bad_ones_are_rejected():
    issues = Issues()
    assert scene_mod.validate_shells(shells_cfg(), issues) and not issues.errors
    cfg = shells_cfg()
    cfg["shells"]["wine"]["mode"] = "shiny"
    cfg["shells"]["beer"]["labelSheet"] = [0, 0, 10, 10]               # outside the crop
    cfg["shells"]["sake"]["maskPolygon"] = [[1, 2]]
    bad = Issues()
    assert not scene_mod.validate_shells(cfg, bad)
    assert len(bad.errors) == 3 and all(e["code"] == "E04" for e in bad.errors)


def _write_scene(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    wide = Image.new("RGB", (1000, 562), (138, 75, 56))
    wide.save(folder / "bar-wide.png")
    Image.new("RGB", (300, 650), (138, 75, 56)).save(folder / "bar-tall.png")
    shell = Image.new("RGBA", (200, 600), (0, 0, 0, 0))
    shell.paste((30, 60, 30, 255), (60, 20, 140, 600))
    shell.save(folder / "shell-sake.png")


def test_convert_makes_avif_webp_and_shells_without_metadata_and_cleans_up(tmp_path):
    src, docs, cache = tmp_path / "scene", tmp_path / "docs", tmp_path / "cache.json"
    _write_scene(src)
    info, sigs, stats = scene_mod.convert(src, docs, cache)
    assert stats["encoded"] == 2 * 2 + 2 and set(info["plates"]) == {"wide", "tall"} and set(info["shells"]) == {"sake"}
    out = docs / "img" / "scene"
    for name in ("bar-wide-1000.avif", "bar-wide-1000.webp", "bar-tall-300.webp", "shell-sake@1x.webp", "shell-sake@2x.webp"):
        assert (out / name).exists(), name            # never upscaled: widths are capped at the source width
    with Image.open(out / "shell-sake@1x.webp") as im:
        assert im.mode == "RGBA" and im.height == 512 and not im.getexif()
    with Image.open(out / "bar-wide-1000.avif") as im:
        assert "exif" not in im.info and "icc_profile" not in im.info
    merged = scene_mod.merge(manifest(), info)
    assert merged["ready"] is True and merged["plates"]["wide"]["ratio"] == pytest.approx(1000 / 562, rel=1e-3)
    assert merged["shells"]["sake"]["labelRect"] == manifest()["shells"]["sake"]["labelRect"]
    # second run encodes nothing; removing the sources deletes the outputs
    _, _, again = scene_mod.convert(src, docs, cache)
    assert again["encoded"] == 0 and again["skipped"] == 6
    (src / "shell-sake.png").unlink()
    _, _, gone = scene_mod.convert(src, docs, cache)
    assert gone["deleted"] == 2 and not (out / "shell-sake@1x.webp").exists()


def test_not_ready_without_plates(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "scene.json").write_text((SHIP / "content" / "scene.json").read_text(encoding="utf-8"), encoding="utf-8")
    res = run(ship, scene_dir=tmp_path / "Design" / "scene")           # folder absent: the v2 scene stays
    assert res.exit_code == 0
    data = json.loads((ship / "docs" / "data" / "scene.json").read_text(encoding="utf-8"))
    assert data["ready"] is False and "files" not in data["plates"]["wide"]
    assert any(i["code"] == "I02" for i in res.issues.items)
    # with plates, the page data says ready and the originals are never copied into the site
    _write_scene(tmp_path / "Design" / "scene")
    res = run(ship, scene_dir=tmp_path / "Design" / "scene")
    data = json.loads((ship / "docs" / "data" / "scene.json").read_text(encoding="utf-8"))
    assert data["ready"] is True
    assert not list((ship / "docs").rglob("bar-wide.png")) and not list((ship / "docs").rglob("shell-sake.png"))


def test_no_em_or_en_dashes_in_visible_site_text():
    from preflight import scan
    assert scan(SHIP) == []


def _hex(v):
    v = v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _lum(rgb):
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((_lum(_hex(a)), _lum(_hex(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _tokens(block):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def test_every_chalk_style_is_at_least_4_5_to_1_on_the_slate():
    """Plan 08 section 3.4: every chalk style, at its real opacity, on the slate under the strongest chalk smudge."""
    css = (SHIP / "docs" / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    tokens = _tokens(css)
    chalk, glow, slate = _hex_i(tokens["chalk"]), _hex_i(tokens["glow"]), _hex_i(tokens["slate"])
    smudge = {"XL": 0.10, "L and M": 0.06, "S": 0.03}                 # XL smudges are scaled 1.4 (--sm), S are halved
    styles = {"chalk": (chalk, 1.0), "glow chalk (links, selected)": (glow, 1.0), "small print and 75% terms": (chalk, 0.75),
              "counts at 70%": (chalk, 0.70), "disabled chip at 65%": (chalk, 0.65), "search placeholder at 65%": (chalk, 0.65),
              "data at 88%": (chalk, 0.88)}
    for board, k in smudge.items():
        ground = _mix(chalk, slate, k)
        for name, (colour, alpha) in styles.items():
            if board == "S" and name.startswith("small print"):
                continue
            r = _ratio_i(_mix(colour, ground, alpha), ground)
            assert r >= 4.5, f"{name} on a {board} board: {r:.2f}:1"
    # the sizes the plan sets as floors are really in the stylesheet
    assert re.search(r"\.t-body \{ font: 400 17px/1\.6", css) and re.search(r"\.t-small \{ font: 400 14px", css)
    body = re.search(r"\.t-body \{[^}]*\}", css).group(0)
    assert "mask" not in body                                         # body text has no grain mask


def _hex_i(v):
    v = v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _mix(fg, bg, a):
    return tuple(f * a + b * (1 - a) for f, b in zip(fg, bg))


def _ratio_i(a, b):
    la, lb = sorted((_lum([c / 255 for c in a]), _lum([c / 255 for c in b])), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_content_top_is_required_on_both_plates_and_below_the_sign():
    issues = Issues()
    assert scene_mod.validate_manifest(manifest(), issues) and not issues.errors
    m = manifest()
    del m["plates"]["tall"]["content_top"]                            # a phone value is missing
    m["plates"]["wide"]["content_top"] = 0.1                          # above the sign's bottom edge: the first board would cover it
    bad = Issues()
    assert not scene_mod.validate_manifest(m, bad)
    assert sum("content_top" in e["message"] for e in bad.errors) == 2
    # the published scene.json carries it for both plates
    out = scene_mod.merge(manifest(), {"plates": {}, "shells": {}})
    assert out["plates"]["wide"]["content_top"] == 0.25 and out["plates"]["tall"]["content_top"] == 0.308
    parity = Issues()
    tall_missing = manifest()
    del tall_missing["plates"]["tall"]["content_top"]
    assert not scene_mod.check_parity(tall_missing, {"plates": {"tall": {}}}, parity)
    assert parity.errors and parity.errors[0]["code"] == "E06"


def test_only_kalam_is_served_and_no_other_font_is_named_in_the_site():
    docs = SHIP / "docs"
    assert sorted(p.name for p in (docs / "assets" / "fonts").iterdir()) == sorted(
        ["Kalam-400-latin-ext.woff2", "Kalam-400-latin.woff2", "Kalam-700-latin-ext.woff2", "Kalam-700-latin.woff2", "OFL-kalam.txt"])
    text = "".join(p.read_text(encoding="utf-8") for p in (docs / "assets").rglob("*") if p.suffix in (".css", ".js"))
    text += (docs / "index.html").read_text(encoding="utf-8")
    for name in ("Outfit", "Cormorant", "Stardos", "Rye"):
        assert name not in text, name
    assert "Type: Kalam (SIL Open Font Licence)" in text
