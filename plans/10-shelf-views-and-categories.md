# Plan 10: New categories, shelf views, the reset clock and front-only photos

Status: **Approved by the owner (2026-11-03).** Built by the shipper; no push without the owner's word.

This changes the welcome page (Plans 01 and 07), the category tree (Plan 01 §4), and the drink page photos (Plan 03). It applies on every page size, under the Plan 07 §5.3 parity rule.

## 1. Owner brief (2026-11-03)

1. Umeshu leaves Liqueur. Spirits shows every distilled type as its own subcategory, for example Gin and Brandy.
2. Beer and Makgeolli become one category, **Fermented Beverages**.
3. On the shelves, tapping a bottle opens that drink, not a category.
4. The counter's New arrivals and In season bottles stand close together. Tapping either board turns the shelves into New arrivals or In season, with more than 5 bottles.
5. A small clock in the bottom-left of the shelves resets the bar to its first look.
6. When a subcategory is chosen, the counter shows that subcategory's new and seasonal bottles. If it has none, the counter shows its usual set.
7. Photos: only the front image. Back labels and other views are removed.

### Answers

| # | Question | Answer |
|---|---|---|
| A1 | Where umeshu goes | **Its own top-level category, "Umeshu".** It isn't in Fermented Beverages. |
| A2 | Do top-shelf bottles open drinks too? | **No, lower shelves only.** Top-shelf bottles keep opening their category. Bottles on the lower shelves and the counter open their drink. |
| A3 | Fermented Beverages bottles | **Makgeolli, then each beer style.** Umeshu isn't in it (A1). |
| A4 | The clock | **A clock drawn in code, showing the visitor's real time,** in brass and wood. No image needed from the owner. |

## 2. Categories

### 2.1 The top shelf

| Order | Key | Name on the tag | Holds (`Core.Category`) | Vessel (Plan 07 §2 shell) |
|---|---|---|---|---|
| 1 | `sake` | Sake | Sake, Craft Sake | sake bottle (unchanged) |
| 2 | `fermented` | Fermented Beverages | Makgeolli, Beer | beer bottle |
| 3 | `umeshu` | Umeshu 梅酒 | Umeshu | the liqueur bottle |
| 4 | `liqueur` | Liqueur | Liqueur (any kind but umeshu) | the liqueur bottle |
| 5 | `wine` | Wine | Wine | unchanged |
| 6 | `spirits` | Spirits | Whisky, Shochu, Soju, Spirit | unchanged |
| 7 | `cocktails` | Cocktails | Cocktail | unchanged |

- **Liqueur is empty today** (its only drinks were the 3 umeshu). Any category with no drinks is left out of the top shelf, the burger's Shelves submenu, the Makers filters and the counter. It comes back by itself when a drink is logged.
  - The route `#/liqueur` shows the existing empty-shelf page.
- **"Fermented Beverages" is the longest tag.** It may wrap onto two lines on the chalk tag, centred. The Plan 07 §8.2 rule still holds: tags never overlap or clip.
- `taxonomy.py`:
  - `CATEGORIES` and `CORE_TO_CATEGORY` follow this table.
  - `Umeshu` maps to `umeshu`, and `Makgeolli` and `Beer` map to `fermented`.
  - `FALLBACK_NAME` and `FALLBACK_NATIVE` move with them: makgeolli's 막걸리 now sits on its subcategory, and 梅酒 on the Umeshu category.

### 2.2 Fermented Beverages: lower-shelf bottles

- **Makgeolli** comes first, with native name 막걸리, on the makgeolli shell.
- **Then the beer styles,** in the `TYPE_VALUES["beer"]` order: Lager, Pilsner, Pale Ale, IPA, Wheat, Stout/Porter, Sour, Saison, Specialty. Each uses the beer shell.
- **Then "Other beer"** for any beer with no `Type` (2 today).
- Empty styles are hidden, as now (I01).

### 2.3 Umeshu

- A category with **no subcategories.** Opening it fills the lower shelves with its drinks (§4.3), like a subcategory view.
- The `Other Detail.Type` flavours (Classic, Fruit Blend and so on) stay as card and drink-page facts, as in Plan 01 §4.3.

### 2.4 Spirits: one bottle per distilled type

- **Order:** Whisky, Gin and Brandy first (`SPIRIT_FIRST`), then any other type alphabetically: Baijiu, Rum, Shochu, Soju, Tequila, Vodka.
- **Where the type comes from:** Whisky, Shochu and Soju come from `Core.Category`. A `Spirit` row takes its type from `Other Detail.Type`.
- **"Other spirits"** is only for `Spirit` rows with no Type. When every spirit has a type, that bottle disappears.
- **Data (researcher, owner approves):** the two `Spirit` rows have no Type yet.
  - *The Botanist Islay Dry Gin* is Gin.
  - *Chusa 40* needs research.
  - Until they're entered, both sit in "Other spirits". No code waits on this.

### 2.5 Old addresses keep working

The build writes a route alias table, `docs/data/aliases.json`, and the router follows it before it shows the empty-shelf page.

| Old | New |
|---|---|
| `#/makgeolli` | `#/fermented/makgeolli` |
| `#/beer` | `#/fermented` |
| `#/beer/<style>` | `#/fermented/<style>` |
| `#/liqueur/umeshu` | `#/umeshu` |
| `#/producer/<old key>` | `#/producer/<new key>`, for the 12 maker addresses that changed in Plan 09 Stage 1 (listed in `Research/approved/producers-00-skeleton.md` §3) |

- The producer aliases are hand-kept in `Ship/content/aliases.json`. This also closes the gap found on 2026-11-02, where old maker links landed on the empty-shelf page.
- The alias swap uses `location.replace`, so it adds no history entry.

### 2.6 Knock-on effects

- **Breadcrumbs, list pages, drink pages, the Makers category filter, search, the seasonal "at most 3 from one category" rule, the build report and the OG image text** all use the new keys and names.
- **Plan 01 §4 and §8:** a note says this plan supersedes the category tree there.

## 3. What a tap does

| Where | Tap the bottle | Tap the chalk board |
|---|---|---|
| Top shelf | Opens the category: the lower shelves show its subcategories (unchanged, A2). | The same. |
| Lower shelves, category view | **Opens the drink whose label that bottle wears** (its drink page). | **Selects the subcategory** (§4.2). |
| Lower shelves, any drinks view (§4.2 to §4.5) | Opens that drink. | (no board on single drinks; the view caption is in §4.6) |
| Counter | Opens that drink (unchanged from Phase 2). | The **New arrivals** or **In season** placard switches the shelves to that view (§4.4, §4.5). |

- **Which drink a subcategory bottle stands for:** the drink whose label it shows, chosen when the page loads.
  - A bottle with a fallback label stands for the newest drink in that subcategory.
  - The choice stays the same until the page is reloaded.
- **Hover and focus:** a lower-shelf bottle shows a small chalk name tag with the drink's name.
- **Keyboard and screen readers:** the bottle and its chalk board are **separate focus stops,** in that order.
  - The bottle reads "{Drink name}, open drink".
  - The board reads "{Subcategory}, {n} drinks, show on the shelves".

## 4. Shelf views

The welcome page now has **views**. The top shelf, counter and burger stay put. Only the **lower shelves** and the **counter groups** change.

### 4.1 Rest

The first look, exactly as today (Plan 07 and §11 there).

### 4.2 Category view

The same as today: the lower shelves show the category's subcategory bottles. Only the taps change (§3).

### 4.3 Subcategory view (and Umeshu)

- **Reached by** tapping a subcategory's chalk board in category view, or opening Umeshu.
- **The lower shelves** fill with that subcategory's own drinks, one bottle per drink, newest first (latest occasion). Each bottle uses its category's shell and the drink's label, or the fallback label.
- **When there are more drinks than fit,** the last place on the bottom shelf becomes a chalk S board: "See all {n}", which opens the list page `#/{cat}/{sub}`.
- **The counter** filters to the subcategory (§6.2).

### 4.4 New arrivals view

- **Reached by** tapping the counter's **New arrivals** placard.
- **The lower shelves** fill with the newest drinks, up to the shelf capacity (§4.7), newest first.

### 4.5 In season view

- **Reached by** tapping the **In season: {Season}** placard.
- **The lower shelves** fill with the season's picks, up to capacity, in score order (Plan 07 §4.3).

### 4.6 View caption

- **In every view except Rest,** a chalk S board sits at the left end of the bottom shelf's front edge. It names the view:
  - "Junmai Ginjo · 47 drinks"
  - "New arrivals · 12"
  - "In season: Autumn · 12"
- **It uses** `aria-live="polite"`, so screen readers hear the change.

### 4.7 Capacity and data

- **Capacity:** the shipper measures how many bottles fit across the lower shelves at the standard shelf spacing, for each plate, and records it in `scene.json` (`lowerCapacity`: wide and tall).
- **No crowding:** bottles never go below the Plan 07 bottle size to fit more.
- **`shelf.json` gains:**
  - `counter.newArrivals` grows to **24** drinks (the first 5 are the rest-state counter).
  - `counter.inSeason.<season>` grows to **24** picks each.
  - Per-subcategory lists (§6.2).
- **Subcategory drinks:** `shelf.json` carries each subcategory's drink list (id, name, label), so the welcome page needs no extra fetch.
  - In Phase 1 this is names and labels only, as Plan 07 §4.4 already allows.

### 4.8 Moving between views

- **Motion:** the lower-shelf bottles fade and drop out, then the new ones fade and rise in. That takes 300ms in all, using `transform` and `opacity` only. With reduced motion, the change is instant.
- **Address and Back button:** a view change **doesn't change the address** or add a history entry. Back leaves the page, as today.
- **Leaving a view:** Esc and the clock (§5) return to Rest. Tapping a top-shelf bottle goes to that category view.

## 5. The reset clock

- **What it is:**
  - A small **wall clock drawn in SVG**: a brass rim, a cream face, dark wooden hands, and 12 tick marks (no numbers).
  - It shows the **visitor's local time**. The hands move once a minute, with no ticking or looping animation (taste rule).
- **Where:** the **bottom-left of the shelves**, at a spot the shipper chooses and records in `scene.json` (`clock`: wide and tall fractions).
  - It must clear every bottle, tag, caption and the counter.
  - Size: about 6% of plate height on the wide plate. The tap target is at least 44px on phones.
- **Behaviour:**
  - Tapping it returns the bar to **Rest** (§4.1) from any view. It closes an open category and resets the counter filter.
  - At Rest it still shows the time. Tapping it then does nothing, apart from a tiny 3px nudge.
  - Its label is "Back to the bar" (`aria-label`), and hover or focus shows a small chalk tag: "Reset".
- **Phase 1 and Phase 2:** the same.

## 6. The counter

### 6.1 Compact groups

- **Each group's 5 bottles stand close together,** side by side, with a gap of about 12% of a bottle's width.
- **The group is centred** over its placard, instead of spread across the whole Plan 07 §4.1 zone.
- **The placards** become chalk S buttons that switch views (§4.4, §4.5). Their wording is unchanged.

### 6.2 Following the chosen subcategory

- **In a subcategory view (or Umeshu):**
  - **New arrivals** shows the newest 5 drinks **in that subcategory.**
  - **In season** shows that subcategory's picks for the current season. These are its drinks with at least one season keyword match, scored as in Plan 07 §4.3, up to 5.
- **When a group has no drinks** for the subcategory, that group shows its usual Rest set.
- **When filtered,** each placard gets a second chalk line, "in Junmai Ginjo", so it's clear the set has changed.
- **Tapping a placard while filtered** opens that group's view for the whole bar, not just the subcategory (§4.4, §4.5).
- **Category view** (before a subcategory is chosen) leaves the counter as it is. The owner asked for subcategories only.
- **Data:** per subcategory, `shelf.json` carries `new` (up to 5 ids) and `season` (up to 5 ids per season, only where keywords match).

## 7. Photos: the front image only

- **The build publishes only each drink's front photo,** plus its thumbnail and label crop. Back label, side label, second photo, spec panel, maker panel and numbered extra views are **no longer encoded or published.** The build deletes the ones already in `docs/img/`.
- **`content/photo-map.json` keeps every mapping,** so nothing is lost on the owner's side.
- **The drink page shows one photo.** There's no thumbnail strip, and the lightbox opens that one photo with no previous and next buttons.
- **A drink whose only photo is a back or other view** shows its category shell, as drinks with no photo do now.
- **The privacy scan** is unchanged, and still runs over every published file.

## 8. Faults to guard against

| Risk | Guard |
|---|---|
| Lower-shelf bottles get too small to fit a big subcategory | Capacity is measured, never squeezed (§4.7). Extra drinks go behind "See all". |
| A view leaves the counter or tags overlapping | The Plan 07 §8.2 and §8.3 rules still apply in every view. The smoke test checks each view at four sizes. |
| An empty Liqueur shelf leaves a gap | Empty categories are left out everywhere (§2.1). The top shelf re-spaces its 6 bottles. |
| Old links break | The alias table (§2.5), with a test for each alias. |
| A filtered counter is confusing | It gets the "in {Subcategory}" line, and the caption names the view (§4.6, §6.2). |
| The clock covers something on phones | Its spot is chosen per plate and checked in the four-size screenshots. |

## 9. Acceptance

- [ ] **Top shelf:** Sake, Fermented Beverages, Umeshu, Wine, Spirits, Cocktails. Liqueur is hidden while empty. The menu's Shelves submenu matches.
- [ ] **Fermented Beverages** opens to Makgeolli, Lager, Pale Ale, IPA, Wheat, Saison, Specialty and Other beer. **Spirits** opens to Whisky, Shochu, Soju and Other spirits, until the two Spirit types are entered. **Umeshu** opens straight to its 3 drinks.
- [ ] **Taps:**
  - A lower-shelf bottle opens its drink page.
  - Its chalk board opens the subcategory view.
  - A top-shelf bottle opens its category.
- [ ] **Subcategory view:**
  - It shows that subcategory's drinks.
  - "See all" appears when needed.
  - The counter filters, with the "in …" line, and falls back to the Rest set where a group is empty.
- [ ] **New arrivals and In season views:** each fills the lower shelves to capacity, with more than 5 bottles.
- [ ] **The clock:** it resets every view to Rest and shows the right local time.
- [ ] **The counter groups are compact,** centred on their placards.
- [ ] **Every old address in §2.5 lands on its new page.**
- [ ] **Drink pages show one front photo.** `docs/img/web` holds no back or extra views.
- [ ] **Build and tests:** the build has 0 errors and the privacy scan is clean. The tests are updated for the new keys and counts, and all pass.
- [ ] **Screenshots** into `reports/plan10/`: every view (Rest, a category, a subcategory, Umeshu, New arrivals, In season), at 1440×900, 1920×1080, 375×812 and 390×844. Include a drink page with a single photo.
- [ ] **Commit with no push.** The designer pushes on the owner's word.

## 10. Decisions log

| # | Decision | Answer (2026-11-03) |
|---|---|---|
| D1 | Umeshu | Its own top-level category (A1). |
| D2 | Bottle taps | Lower shelves and counter open drinks. The top shelf opens categories (A2). |
| D3 | Fermented Beverages bottles | Makgeolli, then each beer style, then Other beer (A3). |
| D4 | The clock | Drawn in SVG, showing real local time (A4). |
| D5 | Shelf views and addresses | Designer's choice: views don't change the address. Esc or the clock resets them. |
| D6 | More than 5 | Up to 24 precomputed, shown up to the measured shelf capacity. |
| D7 | The two untyped spirits (owner approved 2026-11-03) | `the-botanist-islay-dry-gin` is **Gin** and `chusa-40` is **Brandy** (Korean apple spirit, oak-aged, listed as brandy by the IWSC). Both fill the existing empty `Other Detail.Type` cells. They're entered after the Plan 10 build commit, so the two don't clash. |
