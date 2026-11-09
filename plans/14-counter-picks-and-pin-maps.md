# Plan 14: Counter picks per category, shelf balance, and pin maps

Status: **Approved by the owner (2026-11-09): "Approve, build it". Built (2026-11-09):** commits `898eb45`, `ac97114`, `6a9dd0b`, `336ef51` and `e222f2b`. D1 to D4 are confirmed as recommended. No push without the owner's word.

## 1. Owner brief (2026-11-09)

> 1) When the user clicks on any catageory, ensure that there are reccomends for new arrival and whats in season for that category. If there are not enough to fill in this 2 sections, supplement it with other reccomendations from other categories
>
> 2) The bottles dont have to be evened out between the third and second row for the sub category, it can be more on the second so that less in the third if the reccomendations would block it.
>
> 3) under the makers, have a global map shown and with pins to the various regions where i have producers from. Using such pins and color coding them. When click on it will zoom into the region and show the more pins for the region. Hierarchy will be Global>Contients>Regional (EU/East Asia/SEA)>Countries. Within the country have each province/state/region be demarcated using pins as well. When clicked on the region info on the number of producers will show below. Ensure the filter when choosing from map will ensure the list will show the producers and same if we filter the list the map will change as well. In the event that the region contains less than 10 producers, there is no need to show the consolidated level but show the producers directly.
>
> 4) Within the makers page in the producer story, zoom the map in directly to the state level and pin where the brewery is. In the state level show the state capital and major towns/cities if there are any

**Reference image** (sent in chat, kept privately as `Design/pins-reference.jpg`): round-headed push pins in red, yellow, green and black stuck in a blackboard, seen at an angle, each with a soft shadow. The pins on the maps copy this look on the existing chalk slate.

## 2. Where things stand

- **Category view (Plan 10 §4.2, live):** the top shelf holds the categories, and shelves 2 and 3 hold the subcategory bottles, **split evenly** (`welcome.js` `rowsV3`, `per = ceil(n / 2)`). The counter bottles are **hidden** in category view, so the counter is empty apart from the placards.
- **Counter data (Plan 10 §4.7):** `shelf.json` has `counter.newArrivals` (24) and `counter.inSeason.<season>` (24 each) for the whole bar, plus per-subcategory `new` and `season` lists (used only by Umeshu since §13). There are **no per-category lists.**
- **Makers index (Plan 04 §5, Plan 08 §4.4):** a chalk map of **Japan only** (`assets/japan-prefectures.svg`), where a prefecture can be picked to filter the list. Other countries are text buttons ("Elsewhere"). There are country and search filters and a sort.
- **Maker page (Plan 09):** the Facts board shows the Japan map with the prefecture hatched. Makers outside Japan get no map.
- **Producers today:** 159 in 10 countries. Japan has 137, South Korea 8, France 3, and Scotland, Chile, USA and Taiwan 2 each. Denmark, Vietnam and Singapore have 1 each.
- **Locations:** each maker has `location` text ("Morioka, Iwate") and `region` ("Iwate"). **No coordinates.** So a pin "where the brewery is" needs new data (§5.1).

## 3. Counter picks follow the category (brief item 1)

### 3.1 What the visitor sees

- **In category view** (any top-shelf category, including Umeshu), the counter shows its two groups again:
  - **New arrivals:** the newest drinks **in that category**, newest first (latest occasion).
  - **In season:** that category's picks for the current season, scored as in Plan 07 §4.3.
- **Topping up:** each group always shows **5 bottles**. When the category has fewer than 5 for a group, the rest come from **other categories**, taken from the whole-bar list for that group (`counter.newArrivals` or `counter.inSeason.<season>`) in its usual order, skipping any drink already shown.
- **The placard's second line** says what's in the group:
  - "in Sake" when all 5 are from the category;
  - "in Wine + more" when some come from other categories.
- **The topped-up bottles look the same.** Their hover tag and screen-reader label name their own category ("Kavalan Highball, Cocktails").
- **At Rest** the counter is unchanged: the whole-bar sets.
- **The subcategory drink view** (Umeshu, the only one left after Plan 10 §13) uses the same rules, with "in Umeshu".
- **Tapping a placard** while filtered still opens that group's view for the whole bar (Plan 10 §6.2).
- **On phones** the counter still shows one group at a time behind the New / In season tabs. The tabs get the same "in …" line.

### 3.2 Data

- `shelf.json` gains, **per category**:
  - `new`: up to 5 ids, newest first;
  - `season.<season>`: up to 5 ids per season, only drinks with a keyword match.
- The **topping up happens in the build,** so each list the page reads is already 5 long, with a flag for which ids are from other categories (for the "+ more" line). The page does no extra work.
- A category with no drinks is hidden (Plan 10 §2), so it never needs a counter set.

## 4. Lower shelves in category view: more on shelf 2 (brief item 2)

The counter bottles stand in front of the ends of shelf 3. With §3 bringing them back in category view, shelf 3 must leave those ends clear.

- **Wide plate:**
  - **Shelf 3 gets only the room that's clear of the counter groups.** The page measures the counter bottles' boxes, as `avoidCounter()` already does for drink views. It then works out how many subcategory bottles fit on shelf 3 between them, at the normal bottle pitch.
  - **Shelf 2 takes the rest.** It fills first, up to its own measured capacity. Shelf 3 holds only what's left over, centred between the counter groups.
  - **Example:** Sake has 10 subcategories. If shelf 3 has room for 3 between the groups, shelf 2 holds 7 and shelf 3 holds 3, instead of 5 and 5.
  - **If both shelves together can't hold every subcategory** at the Plan 07 minimum bottle size and tag width, the last place on shelf 3 becomes a "See all {n} kinds" chalk board, which opens the category's list page `#/{cat}`. That doesn't happen with today's data. The largest category, Sake, has 10.
- **Tall plate:** unchanged. Phones show the subcategories as one scrolling row on shelf 3, and the counter there sits below the shelf, so nothing blocks it.
- **Tags:** the Plan 07 §8.2 no-overlap rules still apply to the fuller shelf 2. If shelf 2's tags would touch, the pitch tightens down to the Plan 07 minimum before any bottle moves to shelf 3.
- **Selfcheck:** the existing "no lower-shelf bottle behind a counter bottle" check now runs in category view too, for every category, at all four sizes.

## 5. The Makers map (brief item 3)

### 5.1 New data: where each maker is

- **Two new columns in the ledger's Producers sheet:** `Latitude` and `Longitude`, in decimal degrees.
- **The researcher fills them,** in batches like Plan 09:
  - It finds the brewery's street address, from the maker's own website first.
  - It takes the coordinates for that address from OpenStreetMap.
  - Its proposal lists the address, the coordinates and the source for each maker. The owner approves each batch, then the researcher enters it, with the usual backup and check (Plan 06 §4).
- **Where a maker has no single site** (a label-only maker, or a brand made under contract), the pin goes on the town in `location`, and the proposal says so.
- **Published to 3 decimal places** (about 100 m). These are businesses' public addresses, so there's no privacy issue. The street address itself stays in the private proposal and isn't published.
- **The build works out the rest from the coordinates,** so no other new columns are needed:
  - the **province/state** the point falls in (§5.3), by testing it against the map outlines;
  - the **country** the point falls in. If that doesn't match the ledger's `Country`, the build raises **W25**: coordinates outside the maker's country. This catches swapped latitude and longitude.
- **Missing coordinates:** the build places the pin on the town in `location` if the map data has it. Otherwise it uses the centre of the maker's `region`, and raises **W26**: maker placed by its region, not its address. Every maker still gets a pin.

### 5.2 Map data

- **Source:** Natural Earth (public domain, the same source as today's Japan map):
  - the world's countries, using map units so that Scotland stands on its own;
  - first-level provinces and states, for **only the countries with makers**;
  - populated places, for capitals and major towns (§6).
- **Made once by a tool,** not at every build: `build/tools/makemaps.py`. It downloads the Natural Earth files into the private `Research/mapdata/` folder, simplifies them, and writes small files to `docs/assets/maps/`. The owner's approval of this plan covers that download.
  - `world.json`: country outlines, about 120 KB or less.
  - `<country>.json`: one per country with makers, holding its province outlines and its places, about 60 KB or less each.
  - **Run it again** when a maker from a new country is logged. The build raises **E08** if a published maker's country has no map file.
- **One projection for every level** (a Miller-style world projection), so zooming from the world down to a province is one smooth move of the view. Country files load **only when the visitor zooms in** to that country.
- **Licence:** keep `japan-prefectures.LICENSE.txt`'s wording, as `maps/LICENSE.txt`.

### 5.3 The levels

The owner's hierarchy, with the place names used:

| Level | Groups (today's maker counts) |
|---|---|
| **World** | everything (159) |
| **Continent** | Asia (149), Europe (6), North America (2), South America (2) |
| **Region** | East Asia (147), Southeast Asia (2) · Europe (6) · North America (2) · South America (2) |
| **Country** | Japan (137), South Korea (8), Taiwan (2), Vietnam (1), Singapore (1), France (3), Scotland (2), Denmark (1), USA (2), Chile (2) |
| **Japan's area** (D2) | Tohoku (37), Kanto (23), Chubu (27), Kansai (28), Chugoku (8), Shikoku (4), Kyushu (7), Hokkaido (3) |
| **Province / state** | Japan's prefectures; Korea's provinces and metropolitan cities; Taiwan's counties and cities; US states; France's regions; Chile's regions; Denmark's regions; Scotland's council areas; Vietnam's provinces; Singapore as a whole |
| **Maker** | one pin per maker |

(The Japan area counts are worked out from today's prefectures. The build computes all counts from the data.)

**Two rules decide which pins show.** Together they cut out empty steps:

- **Fewer than 10:** a group with **fewer than 10 makers** doesn't break down any further. Clicking it shows **its makers' own pins straight away,** skipping every level in between. For example:
  - Europe (6) opens straight to its 6 makers, with no Region or Country step.
  - South Korea (8) opens straight to its 8 makers, with no province step.
  - Chugoku (8) opens straight to its 8 makers.
- **One child:** a level with only one group below it is skipped. For example, South America → South America region → Chile is one step.

**What shows at each step today:**

| Step | Pins |
|---|---|
| World | Asia (149) as a group pin. Europe, North America and South America are under 10, so they show as group pins that open straight to their makers. |
| Asia | East Asia (147) as a group pin, and Southeast Asia (2), which opens straight to its makers. |
| East Asia | Japan (137) as a group pin. South Korea (8) and Taiwan (2) open straight to their makers. |
| Japan | 8 area pins. Tohoku, Kanto, Chubu and Kansai are 10 or more, so they open to prefectures. The other four open straight to their makers. |
| Tohoku | 6 prefecture pins, each with its count. Fukushima (10) and Miyagi (10) open to their makers, and so do the rest. Below a prefecture there's no level left, so every prefecture opens to makers. |

So the group pins only ever appear where there are 10 or more makers to group. Anything smaller goes straight to the makers.

### 5.4 The pins (D1)

Both kinds copy the reference photo: a round, glossy head on a short silver needle, seen at a slight angle, with a soft shadow on the slate. They're drawn in SVG.

- **Group pins** (a continent, region, country, area or province):
  - a **large chalk-white pin** with the maker count written on its head;
  - its name on a small chalk tag beside it;
  - its size grows a little with the count (3 sizes).
- **Maker pins:**
  - a **smaller pin coloured by the maker's main category** (the category of most of its drinks):

    | Category | Pin |
    |---|---|
    | Sake | red |
    | Fermented Beverages | yellow |
    | Umeshu | pink |
    | Liqueur | orange |
    | Wine | purple |
    | Spirits | blue |
    | Cocktails | green |

  - **A legend** of the colours in use sits under the map, as small pins with the category names.
- **Taps and keys:**
  - Every pin is a `<button>` with a tap target of at least 44 px. Its label is "{Name}, {n} makers, zoom in" or "{Maker}, {location}, open card".
  - Hover and focus lift the pin 2 px and show its name tag.
- **Crowding:**
  - Pins that would overlap by more than a third of a head are nudged apart, with a thin chalk line back to their real spot.
  - If more than 3 makers share one spot (for example a town with several breweries), they show as one pin with a small count, which fans out into a ring when tapped.
  - The smoke test checks that no two pin heads overlap at any level, at all four sizes.

### 5.5 Moving around the map

- **Clicking a group pin** zooms into it: the view eases to fit that group's area in 450 ms (instant with reduced motion). Other countries stay drawn faintly for context, and the chosen area's outline is lightly hatched as today.
- **A chalk breadcrumb** above the map shows the place: "World › Asia › East Asia › Japan › Tohoku". Each part steps back up. **Esc** and a "Back" chalk button go up one level.
- **Clicking a maker pin** opens a small chalk card on the map: name, native name, location, drink count, and "Open maker". Esc or a tap elsewhere closes it.
- **No drag or pinch zoom.** Moving is by pins and the breadcrumb only, so the page still scrolls normally on phones.
- **Phones:** the map board is at most **55% of the screen height** (keeping the Plan 08 §10 fix), and the list starts below it.

### 5.6 The info line under the map

Below the map, a chalk line names the current place and its tallies:

> **Tohoku** · 37 makers · 61 drinks · 5 favourites

At the World level it reads "Everywhere · 159 makers · …". It uses `aria-live="polite"`. On a maker card the line doesn't change.

### 5.7 Map and list move together

- **Map → list:** the list shows **only the makers in the current place.** Zooming into Tohoku filters the list to Tohoku's 37 makers, and a removable chip appears ("Tohoku ×"). Removing the chip goes back to World.
- **List → map:**
  - Choosing a **country** in the dropdown zooms the map to that country.
  - **Search** shows only the matching makers' pins, and zooms the map to the **smallest place that holds all of them.** For example, a search that matches 2 Niigata makers zooms to Niigata. Clearing the search returns to the place chosen before.
  - The count line ("12 makers") and the map's info line always agree.
- **Address:** the place is kept in the address as `#/makers?at=asia/east-asia/japan/tohoku`. It works with Back and with shared links.
  - The old `?country=` and `?region=` links still work, and are read as the matching `at=`.
- **The "Elsewhere" buttons** go, because every country is on the map now. The country dropdown stays.
- **The list is still the main way in.** It stays complete and usable by keyboard and screen reader with the map ignored (Plan 04 §9).

## 6. The map on a maker page (brief item 4)

- **Every maker page with a pin** gets a map in its Facts board, for every country, not only Japan.
- **It opens zoomed to the maker's province or state** (§5.3), drawn in chalk:
  - the province outline, lightly hatched, with its neighbours faint around it;
  - the maker's **coloured pin** at its coordinates;
  - the **capital** of the province, with a small chalk star and its name;
  - up to **4 major towns or cities** in the province, each a chalk dot with its name. They're chosen by population, and only towns of about **50,000 people or more** count. A rural prefecture may show only its capital, and that's fine.
  - Labels never cover the pin or each other. A town whose label won't fit is left out.
- **Special cases:**
  - **City-provinces** (Tokyo, Osaka, Singapore, Daejeon, Copenhagen and others like them) show the city and its neighbours, with the capital star on the city itself and no separate towns.
  - **Small provinces** show enough of their surroundings for the map to read, at least about 60 km across.
- **A small inset** in the corner shows the whole country, with the province hatched, so a reader can see where it is (D3).
- **Capitals and towns come from Natural Earth's populated places.** The owner can correct one in a new hand-kept file, `content/map-places.json` (for example, to rename a town or to add one).
- **The words for screen readers:** "Map of Iwate, Japan, showing Akabu Shuzo in Morioka, with Morioka the capital."
- **The Facts board layout** keeps the Plan 09 §11 container-query rules. The map simply appears for every country now.

## 7. Where things go

| Piece | Files |
|---|---|
| Counter per category | `build/liquid/` shelf output, `assets/js/counter.js`, `welcome.js` |
| Shelf 2 first | `welcome.js` `rowsV3`, `selfcheck.js` |
| Coordinates | Producers sheet (researcher), `build/liquid/` producers output |
| Map files | `build/tools/makemaps.py`, `docs/assets/maps/` |
| Map drawing | `assets/js/map.js` (rewritten for any country and the pins), `makers.js`, `producer.js` |
| New checks | W25, W26, E08 in `checks.py` |

## 8. Order of work

1. **Counter and shelves** (§3, §4). These don't need the new data, so they go first, as their own commit.
2. **Coordinates** (§5.1). The researcher runs this alongside step 1, in 4 batches of about 40 makers, each approved by the owner.
3. **Map files** (§5.2), then **the Makers map** (§5.3 to §5.7), then **the maker page map** (§6), once all coordinates are in. W26 lets the maps be built and checked before then, using region centres.

## 9. Acceptance

**Counter and shelves:**
- [ ] In category view, every category shows 5 New arrivals and 5 In season bottles, with "in {Category}" or "in {Category} + more". A test checks a category that needs topping up (Umeshu, with 3 drinks) and one that doesn't (Sake).
- [ ] On the wide plate, shelf 3 holds only what fits clear of the counter, and shelf 2 holds the rest. Selfcheck finds no lower-shelf bottle behind a counter bottle in any category view, at all four sizes.

**Makers map:**
- [ ] The World view shows the pins as in §5.3. Clicking down to a prefecture and back up through the breadcrumb works, and Esc goes up a level.
- [ ] The fewer-than-10 and one-child rules hold at every level. A test walks the whole tree from today's data.
- [ ] Map → list, list → map and the address all agree, including old `?country=` and `?region=` links.
- [ ] No two pin heads overlap at any level at 1440×900, 1920×1080, 375×812 or 390×844. Every pin is a 44 px target.
- [ ] On phones the map board is at most 55% of the screen height, and there's no sideways scroll.

**Maker page map:**
- [ ] A maker page in each of the 10 countries shows its province, its pin, the capital and any major towns, with no overlapping labels.

**Throughout:**
- [ ] The build has 0 errors, W25 is 0, and W26 counts only the makers still waiting for coordinates. The full pytest and the privacy scan pass. No street address is published.
- [ ] The Makers page with its map and country files loads in under 300 KB at the World level.
- [ ] Screenshots into `reports/plan14/` at the four sizes: a category view with a topped-up counter, Sake's shelves, the map at World, Asia, Japan, Tohoku and a maker card, and one maker page each from Japan, South Korea, France and Singapore.
- [ ] Commits with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **No push** without the owner's word.

## 10. Decisions

| # | Question | Answer |
|---|---|---|
| D1 | What do the pin colours mean? | Owner approved 2026-11-09: **Maker pins coloured by main category, group pins chalk-white with a count** (§5.4). The other choice would be colour by continent, which says less once you're zoomed into one country. |
| D2 | Add Japan's 8 areas between Japan and its prefectures? | Owner approved 2026-11-09: **Yes.** Without it, Japan opens to 40 prefecture pins, and around Tokyo 7 of them crowd into a thumb's width on a phone. The fewer-than-10 rule still applies to each area. |
| D3 | A small country inset on the maker page map? | Owner approved 2026-11-09: **Yes,** so a reader who doesn't know Iwate can see it's in northern Japan. It's a few KB. |
| D4 | Who finds the coordinates? | Owner approved 2026-11-09: **The researcher,** from the maker's address, in owner-approved batches (§5.1). |
| D5 | Coordinates batch 1 (makers 1–40) | Owner, 2026-11-09: "Approve as proposed". 39 entered, mostly at block level (OpenStreetMap has few Japanese house numbers), which the owner accepted. |
| D6 | Date Seven (seven Miyagi breweries, no single site) | Owner: "Leave blank". It gets the Miyagi centre pin, with W26. |
| D7 | Haccoba's location | Owner: "Change to Namie". The brewery's own site puts it in Namie, not Minamisoma. |
| D8 | Coordinates batch 2 (makers 41–80) | Owner, 2026-11-09: "Approve as proposed", including the town and village pins (Hwanggeumbori, Kawanishiya, the Jeju makers). |
| D9 | Isekado's pin | Owner: "Brewery shop, Shimono-cho", not the Jinkyu head office. |
| D10 | Coordinates batch 3 (makers 81–120) | Owner, 2026-11-09: "Approve as proposed", including the 5 town pins (Koueigiku, Machida, Orchid Sake Brewery, Ozawa, Puku Puku). |
| D11 | Kronenbourg's pin | Owner: "Obernai brewery". The ledger location changes from Strasbourg to Obernai to match. |

## 11. Review fixes (2026-11-09)

The designer reviewed `reports/plan14/` (commits `898eb45`, `ac97114` and `6a9dd0b`).

**What's right:**
- **The counter in category view:** "in Sake", and "in Wine + more" with the topped-up bottles.
- **Shelf 2 filling first:** Sake shows 6 on shelf 2 and 4 on shelf 3, clear of the counter groups.
- **The World and Japan levels:** the pin look, the breadcrumb, the legend and the info line.

The fixes below are all needed before any push.

### 11.1 The maker page map shows no capital or towns

- **Fault:** Akabu Shuzo's Iwate map shows only the outline and the pin. Morioka, the capital, isn't marked. Ichinoseki, Oshu, Hanamaki and Kitakami (each about 90,000 people) are missing too. The South Korea page is the same. §6 asks for both.
- **Fix:**
  - **The capital always shows.** If the pin sits on it, as Akabu does in Morioka, the star and label go beside the pin, not under it. That way the reader still sees "Morioka" named.
  - Add up to 4 towns of about 50,000 people or more, as §6 says.
  - Check `content/map-places.json` and the country files really carry Natural Earth's capital flag and populations, and that the label-collision step isn't dropping everything.
- **Check:** a test confirms the maker page map for Akabu (Iwate) labels Morioka plus at least 2 towns. It also confirms that every maker page map labels its province's capital.

### 11.2 The wrong province for Daejeon

- **Fault:** Daejeon Blues' map hatches **Chungcheongnam-do**, and the pin sits in the unhatched hole where Daejeon is. Daejeon is its own metropolitan city, so it should be the hatched province, shown as a city-province (§6 special cases).
- **Fix:** take the province from the point-in-polygon test, as §5.1 says, and not from the `region` text or a nearby centroid. Then treat metropolitan and special cities as city-provinces, with their neighbours shown. Check the other city-provinces the same way: Tokyo, Osaka, Singapore, Copenhagen, Ho Chi Minh City and Taichung.
- **Check:** a test confirms that each maker's hatched province contains its own pin, for all 159 makers.

### 11.3 Phones: the breadcrumb takes five lines and squeezes the map

- **Fault:** at 375 and 390 wide, "World › Asia › East Asia › Japan › Tohoku" wraps onto 3 to 5 lines beside the Back button. That leaves the map under 220 px tall, and the Tohoku and Iwate maps are hard to read.
- **Fix:**
  - **On phones, the breadcrumb is a single line.** It shows Back, then "… › Japan › Tohoku". Tapping "…" opens the full list as a small chalk menu.
  - **The map takes the space the breadcrumb gave back,** up to the 55% limit.
  - **A tall, narrow place** like Tohoku fits the map's height.

### 11.4 Phones: pins overlap in Tohoku

- **Fault:** at 390×844, Iwate's pin and label cover Miyagi's pin. Its count can't be read.
- **Fix:** the §5.4 nudge must keep pin heads **and their name tags** apart. A tag may sit on the left or the right of its pin, whichever side is clear. The smoke test's overlap check must cover tags as well as heads.

### 11.5 Using the coordinates now in the ledger

- **The screenshots were taken before the researcher entered batches 1 and 2.** 79 makers now have `Latitude` and `Longitude`, and batch 3 is going in.
- **Rebuild with them.** Report W25 (which should be 0) and W26 (makers still waiting).
- **Make sure the area and prefecture counts come from the coordinates.**

### 11.6 Acceptance

- [ ] §11.1 to §11.5 pass their checks. The full pytest, the 0-error build and the privacy scan pass.
- [ ] Retake every map and maker page screenshot in `reports/plan14/` at the four sizes. Add `maker-iwate-labels-1440x900.png` and `map-tohoku-375x812.png`.
- [ ] Commit as "Plan 14 §11: map review fixes", ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **No push.**
| D12 | Coordinates batch 4 (makers 121–159) | Owner, 2026-11-09: "Approve as proposed". Every maker except Date Seven now has a pin. |
| D13 | Producers rows that share a page (Machida, Yamamoto) | Owner: "Same pin on both". |
| D14 | Kronenbourg's Region | Owner: "Change to Obernai", so Location, Region and the pin all agree. |

## 12. Second review (2026-11-09)

The designer reviewed commit `336ef51`. §11.1 to §11.5 pass: Morioka is labelled beside the pin with three towns, the Tohoku pins are readable, and the province test covers all 159 makers.

### 12.1 Phones, category view: the counter bottles hide behind the tags

- **Fault:** at 390×844, in Wine's category view, the "Cabernet Sauvignon" tag covers the counter's New bottles, so only 2 of 5 can be seen. The shipper's judgement call drew the tags in front of the counter. The counter stands nearer the viewer, so that also looks wrong.
- **Fix (phones, category view only):**
  - Draw the counter bottles **in front of** the subcategory tags.
  - Move each subcategory tag **onto its shelf's lip as a single line,** with smaller lettering, down to no less than 12px. That way it ends above the counter bottles' tops.
  - If a name still can't fit on one line, the tag sits **above** its bottle on the back wall instead.
- **Check:** the smoke test confirms that no subcategory tag overlaps a counter bottle at 375×812 and 390×844, for every category.

### 12.2 Phones: the Menu button covers the breadcrumb

- **Fault:** at 375×812, the breadcrumb reads "… › Japa", because the Menu button sits on top of it.
- **Fix:** the breadcrumb row ends before the Menu button's left edge. If the last part still won't fit, the breadcrumb shows only "… › Tohoku".
- **Check:** the smoke test confirms the breadcrumb and the Menu button don't overlap, at both phone sizes, at every map level.

### 12.3 Judgement calls

- **Accepted:** the W26 scope, France by department, the pin and tag rules, the stack pins, W27, and the smoke-test retry.
- **"See all {n} kinds":** remove it. It never triggers, and it pointed at the page the visitor is already on.
- **Unused Japan map files** (`japan-prefectures.svg`, its LICENSE and `make_japan_map.py`): delete them.
- **The hand-added towns in `content/map-places.json`** were typed from memory. The researcher is checking them against real sources. Apply its corrections once the owner approves them.

### 12.4 Acceptance

- [ ] §12.1 and §12.2 pass their checks. The full pytest, the 0-error build and the privacy scan pass.
- [ ] Retake the counter-topup and Sake-shelves screenshots at 375×812 and 390×844, and the map screenshots at both phone sizes.
- [ ] Commit as "Plan 14 §12: phone counter and breadcrumb fixes", ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **No push.**

### 12.5 Map data corrections (researcher's check, 2026-11-09)

The researcher checked the three W27 pins against OpenStreetMap's real boundaries, and checked the 151 hand-added towns against Wikidata (`Research/pending/2026-11-09-map-checks.md`).

- **W27:** all three pins are right. Daejeon Blues is in Seo-gu, Akishika in Nose (Osaka) and Hagino in Kurihara (Miyagi). Natural Earth's outlines are coarse near borders.
  - **Fix:** the build looks for the province within **3 km** of the pin, and prefers the one named in the maker's Region or Location. W27 is raised only past 3 km.
  - These three are then hatched in Daejeon, Osaka and Miyagi, and their counts move to match.
- **Towns:**
  - Two have wrong coordinates. Nanto should be 36.557, 136.875, and Fuefuki 35.647, 138.640.
  - Three fall below the 50,000 rule: Fujiyoshida, Kainan and Nanto. **Drop them.**
- **Wrong province capitals.** Correct them in `content/map-places.json`:

  | Country | Province | Wrong | Right |
  |---|---|---|---|
  | Japan | Yamaguchi | Shimonoseki | Yamaguchi City |
  | Japan | Saitama | Kawaguchi | Saitama City |
  | South Korea | South Chungcheong | Cheonan | Hongseong |
  | South Korea | North Gyeongsang | Pohang | Andong |
  | South Korea | South Jeolla | Yeosu | Muan |
  | South Korea | Sejong | Gongju | Sejong (a city-province) |
  | France | Pyrénées-Atlantiques | Biarritz | Pau |
  | France | Morbihan | Lorient | Vannes |
  | France | Manche | Cherbourg | Saint-Lô |
  | France | Pas-de-Calais | Calais | Arras |
  | France | Corrèze | Brive | Tulle |
  | France | Haut-Rhin | Mulhouse | Colmar |
  | France | Marne | Reims | Châlons-en-Champagne |
  | France | Finistère | Brest | Quimper |

  Also apply the smaller slips in the researcher's file: Denmark's Hovedstaden seat, the Vietnamese capitals, and the province name spellings.
- **Capitals must come from a checked list.** "The biggest town" is not the capital. Yamaguchi and Saitama both have makers, so their maker pages were showing the wrong capital.

## 13. Zoom framing and place signs (2026-11-09, owner request)

**The owner's words:** "when zooming into the country level, maintain the states shape and zoom to the state level if drilled down further. have a small sign to denote the country and state when drilling down".

**What the designer saw in the local preview** (a 745 px wide pane):
- **At Japan,** the country fills less than half the map. The prefecture outlines are faint hairlines, and the pins hang off them on leader lines.
- **At Tohoku and Kanto,** the view doesn't frame the area. Kanto sits low and to the right.
- **At Iwate,** the prefecture sits at the top edge and is cut off, and much of the map shows its neighbours.

### 13.1 Province shapes stay drawn from the country level down

- **From the country level down,** every province of that country is drawn as a **clear chalk outline**, at the same stroke weight as the country's coastline. They're not hairlines. Provinces with makers are lightly hatched. Provinces without makers keep their outline and stay unhatched.
- **The outlines stay** at every deeper level (area, province). Zooming in only changes the framing. Shapes never disappear or redraw differently.
- **The chosen area or province** is hatched in glow chalk with a slightly heavier outline, as now. Its neighbours stay outlined, dimmed to about 50%.

### 13.2 Zoom to fit the chosen place

- **Every level frames the chosen place's own outline,** not its makers' pins:
  - fit to the shape's bounding box, centred in the map;
  - about 8% padding on every side;
  - keeping the map's aspect ratio. A tall place like Tohoku or Iwate fills the height, and a wide one fills the width.
- **Nothing of the chosen place is cut off** at any of the four sizes, or at narrow desktop widths like a 745 px pane.
- **Pins sit inside their province.** A pin stands on its real spot, or for a group pin, on a point inside the shape (its visual centre, not the bounding-box centre, which can fall outside a curved shape). Leader lines are used only when the §5.4 nudge must move a pin, and they stay short.
- **The province level** frames that one province, and its makers' pins stand on their real spots.
- **City-provinces** (Tokyo, Osaka, Singapore and others) get at least the §6 minimum of about 60 km across, so they aren't a tiny dot.

### 13.3 The place sign

- **What it is:** a small **hanging wooden sign** in the map's top-left corner. It matches the bar's carved plank sign: a short plank on two little chains, the place name carved or chalked on it in the site's display font.
- **What it says** (from the country level down):
  - At a country: **"JAPAN"**.
  - At an area or province: two lines, the country small on top and the place below, for example **"JAPAN / Tohoku"** or **"JAPAN / Iwate"**. At a province inside an area, the area isn't repeated on the sign. The breadcrumb already shows it.
  - At World, a continent or a region there's no sign. The breadcrumb is enough.
- **Size:** about 18% of the map's width, never more than 200 px. On phones the lettering is at least 13 px.
- **Behaviour:**
  - It swings in gently (a 6° rotation that settles, in 400 ms) when the place changes. With reduced motion it just appears.
  - It's not a button. It's decoration, so it's `aria-hidden`. The breadcrumb and the info line already announce the place.
- **It never covers a pin.** If the chosen place's shape reaches into that corner, the sign moves to the top-right corner instead.

### 13.4 Acceptance

- [ ] At Japan, Tohoku, Kanto, Iwate, Tokyo, South Korea, France and Singapore, the chosen shape is whole, centred and padded, at 1440×900, 1920×1080, 375×812, 390×844 and a 745×527 pane. A smoke check confirms the shape's bounding box sits inside the map with at least 5% padding.
- [ ] Province outlines show at every level from the country down. The smoke test confirms the province paths are present and visible at each of those levels.
- [ ] The sign shows the right words at each level, never overlaps a pin (smoke-checked), and isn't shown at World, continent or region.
- [ ] Retake the map screenshots in `reports/plan14/` at the four sizes, plus `map-japan-745x527.png` and `map-iwate-745x527.png`.
- [ ] The full pytest, the 0-error build and the privacy scan pass. Commit as "Plan 14 §13: zoom framing and place signs", ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **No push.**
