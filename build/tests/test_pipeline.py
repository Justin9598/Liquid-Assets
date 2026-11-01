import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from fixture import make_project, make_workbook
from liquid.pipeline import run


def tree_hash(folder: Path):
    h = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            h[p.relative_to(folder).as_posix()] = hashlib.sha1(p.read_bytes()).hexdigest()
    return h


def load(ship, rel):
    return json.loads((ship / "docs" / "data" / rel).read_text(encoding="utf-8"))


def all_data_text(ship):
    return "".join(p.read_text(encoding="utf-8") for p in sorted((ship / "docs" / "data").rglob("*.json")))


@pytest.fixture()
def project(tmp_path):
    ship = make_project(tmp_path)
    return tmp_path, ship


def test_builds_with_no_errors_and_every_drink_on_one_shelf(project):
    root, ship = project
    res = run(ship)
    assert res.exit_code == 0, res.issues.errors
    shelf = load(ship, "shelf.json")
    assert sum(c["drinkCount"] for c in shelf["categories"]) == 12   # 12 drinks, none left out
    idx = load(ship, "drinks.json")
    assert len(idx) == 12 and all(d["category"] for d in idx)
    # expected warnings because the ledger changes of Plan 05 section 7 are not all in the fixture
    codes = res.issues.counts("warning")
    for c in ("W01", "W03", "W11"):
        assert c in codes


def test_missing_optional_columns_are_warnings_not_errors(tmp_path):
    ship = make_project(tmp_path, drop_notes_columns=True, with_producers=False)
    res = run(ship)
    assert res.exit_code == 0
    codes = res.issues.counts("warning")
    assert codes.get("W13", 0) >= 3 and codes.get("W04", 0) >= 5
    assert load(ship, "drinks/sake-a.json")["story"] is None


def test_notes_column_never_published(project):
    root, ship = project
    run(ship)
    blob = all_data_text(ship)
    for bad in ("Invoice", "Sweep batch", "converted at", "mid-market", "4471"):
        assert bad not in blob
    assert '"notes"' not in blob.lower()


def test_second_run_is_byte_identical_and_reencodes_nothing(project):
    root, ship = project
    run(ship)
    first = tree_hash(ship / "docs")
    res = run(ship)
    assert res.summary["images"]["encoded"] == 0
    assert tree_hash(ship / "docs") == first


def test_planted_invoice_fails_build_with_e02(tmp_path):
    ship = make_project(tmp_path, public_notes_leak=True)
    res = run(ship)
    assert res.exit_code == 1
    assert any(e["code"] == "E02" for e in res.issues.errors)
    assert not (ship / "docs" / "data").exists()  # nothing published


def test_images_upright_and_metadata_stripped(project):
    root, ship = project
    run(ship)
    web = ship / "docs" / "img" / "web"
    # Beta Daiginjo.jpg is stored 1200x900 with EXIF orientation 6, so it must come out portrait
    with Image.open(web / "sake-b-1.webp") as im:
        assert im.height > im.width
    files = list((ship / "docs" / "img").rglob("*.webp"))
    assert files
    for f in files:
        with Image.open(f) as im:
            assert not im.getexif(), f
            assert "exif" not in im.info and "icc_profile" not in im.info and "xmp" not in im.info, f
        raw = f.read_bytes()
        assert b"SecretCameraMaker" not in raw and b"SecretModel" not in raw
    with Image.open(ship / "docs" / "img" / "thumbs" / "sake-a.webp") as im:
        assert im.size == (480, 640)
    with Image.open(web / "sake-a-1.webp") as im:
        assert max(im.size) <= 1200


def test_deleting_a_drink_removes_its_files(tmp_path):
    ship = make_project(tmp_path)
    run(ship)
    assert (ship / "docs" / "data" / "drinks" / "sake-b.json").exists()
    make_workbook(tmp_path / "Drinks Ledger.xlsx", drop_ids=("sake-b",))
    res = run(ship)
    assert res.exit_code == 0
    assert not (ship / "docs" / "data" / "drinks" / "sake-b.json").exists()
    assert not (ship / "docs" / "img" / "thumbs" / "sake-b.webp").exists()
    assert not (ship / "docs" / "img" / "web" / "sake-b-1.webp").exists()


def test_check_mode_writes_nothing_to_docs(project):
    root, ship = project
    res = run(ship, check=True)
    assert res.exit_code == 0
    assert not (ship / "docs" / "data").exists() and not (ship / "docs" / "img").exists()
    assert (ship / "reports" / "build-report.html").exists()


def test_producers_aliases_and_draft_gating(project):
    root, ship = project
    run(ship)
    prods = {p["key"]: p for p in load(ship, "producers.json")}
    assert prods["machida-shuzo"]["drinkCount"] == 2   # alias merge
    assert not any(k.startswith("machida-shuzoten") for k in prods)
    alpha = load(ship, "producers/alpha-shuzo.json")   # status draft: no research published
    assert alpha["about"] == [] and alpha["founded"] is None and alpha["website"] is None
    assert alpha["native"] is None and alpha["sources"] == [] and alpha["related"] == []
    beta = load(ship, "producers/beta-brewery.json")   # approved
    assert beta["about"] == ["Approved story BETA."] and beta["founded"] == 1900
    assert beta["related"] == [{"key": "alpha-shuzo", "name": "Alpha Shuzo", "relationship": "sister brewery"}]
    assert "Secret draft story" not in all_data_text(ship)
    # Unknown producer: no page, but the drink still has a page
    assert "unknown" not in prods
    d = load(ship, "drinks/umeshu-f.json")
    assert d["producer"]["key"] is None and d["producer"]["location"] == "Nagano, Japan"


def test_drink_details_combination_and_photos(project):
    root, ship = project
    run(ship)
    a = load(ship, "drinks/sake-a.json")
    assert a["favourite"] is True and len(a["visits"]) == 2
    assert [v["where"] for v in a["visits"]] == [None, "Sake Hub"]   # newest first; "Unknown" -> null
    assert a["visits"][0]["price"] == 58.0
    assert [x["label"] for x in a["spec"]][:3] == ["Grade", "Polishing ratio", "Rice"]
    assert [p["kind"] for p in a["photos"]] == ["front", "back"]
    b = load(ship, "drinks/sake-b.json")
    assert b["tasting"]["palate"]["sweetness"] == "off-dry"
    assert b["tasting"]["nose"] if "nose" in b["tasting"] else True
    smv = [s for s in b["spec"] if s["label"] == "SMV"][0]
    assert smv["value"] == -20 and smv["viz"] == "smv"
    idx = {d["id"]: d for d in load(ship, "drinks.json")}
    assert idx["sake-a"]["occasions"] == 2 and idx["sake-a"]["sizes"] == ["60ml Tasting", "720ml Bottle"]
    assert idx["sake-b"]["hasTasting"] and idx["sake-b"]["thumb"] == "img/thumbs/sake-b.webp"
    assert idx["sake-c"]["thumb"] is None and idx["wine-e"]["sub"] == "blend"
    assert idx["sake-l"]["thumb"] and idx["craft-d"]["thumb"]      # Unicode name and bracketed name matched
    sugg = json.loads((ship / "reports" / "photo-map.suggested.json").read_text(encoding="utf-8"))
    assert "Beta Dai.jpg" in sugg["photos"]                       # prefix match is only suggested
    assert ".jpg" not in all_data_text(ship)                      # no original filenames published


def test_content_filtered_to_keys_in_use(project):
    root, ship = project
    run(ship)
    assert list(load(ship, "subcategories.json")) == ["sake/junmai-ginjo"]
    assert list(load(ship, "glossary.json")) == ["Nama"]
    assert load(ship, "build.json")["drinkCount"] == 12


def test_wset_sentence_comes_from_the_glossary_when_a_tasting_exists(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "glossary.json").write_text(
        '{"Nama": "Unpasteurised.", "WSET-style tasting": "Edit me.", "Unusedterm": "x"}', encoding="utf-8")
    run(ship)
    assert list(load(ship, "glossary.json")) == ["Nama", "WSET-style tasting"]   # sake-b has a tasting card


def test_js_css_stamping_is_idempotent_and_follows_the_code(tmp_path):
    ship = make_project(tmp_path)
    js = ship / "docs" / "assets" / "js"
    js.mkdir(parents=True)
    (js / "main.js").write_text("export const a = 1;\n", encoding="utf-8")
    (ship / "docs" / "assets" / "css").mkdir()
    (ship / "docs" / "assets" / "css" / "app.css").write_text("body{}\n", encoding="utf-8")
    index = ship / "docs" / "index.html"
    index.write_text("<html><head>\n<!-- build:assets -->\n<!-- /build:assets -->\n</head></html>\n", encoding="utf-8")
    run(ship)
    first = index.read_text(encoding="utf-8")
    import re
    v1 = re.search(r"app\.css\?v=(\w+)", first).group(1)
    assert f"assets/js/main.js?v={v1}" in first and '"./assets/js/main.js": "./assets/js/main.js?v=' in first
    run(ship)
    assert index.read_text(encoding="utf-8") == first                 # nothing changes on a second run
    (js / "main.js").write_text("export const a = 2;\n", encoding="utf-8")
    run(ship)
    assert re.search(r"app\.css\?v=(\w+)", index.read_text(encoding="utf-8")).group(1) != v1


def test_label_pools_only_hold_verified_label_only_crops(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "photo-map.json").write_text(json.dumps({
        "sake-a": {"labelCrop": [0.3, 0.5, 0.4, 0.2], "labelStatus": "ok"},
        "craft-d": {"labelStatus": "skip", "labelSkip": "printed on glass"},
    }), encoding="utf-8")
    res = run(ship)
    assert res.exit_code == 0
    shelf = load(ship, "shelf.json")
    pools = {s["key"]: s["labels"] for c in shelf["categories"] for s in c["subcategories"]}
    assert pools["junmai-ginjo"] == ["img/labels/sake-a.webp"]
    assert pools["craft-sake"] == []                                   # skipped photo stays out of the pool
    assert (ship / "docs" / "img" / "labels" / "sake-a.webp").exists()
    assert not (ship / "docs" / "img" / "labels" / "craft-d.webp").exists()
    assert (ship / "docs" / "img" / "thumbs" / "craft-d.webp").exists()  # still a card thumbnail
    idx = {d["id"]: d for d in load(ship, "drinks.json")}
    assert idx["sake-a"]["label"] and idx["craft-d"]["label"] is None and idx["craft-d"]["thumb"]
    assert any(i["code"] == "I03" for i in res.issues.items)           # the skip is listed
    assert any(i["code"] == "W21" and i["drink"] == "Beta Daiginjo" for i in res.issues.items)   # not judged yet
    html = (ship / "reports" / "build-report.html").read_text(encoding="utf-8")
    assert "printed on glass" in html and "Subcategories on the illustrated fallback label" in html


def test_ok_label_without_a_crop_is_an_error(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "photo-map.json").write_text(json.dumps({"sake-a": {"labelStatus": "ok"}}), encoding="utf-8")
    res = run(ship)
    assert res.exit_code == 1 and any(e["code"] == "E04" for e in res.issues.errors)


def test_phase_1_publishes_the_welcome_page_data_only_and_deletes_leftovers(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "photo-map.json").write_text(json.dumps({
        "sake-a": {"labelCrop": [0.3, 0.5, 0.4, 0.2], "labelStatus": "ok"}}), encoding="utf-8")
    full = run(ship, phase=2)                                  # a full local build first
    assert full.exit_code == 0
    assert (ship / "docs" / "data" / "drinks.json").exists() and (ship / "docs" / "img" / "thumbs").exists()
    res = run(ship, phase=1)
    assert res.exit_code == 0
    data = ship / "docs" / "data"
    assert sorted(p.relative_to(data).as_posix() for p in data.rglob("*") if p.is_file()) == ["build.json", "shelf.json"]
    assert not (ship / "docs" / "img" / "thumbs").exists() and not (ship / "docs" / "img" / "web").exists()
    assert (ship / "docs" / "img" / "labels" / "sake-a.webp").exists()
    assert load(ship, "build.json")["sections"] == {"welcome": True, "shelves": False, "drinks": False, "makers": False}
    # the published tree holds no photo filenames or private text either
    blob = "".join(p.read_text(encoding="utf-8") for p in data.rglob("*.json"))
    assert ".jpg" not in blob and "Invoice" not in blob
    # phase 2 turns everything back on without code changes
    assert run(ship, phase=2).exit_code == 0 and (data / "drinks.json").exists()
    assert load(ship, "build.json")["sections"]["makers"] is True
