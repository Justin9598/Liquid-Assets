# Plan 02: Shelf list page ("Up close")

Status: **Approved design. The owner has answered every open question (§11).**
Author: Claude (designer). This is a plan only. Nothing here is built yet.
Depends on: [01-welcome-page.md](01-welcome-page.md) (taxonomy, bottle shapes, palette, photo map).
Data snapshot: `Drinks Ledger.xlsx` as of 2026-10-30. That's 265 unique drinks.

---

## 1. Concept

Clicking a subcategory bottle on the welcome page takes you **up close to that bottle's shelf**. The bottle you chose stands at the top as the page header, and below it the bar hands you a **paper drinks menu** listing every drink in that subcategory.

The page answers three questions in this order:

1. *What is this?* For example, what a Junmai Ginjo actually is.
2. *What have I had of it?* The list of drinks.
3. *Which one do I want to look at?* Filtering and sorting, then a click through to the drink page (Plan 03).

It keeps the bar's look from Plan 01 §7 (revised): a brick-wall header with a light-oak shelf plank and warm light. The list sits on cream **menu cards** over a soft, plain oak-toned background, so long lists stay easy to read. Reading 74 entries straight off a brick or wood texture would be tiring.

---

## 2. Route

The page lives at `#/<category>/<subcategory>` and uses the same keys as `shelf.json` (Plan 01 §8). For example:

- `#/sake/junmai-ginjo`
- `#/wine/merlot`
- `#/spirits/whisky`
- `#/makgeolli/all`

Filters and sorting are kept in the hash's query part so a filtered view can be bookmarked or shared, for example `#/sake/junmai-ginjo?style=nama,genshu&origin=fukushima&fav=1&sort=producer&q=aiyama`.

An unknown category or subcategory leads to a friendly "This shelf is empty" scene with a link back to the bar. It doesn't show an error page.

---

## 3. Page anatomy

### Desktop (≥ 1024px)

```
┌──────────────────────────────────────────────────────────────────┐
│ [LIQUID ASSETS]  Bar › Sake › Junmai Ginjo                       │ ← small sign = home link; breadcrumb
├──────────────────────────────────────────────────────────────────┤
│   ▯▯ ▯ ▯▮▯ ▯ ▯ ▯ ▯ ▯ ▯   ← sibling strip: mini bottles of the   │
│   ════════════════════      other Sake subcategories (current lit)│
│                                                                  │
│   ┌────┐   JUNMAI GINJO   純米吟醸                                │ ← HERO
│   │    │   74 drinks · 50 producers · 25 prefectures             │
│   │ ▯  │   Rice polished to 60% or less, with no added alcohol.  │
│   │    │   Fragrant and fruity, but grounded…                     │
│   └────┘   [No added alcohol] [Polished ≤ 60%]                   │ ← fact chips
├──────────────────────────────────────────────────────────────────┤
│ 🔍 Search name or producer   Style: [Nama 32][Genshu 21][Muroka]… │ ← TOOLBAR (sticks on scroll)
│ Origin [All ▾]   [★ Favourites]   Sort [Name A–Z ▾]              │
│ Showing 23 of 74 · Clear filters                                 │
├──────────────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                              │ ← MENU GRID (4 columns)
│ │photo │ │photo │ │photo │ │photo │                              │
│ │      │ │      │ │      │ │      │                              │
│ │Name  │ │Name  │ │Name  │ │Name  │                              │
│ │Prod. │ │Prod. │ │Prod. │ │Prod. │                              │
│ └──────┘ └──────┘ └──────┘ └──────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

### Tablet (768–1023px)

The grid drops to 3 columns. The style chips row scrolls sideways *inside its own container*; the page itself never scrolls sideways.

### Phone (< 768px)

- The grid becomes 2 columns.
- The hero stacks: bottle on top (smaller), then the text.
- The sibling strip becomes a single row of mini bottles that scrolls sideways inside its container, centred on the current one.
- The toolbar collapses to a search field plus a **Filter & sort** button that opens a bottom sheet holding the chips, origin, favourites and sort.
- The result count stays visible under the search field.

---

## 4. Header: sign, breadcrumb, sibling strip

- **Small sign:** a scaled-down version of the carved Rye wordmark, about 40px tall, in the top-left corner. Clicking it goes back to the bar with the parent category still selected (`#/sake`).
- **Breadcrumb:** *Bar › Sake › Junmai Ginjo*. Each part is a link, and "Sake" goes to `#/sake`.
- **Sibling strip:** a short shelf plank holding mini versions (about 36px tall) of every visible subcategory bottle in the same category, in the Plan 01 order. The current one is lit and lifted, and the others are dimmed. Hovering shows a tag with the name and count, and clicking switches subcategory. Filters are cleared on switching, since style counts differ between shelves.
  - Categories with a single bottle, such as Makgeolli today, don't show the strip.

---

## 5. Hero

| Element | Content |
|---|---|
| Bottle | The subcategory bottle from the welcome page: same SVG shape, with a random label from the same pool (Plan 01 §6). About 220px tall on desktop and 140px on phone. |
| Title | English name in a large serif (the same family as the cards, §7), with the native name (kanji/hangul) beside it in a lighter weight |
| Stats line | `N drinks · N producers · N origins`. The origin word adapts: "prefectures" if every drink is from Japan, "regions" otherwise |
| Explainer | 1–3 sentences on what the subcategory is (§9) |
| Fact chips | 1–3 short facts that define the subcategory, for example *No added alcohol*, *Polished ≤ 60%* (§9) |

**From the welcome page (enhancement):** clicking a bottle on the welcome page lets that bottle *fly* into the hero position, using the browser's View Transitions API where it's supported. Elsewhere the page simply loads. This is optional polish and must never block navigation.

---

## 6. Toolbar: search, filter, sort

All filtering happens in the visitor's browser on the already-loaded drinks index (§10). At most 265 drinks, so it's instant.

| Control | Behaviour |
|---|---|
| **Search** | Matches as you type against Name and Producer, ignoring case and accents ("cote rotie" finds "Côte Rôtie"). Debounced about 150ms. |
| **Style chips** | One chip per `Core.Style(s)` tag present on this shelf, with its count, sorted by count. Selecting several **narrows** the results (Nama + Genshu = drinks that are both). Chips that would give 0 results with the current filters are disabled but stay visible. Hidden when no drink on the shelf has a style. |
| **Origin** | Single-select dropdown of `Core.Origin` values on this shelf, with counts, in A–Z order. If the shelf spans more than one country, the options are grouped by `Country`. |
| **★ Favourites** | Toggle that shows only `Favourite = ★`. Hidden if the shelf has no favourites. |
| **Sort** | *Name A–Z* (default) · *Favourites first* (★ drinks first, then A–Z) · *Producer* · *Origin* · *ABV high → low* · *Most had* (by number of occasions) · *Rating* and *Recently added* (shown only once at least 5 drinks on the shelf have those fields filled; today none have a Rating and only 41 of 265 have `Added`) |
| **Result count** | "Showing 23 of 74", plus a *Clear filters* link when any filter is active. A screen-reader live region announces the count. |

**Empty result:** a small illustration of an empty shelf plank, the line *"Nothing on this shelf matches."* and a **Clear filters** button.

---

## 7. Menu cards

One card per drink **ID**, not per drinking occasion. The 17 drinks that were had more than once are combined into one card.

```
┌─────────────────────┐
│ ★                   │ ← favourite ribbon (corner), only if ★
│     [ bottle photo ]│ ← 3:4 photo thumbnail
│                     │
│               ×2    │ ← "had 2 times" pill, only if occasions > 1
├─────────────────────┤
│ Aiyama 'Galaxy'     │ ← name, at most 2 lines, then …
│ Kimoto Junmai Ginjo…│
│ Fukunishiki         │ ← producer
│ Hyogo · Japan       │ ← origin · country
│ 16.2% · 720ml       │ ← ABV · size(s)
│ Polished 60% · Aiyama│ ← category facts (max 2, §7.2)
│ [Nama] [Kimoto] +1  │ ← style tags (max 3, then "+n")
│                  📝 │ ← tasting-notes mark, only if notes exist
└─────────────────────┘
```

### 7.1 Card rules

- The whole card is one link to the drink page, `#/drink/<id>` (Plan 03).
- **Name:** shown in full in the link's accessible name, but visually cut off after 2 lines. The longest name today is 76 characters.
- **Sizes:** when a drink was had in more than one size, list them in ascending order ("60ml · 720ml"). `60ml Tasting`, `90ml Pour` and `180ml Carafe` display as "Tasting", "Pour" and "Carafe".
- **ABV:** omitted, along with its separator, when empty. 46 drinks have no ABV.
- **Ratings:** none yet. When a drink has a `Rating`, show it as small cup or star icons in half steps under the name. Show nothing when it's empty, never "0 stars".
- **Photo:** the drink's **front photo**, as a 3:4 *thumbnail crop*. This is not the label crop: on a card the whole bottle reads better. See §10.
- **No photo:** an SVG of the category's bottle shape on a soft paper background, wearing the subcategory's illustrated fallback label (Plan 01 §6.5). It should look as though the bottle was sketched in.

### 7.2 Category facts (two at most, skipped when empty)

| Category | Fact 1 | Fact 2 |
|---|---|---|
| Sake | `Polished {RPR}%` (190 of 229 filled) | Rice (172 of 229) |
| Craft Sake | Main base or flavouring from `Other Detail`, if present | First style tag |
| Makgeolli | Base (`Other Detail.Base`) | Flavouring |
| Liqueur: Umeshu | Flavour/base (`Other Detail.Type`, for example Classic or Fruit Blend) | Base |
| Liqueur: other kinds | Base | Flavouring |
| Beer | Style (`Other Detail.Type`) | Yeast, if present |
| Wine | Vintage | Appellation |
| Whisky | Age statement, or else Single cask / Blend | Region or cask type |
| Shochu / Soju | Base ingredient | Koji |
| Gin / Brandy | Base | Maturation |
| Cocktail | Base | — |

### 7.3 Look

- **Card:** `--paper` (#efe6d2) with a faint washi or menu-paper grain. 8px radius, a soft shadow and a hairline border in #d8ccb3.
- **Text:** dark ink (#2a1d14) with secondary text at #6b5a4a. The body text has to pass 4.5:1 on paper.
- **Fonts:** a warm serif for drink names (for example Fraunces or Cormorant Garamond, at 600 weight) and the humanist sans from Plan 01 for metadata. Kanji and hangul use system CJK fonts.
- **Hover/focus:** the card lifts 3px, the shadow deepens and the photo brightens slightly. The focus ring uses the brass colour.
- **Style tags:** small outlined pills in #8a5a33. They aren't clickable on the card; filtering lives in the toolbar.

### 7.4 Order and quantity

- No pagination. The largest shelf (Junmai Ginjo, 74) renders all at once.
- Thumbnails load lazily, with the first two rows loaded straight away.
- Sorting ties are broken by Name A–Z.

---

## 8. Single-bottle and sparse shelves

- **Makgeolli** (`#/makgeolli/all`), plus any category that shows one bottle while its sub-type is unfilled: the same page, without the sibling strip, and the breadcrumb shortens to *Bar › Makgeolli*.
- **Shelves with 1–3 drinks** (most of Spirits, Wine and Beer today): the toolbar is **hidden** and the cards are centred, because filtering 2 drinks is just noise. The toolbar appears at **8 or more drinks**.

---

## 9. Explainer copy (draft; the owner can edit it)

Copy lives in `Ship/content/subcategories.json`, keyed by `<category>/<subcategory>`, with `explainer` and `facts` fields. The implementer doesn't write copy. Below is the starting text.

### Sake

| Subcategory | Explainer | Fact chips |
|---|---|---|
| Junmai Daiginjo | The top grade: rice polished to 50% or less, nothing but rice, water, kōji and yeast. Usually delicate and aromatic. | No added alcohol · Polished ≤ 50% |
| Junmai Ginjo | Rice polished to 60% or less with no added alcohol. Fragrant and fruity, but with more body than a daiginjo. | No added alcohol · Polished ≤ 60% |
| Tokubetsu Junmai | A "special" junmai: polished to 60% or less, or made by a special method the brewery names on the label. | No added alcohol · Special method or ≤ 60% |
| Junmai | Pure rice sake with no minimum polishing. Often fuller, richer and more savoury. | No added alcohol |
| Daiginjo | Polished to 50% or less, with a small amount of distilled alcohol added to lift the aroma. | Added alcohol · Polished ≤ 50% |
| Ginjo | Polished to 60% or less, with a touch of distilled alcohol added. Light and fragrant. | Added alcohol · Polished ≤ 60% |
| Tokubetsu Honjozo | A "special" honjozo: polished to 60% or less, or made by a named special method. | Added alcohol · Special method or ≤ 60% |
| Honjozo | Polished to 70% or less, with a little added alcohol for a lighter, drier finish. | Added alcohol · Polished ≤ 70% |
| Futsushu | Everyday table sake, made outside the premium grade rules. | Table sake |
| Craft Sake | Brewed like sake but with extra ingredients such as fruit, tea or hops, or steps that take it outside the legal definition of sake. Often from new, small breweries. | Rice-based · Beyond the rules |
| Ungraded | Sakes whose grade hasn't been recorded yet. | — |

### Everything else

| Subcategory | Explainer |
|---|---|
| Makgeolli | Korea's cloudy rice wine: lightly sparkling, milky and often unpasteurised, brewed with nuruk. |
| Umeshu | Japanese plum liqueur made by steeping unripe ume in alcohol and sugar. |
| Other liqueur kinds | One line per kind, written once each kind first appears. |
| Beer styles | One line per style, written once each style first appears. |
| Cabernet Sauvignon | Thick-skinned black grape. Firm tannins and blackcurrant. |
| Merlot | Soft, plummy red grape, rounder than Cabernet. |
| Blend | Wines made from more than one grape. Each drink page lists its grapes. |
| Whisky | Distilled from fermented grain and aged in wooden casks. |
| Gin | Neutral spirit flavoured with juniper and other botanicals. |
| Brandy | Distilled from fermented fruit, here apples. |
| Shochu | Japan's distilled spirit, made from barley, sweet potato, rice and more, with kōji. |
| Soju | Korea's distilled spirit. Traditional versions are made with nuruk. |
| Highball | Spirit topped with soda over ice. |

When a subcategory has no copy, the explainer line is omitted and the hero still works.

---

## 10. Data contract (additions to Plan 01 §8)

The list page reads **`Ship/docs/data/drinks.json`**, the drink index. The build step makes **one record per drink ID**, combining all of that drink's Core rows:

```jsonc
// Ship/docs/data/drinks.json
[
  {
    "id": "aiyama-galaxy-kimoto-junmai-ginjo-origar",
    "name": "Aiyama 'Galaxy' Kimoto Junmai Ginjo Origarami Nama",
    "category": "sake", "sub": "junmai-ginjo",
    "producer": "Fukunishiki", "origin": "Hyogo", "country": "Japan",
    "abv": 16.2,                     // null when empty
    "sizes": ["720ml Bottle"],       // unique, sorted ascending by volume
    "occasions": 2,                  // number of Core rows
    "styles": ["Nama", "Kimoto", "Origarami"],
    "favourite": true,               // ★ on any occasion
    "rating": null,
    "added": null,                   // most recent Added across occasions, ISO date
    "facts": ["Polished 60%", "Aiyama"],   // already worked out per §7.2
    "hasTasting": false,
    "thumb": "img/thumbs/aiyama-galaxy-kimoto-junmai-ginjo-origar.webp"   // null → fallback art
  }
]
```

- **Size:** about 265 records × about 350 bytes ≈ 90KB raw, or about 20KB gzipped from GitHub Pages. That's fine to load whole and filter in the browser.
- **Facts are worked out at build time**, so the page has no special cases per category.
- **Thumbnails:** the build step makes `img/thumbs/<id>.webp` at 480px wide, 3:4, around 75% quality, about 30–50KB each. The crop comes from a `thumbCrop` field in `Ship/content/photo-map.json`. When that's unset, it defaults to the largest centred 3:4 crop. Thumbnails go on the same contact sheet as the label crops so both can be reviewed.
- **Combining occasions:** a drink is a favourite if **any** of its Core rows has ★. Today 3 drinks are starred on only one of their occasions: Aiyama 'Galaxy', Odayaka Sparkling and Shichifukujin Super Dry. For every other field, the build step uses the **first** Core row and lists any disagreement as a warning. Today, rows that share an ID agree on every other card field.
- **Not in the index:** `Notes`, `Price (S$)`, `Bought From`, the detail-sheet fields beyond the facts, and tasting notes. They belong to the drink page (Plan 03) and its per-drink data file.

---

## 11. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | Default sort | **Name A–Z.** *Favourites first* stays available as a sort option (§6). |
| Q2 | "Where I had it" filter using `Bought From` | **No filter on the list page.** The venue appears on the drink page only (Plan 03). |
| Q3 | Notes excerpt on cards | **No excerpt on cards.** How notes are handled, including any public/private split, is decided in Plan 03. `Notes` mixes the description with housekeeping, for example *"ABV corrected from 16 to 15 on 2026-09-19 against the bottle…"*. |
| Q4 | Card photo | **Whole-bottle thumbnail crop.** The label crop stays special to the shelves. |
| Q5 | Hide the toolbar on small shelves | **Yes**, below 8 drinks (§8). |

---

## 12. Accessibility and performance

- The page has an `<h1>` (subcategory name). Each card has an `<h2>`-level name inside an `<a>`, and all of the card's text sits inside that link.
- Chips and the favourites toggle are `<button aria-pressed>`. Sort and origin are native `<select>`s, styled.
- Focus moves to the `<h1>` on navigation so screen-reader users land in context.
- Reduced motion turns off the hero fly-in and the card lift.
- Budget: the page loads ≤ 150KB before images (the drink index plus code). Only the first two rows of thumbnails load straight away (about 8 × 40KB).

---

## 13. Acceptance criteria

- [ ] Every subcategory bottle on the welcome page opens its shelf page, and every route in `shelf.json` renders.
- [ ] The hero shows the bottle in its parent shape with a random label, the name, the native name, stats, the explainer and fact chips (when copy exists).
- [ ] The sibling strip switches subcategory, and it's absent on single-bottle categories.
- [ ] There's one card per drink ID, with drinks had more than once combined (×n pill).
- [ ] Cards are in Name A–Z order by default.
- [ ] Search, style chips (narrowing), origin, favourites and sort all combine correctly and are mirrored in the URL. Reloading a filtered URL restores the same view.
- [ ] Shelves with fewer than 8 drinks show no toolbar.
- [ ] Drinks without photos show the category fallback art, never a broken image.
- [ ] It works at 375px (2 columns, filter bottom sheet) with no sideways page scroll, and keyboard and screen-reader use works.
- [ ] Nothing is requested from `Photos/`. Notes, prices and venues are not shown on this page.
