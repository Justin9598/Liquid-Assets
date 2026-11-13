# Plan 15: New bottle shells, and each drink in its own bottle

Status: **Approved by the owner (2026-11-13): "otherwise you may build it".** D1 to D4 are confirmed as recommended. `content/bottles.json` starts from the designer's draft list in `Design/bottle-review/proposed.json`, because the owner's first corrections were lost to a fault in the review page, which has since been fixed. The owner's corrections are applied afterwards as a data-only change. Covers the bottles and glasses only. The new backgrounds and the clock come in a later plan, once their pictures exist. No push without the owner's word.

## 1. Brief

- **Today:** each category has one bottle shell, cut from `Design/scene/shells-sheet.webp` (Plan 07 §2). Every sake stands in the same green bottle, every spirit in the same clear bottle, and so on.
- **The owner's request** (2026-11-13):
  - Sakes get a few standard bottle colours, generalised from the owner's own bottles, so each sake stands in the one closest to its real bottle. Non-standard bottles get one of the other shapes.
  - Beer gets glasses and cans.
  - Makgeolli gets the standard bottle and a tall version.
  - Shochu gets a standard shochu bottle.
  - Wine gets wine and champagne bottles.
  - Liqueur and cocktails get a range of shapes.
- **Source pictures:** the owner made them in Gemini from `Design/gemini-prompts.md`. The designer copied them to `Design/scene/shells/` under fixed names (§2).
- **What changes:**
  - one shell per **drink**, not per category;
  - a hand-checked list that says which shell each drink uses (§4);
  - defaults by category, subcategory, size and wine colour for anything the list doesn't name.

## 2. Source sheets

**Location:** `Design/scene/shells/`. These are private; they're read at build time only and never published.

**Layout:** each sheet is a grid of renders on black, with cells numbered left to right, top row first. Some cells span two rows. Gemini sized each sheet itself, so **crop boxes are measured per sheet**, not on a shared grid.

| Sheet | Cells → shell key |
|---|---|
| `sheet-sake-colours.jpg` (1376×768, 4×2) | 1 `sake-green`, 2 `sake-black`, 3 `sake-brown`, 4 `sake-clear`, 5 `sake-frosted`, 6 `sake-cobalt`, 7 `sake-skyblue`, 8 `sake-pink` |
| `sheet-sake-shapes.jpg` (1376×768) | `sake-isshobin`: the tall brown bottle on the left, spanning both rows. `sake-small`: the clear 300 ml bottle, top row. `sake-sparkling`: **the gold-foil bottle**, bottom row second. `sake-craft`: the matte black bottle, top right. The other green sparkling bottle and the second black bottle are spares. |
| `sheet-beer.jpg` (1365×768) | `beer-bottle`, `beer-can`, `beer-can-tall`, `beer-pint` (top row); `beer-tulip`, `beer-weizen`, `beer-stout` (bottom row) |
| `sheet-wine.jpg` (1376×768) | `wine-red`: the tall left bottle. `wine-white`: top row third. `wine-rose`: **the pink bottle**, bottom row. `champagne`: the large right bottle. The brown top-middle bottle and the small champagne are spares. |
| `sheet-shochu-soju.jpg` (1408×768) | `shochu`, `shochu-jar`, `soju`. **The printed file names under each cell must be cropped off.** |
| `sheet-spirits.jpg` (1365×768, 4×2) | Top row: `whisky` (square), `whisky-round`, `gin`, `brandy`. Bottom row 3: `spirit-clear`. The rest of the bottom row are spares. |
| `sheet-makgeolli.jpg` (1376×768) | `makgeolli` (left), `makgeolli-tall` (middle; the right one is the same picture) |
| `sheet-cocktails.jpg` (1408×768, white gutters) | Top row: `cocktail-highball` (cell 1), `cocktail-rocks` (cell 3). Bottom row: `cocktail-coupe` (**the pink one**, cell 6), `cocktail-martini` (cell 7), `cocktail-can` (cell 8). The rest are spares. |
| `sheet-liqueur.jpg` (1408×768, white gutters) | `liqueur`, `liqueur-round`, `umeshu`, `yuzu` |
| `tasting-glass.jpg` (848×1264) | `tasting-glass` (spare: see D1) |

**Replacing a sheet later:** the owner may swap in a sharper (2K) version under the same name. Each bottle is only about 350 px tall at the moment. A replaced sheet needs its crop boxes and polygons measured again; the build flags it (§6, W29).

## 3. Cutting the shells

The cutting work from Plan 07 §2.2 stays as it is: crop box, mask polygon, base line, contact shadow, and 1x/2x WebP output into `docs/img/scene/`. `content/shells.json` gains a `source` field per shell, naming its sheet.

### 3.1 Mask mode

| Mode | Shells |
|---|---|
| `opaque` (solid mask) | All coloured or frosted bottles, cans, `makgeolli`, `makgeolli-tall`, `shochu-jar`, `yuzu` |
| `glass` (luminance alpha) | `sake-clear`, `sake-small`, `gin`, `spirit-clear`, every beer and cocktail glass, `tasting-glass` |

- **Amber spirits** (`whisky`, `whisky-round`, `brandy`, `liqueur`, `liqueur-round`, `umeshu`) are mostly liquid, so try `opaque` first. Use `glass` only if the shelf glow should show through.
- **Labels on clear bottles:** on a `glass` bottle, the blank label must come out fully opaque. Force alpha to 1 inside its `labelSheet` rectangle.
- **Floor glow:** several cells have a faint glow under the base. Cut it off at the base line, as with the old sheet.

### 3.2 Labels

| Shell kind | Label rule |
|---|---|
| Any shell with a **blank cream or white paper label** in its render (all sake, `shochu`, `soju`, wine, `champagne`, the spirits and liqueurs, `beer-bottle`, `makgeolli`, `makgeolli-tall`) | `labelRect` = the rendered blank label, inset 2%. **`multiply`** blend, so the shell's shading and paper texture show through, as the sake does today. |
| Cans (`beer-can`, `beer-can-tall`, `cocktail-can`) | `labelRect` on the can body, about 70% of its height and 80% of its width, centred. `normal` blend with the existing curvature overlay, so it reads as the can's print. |
| `shochu-jar` | **No photo label.** The hanging tag stays blank. |
| All glasses | No label (same as today). |

**Old labels:** the old `normal` + curvature treatment for bottles with no paper label is no longer needed for any bottle.

### 3.3 Relative size (`scale`)

Today `scale` comes from pixel height on one sheet. The new sheets are at different zoom levels, so **`scale` is set by hand** in `shells.json`. It keeps shelves readable rather than strictly true to life.

| Scale | Shells |
|---|---|
| 1.00 | every 720 ml sake colour, `sake-isshobin`, `sake-sparkling`, `wine-*`, `champagne`, `makgeolli-tall` |
| 0.95 | `sake-craft`, `shochu`, `whisky`, `gin`, `spirit-clear`, `liqueur`, `umeshu`, `yuzu`, `makgeolli` |
| 0.85 | `whisky-round`, `brandy`, `liqueur-round`, `beer-bottle` |
| 0.80 | `sake-small`, `soju` |
| 0.75 | `beer-weizen`, `cocktail-highball` |
| 0.70 | `beer-pint`, `beer-stout`, `beer-tulip`, `beer-can-tall`, `cocktail-coupe`, `cocktail-martini`, `shochu-jar` |
| 0.60 | `beer-can`, `cocktail-can`, `cocktail-rocks` |
| 0.45 | `tasting-glass` |

- **Width:** wide shells such as `sake-isshobin`, `champagne` and `liqueur-round` keep their true width at their scale. A slot that is too narrow fits by height first, as today (`max-width: 100%`).
- **Isshobin:** this means the isshobin reads as bigger by its width, not its height. That's intended, because it must not hit the shelf above.

## 4. Which shell each drink uses

### 4.1 The list: `Ship/content/bottles.json` (new, hand-edited)

```json
{ "_readme": "…", "bottles": { "<drink ID>": "<shell key>", … } }
```

- **Contents:** the IDs and shell keys only. No names, notes or photo names. It's public in the repo, and that's fine.
- **How it's filled:** the designer drafts a sake list from the owner's photos (§4.3). The owner checks and corrects it, and the approved list goes into the file. Other categories can be added to the list later. They don't need it on day one, because the defaults (§4.2) cover them.

### 4.2 Defaults, used when a drink isn't in the list

The build works these out in order. The first rule that matches wins.

| Category / sub | Rule |
|---|---|
| Sake (all subs) | `sake-green` |
| Fermented / makgeolli | `makgeolli` |
| Fermented / beer styles | **By the drink's sizes:** any bottle size → `beer-bottle`. Can of 400 ml or more → `beer-can-tall`, other cans → `beer-can`. Pint or glass only → the style's glass: `wheat` → `beer-weizen`, `ipa`/`specialty`/`saison` → `beer-tulip`, `stout`/`porter` → `beer-stout`, else → `beer-pint`. |
| Wine | **By `Wine Detail.Colour`:** Red → `wine-red`, White → `wine-white`, Rosé → `wine-rose`, Sparkling → `champagne`. If empty → `wine-red`. |
| Spirits | `whisky` → `whisky` (but `whisky-round` when the country is USA), `gin` → `gin`, `brandy` → `brandy`, `shochu` → `shochu`, `soju` → `soju`, anything else → `spirit-clear` |
| Umeshu | `umeshu` |
| Liqueur | `liqueur` |
| Cocktails | Any can size → `cocktail-can`. Otherwise by sub: `highball` → `cocktail-highball`, else → `cocktail-coupe`. |

**Which size counts:** where a drink has several sizes, the largest bottle or can decides. A 60 ml tasting never decides if there's any other size.

### 4.3 The sake list (designer's job, after this plan is approved)

- **How it's drafted:** the designer looks at each sake's photo and picks the closest shell.
  - **Colour:** one of the eight 720 ml colours.
  - **Shape:** where the bottle clearly isn't a 720 ml yotsugo-bin, one of `sake-isshobin`, `sake-small`, `sake-sparkling` or `sake-craft`.
  - **No good fit:** an odd bottle that fits none of these gets the nearest shape in **any colour that suits it** (the owner's "random colour" rule).
- **For the owner:** it's delivered as a private review page in `Design/` showing each sake's photo next to its proposed shell, with the IDs. The owner corrects it in chat or on the page.
- **Into the site:** the approved list goes into `content/bottles.json`.
- **Drinks with no photo:** sakes without a photo stay on the default (§4.2) and are listed in the page so the owner can pick one if they remember.
- **The draft is ready** (2026-11-13): `Design/bottle-review.html`, with the proposal as `Design/bottle-review/proposed.json`. It covers 184 sakes with photos:

  | Shell | Count |
  |---|---|
  | `sake-black` | 54 |
  | `sake-green` | 48 |
  | `sake-brown` | 25 |
  | `sake-frosted` | 21 |
  | `sake-clear` | 16 |
  | `sake-small` | 5 (the 180 ml and 300 ml bottles) |
  | `sake-sparkling` | 4 |
  | `sake-skyblue` | 4 |
  | `sake-cobalt` | 4 |
  | `sake-pink` | 1 |
  | `sake-craft` | 1 |
  | `sake-isshobin` | 1 |

  73 sakes have no photo.

### 4.4 Where the drink's own shell is used

**The rule:** wherever a bottle stands for **one particular drink**, it uses that drink's shell. Where it stands for a **category or subcategory with no particular drink**, it uses the category's default shell from §4.5.

| Place | Shell |
|---|---|
| Welcome counter picks | The pick's drink |
| Welcome shelves: a category or subcategory bottle wearing a label photo from one drink | **That drink's shell** (the label already comes from it) |
| Welcome shelves: a bottle with the fallback drawn label | The category default (§4.5) |
| Shelf page hero | As welcome: the shell of the drink whose label is shown, else the default |
| Shelf cards, drink page with no photo, producer ledge | The drink's own shell |

### 4.5 Category defaults (for bottles with no particular drink)

| Category / sub | Default |
|---|---|
| sake (all subs) | `sake-green` |
| fermented | `beer-bottle` |
| fermented/makgeolli | `makgeolli` |
| fermented/ipa, specialty, saison | `beer-tulip` |
| fermented/wheat | `beer-weizen` |
| fermented/lager, pale-ale | `beer-pint` |
| wine | `wine-red` |
| spirits | `whisky` |
| spirits/gin | `gin` |
| spirits/brandy | `brandy` |
| spirits/shochu | `shochu` |
| spirits/soju | `soju` |
| umeshu | `umeshu` |
| liqueur | `liqueur` |
| cocktails | `cocktail-highball` |

**Note:** this changes the welcome page's beer subcategory bottles from the brown bottle to glasses. Glasses carry no label photo, so those slots show the slate tag only, as the cocktail glasses do today.

## 5. Data and code changes

- **Build** (`liquid/shells.py`, `pipeline.py`):
  - read `source` per shell;
  - set `scale` from `shells.json` rather than measuring it;
  - force opaque labels on glass shells;
  - emit the new shell keys into `data/scene.json`.
- **Retiring the old sheet:** `shells-sheet.webp` is no longer read. Delete the old keys (`sake`, `makgeolli`, `wine`, `beer`, `spirits`, `liqueur`, `cocktail`, `highball`) and their WebP files from `docs/img/scene/`.
- **Mask polygons:** derive them with `derive_shell_masks.py` (taught to read `source`), then check every one by eye on the plate.
- **Build** (drinks): work out each drink's `shell` (§4.1, then §4.2) and add it to `drinks.json` records and the counter-pick data.
- **JS:**
  - `labels.js`: `shapeFor(cat, sub)` returns the §4.5 default keys.
  - New `shellOf(d)`, which returns `d.shell` or falls back to `shapeFor`.
  - `welcome.js`, `counter.js`, `shelf.js`, `shells.js` (`drinkShell`) and `producer.js` follow §4.4.
- **Checks:**
  - **E09:** `bottles.json` names an unknown shell key.
  - **W28:** `bottles.json` names an ID that isn't in Core.
  - **W29:** a shell's crop box falls outside its source sheet, or its source sheet's size has changed since the crop was measured.
  - **Report:** a count of drinks by shell, and a list of sakes on the default.

## 6. Acceptance

- [ ] **Shells on the plate:** the build report's "shells on plate" contact sheet shows all 39 shells over both bar plates' shelf area.
  - No black fringe, no missing rim and no floor glow.
  - Clear-glass labels are fully opaque.
- [ ] **Label contact sheet:** a new contact sheet shows every labelled shell with a sample label photo. Each label sits inside its paper label, multiply-blended, with nothing hanging past the bottle's edge.
- [ ] **Welcome page:** with `bottles.json` holding a test list that covers each sake colour and shape, the shelves and counter show the drink's own shells. Bottles stay inside their slots, and the isshobin doesn't touch the shelf above.
- [ ] **Defaults:** each §4.2 default is right on these drinks: Ardbeg (`whisky`), Woodford Reserve (`whisky-round`), The Botanist (`gin`), Chusa 40 (`brandy`), Kujira no Kuromugi (`shochu`), Hwanggeumbori (`soju`), the three Kavalan/Suntory highballs (cans → `cocktail-can`, else `cocktail-highball`), the makgeolli, a pint beer and a canned beer.
- [ ] **Screenshots** at 1440×900, 1920×1080, 375×812 and 390×844:
  - the welcome page;
  - the sake, beer, spirits and cocktail shelves;
  - one drink page with no photo;
  - one producer page with several bottles.

  Save them in `reports/plan15/`.
- [ ] **Tests:** the full pytest passes with new tests for §4.2 and E09/W28. The build has 0 errors, and the privacy scan is clean (no `Design/` paths or sheet names in `docs/`).
- [ ] **Commits:** "Plan 15 §2–3: new bottle shells from the Gemini sheets", then "Plan 15 §4–5: a shell for each drink". **No push.**

## 7. Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | Should 60 ml tastings show as the tasting glass? | **No.** 112 sake entries are tastings, and a glass carries no label photo, so half the sake shelf would lose its labels. Keep `tasting-glass` cut and ready as a spare. |
| D2 | Should beer drunk by the pint show as a glass instead of a labelled bottle? | **Yes, as §4.2.** Those photos are of the glass anyway. |
| D3 | Should the welcome page's beer subcategory bottles become glasses (§4.5)? | **Yes.** It makes the beer shelf read as beer at a glance. The slate tag names the style. |
| D4 | Delete the old shells sheet's WebP outputs? | **Yes.** The source stays in `Design/scene/`. |
