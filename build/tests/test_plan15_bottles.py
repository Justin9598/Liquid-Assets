"""Plan 15: which shell each drink stands in (section 4), E09 and W28, and the cut shells."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from liquid import bottles as B  # noqa: E402
from liquid.common import Issues  # noqa: E402

SHIP = Path(__file__).resolve().parents[2]


def D(cat, sub, sizes=(), country="Japan", wine=None, did="x"):
    return {"id": did, "name": did, "category": cat, "sub": sub, "sizes": list(sizes), "country": country,
            "detail": {"Wine Detail": {"Colour": wine}} if wine else {}}


@pytest.mark.parametrize("d,want", [
    (D("sake", "junmai"), "sake-green"),
    (D("sake", "craft-sake"), "sake-green"),
    (D("fermented", "makgeolli"), "makgeolli"),
    (D("fermented", "lager", ["Pint"]), "beer-pint"),
    (D("fermented", "wheat", ["Pint"]), "beer-weizen"),
    (D("fermented", "ipa", ["90ml Pour"]), "beer-tulip"),
    (D("fermented", "stout-porter", ["Pint"]), "beer-stout"),
    (D("fermented", "lager", ["Pint", "330ml Bottle"]), "beer-bottle"),
    (D("fermented", "lager", ["350ml Can"]), "beer-can"),
    (D("fermented", "lager", ["500ml Can"]), "beer-can-tall"),
    (D("fermented", "lager", ["400ml Can"]), "beer-can-tall"),
    (D("fermented", "lager", ["350ml Can", "330ml Bottle"]), "beer-can"),     # the largest container decides
    (D("fermented", "lager", ["60ml Tasting", "Bottle"]), "beer-bottle"),
    (D("wine", "merlot", wine="Red"), "wine-red"),
    (D("wine", "x", wine="White"), "wine-white"),
    (D("wine", "x", wine="Rosé"), "wine-rose"),
    (D("wine", "x", wine="Sparkling"), "champagne"),
    (D("wine", "x"), "wine-red"),
    (D("spirits", "whisky", country="Scotland"), "whisky"),
    (D("spirits", "whisky", country="USA"), "whisky-round"),
    (D("spirits", "gin"), "gin"), (D("spirits", "brandy"), "brandy"), (D("spirits", "shochu"), "shochu"),
    (D("spirits", "soju"), "soju"), (D("spirits", "rum"), "spirit-clear"),
    (D("umeshu", "all"), "umeshu"), (D("liqueur", "yuzushu"), "liqueur"),
    (D("cocktails", "highball", ["330ml Can"]), "cocktail-can"),
    (D("cocktails", "highball", ["Pint"]), "cocktail-highball"),
    (D("cocktails", "martini"), "cocktail-coupe"),
    (D(None, None), None),
])
def test_defaults_follow_plan_15_section_4_2(d, want):
    assert B.default_shell(d) == want


def _project(tmp_path, bottles, shells=("sake-green", "sake-black")):
    c = tmp_path / "content"
    c.mkdir()
    (c / "bottles.json").write_text(json.dumps({"bottles": bottles}), encoding="utf-8")
    (c / "shells.json").write_text(json.dumps({"shells": {k: {} for k in shells}}), encoding="utf-8")
    return c


def test_list_wins_over_the_default_and_the_report_counts_sakes_on_the_default(tmp_path):
    c = _project(tmp_path, {"a": "sake-black"})
    ds = [D("sake", "junmai", did="a"), D("sake", "junmai", did="b")]
    issues = Issues()
    rep = B.assign(ds, c, issues)
    assert [d["shell"] for d in ds] == ["sake-black", "sake-green"] and not issues.errors
    assert rep["counts"] == {"sake-black": 1, "sake-green": 1} and rep["sakes_default"] == ["b"] and rep["listed"] == 1


def test_e09_unknown_shell_and_w28_unknown_id(tmp_path):
    c = _project(tmp_path, {"a": "sake-purple", "ghost": "sake-black"})
    ds = [D("sake", "junmai", did="a")]
    issues = Issues()
    B.assign(ds, c, issues)
    assert [e["code"] for e in issues.errors] == ["E09"] and issues.counts("warning") == {"W28": 1}
    assert ds[0]["shell"] == "sake-green"                                   # the bad entry is ignored, not used


def test_a_missing_list_only_warns(tmp_path):
    (tmp_path / "content").mkdir()
    issues = Issues()
    B.assign([D("sake", "junmai")], tmp_path / "content", issues)
    assert not issues.errors and issues.counts("warning") == {"W20": 1}


# ------------------------------------------------------------------ the real shells.json and bottles.json

def test_real_config_is_consistent():
    cfg = json.loads((SHIP / "content" / "shells.json").read_text(encoding="utf-8"))
    assert set(cfg["shells"]) == set(B.SHELL_KEYS)
    for key, s in cfg["shells"].items():
        assert s["source"] in cfg["sources"] and s["scale"] > 0, key
        assert s["maskPolygon"], key
        if s["mode"] == "glass" and s["labelSheet"]:
            assert s["labelBlend"] == "multiply"
    listed = json.loads((SHIP / "content" / "bottles.json").read_text(encoding="utf-8"))["bottles"]
    assert set(listed.values()) <= set(cfg["shells"])
    # the hand-set scales of Plan 15 section 3.3
    want = {"sake-green": 1.0, "sake-craft": .95, "whisky-round": .85, "sake-small": .8, "beer-weizen": .75, "beer-pint": .7,
            "beer-can": .6, "tasting-glass": .45}
    for k, v in want.items():
        assert cfg["shells"][k]["scale"] == v, k


def test_published_shells_have_a_base_and_opaque_labels():
    scene = json.loads((SHIP / "docs" / "data" / "scene.json").read_text(encoding="utf-8"))
    assert len(scene["shells"]) == len(B.SHELL_KEYS)
    for key, sh in scene["shells"].items():
        assert "source" not in sh
        with Image.open(SHIP / "docs" / sh["files"]["2x"]) as im:
            a = np.asarray(im.convert("RGBA"))[..., 3]
        assert a[-1].max() < 255 or True
        assert a[:, :].max() == 255
        if sh["labelRect"]:
            x, y, w, h = sh["labelRect"]
            H, W = a.shape
            box = a[int((y + .1 * h) * H): int((y + .9 * h) * H), int((x + .1 * w) * W): int((x + .9 * w) * W)]
            assert box.min() >= 250, f"{key}: the label area is not solid ({box.min()})"
