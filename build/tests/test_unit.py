import datetime as dt

import pytest

from liquid import checks, model, photos
from liquid.common import Issues, norm_key, slugify
from liquid.ledger import Ledger, size_ml, split_styles, to_date, to_number, to_price


# ---------------------------------------------------------------- normalise
def test_size_ml():
    assert size_ml("1.8L Magnum") == 1800
    assert size_ml("1L Bottle") == 1000
    assert size_ml("60ml Tasting") == 60
    assert size_ml("720ml Bottle") == 720
    assert size_ml("Bottle") is None


def test_to_date_and_number():
    issues = Issues()
    assert to_date("2026-10-14 12:29") == "2026-10-14"
    assert to_date("2026-10-17") == "2026-10-17"
    assert to_date(dt.datetime(2026, 1, 2, 3, 4)) == "2026-01-02"
    assert to_date("yesterday", issues, {"sheet": "Core", "row": 2, "drink": "x"}) is None
    assert issues.warnings[0]["code"] == "W15"
    assert to_number("16.2") == 16.2 and to_number(7) == 7 and to_number(None) is None
    assert to_price(58) == 58.0 and to_price(92.094) == 92.09


def test_split_styles_dedupes_and_keeps_order():
    assert split_styles("Nama,  Genshu, nama , Kimoto") == ["Nama", "Genshu", "Kimoto"]
    assert split_styles(None) == []


def test_norm_key_ignores_case_accents_punctuation():
    assert norm_key("Côte Rôtie (Edition)") == norm_key("cote rotie edition")
    assert norm_key("DATE SEVEN Season Ⅱ") == norm_key("date seven season II")
    assert slugify("Stout/Porter") == "stout-porter"


# ---------------------------------------------------------------- combine / classify
def _ledger(core_rows, sheets=None):
    L = Ledger()
    L.core = [(i + 2, r) for i, r in enumerate(core_rows)]
    L.sheets = {k: [(i + 2, r) for i, r in enumerate(v)] for k, v in (sheets or {}).items()}
    L.validation = {}
    L.present_sheets = {"Core"}
    return L


def row(**kw):
    base = {"ID": "a", "Name": "A", "Category": "Sake", "Size": "720ml Bottle", "ABV %": 15, "Producer": "P",
            "Origin": "Fukushima", "Country": "Japan", "Style(s)": None, "Acquired": None, "Bought From": None,
            "Price (S$)": None, "Rating": None, "Favourite": None, "Added": None, "Public Notes": None,
            "Visit Note": None}
    base.update(kw)
    return base


def test_combine_star_on_one_row_only_and_sizes_sorted():
    issues = Issues()
    L = _ledger([row(Size="720ml Bottle"),
                 row(**{"Size": "60ml Tasting", "Favourite": "★", "Bought From": "Unknown"}),
                 row(Size="1.8L Magnum", Added="2026-10-02 10:00"), row(Size="Bottle", Added="2026-09-01")])
    drinks = model.combine_drinks(L, issues)
    assert len(drinks) == 1
    d = drinks[0]
    assert d["favourite"] is True
    assert d["sizes"] == ["60ml Tasting", "720ml Bottle", "1.8L Magnum", "Bottle"]
    assert d["added"] == "2026-10-02"
    assert len(d["visits"]) == 4 and d["visits"][1]["where"] is None  # "Unknown" venue removed
    assert not issues.warnings


def test_combine_warns_when_rows_disagree():
    issues = Issues()
    L = _ledger([row(), row(Producer="Other")])
    model.combine_drinks(L, issues)
    assert [w["code"] for w in issues.warnings] == ["W06"]


def test_classify_wine_blend_and_fallbacks():
    issues = Issues()
    L = _ledger([row(ID="w1", Name="W1", Category="Wine"), row(ID="w2", Name="W2", Category="Wine"),
                 row(ID="b1", Name="B1", Category="Beer"), row(ID="x1", Name="X1", Category="Mystery"),
                 row(ID="u1", Name="U1", Category="Umeshu"), row(ID="s1", Name="S1", Category="Sake")],
                {"Wine Detail": [{"ID": "w1", "Grape(s)": "merlot, Cabernet Sauvignon"},
                                 {"ID": "w2", "Grape(s)": "  MERLOT "}],
                 "Other Detail": [{"ID": "u1", "Type": "IPA"}, {"ID": "b1", "Type": "ipa"}]})
    drinks = model.combine_drinks(L, issues)
    model.join_details(L, drinks, issues)
    model.classify(L, drinks, issues)
    by = {d["id"]: d for d in drinks}
    assert (by["w1"]["category"], by["w1"]["sub"]) == ("wine", "blend")
    assert (by["w2"]["sub"], by["w2"]["sub_name"]) == ("merlot", "Merlot")
    assert (by["b1"]["category"], by["b1"]["sub"]) == ("beer", "ipa")
    assert by["x1"]["category"] is None
    assert (by["u1"]["category"], by["u1"]["sub"]) == ("liqueur", "umeshu")  # Umeshu is a kind of Liqueur; IPA only warns
    assert by["s1"]["sub"] == "ungraded"
    assert sorted(w["code"] for w in issues.warnings) == ["W03", "W07"]


def test_detail_row_without_core_id_is_dropped_with_w11():
    issues = Issues()
    L = _ledger([row()], {"Sake Detail": [{"ID": "ghost", "Grade": "Junmai"}]})
    drinks = model.combine_drinks(L, issues)
    model.join_details(L, drinks, issues)
    assert issues.warnings[0]["code"] == "W11" and drinks[0]["detail"] == {}


# ---------------------------------------------------------------- photos
def _drinks(*names):
    return [{"id": slugify(n), "name": n} for n in names]


def test_exact_match_and_view_suffixes():
    ds = _drinks("Alpha Nama", "Jukyu HIRVI (19)", "Delta (Honey-Yeast) Craft")
    files = ["Alpha Nama.jpg", "ALPHA nama (back label).jpg", "Alpha Nama (2).jpg", "Jukyu HIRVI (19).jpg",
             "Delta (Honey-Yeast) Craft.jpg", "Random.jpg"]
    m, unmatched, _ = photos.build_photo_map(ds, files, {}, Issues())
    assert m["alpha-nama"]["front"] == "Alpha Nama.jpg"
    assert sorted(o["kind"] for o in m["alpha-nama"]["others"]) == ["back", "extra"]
    assert m["jukyu-hirvi-19"]["front"] == "Jukyu HIRVI (19).jpg"       # (19) is part of the name
    assert m["delta-honey-yeast-craft"]["front"] == "Delta (Honey-Yeast) Craft.jpg"
    assert unmatched == ["Random.jpg"]


def test_prefix_matches_are_only_suggested():
    ds = _drinks("Against The Grain (Normat) Tokubetsu Junmai")
    m, unmatched, sugg = photos.build_photo_map(ds, ["Against The Grain.jpg"], {}, Issues())
    assert m == {} and unmatched == ["Against The Grain.jpg"]
    assert sugg["Against The Grain.jpg"]["candidates"][0]["id"] == ds[0]["id"]


def test_manual_entry_wins_and_missing_file_is_e03():
    ds = _drinks("Alpha Nama")
    issues = Issues()
    manual = {"alpha-nama": {"front": "Other.jpg", "labelCrop": [0.1, 0.2, 0.5, 0.5]}, "ghost": {"front": "x"}}
    m, unmatched, _ = photos.build_photo_map(ds, ["Alpha Nama.jpg", "Other.jpg"], manual, issues)
    assert m["alpha-nama"]["front"] == "Other.jpg" and m["alpha-nama"]["labelCrop"] == [0.1, 0.2, 0.5, 0.5]
    assert any(w["code"] == "W16" for w in issues.warnings)
    issues2 = Issues()
    photos.build_photo_map(ds, ["Alpha Nama.jpg"], {"alpha-nama": {"front": "Missing.jpg"}}, issues2)
    assert issues2.errors[0]["code"] == "E03"


# ---------------------------------------------------------------- privacy scan
@pytest.mark.parametrize("marker", ["Invoice", "Sweep batch", "converted at", "mid-market", "corrected from"])
def test_privacy_scan_fails_on_planted_marker(marker):
    issues = Issues()
    files = {"drinks/x.json": '{"story": "ok ' + marker + ' 12"}\n'}
    checks.check_privacy(files, [], {}, issues)
    assert [e["code"] for e in issues.errors] == ["E02"]


def test_privacy_scan_fails_on_filename_and_notes_field():
    issues = Issues()
    checks.check_privacy({"drinks/x.json": '{"a": "see Pear.jpg"}\n'}, ["Pear.jpg"], {}, issues)
    assert issues.errors and issues.errors[0]["code"] == "E02"
    issues = Issues()
    checks.check_privacy({"drinks/x.json": '{"notes": "hello"}\n'}, [], {}, issues)
    assert issues.errors and issues.errors[0]["code"] == "E02"
    issues = Issues()
    checks.check_privacy({"drinks/x.json": '{"story": "a clean sentence"}\n'}, ["Pear.jpg"], {}, issues)
    assert not issues.errors


def test_privacy_scan_catches_draft_producer_research():
    page = {"approved": False, "name": "P", "key": "p", "raw_gated": {"About": "A long secret blurb about the brewery"}}
    issues = Issues()
    checks.check_privacy({"producers/p.json": '{"about": ["A long secret blurb about the brewery"]}\n'},
                         [], {"p": page}, issues)
    assert issues.errors and issues.errors[0]["code"] == "E02"


def test_other_bottle_when_some_drinks_have_a_sub_type():
    """Plan 01 section 4 shared rule: 'Other {category}' (key other) beside real sub-types, 'all' when none."""
    issues = Issues()
    L = _ledger([row(ID="w", Name="W", Category="Whisky"), row(ID="s1", Name="S1", Category="Spirit"),
                 row(ID="s2", Name="S2", Category="Spirit"), row(ID="g", Name="G", Category="Spirit"),
                 row(ID="b1", Name="B1", Category="Beer"), row(ID="b2", Name="B2", Category="Beer")],
                {"Other Detail": [{"ID": "g", "Type": "Gin"}]})
    drinks = model.combine_drinks(L, issues)
    model.join_details(L, drinks, issues)
    model.classify(L, drinks, issues)
    by = {d["id"]: d for d in drinks}
    assert (by["s1"]["sub"], by["s1"]["sub_name"]) == ("other", "Other spirits")
    assert by["s2"]["sub"] == "other" and by["g"]["sub"] == "gin" and by["w"]["sub"] == "whisky"
    assert by["s1"]["sub_order"] > by["g"]["sub_order"]          # placed last
    assert by["b1"]["sub"] == by["b2"]["sub"] == "all"           # nothing in Beer has a type: single bottle


def test_dotted_front_and_back_suffixes():
    ds = _drinks("Odayaka Junmai Daiginjo 30th Anniversary Sake")
    files = ["Odayaka Junmai Daiginjo 30th Anniversary Sake.FRONT.jpg",
             "Odayaka Junmai Daiginjo 30th Anniversary Sake.BACK.jpg"]
    m, unmatched, _ = photos.build_photo_map(ds, files, {}, Issues())
    e = m[ds[0]["id"]]
    assert e["front"] == files[0] and e["others"] == [{"file": files[1], "kind": "back"}]
    assert unmatched == []
    assert photos.split_view("X.front") == ("X", "front") and photos.split_view("X.Back") == ("X", "back")
    assert photos.split_view("Honey (Honey-Yeast)") == ("Honey (Honey-Yeast)", None)


def test_liqueur_kinds_and_other_bottle():
    """Plan 01 section 4.3: Umeshu first, then kinds from Type, 'Other liqueurs' last."""
    issues = Issues()
    L = _ledger([row(ID="u", Name="U", Category="Umeshu"), row(ID="y", Name="Y", Category="Liqueur"),
                 row(ID="c", Name="C", Category="Liqueur"), row(ID="o", Name="O", Category="Liqueur")],
                {"Other Detail": [{"ID": "u", "Type": "Classic", "Base": "Shochu"},
                                  {"ID": "y", "Type": "Yuzushu"}, {"ID": "c", "Type": "Cream", "Base": "Dairy"}]})
    drinks = model.combine_drinks(L, issues)
    model.join_details(L, drinks, issues)
    model.classify(L, drinks, issues)
    by = {d["id"]: d for d in drinks}
    assert all(d["category"] == "liqueur" for d in drinks)
    assert (by["u"]["sub"], by["u"]["sub_name"]) == ("umeshu", "Umeshu")
    assert by["y"]["sub"] == "yuzushu" and by["c"]["sub"] == "cream"
    assert (by["o"]["sub"], by["o"]["sub_name"]) == ("other", "Other liqueurs")
    order = sorted(drinks, key=lambda d: d["sub_order"])
    assert [d["id"] for d in order] == ["u", "c", "y", "o"]      # umeshu, then kinds A-Z, other last
    assert model.build_facts(by["u"]) == ["Classic", "Shochu"]    # umeshu flavour/base is a card fact
    assert model.build_facts(by["c"]) == ["Dairy"]


def test_old_umeshu_category_is_gone():
    from liquid import taxonomy as T
    assert "umeshu" not in {k for k, _, _ in T.CATEGORIES} and "liqueur" in {k for k, _, _ in T.CATEGORIES}
