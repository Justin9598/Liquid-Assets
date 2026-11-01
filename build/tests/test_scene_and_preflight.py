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
    return json.loads((SHIP / "content" / "scene.json").read_text(encoding="utf-8"))


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


def test_text_contrast_is_at_least_4_5_to_1_in_both_themes():
    css = (SHIP / "docs" / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    cut = css.index("@media (prefers-color-scheme: dark)")
    light = _tokens(css[:cut])
    dark_block = css[cut:]
    dark = {**light, **_tokens(dark_block)}
    pairs = [("ink", "paper"), ("ink2", "paper"), ("link", "paper"), ("ink", "oak-soft"), ("ink2", "oak-soft"),
             ("link", "oak-soft"), ("brass-dark", "paper"), ("chalk", "iron")]
    for name, tokens in (("light", light), ("dark", dark)):
        for fg, bg in pairs:
            r = ratio(tokens[fg], tokens[bg])
            assert r >= 4.5, f"{name}: --{fg} on --{bg} is only {r:.2f}:1"
    # the menu overlay: chalk and glow on the dark-oak panel, muted counts too
    for fg in ("#f2ede4", "#f4c27a", "#d2c8b8", "#e6dfd3"):
        assert ratio(fg, "#2a1e14") >= 4.5 and ratio(fg, "#3a2a1b") >= 4.5
    # oak panels (hero text boards): secondary text and links on the darkest point of the gradient
    assert ratio('#3b2f24', '#c9a172') >= 4.5 and ratio('#2a1d14', '#c9a172') >= 4.5
    assert ratio('#cfc4b3', '#3a2a1b') >= 4.5 and ratio('#f0c27a', '#3a2a1b') >= 4.5
    # slate tags: off-white on iron
    assert ratio("#cfc6b8", light["iron"]) >= 4.5
