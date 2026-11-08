import hashlib
import shutil
import json
from pathlib import Path

import pytest
from PIL import Image

from fixture import make_project, make_workbook
from liquid.common import Issues
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
    assert [v["where"] for v in a["visits"]] == ["Sake Hub", None]   # no price (free) first, then the bottle with a price; "Unknown" -> null
    assert all("price" not in v for v in a["visits"])               # Plan 11
    assert [x["label"] for x in a["spec"]][:3] == ["Grade", "Polishing ratio", "Rice"]
    assert [p["kind"] for p in a["photos"]] == ["front"]          # the front image only (Plan 10 section 7)
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
    assert sorted(p.relative_to(data).as_posix() for p in data.rglob("*") if p.is_file()) == ["aliases.json", "build.json", "shelf.json"]
    assert not (ship / "docs" / "img" / "thumbs").exists() and not (ship / "docs" / "img" / "web").exists()
    assert (ship / "docs" / "img" / "labels" / "sake-a.webp").exists()
    assert load(ship, "build.json")["sections"] == {"welcome": True, "shelves": False, "drinks": False, "makers": False}
    # the published tree holds no photo filenames or private text either
    blob = "".join(p.read_text(encoding="utf-8") for p in data.rglob("*.json"))
    assert ".jpg" not in blob and "Invoice" not in blob
    # phase 2 turns everything back on without code changes
    assert run(ship, phase=2).exit_code == 0 and (data / "drinks.json").exists()
    assert load(ship, "build.json")["sections"]["makers"] is True


# ------------------------------------------------------------------ Plan 08 section 6: the privacy scan over what is on disk

def _set_notes(ship, row_id, text, public=None):
    import openpyxl
    path = ship.parent / "Drinks Ledger.xlsx"
    wb = openpyxl.load_workbook(path)
    ws = wb["Core"]
    heads = [c.value for c in ws[1]]
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == row_id:
            ws.cell(r, heads.index("Notes") + 1).value = text
            if public is not None:
                ws.cell(r, heads.index("Public Notes") + 1).value = public
    wb.save(path)


def test_notes_text_found_in_any_published_file_fails_the_build(tmp_path):
    ship = make_project(tmp_path)
    secret = "Quietly tasted at the back table with the chef after closing time"
    _set_notes(ship, "sake-c", secret)
    _set_notes(ship, "sake-j", "Fine", public=f"Lovely. {secret} and then some.")      # another drink's story repeats it
    res = run(ship)
    assert res.exit_code == 1
    assert any(e["code"] == "E02" and "Notes text" in e["message"] for e in res.issues.errors)
    assert not (ship / "docs" / "data").exists()


def test_notes_the_owner_made_public_in_the_same_row_are_not_a_leak(tmp_path):
    ship = make_project(tmp_path)
    same = "A bright and fruity pour that stays public on purpose"
    _set_notes(ship, "sake-c", same, public=same)
    res = run(ship)
    assert res.exit_code == 0, res.issues.errors


def test_the_on_disk_scan_reads_every_file_in_data_and_img_in_every_phase(tmp_path):
    from liquid import checks
    ship = make_project(tmp_path)
    for phase in (1, 2):
        res = run(ship, phase=phase)
        assert res.exit_code == 0 and res.summary["scanned"] >= 2
    docs = ship / "docs"
    photos = ["Alpha Junmai Ginjo Nama.jpg", "Beta Daiginjo.jpg"]
    issues = Issues()
    assert checks.scan_published(docs, photos, [], issues) > 5 and not issues.errors
    # a stale data file with a private marker, an image named like an original photo, an image with EXIF, a filename in the bytes
    (docs / "data" / "stale.json").write_text('{"x": "Invoice 12 from the shop"}', encoding="utf-8")
    shutil.copy(docs / "img" / "thumbs" / "sake-a.webp", docs / "img" / "thumbs" / "Beta Daiginjo.jpg")
    im = Image.new("RGB", (8, 8))
    exif = Image.Exif()
    exif[0x010F] = "Secret"
    im.save(docs / "img" / "thumbs" / "exif.webp", exif=exif)
    (docs / "img" / "thumbs" / "bytes.webp").write_bytes(b"RIFF....WEBPVP8 " + b"Alpha Junmai Ginjo Nama.jpg")
    bad = Issues()
    checks.scan_published(docs, photos, [], bad)
    text = " | ".join(e["message"] for e in bad.errors)
    for part in ("invoice", "named like an original photo", "metadata is not stripped in img/thumbs/exif.webp", "inside img/thumbs/bytes.webp"):
        assert part in text, (part, text)


# ------------------------------------------------------------------ Plan 10: categories, shelf views data, aliases, front-only photos

def test_plan_10_shelf_data_aliases_and_front_only_photos(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "aliases.json").write_text('{"producers": {"old-key": "alpha-shuzo"}}', encoding="utf-8")
    res = run(ship)
    assert res.exit_code == 0, res.issues.errors
    shelf = load(ship, "shelf.json")
    keys = [c["key"] for c in shelf["categories"]]
    assert keys == ["sake", "fermented", "umeshu", "wine", "spirits"]       # Liqueur is empty, so it is left out (section 2.1)
    by = {c["key"]: c for c in shelf["categories"]}
    assert by["umeshu"]["direct"] is True and [s["key"] for s in by["umeshu"]["subcategories"]] == ["all"]
    assert by["umeshu"]["subcategories"][0]["native"] == "梅酒" and by["umeshu"]["drinkCount"] == 2
    ferm = [s["key"] for s in by["fermented"]["subcategories"]]
    assert "ipa" in ferm
    sake = by["sake"]["subcategories"][0]
    assert {"id", "name", "label"} <= set(sake["drinks"][0]) and "new" not in sake and "season" not in sake        # only Umeshu follows the counter
    um = by["umeshu"]["subcategories"][0]
    assert len(um["new"]) <= 5 and set(um["season"]) == {"spring", "summer", "autumn", "winter"}
    assert len(shelf["counter"]["newArrivals"]) >= 5
    # old addresses: the build writes the table the router follows
    al = load(ship, "aliases.json")
    assert {"from": "beer/*", "to": "fermented/*"} in al["routes"] and {"from": "liqueur/umeshu", "to": "umeshu"} in al["routes"]
    assert {"from": "makgeolli", "to": "fermented/makgeolli"} in al["routes"] and al["producers"] == {"old-key": "alpha-shuzo"}
    # one published photo per drink: the front image
    web = sorted(p.name for p in (ship / "docs" / "img" / "web").iterdir())
    assert web and all(n.endswith("-1.webp") for n in web)
    assert [p["kind"] for p in load(ship, "drinks/sake-a.json")["photos"]] == ["front"]


def test_the_lower_shelf_capacity_is_measured_and_capped():
    from liquid import scene as scene_mod
    P = json.loads((Path(__file__).resolve().parents[2] / "content" / "scene.json").read_text(encoding="utf-8"))["plates"]
    wide = scene_mod.lower_capacity(P["wide"], "wide", {"sake": {"aspect": 0.33}, "spirits": {"aspect": 0.45}})
    assert wide["shelves"] == 2 and 1 <= wide["perShelf"] and wide["total"] <= scene_mod.SHELF_VIEW_LIMIT
    tall = scene_mod.lower_capacity(P["tall"], "tall", {})
    assert tall["scrolls"] is True and tall["total"] == scene_mod.SHELF_VIEW_LIMIT


# ------------------------------------------------------------------ Plan 09 section 7: W22, the maker About-text check

def test_w22_flags_about_text_that_breaks_the_writing_rules(tmp_path):
    from liquid.producers import check_about
    good = " ".join(["word"] * 80)
    ok = Issues()
    check_about("Fine", [good, good[:100]], ok)
    assert not ok.items
    bad = Issues()
    check_about("Dashy", ["Brewed since 1850 — a long story. Our Finest rice, with PASSION, and a world-class cup – truly."], bad)
    msgs = " | ".join(i["message"] for i in bad.items)
    assert all(i["code"] == "W22" for i in bad.items)
    for part in ("em or en dash", "'finest'", "'passion'", "'world-class'", "words (60 to 120 wanted)"):
        assert part in msgs, (part, msgs)
    long = Issues()
    check_about("Long", [good] * 4, long)
    msgs = " | ".join(i["message"] for i in long.items)
    assert "4 paragraphs" in msgs and "320 words" in msgs
    # in the real pipeline the fixture's approved maker (Beta Brewery, 3 words) is flagged, and the draft one is never checked
    ship = make_project(tmp_path)
    res = run(ship)
    flagged = [i["drink"] for i in res.issues.items if i["code"] == "W22"]
    assert flagged == ["Beta Brewery"]


# ------------------------------------------------------------------ Plan 09 section 11.1: paragraphs survive the ledger load

def test_a_cell_with_two_paragraphs_gives_two_about_entries(tmp_path):
    import openpyxl
    from liquid.common import clean_paragraphs
    assert clean_paragraphs("A  b\r\n\n\n\nC \n") == "A b\n\nC" and clean_paragraphs("  \n ") is None
    ship = make_project(tmp_path)
    path = tmp_path / "Drinks Ledger.xlsx"
    wb = openpyxl.load_workbook(path)
    ws = wb["Producers"]
    heads = [c.value for c in ws[1]]
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == "Beta Brewery":
            ws.cell(r, heads.index("About") + 1).value = "First  paragraph here.\n\n\nSecond paragraph here."
    wb.save(path)
    run(ship)
    assert load(ship, "producers/beta-brewery.json")["about"] == ["First paragraph here.", "Second paragraph here."]


def test_w24_flags_a_sources_entry_that_is_not_a_web_address():
    from liquid.producers import check_sources
    ok = Issues()
    check_sources("Fine", ["https://a.example/x", "http://b.example"], ok)
    check_sources("Empty", [], ok)
    assert not ok.items
    bad = Issues()
    check_sources("Labelled", ["https://a.example/x", "Brewery back label", "www.no-scheme.example"], bad)
    assert [i["code"] for i in bad.items] == ["W24", "W24"]
    assert "Brewery back label" in bad.items[0]["message"] and bad.items[0]["drink"] == "Labelled"
