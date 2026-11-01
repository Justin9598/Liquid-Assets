"""Builds a small fixture workbook and photos that cover the awkward cases seen in the real ledger."""
from __future__ import annotations

import shutil
from pathlib import Path

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from PIL import Image

CORE_HEADERS = ["ID", "Name", "Category", "Size", "ABV %", "Producer", "Origin", "Country", "Style(s)",
                "Acquired", "Bought From", "Price (S$)", "Rating", "Favourite", "Notes", "Added",
                "Public Notes", "Visit Note"]
FORMULA = '=IFERROR(INDEX(Core!$B$2:$B$400,MATCH($A{r},Core!$A$2:$A$400,0)),"")'

PRIVATE_NOTE = "Invoice 4471 from Supplier X. Sweep batch 3, converted at 1 SGD = 1,048 KRW (mid-market)."

# id, name, category, size, abv, producer, origin, country, styles, bought, price, fav, notes, added, public, visit
CORE_ROWS = [
    ["sake-a", "Alpha Junmai Ginjo Nama", "Sake", "60ml Tasting", 16.2, "Alpha Shuzo", "Fukushima", "Japan",
     "Nama, Genshu", "Sake Hub", None, None, PRIVATE_NOTE, "2026-10-01 12:00", "A bright, fruity pour.", "Tasting event"],
    ["sake-a", "Alpha Junmai Ginjo Nama", "Sake", "720ml Bottle", 16.2, "Alpha Shuzo", "Fukushima", "Japan",
     "Nama, Genshu", "Unknown", 58, "★", PRIVATE_NOTE, "2026-10-09", None, None],
    ["sake-b", "Beta Daiginjo", "Sake", "720ml Bottle", 16, "Beta Brewery", "Hyogo", "Japan", None,
     "Shop One", 120.5, None, PRIVATE_NOTE, None, None, None],
    ["sake-c", "Gamma Sake", "Sake", "1.8L Magnum", None, "Alpha Shuzo", "Fukushima", "Japan", None,
     "Shop Two", 99, None, None, None, None, None],
    ["craft-d", "Delta (Honey-Yeast) Craft Sake", "Craft Sake", "720ml Bottle", 12, "Delta KK (Honey)", "Tochigi",
     "Japan", "Flavoured", "Shop One", 40, None, None, None, None, None],
    ["wine-e", "Epsilon Red Blend 2025", "Wine", "750ml Bottle", 13.5, "Domaine E", "Bordeaux", "France", None,
     "Wine Shop", 45, None, None, None, None, None],
    ["umeshu-f", "Foxtrot Umeshu", "Umeshu", "500ml Bottle", 12, "Unknown", "Nagano", "Japan", None, "Shop Two",
     30, None, None, None, None, None],
    ["beer-g", "Golf IPA", "Beer", "330ml Can", 6.5, "Golf Brewing", "Jeju", "South Korea", None, "Shop Two", 8,
     None, None, None, None, None],
    ["umeshu-h", "Hotel Plum", "Umeshu", "500ml Bottle", 10, "Hotel Shoten", "Wakayama", "Japan", None,
     "Shop Two", 28, None, None, None, None, None],
    ["soju-i", "India Soju", "Soju", "360ml Bottle", 17, "Soju Co", "Seoul", "South Korea", None, "Shop Two", 6,
     None, None, None, None, None],
    ["sake-j", "Juliet Junmai", "Sake", "720ml Bottle", 15, "Machida Shuzo", "Gunma", "Japan", None, "Shop One",
     50, None, None, None, None, None],
    ["sake-k", "Kilo Junmai", "Sake", "720ml Bottle", 15, "Machida Shuzoten", "Gunma", "Japan", None, "Shop One",
     52, None, None, None, None, None],
    ["sake-l", "Obuse Numero Six 【小布施 Numero SIX】", "Sake", "720ml Bottle", 15,
     "Obuse Winery", "Nagano", "Japan", None, "Shop One", 60, None, None, None, None, None],
]


def _list_dv(ws, col, values, last=400):
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    dv.add(f"{col}2:{col}{last}")
    ws.add_data_validation(dv)


def make_workbook(path: Path, *, public_notes_leak=False, drop_notes_columns=False, with_producers=True,
                  drop_ids=()):
    wb = openpyxl.Workbook()
    core = wb.active
    core.title = "Core"
    headers = list(CORE_HEADERS)
    if drop_notes_columns:
        headers = [h for h in headers if h not in ("Public Notes", "Visit Note")]
    core.append(headers)
    for row in CORE_ROWS:
        if row[0] in drop_ids:
            continue
        d = dict(zip(["ID", "Name", "Category", "Size", "ABV %", "Producer", "Origin", "Country", "Style(s)",
                      "Bought From", "Price (S$)", "Favourite", "Notes", "Added", "Public Notes", "Visit Note"],
                     row))
        if public_notes_leak and d["ID"] == "sake-b":
            d["Public Notes"] = "Leaky. Invoice 99 from the shop."
        core.append([d.get(h) for h in headers])
    _list_dv(core, "C", ["Sake", "Craft Sake", "Makgeolli", "Umeshu", "Beer", "Whisky", "Wine", "Shochu", "Soju",
                         "Spirit", "Cocktail"])
    en = wb.create_sheet("New Entry")
    en.append(CORE_HEADERS[:16])

    sd = wb.create_sheet("Sake Detail")
    sd.append(["ID", "Name", "Grade", "Milling % (RPR)", "Rice", "Yeast", "SMV", "Acidity"])
    sake_rows = [("sake-a", "Junmai Ginjo", 60, "Aiyama", None, 3.5, 1.8), ("sake-b", "Daiginjo", 40, None, None, -20, None),
                 ("sake-j", "Junmai", 70, None, None, None, None), ("sake-k", "Junmai", 70, None, None, None, None),
                 ("sake-l", "Tokubetsu Honjozo", None, None, None, None, None),
                 ("orphan-id", "Junmai", 60, None, None, None, None)]
    for i, r in enumerate(sake_rows, start=2):
        sd.append([r[0], FORMULA.format(r=i), *r[1:]])
    for r in range(len(sake_rows) + 2, 20):  # formula rows with no ID, as in the real ledger
        sd.append([None, FORMULA.format(r=r)])
    _list_dv(sd, "C", ["Junmai Daiginjo", "Junmai Ginjo", "Tokubetsu Junmai", "Junmai", "Daiginjo", "Ginjo",
                       "Tokubetsu Honjozo", "Honjozo", "Futsushu"])

    wd = wb.create_sheet("Wine Detail")
    wd.append(["ID", "Name", "Vintage", "Grape(s)", "Appellation", "Colour", "Sweetness", "Oak"])
    wd.append(["wine-e", FORMULA.format(r=2), 2025, "merlot,  Cabernet Sauvignon", "Medoc", "Red", None, None])
    for n in ("Whisky Detail", "Shochu Detail"):
        ws = wb.create_sheet(n)
        ws.append(["ID", "Name", "Age Statement", "Cask Type", "Region", "Bottler", "Single Cask or Blend",
                   "Cask Strength", "Peated (ppm)"] if n == "Whisky Detail"
                  else ["ID", "Name", "Base Ingredient", "Koji", "Distillation", "Maturation"])
    od = wb.create_sheet("Other Detail")
    od.append(["ID", "Name", "Base", "Flavouring or Botanicals", "Maturation", "Sweetness", "Yeast", "Type"])
    od.append(["beer-g", FORMULA.format(r=2), None, None, None, None, "Ale yeast", "IPA"])
    od.append(["umeshu-h", FORMULA.format(r=3), None, None, None, None, None, "IPA"])  # invalid for umeshu
    od.append(["soju-i", FORMULA.format(r=4), "Rice", None, None, None, None, None])

    tn = wb.create_sheet("Tasting Notes")
    heads = ["ID", "Name", "Clarity", "App Intensity", "Colour", "App Other", "Nose Condition", "Nose Intensity",
             "Aroma", "Sweetness", "Acidity", "Umami", "Alcohol", "Body", "Mousse", "Flavour Intensity", "Flavour",
             "Palate Other", "Finish", "Quality", "Category", "Ginjo?", "Production", "Special Style"]
    tn.append(heads)
    row = {h: None for h in heads}
    row.update({"ID": "sake-b", "Name": FORMULA.format(r=2), "Clarity": "clear", "Colour": "colourless",
                "Aroma": "pear, melon", "Sweetness": "off-dry", "Quality": "good"})
    tn.append([row[h] for h in heads])
    _list_dv(tn, "J", ["dry", "off-dry", "medium-dry", "medium-sweet", "sweet", "luscious"])
    _list_dv(tn, "T", ["faulty", "poor", "acceptable", "good", "very good", "outstanding"])

    if with_producers:
        pr = wb.create_sheet("Producers")
        pr.append(["Producer", "Page Key", "Display Name", "Native Name", "Brands", "Location", "Region",
                   "Country", "Founded", "Master", "Website", "About", "Related", "Sources", "Status"])
        pr.append(["Alpha Shuzo", "alpha-shuzo", "Alpha Shuzo", "アルファ", "Alpha", "Iwaki, Fukushima",
                   "Fukushima", "Japan", 1850, "Mr Tanaka", "https://alpha.example", "Secret draft story ALPHA.\n\nSecond paragraph.",
                   "beta-brewery:sister brewery", "https://draftsrc.example", "draft"])
        pr.append(["Beta Brewery", "beta-brewery", "Beta Brewery", None, None, "Kobe, Hyogo", "Hyogo", "Japan",
                   1900, None, "https://beta.example", "Approved story BETA.", "alpha-shuzo:sister brewery",
                   "https://src.example/b", "approved"])
        pr.append(["Machida Shuzo", "machida-shuzo", "Machida Shuzo", None, "Machida", "Gunma", "Gunma", "Japan",
                   None, None, None, None, None, None, "draft"])
        pr.append(["Machida Shuzoten", "machida-shuzo", "Machida Shuzo", None, "Machida Shuzoten", "Gunma", "Gunma",
                   "Japan", None, None, None, None, None, None, "draft"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def make_photos(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)

    def save(name, size=(900, 1200), color=(120, 80, 40), orientation=None):
        im = Image.new("RGB", size, color)
        # a marker so uprightness can be tested: the top-left quadrant is white
        for x in range(size[0] // 2):
            for y in range(size[1] // 8):
                im.putpixel((x, y), (255, 255, 255))
        exif = Image.Exif()
        exif[0x010F] = "SecretCameraMaker"
        exif[0x0110] = "SecretModel"
        if orientation:
            exif[0x0112] = orientation
        im.save(folder / name, "JPEG", exif=exif)

    save("Alpha Junmai Ginjo Nama.jpg")
    save("Alpha Junmai Ginjo Nama (back label).jpg", color=(40, 80, 120))
    save("Delta (Honey-Yeast) Craft Sake.jpg")
    save("Beta Daiginjo.jpg", size=(1200, 900), orientation=6)  # stored sideways, relies on EXIF
    save("Obuse Numero Six 【小布施 Numero SIX】.jpg")
    save("Beta Dai.jpg")             # prefix only: suggestion, never auto-published
    save("photo_2026-06-26_12-29-32.jpg")  # unmatched generic export


def make_project(root: Path, **kw):
    """Create <root>/Drinks Ledger.xlsx, <root>/Photos, <root>/New and an empty Ship tree. Returns Ship path."""
    ship = root / "Ship"
    (ship / "content").mkdir(parents=True, exist_ok=True)
    (ship / "docs").mkdir(parents=True, exist_ok=True)
    (ship / "content" / "photo-map.json").write_text("{}", encoding="utf-8")
    (ship / "content" / "subcategories.json").write_text('{"sake/junmai-ginjo": {"explainer": "x", "facts": []}, '
                                                          '"sake/zzz-unused": {"explainer": "y", "facts": []}}',
                                                          encoding="utf-8")
    (ship / "content" / "glossary.json").write_text('{"Nama": "Unpasteurised.", "Unusedterm": "Nope."}',
                                                     encoding="utf-8")
    (root / "New").mkdir(exist_ok=True)
    make_workbook(root / "Drinks Ledger.xlsx", **kw)
    make_photos(root / "Photos")
    return ship
