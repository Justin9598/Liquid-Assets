# Plan 04: Producer page and Makers index ("The Makers")

Status: **Approved design. The owner has answered every open question (§11).**
Author: Claude (designer). This is a plan only. Nothing here is built yet.
Depends on: [01](01-welcome-page.md) (palette, bottle shapes), [02](02-shelf-list-page.md) (menu cards), [03](03-drink-detail-page.md) (Producers sheet, The Maker section).
Data snapshot: `Drinks Ledger.xlsx` as of 2026-10-30. That's 152 distinct `Core.Producer` values.

---

## 1. Concept

The brief asks for *information about the brewery as well*. Each producer gets a page that feels like **a delivery crate from that brewery**:

- A wooden crate end, stencilled with the maker's name, location and founding year.
- Every one of their bottles you've had standing in a row on top of the crate.
- Below that, the maker's story and facts, and the full list of their drinks.

A companion **Makers index** (`#/makers`) lists every producer, so a visitor can browse by brewery instead of by style.

### What the data supports today

| Fact | Number |
|---|---|
| Distinct producer names | 152: 132 in Japan, 8 in South Korea, 2 each in Scotland, Chile, the USA, Taiwan and France, 1 each in Vietnam and Singapore |
| Producers with only **one** drink | 104 (68%) |
| Producers with 5 or more drinks | 7: Akebono Shuzo 12, Niida Honke 9, Iinuma Meijo 8, Fukuchiyo Shuzo 6, then Kikunotsukasa, Nagai and Fuchu Homare at 5 |
| Producers spanning more than one category | Akebono Shuzo (Sake 11, Liqueur 1) and Kavalan (Whisky 1, Cocktail 2) |
| Producer descriptions in the ledger | **0**. The content comes from the new `Producers` sheet (§8) |

Most producer pages will therefore show **one drink plus a story**. The design has to look complete in that case, not like an empty crate.

---

## 2. Routes

| Route | Page |
|---|---|
| `#/makers` | Makers index |
| `#/producer/<key>` | One producer. `<key>` is the producer's **page key** (§8), for example `#/producer/iinuma-meijo` |

- **Breadcrumb:** *Bar › Makers › Iinuma Meijo*.
- **Ways in:**
  - "Visit producer →" and the producer name on every drink page (Plan 03 §7).
  - The Makers index.
  - A new **"The Makers" serving board** on the welcome page counter (§7). That's an addition to Plan 01.
- **"Unknown" gets no page.** Two drinks have the producer `Unknown`: Iamnishiki Tokubetsu Junmai (Nagano) and KIUBIJIN Junmai Ginjo Yunagi (Fukuoka). On their drink pages, The Maker section shows *"Producer not recorded · Nagano, Japan"* with no link and no "More from".

---

## 3. Producer page anatomy

### Desktop (≥ 1024px)

```
┌──────────────────────────────────────────────────────────────────┐
│ [LIQUID ASSETS]  Bar › Makers › Iinuma Meijo                     │
├──────────────────────────────────────────────────────────────────┤
│ ░░░░░░░░░░░░░░░░ brick back wall, warm light ░░░░░░░░░░░░░░░░░░░ │
│            ▯  ▯  ▯  ▯  ▯  ▯  ▯  ▯     ← their bottles on the crate │
│   ╔══════════════════════════════════════════════════════════╗   │
│   ║  ▓ IINUMA MEIJO ▓          飯沼銘醸                        ║   │ ← CRATE END (hero)
│   ║  TOCHIGI · JAPAN · EST. ____        ◉ sugidama (sake only) ║   │   stencilled lettering
│   ╚══════════════════════════════════════════════════════════╝   │
├──────────────────────────────────────────────────────────────────┤
│  8 drinks   ·   1 category   ·   had 11 times                     │ ← TALLY STRIP
├──────────────────────────────────────────────────────────────────┤
│ ┌── THE STORY ───────────────────────┐ ┌── THE FACTS ───────────┐ │
│ │ 2–4 paragraph blurb …              │ │ Location  Tochigi       │ │
│ │                                    │ │ Founded   ____          │ │
│ │                                    │ │ Brands    Sugata, …     │ │
│ │ Sources: brewery site ↗ · …        │ │ Website   ↗             │ │
│ └────────────────────────────────────┘ │ [ small locator map ]   │ │
│                                        └─────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ THEIR BOTTLES ON MY SHELF                                         │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   ← Plan 02 menu cards, A–Z   │
│ └──────┘ └──────┘ └──────┘ └──────┘                               │
├──────────────────────────────────────────────────────────────────┤
│ RELATED MAKERS  ▭ Dassai Blue (sister brewery) ▭ Date Seven …      │ ← only when set
│ MORE FROM TOCHIGI  ▭ ▭ ▭ ▭ →                                       │
└──────────────────────────────────────────────────────────────────┘
```

### Tablet and phone

- **Tablet:** The Story and The Facts stack into one column, with The Facts first so the location is seen early.
- **Phone:**
  - The crate end goes full width and the lettering shrinks to fit.
  - The bottle row shows at most 5 bottles followed by "+n". The full set is in the grid below.
  - The cards go into 2 columns, and the "Related" and "More from" rows scroll sideways inside their containers.
  - The page itself never scrolls sideways.

---

## 4. Producer page sections

### 4.1 Crate-end hero

- **Wood:** a pale pine crate end with plank seams, nail heads and slightly worn edges. Its pale pine stands out against the brick wall, so it reads as a crate sitting *on* the counter.
- **Lettering:** stencil-style capitals in a dark ink with uneven coverage. **Font: Stardos Stencil** (Google Fonts), used only on crates and crate tiles. The native name (for example 飯沼銘醸) is "stamped" beside it in a red seal-ink box, but only when the Producers sheet has one.
- **Location line:** `LOCATION · COUNTRY · EST. YEAR`. Each part is left out when it's unknown.
- **Bottles on top:** one SVG bottle per drink, each in its category's shape (Plan 01 §3) with its own photo label (Plan 01 §6). They stand in a row, A–Z, with no more than 12 on desktop. The row is centred, so a single bottle stands alone in a spotlight, which looks deliberate. Each bottle links to its drink page.
- **Category ornament** (optional polish): Japanese sake breweries get a small **sugidama**, the cedar ball breweries hang outside, hung from the crate's corner. Other producers get no ornament.

### 4.2 Tally strip

`N drinks · N categories · ★ N favourites · had N times`. The favourites and "had" parts appear only when they add something (favourites > 0, times had > drinks).

### 4.3 The Story

- The blurb comes from `Producers.About`, 2–4 short paragraphs, in the serif body text with the brass drop cap used in Plan 03.
- A **Sources** line underneath lists `Producers.Sources` as small links, because the blurbs are researched rather than first-hand.
- **No blurb yet:** the section is left out, and The Facts panel widens to fill the row. It never says "Coming soon".

### 4.4 The Facts

| Field | Source |
|---|---|
| Location | `Producers.Location`, falling back to `Core.Origin` |
| Country | `Producers.Country`, falling back to `Core.Country` |
| Founded | `Producers.Founded` (year) |
| Brands | `Producers.Brands`, for example "Dassai" for Asahi Shuzo (Yamaguchi) or "Kubota" for Asahi Shuzo (Niigata) |
| Master brewer | `Producers.Master` (tōji, master blender), optional |
| Website | `Producers.Website`, opening in a new tab |
| Locator map | A small inline SVG: Japan's outline with the prefecture highlighted for Japanese producers, or the country's outline elsewhere (§6) |

### 4.5 Their bottles on my shelf

- The Plan 02 menu cards, without the toolbar. No producer has more than 12 drinks, so filtering would only add clutter.
- Ordered A–Z. When the producer spans more than one category (today Akebono and Kavalan), cards are **grouped under small category headings** (Sake, Liqueur…), ordered as on the top shelf.
- On this page each card replaces its producer line with its **category › subcategory**, since the producer is already obvious.

### 4.6 Related makers and More from the region

- **Related makers:** only appears when `Producers.Related` is set. Each entry is a mini crate tile with the name and its relationship ("sister brewery", "collaboration member", "parent company").
- **More from {Location}:** other producers in the same prefecture or region, sorted by number of drinks. Hidden when there are none. For example, Fukushima has 37 drinks across many breweries, which makes for good browsing.

---

## 5. Makers index (`#/makers`)

### 5.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ [LIQUID ASSETS]  Bar › Makers                                    │
│                                                                  │
│  THE MAKERS            152 producers · 9 countries                │
│  ┌──────────────────────────┐   🔍 Search makers                  │
│  │   Japan prefecture map   │   Country [All ▾]  Sort [A–Z ▾]     │
│  │   dots sized by drinks   │                                     │
│  │   (click = filter)       │   ── JAPAN · 132 ────────────────── │
│  └──────────────────────────┘   ▭ Akebono Shuzo  Fukushima   12   │
│  Elsewhere: South Korea 8 ·     ▭ Akabu Shuzo    Iwate         1   │
│  Scotland 2 · Chile 2 · …       …                                 │
│                                 ── SOUTH KOREA · 8 ────────────── │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Behaviour

- **Rows:** each row is a compact **crate tile**: a little stencilled pine label with the name, location and drink count. Producers with a ★ drink get a small brass star. Each row links to `#/producer/<key>`.
- **Grouping:** by country, with Japan first and the rest by number of producers. Within each group, tiles are A–Z.
- **Search:** matches the producer name, native name and brands, ignoring case and accents. Searching "Dassai" finds Asahi Shuzo (Yamaguchi).
- **Sort:** *A–Z* (default) · *Most drinks* · *Region*.
- **Map (§6):** clicking a prefecture filters the list to it and shows a removable chip ("Fukushima ×"). The country dropdown does the same for other countries.
- Filters live in the URL, using the same conventions as Plan 02, for example `#/makers?country=japan&region=fukushima&sort=most`.

---

## 6. Maps

- **Japan prefecture map:** a single inline SVG of the 47 prefectures in muted wood tones. Prefectures with drinks are filled in the brass colour, and a dot sized by drink count marks each one.
  - The SVG source must have an **open licence compatible with publishing**, checked before use, and credited in the site footer.
  - Hovering or focusing shows "Fukushima · 37 drinks · N makers".
- **Other countries:** listed as text links with counts under the map ("Elsewhere: South Korea 8 · …"). A world map isn't worth it for 20 producers.
- **Locator map on a producer page:** the same Japan SVG at small size with only that prefecture highlighted. For other countries, a simple country outline, or just the text location if no outline is available.
- **Normalising locations:** `Core.Origin` mixes prefectures ("Fukushima") with finer places ("Port Ellen, Islay", "Hyde Park, New York", "Colchagua Valley"). The map needs a clean prefecture value for each Japanese producer. That comes from `Producers.Region` (§8). The build step warns when a Japanese producer's Region isn't one of the 47 prefectures.

---

## 7. Welcome page addition (an update to Plan 01)

The bar counter gets a **wooden serving board reading "The Makers"** at its right-hand end, styled like the category board (Plan 01 §7.5). It links to `#/makers`. On phone, it becomes a small link in the fixed counter strip. Plan 01 §2 and §11 have been updated to include it.

---

## 8. Producers sheet: final columns

This extends the columns set in Plan 03 §10.3. There is **one row per distinct `Core.Producer` string**.

| Column | Purpose | Example |
|---|---|---|
| `Producer` | Exact `Core.Producer` text. This is the join key. | `Asahi Shuzo (Dassai)` |
| `Page Key` | Which page this row belongs to. **Rows with the same Page Key are merged into one page** (aliases). | `asahi-shuzo-yamaguchi` |
| `Display Name` | Clean name for the page | `Asahi Shuzo` |
| `Native Name` | Name in kanji or hangul | `旭酒造` |
| `Brands` | Comma-separated brand names (used by search) | `Dassai` |
| `Location` | Town and region for display | `Iwakuni, Yamaguchi` |
| `Region` | Prefecture or province, used by the map and "More from" | `Yamaguchi` |
| `Country` | Country | `Japan` |
| `Founded` | Year | |
| `Master` | Tōji, master brewer or blender (optional) | |
| `Website` | Official URL | |
| `About` | 2–4 short paragraphs (public) | |
| `Related` | Page keys with a relationship, as `key:relationship`, separated by semicolons | `dassai-blue:sister brewery` |
| `Sources` | URLs used for the blurb, separated by semicolons | |
| `Status` | `draft` / `approved`. **Only `approved` rows publish anything beyond the Core-derived fields** (name, location, drinks): About, Founded, Master, Website, Sources, Native Name, Brands and Related are all held back for `draft` rows. *(Clarified 2026-10-30 to match §12.)* | `draft` |

`Status` means drafted research never goes live until the owner has reviewed it. Until then the page shows only what comes from Core (name, location, drinks).

### 8.1 Name problems in the current data

| Case | Ledger strings | Proposed handling |
|---|---|---|
| **Same name, different companies** | `Asahi Shuzo` (Niigata, Kubota) and `Asahi Shuzo (Dassai)` (Yamaguchi) | Separate pages: `asahi-shuzo-niigata` and `asahi-shuzo-yamaguchi`. Both display as "Asahi Shuzo", told apart by Location and Brands. |
| **Sister brewery** | `Dassai Blue` (Hyde Park, New York) | Its own page, with Related set to `asahi-shuzo-yamaguchi:parent company`, and the reverse set as well. |
| **Collaboration** | Three `Date Seven (… Miyagi Collective)` strings | One page, `date-seven`, using the alias merge. The blurb names the member breweries. Related links to member breweries already in the ledger, such as `Yamawa Shuzoten`. |
| **Same brewery, two names** | `Machida Shuzo` / `Machida Shuzoten` (both Gunma); `Yamamoto Shuzoten` / `Yamamoto Gomei Kaisha` (both Akita) | **Merge (owner confirmed).** Page keys `machida-shuzo` and `yamamoto-shuzoten`. The trading name is the Display Name, and the company name goes in Brands so search still finds it. |
| **Similar names, different breweries** | `Iinuma Honke` (Chiba) and `Iinuma Meijo` (Tochigi) | Separate pages. No action needed. |
| **Brand inside the producer name** | `Hakushika (Tatsuuma Honke)`, `Konohana Brewery (ALLWRIGHT)`, `Wakaze (Kura Grand Paris)`, `RiceWine K.K. (HINEMOS)`, `Obuse Winery (Sogga Père et Fils)` | Use a clean Display Name, and move the bracketed brand into Brands. |
| **Unknown** | `Unknown` (2 drinks, different prefectures) | No row and no page (§2). |

**Merging rule:** an alias page combines all of its rows' drinks. Its Facts come from the row whose `Producer` text equals the Display Name, or else from the first row in sheet order. The build step lists any Page Key whose rows disagree on Region or Country.

---

## 9. Data contract (additions)

- **`Ship/docs/data/producers.json`:** one small record per page, used by the Makers index, the map and "More from":

  ```jsonc
  { "key": "iinuma-meijo", "name": "Iinuma Meijo", "native": null, "region": "Tochigi",
    "country": "Japan", "brands": [], "drinkCount": 8, "favourites": 1, "hasStory": false }
  ```

- **`Ship/docs/data/producers/<key>.json`:** the full page data, loaded on demand. It includes the approved facts, the About text, sources, related makers (key, name, relationship), the drink IDs with their category and subcategory, and the "More from" producer keys.
- **Plan 03 change:** the drink page's `producer.key` must be the **Page Key**, not the slugified Core string, so aliases link to the merged page.
- **Privacy guard** (Plan 03 §10.4) also covers these files. Rows marked `draft` must never leak About, Founded, Master or Website into published JSON.

---

## 10. Accessibility and performance

- The `<h1>` is the Display Name. The native name has `lang="ja"` or `lang="ko"` so screen readers pronounce it properly.
- Map prefectures are focusable `<button>`s with text labels. The list next to the map is the primary way to navigate, and the map is an extra.
- The crate's stencil lettering is decorative. The `<h1>` underneath is real text, styled, and never an image.
- The Makers index loads `producers.json` (152 × about 200 bytes ≈ 30KB) plus the map SVG (≤ 60KB when optimised). A producer page loads its JSON (≤ 5KB) and lazy-loads the thumbnails.

---

## 11. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | Which producers get a page | **Every producer except Unknown**, including the 104 with one drink (§2). |
| Q2 | Makers index and counter plaque | **Both** (§5, §7). |
| Q3 | Japan prefecture map | **Yes:** on the index, plus a locator map on each producer page (§6). |
| Q4 | Machida Shuzo / Machida Shuzoten; Yamamoto Shuzoten / Yamamoto Gomei Kaisha | **Merge each pair** into one page (§8.1). |
| Q5 | Review step for researched content | **Yes:** the `Status` column, where only `approved` rows publish research (§8). |
| Q6 | Crate font | **Stardos Stencil** (§4.1). |

---

## 12. Acceptance criteria

- [ ] Every distinct Page Key (all producers except Unknown) has a page at `#/producer/<key>`, and every drink page links to it.
- [ ] Alias rows merge into one page, and same-name different producers (Asahi Shuzo ×2) stay separate and are told apart by location.
- [ ] A one-drink producer with no approved research still renders a complete crate: name, location, one bottle, one card. No empty sections.
- [ ] Rows marked `draft` publish nothing beyond the Core-derived fields.
- [ ] Multi-category producers group their cards by category.
- [ ] The Makers index groups producers by country, and its search covers names, native names and brands. Map, country filter and sort are mirrored in the URL.
- [ ] The welcome page counter links to the Makers index.
- [ ] It works at 375px with no sideways page scroll, and works by keyboard and screen reader (the map has a list equivalent).
