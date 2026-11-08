# Plan 05: Data build step ("The cellar")

Status: **Approved design. The owner has answered every open question (§12).**
Author: Claude (designer). This is a plan only. Nothing here is built yet. Implementation belongs to the `shipper` subagent (`.claude/agents/shipper.md`).
Depends on: Plans [01](01-welcome-page.md)–[04](04-producer-page.md). This plan produces every data file and image those pages read.
Data snapshot: `Drinks Ledger.xlsx` and `Photos/` as of 2026-10-30.

---

## 1. Purpose

GitHub Pages only serves static files, so the site can't read Excel. The **build step** is a local script that turns the private sources into the public site data:

- **Private sources:** the ledger and the original photos.
- **Public output:** JSON plus resized images.

```
Drinks Ledger.xlsx ─┐                          ┌─► docs/data/*.json        (Plans 01–04)
Photos/ ────────────┼─►  build  ─► checks ─────┼─► docs/img/{labels,thumbs,web}/*.webp
Ship/content/*.json ┘    (local)   + privacy   └─► reports/ (warnings, contact sheet; never published)
```

### Principles

1. **One command:** the owner runs it after editing the ledger, then pushes.
2. **Read-only on sources:** it never writes to the ledger, `Photos/` or `New/`.
3. **Deterministic:** the same inputs give byte-identical outputs, so git diffs only show real changes.
4. **Incremental images:** only new or changed photos are re-encoded.
5. **Private by construction:** private fields are never read into the output model at all. On top of that, a final scan **fails the build** if anything private leaks (§8).
6. **Loud but forgiving:** data gaps produce **warnings**, and the site still builds. Only broken references or privacy leaks are **errors** that stop it.

---

## 2. Folder layout (final, for the whole project)

```
Liquid Assests/                     ← owner's working folder (NOT pushed)
├─ Drinks Ledger.xlsx               ← private source of truth
├─ Photos/                          ← private original photos
├─ New/                             ← inbox: photos of drinks not yet logged
└─ Ship/                            ← the git repository "Liquid-Assets" (pushed)
   ├─ plans/                        ← these plan documents
   ├─ content/                      ← hand-edited inputs (versioned)
   │  ├─ photo-map.json             ← drink ID → photos and crops (Plan 01 §6.1)
   │  ├─ subcategories.json         ← explainer copy (Plan 02 §9)
   │  └─ glossary.json              ← term definitions (Plan 03 §9)
   ├─ build/                        ← the build script, its tests and requirements.txt
   ├─ docs/                         ← SITE ROOT served by GitHub Pages
   │  ├─ index.html, assets/        ← hand-written site code. The build edits only the marked
   │  │                               `build:assets` block in index.html (version stamps), and
   │  │                               writes assets/og-image.png and favicon.png (§14)
   │  ├─ data/                      ← GENERATED. Wiped and rebuilt each run
   │  └─ img/                       ← GENERATED. Incrementally updated
   └─ reports/                      ← GENERATED. git-ignored, local only
```

**Path correction for Plans 01–04:** those plans originally wrote output paths as `Ship/data/…`, `labels/…`, `thumbs/…` and `photos/web/…`. In the final layout they live at:

| Earlier path | Final path (Plans 01–04 have been updated to match) |
|---|---|
| `Ship/data/…` | `Ship/docs/data/…` |
| `labels/…` | `Ship/docs/img/labels/…` |
| `thumbs/…` | `Ship/docs/img/thumbs/…` |
| `photos/web/…` | `Ship/docs/img/web/…` |
| `Ship/data/photo-map.json` | `Ship/content/photo-map.json` (an input, not published) |

Paths inside the JSON stay **relative to `docs/`**, for example `img/thumbs/<id>.webp`, as Plan 01 §8 requires.

---

## 3. Tooling

| Need | Choice | Status on the owner's PC |
|---|---|---|
| Language | Python 3.14 | Installed |
| Excel reading | `openpyxl` 3.1.x | Installed (3.1.5) |
| Images | `Pillow` 12.x with WebP | Installed (12.3.0, WebP supported) |
| Tests | `pytest` | **Not installed.** Add to `build/requirements.txt` |

- No Node, no bundler and no database.
- `build/requirements.txt` pins exact versions.
- The script must print UTF-8 regardless of the Windows console code page, because the ledger contains ★, kanji, hangul and 【】.

---

## 4. How the owner runs it

The owner double-clicks **`Ship/build/build.bat`**, or runs:

```bash
python Ship/build/build.py
```

| Option | Effect |
|---|---|
| *(none)* | Full build: data plus incremental images, then checks and the report |
| `--check` | Validate and report only. Nothing is written to `docs/`. |
| `--force-images` | Re-encode every image, for example after changing a size or quality setting |
| `--ledger PATH` / `--photos PATH` | Override the default locations (`../Drinks Ledger.xlsx`, `../Photos`, relative to `Ship/`) |

- **On finishing,** the script prints a short summary (counts, warnings, errors) and the path to `reports/build-report.html`. The exit code is non-zero on errors.
- **Excel open with unsaved changes:** when `~$Drinks Ledger.xlsx` (Excel's lock file) exists, the build warns that unsaved edits won't be included, and continues with the saved file.

---

## 5. Pipeline stages

### S1. Load

- Open the ledger **read-only**. Read the sheets listed in CLAUDE.md, plus the new `Producers` sheet.
- Read headers **by name, not position**, so adding or reordering columns can't break the build.
- **Missing optional columns or sheets** (`Public Notes`, `Visit Note`, `Producers`, `Other Detail.Type`) count as empty, with a warning given **once**, so the build works before the data-prep tasks are done.
- Detail-sheet `Name` cells are formulas. Ignore them, because names come from `Core`. Skip rows with no `ID`.
- Read each sheet's **data-validation lists** (Plan 01 §4.1, Plan 03 §6), so scales and grade lists follow the ledger.
- **Never load** `Notes` or `Price` text into anything except the fields allowed in §8.

### S2. Normalise

| Field | Rule |
|---|---|
| Strings | Trim, collapse doubled spaces, Unicode-normalise (NFC). Accents and kanji are kept for display. |
| `ABV %` | Number or empty. It's currently a mix of int, float and empty. |
| `Price (S$)` | Number with 2 decimal places, or empty |
| `Size` | Keep the label, and work out `ml` for sorting ("1.8L Magnum" = 1800, "60ml Tasting" = 60, a bare "Bottle" = unknown and sorted last) |
| `Style(s)` | Split on commas, trim, remove duplicates, keep order |
| `Added` / `Acquired` | Parse `YYYY-MM-DD[ HH:MM]` into an ISO date. Anything unparseable gets a warning. |
| `Bought From` | `"Unknown"` becomes empty (Plan 03 §8.2) |
| `Favourite` | `★` = true |

### S3. Combine occasions into drinks

Group Core rows by `ID`. Today that's 290 rows into 265 drinks.

| Field | Rule (Plan 02 §10) |
|---|---|
| `favourite` | True if **any** row is ★ |
| `occasions` / `visits` | One entry per row, in ledger order |
| `sizes` | Unique, sorted by ml |
| `added` | The latest date across rows |
| Everything else | Taken from the **first** row. Any disagreement gets warning `W06`. |
| `story` | The first non-empty `Public Notes` |

### S4. Join details

- Join `Sake / Whisky / Wine / Shochu / Other Detail` and `Tasting Notes` on `ID`.
- A detail row whose ID isn't in Core produces `W11` and is dropped.
- Build the **spec list** (Plan 03 §5) and the **facts** (Plan 02 §7.2) here, so the pages need no logic per category.

### S5. Classify

Assign `category` and `sub` for each drink (Plan 01 §4 and §8):

- **Sake:** grade from the `Sake Detail` validation list order, with Craft Sake, then Ungraded last.
- **Makgeolli:** a single `all` bottle.
- **Liqueur:** `Core.Category = Umeshu` gives the `umeshu` bottle, and `Core.Category = Liqueur` gives the kind from `Other Detail.Type` (Plan 01 §4.3). For umeshu rows, `Other Detail.Type` holds the flavour/base, which becomes a card fact rather than a subcategory.
- **Beer, Cocktail, and Spirit types:** from `Other Detail.Type`, which is checked against the values allowed for that category (`W03` when it doesn't fit, for example "IPA" on an umeshu).
- **Wine:** single grape, or else `blend`. Grape names are normalised for case and spacing.
- **Unfilled Type:** the drink goes into the category's fallback bottle (Plan 01 §4, shared rule).
- **Unknown `Core.Category`:** gives `W07`. The drink is listed in the report and left out of the shelves, but it still gets a drink page.
- **Empty subcategories** are dropped from `shelf.json` (`I01`, info only).

### S6. Producers

- Join the `Producers` sheet on the exact `Producer` text, then resolve **Page Key** aliases and merges (Plan 04 §8).
- Fields gated by `Status`: everything beyond the Core-derived fields (About, Founded, Master, Website, Sources, Native Name, Brands, Related) is published **only** when `Status = approved` (Plan 04 §8).
- `Unknown` never gets a page.
- Work out "More from this producer", "More from {Region}" and tallies.
- Warnings:
  - `W04`: producer missing from the Producers sheet. It falls back to Core fields, with the Page Key set to a slug of the Producer text.
  - `W05`: a Japanese Region that isn't one of the 47 prefectures.
  - `W08`: rows in an alias group disagree.

### S7. Photo map

`content/photo-map.json` is hand-curated, and the build **never overwrites it**.

1. Load the manual entries. **Manual always wins.**
2. For drinks with no manual entry, **auto-match** using the Plan 01 §6.1 rules. Front versus other views is decided by these filename suffixes: `(back label)`, `(side label)`, `(second photo)`, `(spec panel)`, `(maker panel)`, `(n)`, plus the dotted forms `.FRONT` and `.BACK` before the extension (for example `Odayaka Junmai Daiginjo 30th Anniversary Sake.FRONT.jpg`; added 2026-10-30). Bracketed text that's part of a drink's name, such as `(Honey-Yeast)` or `(Fukushima Akatsuki)`, is **not** a view suffix.
3. **Exact matches** are used straight away. **Prefix or fuzzy matches** are *not* used. They're written to `reports/photo-map.suggested.json` for the owner to copy into the real map after review (§12 Q2).
4. Report **unmatched photos** (`W01`, 41 today) and **drinks without a photo** (`W02`).

Photo-map entry format:

```jsonc
"against-the-grain-normat-tokubetsu-junma": {
  "front": "Against The Grain.jpg",
  "others": [ { "file": "…", "kind": "back" } ],
  "labelCrop": [0.15, 0.30, 0.70, 0.50],   // optional; x, y, w, h fractions
  "thumbCrop": [0.05, 0.10, 0.90, 0.85]    // optional
}
```

### S8. Images

For each mapped photo:

| Output | Size | Crop | Quality |
|---|---|---|---|
| `img/labels/<id>.webp` | 320px wide | `labelCrop`, default x 15–85%, y 30–80% | WebP 75 |
| `img/thumbs/<id>.webp` | 480 × 640 (3:4) | `thumbCrop`, default the largest centred 3:4 | WebP 75 |
| `img/web/<id>-<n>.webp` | 1200px long edge | none | WebP 80 |

- **Rotate using the EXIF orientation first.** 4 of today's photos are stored sideways and rely on it.
- **Strip all metadata** from every output, including EXIF, GPS and the camera model. No current photo has GPS data, but phone photos added later might.
- **Never upscale.** The smallest photo today is 654×784.
- **Incremental:** a manifest at `build/.image-cache.json` (git-ignored) stores a hash of the source file, crop and settings for each output, and unchanged outputs are skipped. Outputs whose drink or photo is gone are **deleted**.
- **Naming:** files are named by drink ID only. Original filenames never appear in the output.

### S9. Emit JSON

Everything is written to `docs/data/`, and the directory is wiped first:

| File | Plan | Used by |
|---|---|---|
| `shelf.json` | 01 §8 | Welcome page |
| `drinks.json` | 02 §10 | Shelf list pages, "More from" cards |
| `drinks/<id>.json` | 03 §10.1 | Drink page |
| `producers.json` | 04 §9 | Makers index, map |
| `producers/<key>.json` | 04 §9 | Producer page |
| `subcategories.json`, `glossary.json` | 02 §9, 03 §9 | Copied from `content/`, keeping only keys that are in use |
| `build.json` | — | `{ generated, drinkCount, producerCount, version }` for the site footer |

- **Stable output:** keys in a fixed order, arrays in their defined display order, 1-space indentation, UTF-8 without escaping (kanji stays readable), and a trailing newline.
- `generated` is the only field that changes on every run. It holds the ledger **file's last-modified time**, **not** the build time and not Excel's internal property (which can be stale), so rebuilding unchanged data produces no diff.

### S10. Checks

| Check | Fails the build? |
|---|---|
| **Privacy scan:** every file in `docs/data/` contains none of: `Invoice`, `Sweep batch`, `converted at`, `mid-market`, `corrected from`, or any original photo filename | **Error `E02`** |
| No published record has a `notes` field, and no `draft` producer has published research | **Error `E02`** |
| Every `id`, `key`, `sub`, `prev`/`next`, `moreFrom…` and image path points to something that exists | **Error `E03`** |
| Every subcategory route in `shelf.json` has at least one drink | **Error `E03`** |
| Each JSON file matches its schema (types and required fields) | **Error `E04`** |
| Golden counts are logged for review (drinks, per category, per subcategory), compared with the previous build | Info. Big drops get `W12`. |

### S11. Report

`reports/build-report.html` is one local page, never published, with:

1. **Summary:** counts, errors and warnings, and changes since the last build (drinks added or removed, photos added).
2. **To do for the owner:** warnings grouped by code, each pointing to the sheet, row and drink name. For example *"W03 · Other Detail row 12 · Under 15M · Type 'Classic' isn't a beer style"*.
3. **Contact sheet:** every label crop and thumbnail crop beside the original, so crops can be checked and corrected in `photo-map.json`.
4. **Inbox:** files in `New/`, shown as *"photos waiting to be logged"* with thumbnails. They're listed only and never processed.

---

## 6. Warning and error codes

| Code | Meaning | Today |
|---|---|---|
| E02 | Privacy leak in output | Must be 0 |
| E03 | Broken reference | Must be 0 |
| E04 | Schema violation | Must be 0 |
| W01 | Photo not matched to any drink | 40 (first build) |
| W02 | Drink has no front photo | 93 (first build) |
| W03 | `Other Detail.Type` not valid for the category | — |
| W04 | Producer missing from Producers sheet | 152 until the sheet exists |
| W05 | Japanese Region isn't one of the 47 prefectures | — |
| W06 | Rows sharing an ID disagree on a field | 0 today (favourite is handled by the "any" rule) |
| W07 | Unknown Core.Category | 0 |
| W08 | Alias rows disagree | — |
| W09 | Sake grade not in the validation list | 0 |
| W10 | Category falling back to a single bottle because Type is unfilled | Beer and Cocktail, plus Spirits' `other` bottle, until Type is filled |
| W11 | Detail row with no matching Core ID | 0 |
| W12 | Count dropped sharply since the last build | — |
| I01 | Empty subcategory hidden | Tokubetsu Honjozo |

---

## 7. Ledger changes needed (consolidated from Plans 01–04)

The build must tolerate every one of these being missing (§5 S1).

| Where | Change | From |
|---|---|---|
| `Core` | New column `Public Notes` (per drink) | Plan 03 Q1 |
| `Core` | New column `Visit Note` (per row) | Plan 03 Q1 |
| `Other Detail` | Fill `Type` for Beer, Spirit, Cocktail, Umeshu (flavour/base) and any Liqueur (kind). Add the combined dropdown list to `H2:H400`. **Add rows for the 3 umeshu.** | Plans 01 and 02 |
| New sheet `Producers` | The columns from Plan 04 §8, with one row per `Core.Producer` | Plans 03 and 04 |
| `content/photo-map.json` | Manual matches for the 41 unmatched photos, plus crop fixes from the contact sheet | Plan 01 §6 |

---

## 8. Privacy model

There are two layers, so one mistake can't leak anything.

1. **Allow-list on read.** The output model is built from an explicit list of allowed fields. Anything not on it is never copied out of the ledger.
   - **Allowed:** ID, Name, Category, Size, ABV, Producer, Origin, Country, Style(s), Bought From, Price, Rating, Favourite, Added/Acquired (as dates), Public Notes, Visit Note, all detail-sheet fields, all tasting fields, and approved Producers fields.
   - **Never read into the output:** `Notes`, any column not on the list, original filenames, and `draft` research.
2. **Deny-scan on write.** The S10 privacy scan checks every published file for known private markers, and fails the build if it finds one.

Also, photo metadata is stripped (S8), and the ledger and original photos live **outside** the repository (§2).

---

## 9. Data-prep tasks (one-off, separate from the build)

These are content jobs, not code. Each produces drafts that the owner reviews **in the ledger or `content/`**, and the build then picks them up.

| # | Task | Output |
|---|---|---|
| D1 | ~~Draft `Public Notes` and `Visit Note` from the existing `Notes`~~ | **Dropped by the owner (2026-11-08):** no drink stories. The columns stay optional and empty, and drink pages show no Story board. |
| D2 | Research and draft the `Producers` sheet (152 rows), with sources | Rows with `Status = draft` |
| D3 | Propose `Other Detail.Type` values for Beer, Spirit, Cocktail and Umeshu (about 13 drinks) | Suggested values  **Done (owner approved 2026-11-08):** `kavalan-dry-single-malt-highball` and `kavalan-highball-whisky-soda` are Highball, `underwater-sake-yeast-beer` is Specialty, and `under-15m` is Pale Ale (a best guess, since no style is printed). The spirits were typed on 2026-11-03 (Plan 10 D7). |
| D4 | Match the 41 unmatched photos, and check crops on the contact sheet | `content/photo-map.json` entries |
| D5 | Write copy for `subcategories.json` and `glossary.json` from the Plan 02 §9 and Plan 03 §9 drafts | Two content files |

Plan 06 (deployment) covers how a new drink goes from `New/` to the ledger to the live site.

---

## 10. Testing

These are pytest tests in `build/tests/`, using a **small fixture workbook** with about 10 drinks that covers every awkward case seen in the real data:

- A repeated ID where ★ is on one row only
- Formula `Name` cells on a detail sheet
- An empty Type
- A wine blend
- `Unknown` producer
- An alias producer
- A Unicode filename with `【】`
- A bracketed name that isn't a view suffix
- A sideways EXIF photo

What the tests cover:

1. **Unit tests:** normalise, combine, classify, photo matching and the privacy scan. The scan is given a deliberately leaked string and must fail.
2. **Golden test:** building the fixture twice produces byte-identical `docs/data/`.
3. **Snapshot of real counts** (optional, run locally): 265 drinks; Sake 242 (with the 11 bottles from Plan 01 §4.1); Makgeolli 5; Liqueur 3 (all Umeshu); Beer 2; Wine 3; Spirits 8; Cocktails 2. That's 265 in total, with no drink left out.

---

## 11. Performance

- **First run:** encoding 280 photos into 3 sizes takes roughly 1–3 minutes on a normal laptop.
- **Later runs:** about 5 seconds, since only data is rebuilt and only changed images are re-encoded.
- **Published size:** about 50MB of images plus about 1MB of JSON.

---

## 12. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | Repository layout | **`Ship/` is the git repo**, holding plans, content, the build script and the site in `docs/`. The ledger, `Photos/` and `New/` stay only on the owner's PC (§2). The owner also asked for a **Sonnet subagent to handle shipping from these plans**, defined in `.claude/agents/shipper.md`. |
| Q2 | Fuzzy photo matches | **Wait for owner confirmation.** Exact matches publish automatically. Prefix and fuzzy matches go to `reports/photo-map.suggested.json` (§5 S7). |
| Q3 | Where the build runs | **Locally only** (`build.bat`). No GitHub Actions, and no private data uploaded (§4). |
| Q4 | Timing of data-prep tasks D1–D5 | **In parallel** with building the site (§9). |

---

## 13. Acceptance criteria

- [ ] `build.bat` produces all the files in §5 S9 and the images in S8 from the current ledger, with 0 errors.
- [ ] A second run with no changes produces **no git diff** in `docs/` and re-encodes no images.
- [ ] Deleting a drink from the ledger removes its JSON and images on the next build.
- [ ] The build works with none of the §7 ledger changes made, giving warnings rather than errors.
- [ ] Planting `Invoice` in a published field makes the build **fail** with E02.
- [ ] No output image keeps any EXIF data, and the 4 sideways photos come out upright.
- [ ] The report lists every warning with sheet, row and drink name, shows the crop contact sheet, and lists the `New/` inbox.
- [ ] Real-data counts match §10.3, and every drink appears in exactly one category.

---

## 14. Amendments after the first build (2026-10-30, designer)

The shipper's first build raised 8 issues. Here is how each one was resolved:

| # | Issue | Resolution |
|---|---|---|
| 1 | The photo counts differ from this plan's estimates, and the Odayaka `.FRONT` / `.BACK` photos weren't recognised | Counts updated in §6. The dotted suffixes were added to S7. |
| 2 | Fallback bottle naming inside a mixed category (Spirits) | Plan 01 §4 shared rule amended: an **"Other {category}"** bottle with key `other` when some drinks in the category have a sub-type, and a single **`all`** bottle when none do. |
| 3 | `draft` producer rows: which fields are held back | Everything beyond the Core-derived fields, including Native Name, Brands and Related. Plan 04 §8 and S6 aligned. |
| 4 | Producer blurb length on the drink page | The first paragraph of About only (Plan 03 §7). |
| 5 | The shipper wrote the "WSET-style tasting ⓘ" sentence, and composed the umeshu explainer lines | Accepted. The sentence belongs in `content/glossary.json` so the owner can edit it. |
| 6 | `.bat` line endings, and `404.html` links on github.io | Accepted: CRLF for `.bat` (Plan 06 §3), and the small path-fix script in `404.html`. |
| 7 | Source of the `generated` timestamp | The ledger file's last-modified time (S9). |
| 8 | Warning and error codes added beyond §6 (W13–W20, E01, E05) | Accepted. The build report and `build/liquid/checks` are the full reference. |

**Before launch, the shipper still needs to do these (from its report):**

- Version-stamp the JS and CSS URLs the same way as the data (Plan 06 §7). Otherwise, for up to 10 minutes after a deploy, the new data can meet old code.
- Generate the Open Graph share image and the PNG favicon fallback (Plan 06 §8).
- Rename the Spirits fallback bottle to "Other spirits" with key `other` (resolution 2).
- Move the WSET sentence into `content/glossary.json` (resolution 5).
- Recognise the `.FRONT` / `.BACK` suffixes (resolution 1).

**Second pass (2026-10-30):** all five pre-launch fixes are done, and the designer checked them: 34 tests pass, the privacy scan is clean, and pages work at 1440 and 375px. Three further decisions:

- The build owns the marked `build:assets` block in `docs/index.html` and the two generated PNGs. The §2 layout is updated to say so.
- Asset versioning uses an import map, which needs Chrome 89+, Safari 16.4+ or Firefox 108+ (all 2023 or newer). That's accepted for a personal site.
- The share image's counter boards (formerly brass plaques) are blank in the generated PNG. It's cosmetic polish for later: either add the plaque text, or draw the plaques without the blank bars.

**Third pass (2026-10-30), from the owner's new welcome page direction:**

- **Art direction:** Plan 01 §7 is rewritten as a rustic brick-and-timber bar from the owner's reference image, which is kept privately at `Design/welcome-reference.jpg`, outside the repo. New palette tokens apply, and Plans 02–04 now describe brick and oak instead of dark wood.
- **Liqueur:** the `umeshu` category becomes **`liqueur`** (S5 above). Today's 3 drinks form one `umeshu` subcategory at `#/liqueur/umeshu`, and the old `#/umeshu` hashes redirect.
- **Share image:** it has to be redrawn from the new scene. It follows automatically if the build draws it from the same scene artwork.
