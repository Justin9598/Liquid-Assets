# Plan 03: Drink detail page ("On the counter")

Status: **Approved design. The owner has answered every open question (§12).** Ledger updates are needed (§12.1).
Author: Claude (designer). This is a plan only. Nothing here is built yet.
Depends on: [01-welcome-page.md](01-welcome-page.md) (palette, bottle shapes, photo map) and [02-shelf-list-page.md](02-shelf-list-page.md) (routes, cards, drinks index).
Data snapshot: `Drinks Ledger.xlsx` as of 2026-10-30.

---

## 1. Concept

Clicking a menu card **sets the bottle down on the bar counter in front of you**. The page is about one drink, and it reads like turning the bottle in your hands:

1. **The bottle:** its photos, front and back.
2. **The label:** what it is, as hard facts (grade, polishing, rice, SMV, ABV…).
3. **The glass:** how it tasted, using the structured tasting card when one exists.
4. **The story:** the public notes.
5. **The maker:** the brewery or distillery, and what else they make that's in the ledger.
6. **The tab:** every time it was had: size, where and price.

Visually it continues the bar scene (Plan 01 §7, revised). The top third is the plank counter top in front of the brick wall, with the bottle photo standing on it in warm light. Everything below is laid out on cream paper panels, the same material as the menu cards in Plan 02.

---

## 2. Route and navigation

- **Route:** `#/drink/<id>`, where `<id>` is the Core `ID`. An unknown ID shows the empty-shelf scene from Plan 02 with a link back to the bar.
- **Breadcrumb:** *Bar › Sake › Junmai Ginjo › Aiyama 'Galaxy'…*. The drink name is shortened in the breadcrumb only.
- **Back to shelf:** returns to the shelf **with its filters still applied**, by restoring the previous hash. When the visitor arrived directly (a shared link), it goes to the plain shelf URL.
- **Previous / next:** moves through the same subcategory in Name A–Z order, using the arrow buttons at the bottom of the hero and the ← / → keys. It wraps around at the ends.

---

## 3. Page anatomy

### Desktop (≥ 1024px)

```
┌──────────────────────────────────────────────────────────────────┐
│ [LIQUID ASSETS]  Bar › Sake › Junmai Ginjo › Aiyama 'Galaxy'…    │
├──────────────────────────────────────────────────────────────────┤
│ ░░░░░░░░░░░░ brick wall · plank counter top, warm light ░░░░░░░░░ │
│   ┌───────────┐    ★ FAVOURITE                                   │ ← HERO
│   │           │    Aiyama 'Galaxy' Kimoto Junmai Ginjo           │
│   │  bottle   │    Origarami Nama                                │
│   │  photo    │    Fukunishiki · Hyogo, Japan                    │
│   │           │    [Sake › Junmai Ginjo]  16.2% · 720ml ×2 visits│
│   └───────────┘    [Nama] [Kimoto] [Origarami]  ← tap = glossary  │
│   ▫ ▫ ▫  thumbnails (front / back / side)                         │
│   ‹ prev                                               next ›    │
├──────────────────────────────────────────────────────────────────┤
│ ┌── THE LABEL ──────────────┐  ┌── THE GLASS ──────────────────┐ │
│ │ Grade      Junmai Ginjo   │  │ Appearance  ● pale, colourless │ │
│ │ Polished   60%  ▓▓▓▓▓▓░░░░ │  │ Nose        light · clean     │ │
│ │ Rice       Aiyama         │  │ Sweetness   ○●○○○○ off-dry    │ │
│ │ SMV  +3.5  sweet ──●── dry│  │ Acidity     ●○○○○ low         │ │
│ │ Acidity    1.8            │  │ …                             │ │
│ └───────────────────────────┘  │ Quality     [ GOOD ] stamp    │ │
│                                └───────────────────────────────┘ │
│ ┌── THE STORY ──────────────────────────────────────────────────┐│
│ │ Public notes paragraph(s)                                     ││
│ └───────────────────────────────────────────────────────────────┘│
│ ┌── THE MAKER ──────────────────────────────────────────────────┐│
│ │ Fukunishiki  富久錦 · Hyogo · est. ____                       ││
│ │ Short producer blurb …                   [Visit producer →]   ││
│ │ More from Fukunishiki (3):  ▭ ▭ ▭ →                           ││
│ └───────────────────────────────────────────────────────────────┘│
│ ┌── THE TAB ────────────────────────────────────────────────────┐│
│ │ 720ml Bottle · Mirai Sake Hall ·                       ││
│ │ 720ml Bottle · Shu Kuu Izakaya ·                       ││
│ └───────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Tablet and phone

- **Tablet:** The Label and The Glass stack into one column. The hero keeps the photo on the left and the text on the right.
- **Phone:** everything stacks. The photo goes full width at the top (max 60% of the screen height), and thumbnails become a row that scrolls sideways inside its container. Previous/next become a slim bar fixed to the bottom of the screen. The page never scrolls sideways.

**Section rule:** a section with no data is **left out entirely**, with no empty boxes. A drink with only Core data still gets a complete-looking page: the hero, The Label (with only the Core fields), The Maker and The Tab.

---

## 4. Hero

| Element | Source | Notes |
|---|---|---|
| Main photo | Front photo from `photo-map.json`, in a **web** size (§10) | Stands on the counter with a faint reflection below it. Clicking opens the lightbox. |
| Thumbnails | Every photo of the drink: front, back label, side label, second photo, spec/maker panels | There are 57 back-label photos. Thumbnails only appear when there are 2 or more photos. |
| No photo | The category's SVG bottle with the subcategory's fallback label (Plan 01 §6.5) | It's labelled in tiny text: "No photo yet". |
| Favourite | `Favourite = ★` on any occasion | Brass ribbon reading "Favourite". |
| Name | `Core.Name` | Full, never cut off. Serif, large. |
| Producer · origin | `Producer`, `Origin`, `Country` | The producer name links to the producer section below, and later to the producer page (§7). |
| Shelf chip | Category › subcategory | Links back to that shelf. |
| Quick facts | ABV, sizes, number of visits | The same formatting rules as the Plan 02 cards. |
| Style tags | `Core.Style(s)` | **Clicking or tapping opens a glossary popover** (§9). Tags can't link to filters, because filters are per shelf. |
| Rating | `Rating` (empty today) | Shown as half-step cup icons once filled, otherwise left out. |

**Lightbox:** full-screen dark overlay. Swipe or arrow keys move between photos, Esc or a tap on the backdrop closes it, and each photo has a caption ("Back label"). The lightbox uses the same 1200px **web** size as the hero (§10.2), so there is no separate large size.

---

## 5. The Label: specification panel

A two-column list of facts, styled like the spec block on the back of a sake bottle: small caps for the field names and tabular numbers. The fields depend on the category, and **empty fields are skipped**.

| Category | Fields, in order (source sheet) |
|---|---|
| **Sake / Craft Sake** | Grade · Polishing ratio · Rice · Yeast · SMV · Acidity (`Sake Detail`), then ABV · Size(s) (`Core`) |
| **Makgeolli, Liqueur, Beer, Gin, Brandy, Cocktail** | Type · Base · Flavouring or botanicals · Maturation · Sweetness · Yeast (`Other Detail`), then ABV · Size(s) |
| **Wine** | Vintage · Grape(s) · Appellation · Colour · Sweetness · Oak (`Wine Detail`), then ABV · Size(s) |
| **Whisky** | Age statement · Cask type · Region · Bottler · Single cask or blend · Cask strength · Peat (ppm) (`Whisky Detail`), then ABV · Size(s) |
| **Shochu / Soju** | Base ingredient · Kōji · Distillation · Maturation (`Shochu Detail`), then ABV · Size(s) |

### Visual extras (sake only, when the value exists)

- **Polishing ratio bar:** a horizontal grain of rice drawn as a bar. The kept portion (for example 60%) is filled and the polished-away portion is ghosted. It sits in the row as a small inline graphic. 190 of the 229 sake detail rows have this value.
- **SMV gauge:** a short horizontal scale with *Sweet* at the left and *Dry* at the right, running from −15 to +15, with a marker at the value. Values beyond the range (Akishika's −20, for example) pin to the end with a small arrow, and the exact number is always printed. 64 sakes have SMV.
- Acidity is shown as a number only. A scale would suggest more precision than the data has (40 values).

---

## 6. The Glass: tasting card

The tasting card uses the `Tasting Notes` sheet, which follows the **WSET Systematic Approach to Tasting for sake**. Only **8 drinks** have one today. For every other drink the section is left out, with no placeholder.

### Layout: three short blocks and a conclusion

| Block | Fields | Display |
|---|---|---|
| **Appearance** | Clarity · Intensity · Colour · Other | A small **colour swatch** circle tinted to match (colourless → lemon-green → lemon → gold → amber → brown), followed by the words, for example "clear · pale · colourless". |
| **Nose** | Condition · Intensity · Aroma | Intensity as a 5-step dot scale. Aroma descriptors as small italic text tags. "Unclean (faulty?)" gets a muted warning colour. |
| **Palate** | Sweetness (6 steps) · Acidity · Umami · Body · Flavour intensity · Finish (5 steps each) · Alcohol (3 steps) · Mousse · Flavour · Other | One row per scale: field name, a dot scale, then the WSET term ("medium(+)"). Mousse appears as a word (delicate / creamy / aggressive). Flavour descriptors appear as tags. |
| **Conclusion** | Quality · Category · Ginjō? · Production · Special style | **Quality** is a rubber-stamp graphic in brass on the paper (FAULTY → OUTSTANDING). Category ("premium") and ginjō or non-ginjō appear as small labelled chips. |

- The scale steps come from the sheet's data-validation lists, so the card always matches the ledger's vocabulary.
- **Partial cards:** most of the 8 have gaps, for example Komesou Brocken Splash has no Quality. Hide any row without a value. If a whole block is empty, hide the block.
- A small "WSET-style tasting" caption with an ⓘ explains the method in one sentence.

---

## 7. The Maker: producer section

The brief asks for *information about the brewery as well*. Today the ledger only has `Producer`, `Origin` and `Country`, across **152 producers**, and none of them has any description.

**What's shown on the drink page:**

| Element | Source |
|---|---|
| Producer name, plus a native-script name if known (for example 旭酒造) | New `Producers` sheet (§10.3) |
| Location (prefecture or region, country) and founding year | `Producers` sheet, falling back to `Core.Origin` / `Country` |
| The **first paragraph** of `Producers.About`; the full text is on the producer page (amended 2026-10-30) | `Producers` sheet |
| Website link | `Producers` sheet |
| **More from this producer** | Worked out by the build step: other drinks in the ledger with the same `Producer` (for example Akebono Shuzo 12, Niida Honke 9, Iinuma Meijo 8), as a row of mini menu cards that scrolls sideways inside its container. Hidden when the producer has only this one drink. |
| "Visit producer →" | Links to the producer's own page, `#/producer/<key>` (Plan 04) |

With no producer blurb, the section still shows the name, location and "More from this producer". It never shows "No information".

**Matching:** producers are matched on the exact `Producer` string. The build step warns about names that are probably the same producer under two spellings (same name once case, punctuation and suffixes like *Shuzo* or *Brewery* are ignored).

---

## 8. The Story and The Tab

### 8.1 The Story: public notes

`Notes` can't be published as it is. Among the 240 drinks with notes, the text mixes three kinds of content:

| Kind | Example | Public? |
|---|---|---|
| Description | "Flagship of Fujioka Shuzo's tiny 'Sokuu' line, hand-made in Fushimi, Kyoto; soft, pear-like fruit…" | ✅ |
| Occasion context | "Sake Hub Hokkaido tasting event", "WSET Level 1", "Drunk at ShuKuu Izakaya on 2026-10-28…" | Belongs in **The Tab**, against that visit |
| Ledger housekeeping | "Sweep batch 1, 2026-09-21: …", "Invoice <number> from <supplier>…", "ABV corrected from 16 to 15…", currency conversions | ❌ never published |

**Decided approach (§12 Q1):** add **two columns** to `Core`. The original `Notes` stays as the private working notes and is **never** published.

- **`Public Notes`** holds the description, and is per drink. The build step uses the first non-empty value across the drink's rows.
- **`Visit Note`** holds the occasion context, and is per row. It appears in The Tab against that visit.

**Migration:** as a separate data-prep task, the existing Notes can be drafted into the two new columns automatically, with housekeeping stripped out. The owner then reviews the drafts in Excel. The build step publishes **only** what is in the new columns, so a drink with empty Public Notes simply has no Story section.

Display: the serif body text, at most about 65 characters per line, with the first letter set as a small drop cap in the brass colour.

### 8.2 The Tab: every occasion

One line per Core row. **94%** of drinks (248 of 265) have exactly one visit, and the maximum is 4.

| Field | Source | Display |
|---|---|---|
| Date | `Acquired`, else `Added` (date part only) | Left out when both are empty, which is most rows today |
| Size | `Size` | "720ml Bottle", "Tasting" … |
| Where | `Bought From` | Shown, as decided in Plan 02 Q2. "Unknown" (20 rows) is left out. |
| Price | `Price (S$)` | "", always 2 decimal places. Left out when empty. |

> *Superseded by [Plan 11](11-no-prices.md) (2026-11-08): prices are no longer published. Visits are listed cheapest first, with no price shown.*

| Visit note | `Visit Note` | Small italic text under the line |

Order: by date, newest first. Rows without a date come after, in ledger order. The heading reads *"The Tab: had 4 times"*. When there is only one visit, the section shrinks to one line inside the hero's quick facts, and the separate panel is left out.

---

## 9. Glossary popovers

Style tags and some spec field names (SMV, Polishing ratio, Kōji, Nuruk, Origarami…) have a dotted underline. Clicking or tapping opens a small paper popover with a one-line definition, closed with Esc, by clicking outside, or by tapping again.

Copy goes in `Ship/content/glossary.json`. Starting drafts for the tags that appear in the ledger:

| Term | Definition |
|---|---|
| Nama | Unpasteurised. Fresher and livelier, and kept cold. |
| Genshu | Undiluted. Bottled at full brewing strength, usually 17–20%. |
| Muroka | Not charcoal-filtered, so it keeps more colour and flavour. |
| Sparkling | Carbonated, either naturally in the bottle or added. |
| Flavoured | Made with added fruit, tea or other ingredients. |
| Kimoto | Traditional starter made by pole-ramming the rice mash. Deep and savoury. |
| Yamahai | Traditional starter without the ramming. Rich, with higher acidity. |
| Mizumoto | Medieval "water starter" method. Often tangy and sweet. |
| Origarami | Lightly cloudy, with a little fine sediment left in. |
| Nigori | Cloudy sake, coarsely filtered so rice solids stay in. |
| Doburoku | Unfiltered, rustic sake with the whole mash left in. |
| Hopped | Brewed or finished with hops. |
| Cask-aged | Matured in wooden casks. |
| Kijoshu | Brewed with sake in place of some water. Sweet and rich. |
| Taruzake | Aged briefly in cedar barrels for a woody aroma. |
| SMV | Sake Meter Value. Higher is drier, lower is sweeter. |
| Polishing ratio | How much of each rice grain remains after milling. Lower means more polished. |
| Kōji | Mould-grown rice that turns starch into sugar. |
| Nuruk | Korean wheat-based fermentation starter. |

---

## 10. Data contract (additions to Plans 01 and 02)

### 10.1 Per-drink file

`Ship/docs/data/drinks/<id>.json` is loaded when the page opens. The shelf index in `drinks.json` stays small.

```jsonc
{
  "id": "aiyama-galaxy-kimoto-junmai-ginjo-origar",
  "name": "…", "category": "sake", "sub": "junmai-ginjo",
  "producer": { "key": "fukunishiki", "name": "Fukunishiki", "native": null,
                "location": "Hyogo, Japan", "founded": null, "about": null, "url": null },
  "abv": 16.2, "styles": ["Nama", "Kimoto", "Origarami"], "favourite": true, "rating": null,
  "spec": [ { "label": "Grade", "value": "Junmai Ginjo" },
            { "label": "Polishing ratio", "value": 60, "unit": "%", "viz": "polish" },
            { "label": "SMV", "value": 3.5, "viz": "smv" } ],          // already ordered, empty fields removed
  "tasting": null,                                                 // or { appearance:{…}, nose:{…}, palate:{…}, conclusion:{…} }
  "story": null,                                                   // Public Notes only, never Notes
  "visits": [ { "date": null, "size": "720ml Bottle", "where": "Mirai Sake Hall", "note": null },
              { "date": null, "size": "720ml Bottle", "where": "Shu Kuu Izakaya", "note": null } ],
  "photos": [ { "kind": "front", "web": "img/web/<id>-1.webp", "w": 1200, "h": 1600 } ],
  "moreFromProducer": ["<id>", "…"],
  "prev": "<id>", "next": "<id>"
}
```

### 10.2 Image sizes

All sizes are made by the build step from `Photos/`. The originals are never published.

| Size | Use | Long edge | Approx. size |
|---|---|---|---|
| `img/labels/` | Welcome page bottle labels (Plan 01) | 320 wide | 20–40KB |
| `img/thumbs/` | List cards and "More from" mini cards (Plan 02) | 480 wide | 30–50KB |
| `img/web/` | Detail hero, thumbnails and lightbox | 1200 | 120–200KB |

The total is roughly **50MB** of published images, well within GitHub Pages' 1GB limit. There is deliberately no larger lightbox size (§12 Q5).

### 10.3 Producer data

The new **`Producers` sheet** in the ledger has these columns: `Producer` (exact match to `Core.Producer`) · `Native Name` · `Location` · `Founded` · `Website` · `About`. The build step joins it on Producer.

### 10.4 Privacy guard

The build step must **never** read `Notes`, invoice text or the original filenames into any published file. An automated check fails the build if any published JSON contains known private markers. The full list is in Plan 05 §5 S10.

---

## 11. Accessibility and performance

- The `<h1>` is the drink name. Sections use `<h2>` (The Label, The Glass…).
- Dot scales say what they mean in text, for example "Acidity: low, 1 of 5", rather than relying on the visual alone.
- The lightbox traps focus while open and returns focus to the thumbnail when closed. The glossary popovers are `<button aria-expanded>` with the definition in a linked region.
- The first view loads the per-drink JSON (about 3KB) plus one `web` photo. Thumbnails and "More from" cards load lazily.

---

## 12. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | How Notes become publishable | **Two new Core columns,** `Public Notes` and `Visit Note`. `Notes` stays private and is never published (§8.1). |
| Q2 | Price paid in The Tab | **Show it** (§8.2). |
| Q3 | Where producer information comes from | **A new `Producers` sheet** in the ledger (§10.3), with blurbs drafted from public sources for owner review. |
| Q4 | Producer pages | **Each producer gets its own page.** Plan 04 is to be written. |
| Q5 | Lightbox photo size | **1200px `web` size only,** with no 2000px size, for about 50MB of images (§10.2). |
| Q6 | Tasting card wording | **WSET terms** ("medium(+)"), with dot scales (§6). |

### 12.1 Data-prep tasks (separate from building the site)

1. **Notes split:** add the `Public Notes` and `Visit Note` columns to `Core`. Draft their contents from the existing `Notes` for all 240 drinks with notes, removing invoices, sweep-batch logs, corrections and currency conversions. The owner reviews the drafts in Excel before publishing.
2. **Producers sheet:** create the `Producers` sheet (§10.3) with one row for each of the 152 `Core.Producer` values. Draft each blurb, native name, founding year and website from public sources, with the sources recorded. Start with the producers that have the most drinks: Akebono Shuzo 12, Niida Honke 9, Iinuma Meijo 8, Fukuchiyo Shuzo 6… The owner reviews before publishing.

---

## 13. Acceptance criteria

- [ ] Every card on every shelf opens `#/drink/<id>`, and every drink ID in the ledger has a page.
- [ ] Sections without data are absent, with no empty boxes. A Core-only drink still shows the hero, The Label (Core fields), The Maker and The Tab line.
- [ ] Sake pages show the polishing bar and SMV gauge when the values exist, and out-of-range SMV pins to the end with the exact value printed.
- [ ] The 8 drinks with tasting notes show the tasting card, with empty rows hidden and the scale steps taken from the sheet's validation lists.
- [ ] "More from this producer" lists the other drinks with the same Producer and is hidden for single-drink producers.
- [ ] Combined drinks list every visit in The Tab, and "Unknown" venues are left out.
- [ ] No published file contains `Notes` text. The privacy guard (§10.4) passes.
- [ ] The lightbox, glossary and previous/next work by keyboard and touch. It works at 375px with no sideways page scroll.
- [ ] Nothing is requested from `Photos/`.
