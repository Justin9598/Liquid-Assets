# Plan 07: Welcome page v4: bottle shells, counter displays, burger menu, phone parity

Status: **Approved (owner brief and answers, 2026-11-01).**
Author: Claude (designer). This is a plan only. The `shipper` implements it.
Builds on: [Plan 01](01-welcome-page.md) (v3 scene, §15), [Plan 06](06-deployment.md) (Phase 1, welcome page only).
Supersedes, **on the welcome page:**
- Plan 01 §13 (the iron-puck menu and overlay). The burger replaces them (§3).
- The Plan 01 §2.3 counter anchors (slate at the left, menu at the right). They're replaced by §4.1.
- The Plan 01 §12C shell brief. It's replaced by the owner's sheet (§2).

Design read and dials are unchanged from Plan 01 §2: variance 6, motion 5, density 3.

---

## 1. Owner brief (2026-11-01)

1. Use the supplied renders as the bottles for the categories.
2. Put **5 new items on the left of the counter**, changing with every new addition, and **5 seasonal recommendations on the right**.
3. Use the supplied **hamburger image as the menu** on the counter. On press, it splits into one layer per option, with the words beside the layers. Clicking away collapses it back.
4. Desktop and phone should give a similar experience, now and in future.

### Answers

| Question | Owner's decision |
|---|---|
| Phones until the tall bar image exists | **Keep the old design for now.** |
| What "fits the season" means | **Japanese seasons**, picked automatically, with owner pins allowed |
| Burger layers | **4 layers, grouped:** The Bar, Shelves, The Makers, About |
| Liqueur bottle | **Use the liquor (spirits) bottle** |

---

## 2. Bottle shells from `Design/scene/shells-sheet.webp`

### 2.1 Source and mapping

The source is 1672×941, on black, with 10 cells in two rows. Cells are numbered left to right, top row first.

| Cell | Render | Used for |
|---|---|---|
| 1 | Green sake bottle with a **blank paper label** | **Sake** (vessel and all subcategories) |
| 2 | Milky PET bottle | **Makgeolli** |
| 3 | Dark Bordeaux wine bottle, red capsule | **Wine** |
| 4 | Brown longneck beer bottle | **Beer** (vessel and all style bottles) |
| 5 | Silver can | Not used yet (kept for later) |
| 6 | Pint glass of beer | Not used yet (kept for later) |
| 7 | Clear corked liquor bottle | **Spirits**. Also **Liqueur** (owner's answer), with the liquid tinted amber so the two shelves differ by colour. |
| 8 | Coupe | Not used yet |
| 9 | Martini glass | **Cocktail** top-shelf vessel |
| 10 | Highball glass with ice | **Cocktail** subcategory glasses |

### 2.2 Cutting them out

- Crop each used cell, then remove the black background to get a transparent image:
  - **Opaque objects** (wine, beer, makgeolli, the sake bottle's label area) get a solid mask with a 1–2px feathered edge.
  - **Clear glass** (the liquor bottle, martini, highball) keeps partial transparency, so the shelf glow shows through it.
- Work automatically first. Then refine by hand with a mask polygon stored in **`Ship/content/shells.json`**, which also records for each shell:
  - the crop box,
  - the mask polygon,
  - the `labelRect` (fractions of the shell),
  - the base line (where the glass meets the shelf),
  - a soft contact shadow.
- **Check every cut-out composited over the bar plate's shelf area,** not on black. A dark halo or a missing rim is a fail. The build report gets a "shells on plate" contact sheet.
- **Outputs:** WebP at 1x and 2x into `docs/img/scene/`. The original sheet is never published. Cells are about 440px tall, which is enough for bottles up to about 200 CSS px.
- If a clean cut-out of a cell can't be made, keep the drawn v2 shape for that category and list it in the report.

### 2.3 Labels on the shells

| Shell | How the photo label goes on |
|---|---|
| Sake (has a white paper label) | Clipped to the white label and `multiply` blended, so the shell's shading shows through (Plan 01 §7.1) |
| Makgeolli, Wine, Beer, Liquor (no white label) | Normal blend, clipped to `labelRect` on the body, with a curvature overlay on top (darker at the left and right edges, plus a thin highlight strip) and a 1px soft shadow, so it reads as a paper label stuck to the glass |
| Martini, Highball | **No photo label.** The slate tag underneath names the subcategory. |

The Plan 01 §15.3 label-only rule still applies. A photo marked `skip` never becomes a label, and the bottle uses the fallback label instead.

---

## 3. Burger menu (welcome page)

### 3.1 Source and layers

`Design/scene/burger.webp` is 1536×1024, on black, a burger on a speckled plate on a wooden table edge. Cut out the **burger and plate** (no table, no background).

The burger is split into **4 layers** along its natural boundaries. The cut paths follow the real edges where the layers meet; they aren't straight horizontal lines. The paths are stored in **`Ship/content/burger.json`**.

| # | Burger layer | Menu option |
|---|---|---|
| 1 | Top bun (sesame) | **The Bar** (home) |
| 2 | Lettuce, tomato, onion, bacon | **Shelves** (opens the 7 categories, §3.4) |
| 3 | Cheese and both patties | **The Makers** (in Phase 1, shown as "The Makers · Soon", not a link) |
| 4 | Sauce, bottom bun and the plate | **About** (the one-line description and credits from Plan 01 §13) |

**One layer per option:** the number of layers always equals the number of top-level options. When the option list changes, the designer amends this table and the shipper re-cuts `burger.json` (2 to 6 layers supported).

### 3.2 At rest

- The burger on its plate sits on the counter top at the right end (§4.1), about **13% of plate height** (roughly 115px at 1440×900), with a small soft shadow.
- A slate tag in front reads **Menu**.
- On hover or focus, the burger lifts 2px and the spot above it warms. On press, it dips 1px.

### 3.3 Opening: the burger splits

When the burger is pressed:
1. The scene dims to about 50% and blurs. A solid fallback is used when reduced transparency is set.
2. The burger rises from the counter to the **vertical centre and right third** of the viewport, scaling to about **3×**. The plate fades out as it lifts.
3. The 4 layers **split apart vertically** in a stagger, top bun first. Each layer moves to its slot, with gaps of about one layer height. The easing is a spring (`cubic-bezier(0.16,1,0.3,1)` or an equivalent spring), about 550ms in total.
4. Each option's **words slide in beside its layer,** on the left, since the burger sits right. The words are Cormorant Garamond at about 32–40px, chalk colour, with a soft shadow for contrast on the dimmed scene.
5. Every animation uses only `transform` and `opacity`.

### 3.4 Shelves submenu

- Pressing the **Shelves** layer or its words reveals the 7 categories, each with its drink count (Sake 242…), as a short list beside that layer.
- Pressing a category selects that shelf on the bar (`#/<category>`) and closes the menu.

### 3.5 Closing

- Clicking or tapping anywhere outside the layers and words, pressing **Esc**, or choosing an option closes the menu.
- The layers **rejoin** in reverse stagger, and the burger shrinks back onto its plate on the counter.
- Focus returns to the burger button.

### 3.6 Accessibility

- The burger is a `<button aria-label="Menu" aria-expanded aria-controls>`. The open menu is a `role="dialog"` with `aria-modal`. Focus is trapped while it's open.
- **Layer images are decorative** (`aria-hidden`). The words are the real links and buttons, and each is at least 44px tall.
- With `prefers-reduced-motion`, the menu opens already split and closes with a 150ms crossfade, with no flying.

### 3.7 Other pages

*Superseded by [Plan 08 §3.2](08-phase-2-launch.md) once approved: every page uses the same split burger menu as the counter.*

Plans 02–04 pages (Phase 2 onwards) keep the iron-puck button in their header. It opens the same four options as a plain list. The burger animation belongs to the bar counter.

---

## 4. Counter displays

### 4.1 Counter layout (wide plate)

This replaces the Plan 01 §2.3 anchors. All positions are fractions of the plate.

| Zone | x range | Content |
|---|---|---|
| Left | 0.04 – 0.31 | **New arrivals**: 5 bottles |
| Centre | 0.38 – 0.62 | **Status slate** (Plan 01 §5, moved to the centre) |
| Right | 0.64 – 0.85 | **In season**: 5 bottles |
| Far right | 0.87 – 0.97 | **Burger menu** (§3) |

- **Bottles on the counter** stand on the measured counter-top line. The counter is nearer the viewer than the shelves, so they're about **15% of plate height**, larger than the shelf bottles. They use the §2 shells and labels, evenly spaced within their zone.
- Each group has a **small slate placard** in front: "New arrivals" and "In season: Autumn". The season name updates with the date.
- **Hover/focus:** the bottle lifts 3px and a name tag appears.
- **Phase 1 press:** the slate shows *"{Name}, {Category}. Its page opens soon."* for about 3 seconds. In Phase 2 the bottle links to its drink page.

### 4.2 New arrivals (left)

- **The 5 most recent drinks.** Each drink is ranked by its latest occasion date: `Acquired`, else `Added`. Ties go to the later ledger row.
- **Repeat visits count,** so a re-tasted drink moves back to the front, and drinks are never shown twice.
- **It changes automatically at every build,** with no owner action.
- Today it shows the latest drinks in the ledger. Once the Fermenteria batch is entered (see the update note of 2026-11-01), it fills with those.

### 4.3 In season (right)

- **The season comes from the visitor's current month,** read in the browser, so it changes without a rebuild:

  | Season | Months |
  |---|---|
  | Spring | March to May |
  | Summer | June to August |
  | Autumn | September to November |
  | Winter | December to February |

- **The build precomputes 5 picks for each season** and stores them in `shelf.json`.
- **Matching keywords** live in `Ship/content/seasonal.json`, so the owner can edit them. They're checked against Name, Style(s), Public Notes and `Other Detail.Type`, ignoring case:

  | Season | Keywords |
  |---|---|
  | Spring | haru, spring, sakura, hanami, 春, 桜, nigori, usunigori, sparkling |
  | Summer | natsu, natsuzake, summer, 夏, sparkling, yuzu, citrus, Wheat, Lager, Pilsner, Highball |
  | Autumn | hiyaoroshi, ひやおろし, akiagari, aki, autumn, 秋, halloween, kimoto, yamahai, aged, amber, Pale Ale |
  | Winter | shiboritate, 新酒, shinshu, winter, 冬, nama genshu, nigori, kimoto, yamahai, Stout/Porter, Whisky |

  An ABV of 13% or less also counts as a summer match.
- **Scoring:**
  - +3 per keyword match (counted once per season).
  - +2 if a favourite (★).
  - +1 if it has an `ok` label photo.
  - +0.5 if it's among the 30 most recent.
- **Choosing the 5:** take the top 5, with at most **3 from one category**. If fewer than 5 match, fill the rest with favourites, then recent drinks.
- **Owner pins:** `seasonal.json` → `"pins": { "autumn": ["<id>", …] }` puts drinks first, and `"exclude": [...]` removes them.
- **The build report** lists each season's 5 picks and why each was chosen.

### 4.4 Data

`shelf.json` gains:

```jsonc
"counter": {
  "newArrivals": [ { "id", "name", "category", "sub", "label" } ],
  "inSeason": {
    "spring": [ ... ],
    "summer": [ ... ],
    "autumn": [ ... ],
    "winter": [ ... ]
  }
}
```

- Each `label` is the cropped label image, or `null` for the fallback label.
- These are Phase 1 data: names and labels only, which is fine to publish.

---

## 5. Phone parity

### 5.1 Why the phone looks different now

- Phones show the v2 drawn bar on purpose. The wide plate can't fill a portrait screen without cutting off the shelves (Plan 01 §15.2).
- **The owner chose to keep it until the tall image exists.** v4 (shells, counter displays, burger) therefore ships on **desktop and landscape first**.

### 5.2 What ends the gap

- **The owner makes `bar-tall`** (Plan 01 §12 prompt B, with `Design/scene/bar-wide.webp` attached as the style reference) and saves it to `Design/scene/`.
- The shipper then measures it, and phones get the full v4 at once:

  | Element | Tall-plate layout |
  |---|---|
  | Vessels | Two rows of vessels |
  | Subcategories | Two lower shelves that scroll sideways |
  | Counter | Shows **one group at a time**, with two small tabs, **New** and **In season**, and the burger at the right |
  | Burger | Opens to the left of centre and fills most of the screen height |

### 5.3 Standing parity rule (from v4 on)

- **One feature, both layouts.** Once both plates exist, no welcome page change ships unless it works on **both** the wide and the tall plate. `scene.json` must hold phone values for every desktop feature, and the build fails with **`E06`** if one is missing.
- **Smoke test at two sizes.** Plan 06 §6 checks every push at **1440×900 and 375×812**, plus 1920×1080 for the plate. The shipper attaches both screenshots to its report.
- **Asset pairs.** Any future scene asset (a new plate, a new counter prop) is briefed and delivered as a **wide and tall pair**.

---

## 6. Acceptance criteria

- [ ] **Shells:**
  - Sake, Makgeolli, Wine, Beer, Spirits, Liqueur (tinted) and Cocktail (martini vessel, highball glasses) use the cut-outs, with no black halos, on the plate at 1440×900 and 1920×1080.
  - Labels follow §2.3 and the label-only rule.
  - The original sheet isn't published.
- [ ] **Counter:**
  - The left group shows the 5 latest drinks by latest occasion.
  - The right group shows the 5 picks for the current Japanese season, with the season name on its placard.
  - Hover shows names, and in Phase 1 a press shows the "opens soon" slate message.
- [ ] **Burger:**
  - The burger rests on its plate at the counter's right.
  - Pressing it splits it into exactly 4 layers with their words beside them.
  - Shelves opens the 7 categories.
  - The Makers shows "Soon" in Phase 1.
  - Clicking away, Esc or choosing an option rejoins the layers onto the counter.
  - Keyboard and screen-reader behaviour follows §3.6, and reduced motion follows §3.6.
- [ ] **Desktop:** 1440×900 and 1920×1080 have no scroll, nothing overlaps, and all four counter zones fit.
- [ ] **Phone:** phones still show v2 until `bar-tall` exists, and the report says so. Once it exists, the §5.2 layout applies, and the §5.3 rule is enforced by `E06` and the two-size smoke test.
- [ ] The build report includes the shells-on-plate sheet, the burger layer sheet and each season's picks.

---

## 7. Tall plate delivered (2026-11-01): phones move to v4

### 7.1 The image

- **File:** `Design/scene/bar-tall.webp`, **852×1846**. That's exactly 9:19.5.
- **Contents:**
  - A beamed ceiling with a large paper lantern, and the carved **LIQUID ASSETS** sign (serif lettering).
  - A light-oak backlit unit with **three level, empty shelves**, spanning about x 17–87% and y 33–57%.
  - A clear plank counter top at about y 60–66%, a tall vertical-board counter front, and four seagrass stools.
  - A cherry-blossom print and a barrel at the left, and shoji screens with a vase of blossom at the right.
- **Checked against Plan 01 §12B:** straight-on camera, level and empty shelves, correct sign, shelves centred. All pass.
- **Known differences, accepted:**
  - It has **3 shelves, not 4.**
  - The sign's lettering is a carved serif, while the wide plate's is brush-style.
  - The resolution (852 wide) is below the 1290 target, so it will look slightly soft on high-density phones.
  - The owner can replace it later under the same name.

### 7.2 Phone layout on the 3-shelf tall plate

This replaces the four-shelf layout in §5.2 and Plan 01 §2.5.

| Shelf | Content |
|---|---|
| Shelf 1 | Vessels: **Sake, Makgeolli, Liqueur, Beer** |
| Shelf 2 | Vessels: **Wine, Spirits, Cocktail** |
| Shelf 3 | **Subcategory bottles** for the selected category. 3 visible at a time, scrolling sideways in the shelf with scroll-snap, with soft fades at the ends when there's more. The default mixed state shows a scrollable mix. |
| Counter top | Two small tabs, **New** and **In season**, showing one group of 5 counter bottles at a time. The **burger** on its plate sits at the right, and the status slate shows as a slim line above the tabs. |

Bottle size follows the 82% clear-height rule (Plan 01 §2.5). Counter bottles follow the 15% rule, measured against this plate. The burger opens to the left of centre (§5.2).

### 7.3 Parity now applies

- With both plates present, **phones switch from v2 to v4.** The v2 scene code is retired from the welcome page.
- The §5.3 parity rule is now in force:
  - `E06` fails the build if `scene.json` lacks phone values for any desktop feature.
  - Every push gets the two-size smoke test with screenshots.
- `scene.json` gains a `tall` block, measured from this image the same way as the wide one: shelf lines, clear heights, counter-top line, and the slate, tabs and burger anchors.

---

## 8. Review fixes (2026-11-01)

The designer reviewed the first v4 build at 1440×900, 1920×1080, 375×812 and 390×844. The owner approved these fixes before any push.

### 8.1 Phone Shelves submenu must not cover other layers

- **Fault:** on the tall plate, opening Shelves lays the 7-category list over The Makers and About, and their words show through it.
- **Fix:** when Shelves opens on a phone, the layers below it (cheese/patties and the bottom bun) **slide down** to make room, and the list opens **inline under the Shelves layer**. Use the same spring ease as §3.3, and `transform` only. Closing the submenu slides them back.
- The panel is opaque (`--iron` at full opacity), so no text shows through.
- If the opened stack is taller than the viewport, the open menu scrolls inside itself. The page never scrolls.
- Desktop stays as built: the list opens to the left of the burger.

### 8.2 Subcategory name tags never overlap or clip

- **Fault:** on the wide plate at 1440×900 with a category open, the tags on shelf 2 run into each other, for example "Junmai Daiginjo" into "Junmai Ginjo", and get cut off.
- **Fix:**
  - Each tag's max width is its bottle slot (slot pitch minus an 8px gap). Names wrap to at most 2 lines, then the Japanese name and count go on a third line.
  - Text is never truncated with an ellipsis or hidden by overflow.
  - If a tag still doesn't fit at the minimum type size (12px), the shelf shows fewer bottles per row (wrap onto the next shelf) rather than shrink further.
  - Tags must also stay off the counter top on the tall plate. On phones, Tokubetsu Junmai's tag currently runs onto the counter beside the burger.
- **Test:** add a check to the smoke test that no two tag boxes intersect, and that every tag box lies inside the plate's shelf area, at all four sizes and for every category.

### 8.3 Lower shelves centred; counter bottles yield while a category is open

- **Fault:** the in-season counter bottles stand in front of the right end of the bottom shelf, so the build pushed the lower shelves into x 0.31–0.64, left of centre.
- **Fix:**
  - Remove the `shelfX` limit. Lower shelves are centred on the shelf unit's measured centre line and use its full clear width, as in Plan 01 §2.5.
  - **While a category is open, the counter bottles fade out** (opacity, 200ms) on the wide plate too, as on the tall plate. The counter labels (New arrivals, In season) stay visible, so the zones still read. The bottles come back when the view returns to the top shelf (`#/`).
  - In the resting state (`#/`), the lower shelves keep their mixed display. Where a counter bottle would cover a lower-shelf bottle, leave that lower-shelf slot empty instead of drawing one behind the other.
- This applies the §5.3 parity rule: both plates now behave the same way when a category opens.

### 8.4 Screenshots

- Retake `burger-open-phone-390x844.png`. The current one is a bad capture, with no burger layers, a black backdrop and a fallback font.
- Add `burger-shelves-phone-375x812.png` and `burger-shelves-phone-390x844.png`, showing the fix from §8.1.
- Add `sake-open-desktop-1440x900.png` and `sake-open-desktop-1920x1080.png`, showing the fixes from §8.2 and §8.3.

### 8.5 Acceptance

- [ ] On both phone sizes, the Shelves submenu covers no other layer's words.
- [ ] No tag overlaps or clips for any category at the four sizes, and the new automated check passes.
- [ ] The lower shelves are centred on the wide plate, and the counter bottles fade out while a category is open and return at `#/`.
- [ ] In the resting state, no lower-shelf bottle is drawn behind a counter bottle.
- [ ] Build 0 errors, all tests pass, privacy scan clean, no commit or push.

---

## 9. Burger words: they stay, on chalkboards (2026-11-01, owner request)

### 9.1 The words stay until the menu is hidden

- **Fault (owner report):** the option words show while the burger splits, then vanish.
- **Cause:** `burger.js` `open()` sets every word row's inline `opacity` to `0` before the animation. When the animations finish they are cancelled, but that inline `0` is never cleared, so the rows go back to invisible. The screenshots missed it because `still=1` takes the instant path, which never sets the inline `0`.
- **Rule:** once the burger has split, every option board stays fully visible, whatever the pointer, focus, hover or a panel is doing, until the menu starts closing. The boards leave only as part of the close animation (§3.5).
- **Fix:** clear the rows' inline opacity at the end state, and don't use inline styles to hide what a class should control. The `split` class shows the rows; closing is the only thing that hides them.
- **Regression test:** the smoke test opens the menu **without** `still=1` and calls `document.getAnimations().forEach(a => a.finish())` (the pane's clock may not advance). Then it waits 1 second and asserts that every `.bd-row` has a computed opacity of 1. It also hovers each layer and opens and closes Shelves, checking again after each step. Run this at all four sizes.

### 9.2 Each word is chalked on a small blackboard in front of its layer

The plain serif words are replaced. Each option is a **small blackboard with the word written in chalk**, standing **in front of** its burger layer, as if propped against it on the counter. That ties the menu to the bar, where specials go on a chalkboard.

**The board**
- **Size:** fits its word, with padding of 0.45em vertical and 0.8em horizontal. Minimum height 44px (tap target).
- **Surface:** slate `#262a28`, with 2 or 3 very faint chalk-dust smudges (radial gradients of `--chalk` at 4–6% opacity) so it reads as a used board, not a flat panel. Draw it in CSS. No image file.
- **Frame:** a thin wooden frame, 4px on desktop and 3px on phones, in the bar's wood tones (`#7a5534` outer, `#5a3b22` inner edge), with `--r-sm` corners. Use the site's one radius system.
- **Shadow:** `0 6px 14px rgba(20, 8, 2, .55)` so the board sits forward of the layer.
- **Tilt:** a fixed, slight tilt for a hand-placed feel: −1.5°, +1°, −1°, +1.5° from top to bottom. It's static and never animated beyond the entrance.

**Placement: in front of the layer**
- The board **overlaps the near edge of its layer by about 18% of the layer's width.** That's the left edge on desktop, where the words sit to the left, and the right edge on phones, where they sit to the right (§7.2). It's vertically centred on the layer.
- The board stacks **above** the burger art, so it's in front of the layer, never behind it.
- The board never covers more than 25% of its layer's area, so each layer still reads as a burger layer.

**The chalk lettering**
- **Font:** **Kalam** (OFL, Indian Type Foundry), weights 400 and 700, self-hosted as woff2 in `docs/assets/fonts/` with Latin and Latin-ext subsets, plus `OFL-kalam.txt`. Add it as `--chalkhand: 'Kalam', 'Cormorant Garamond', serif;`. No Google Fonts link.
- **Words:** 700, `clamp(22px, 2.1vw, 30px)` on desktop and `clamp(19px, 5.6vw, 24px)` on phones, colour `--chalk`.
- **Chalk grain:** a subtle chalk texture on the letters: a CSS `mask-image` of fine noise (inline SVG `feTurbulence` as a data URI) at about 85% coverage, plus `text-shadow: 0 0 1px rgba(242, 237, 228, .35)` for the dusty edge. It must stay crisp enough to read. If the mask hurts legibility at phone sizes, drop the mask on phones and keep only the shadow.
- **"Soon"** (The Makers in Phase 1): chalked smaller under the word, Kalam 400 at 0.55em, `--chalk` at 65% opacity, with a hand-drawn chalk underline (a 1.5px SVG stroke, slightly wavy). The old pill outline is removed.

**States**
- **Hover or focus:** the board lifts 2px (transform) and the chalk turns `--glow`. The keyboard focus ring is the site's usual `--glow` outline around the frame.
- **Open (Shelves or About with its panel showing):** the word gets a chalk underline (the same wavy stroke) and stays `--glow`.
- **Makers "Soon":** no hover lift, default cursor.

**Entrance and exit**
- **Opening:** each board drops in with its layer, the same spring and stagger as now (§3.3): opacity plus a short translate, followed by its tilt. No looping.
- **Closing:** the boards fade with the layers in the close animation. That's the only time they leave (§9.1).
- **Reduced motion:** boards appear in place with a 150ms fade.

### 9.3 Panels become chalkboards too

So the menu reads as one set:
- The **Shelves** list (§3.4, and the phone layout in §8.1) becomes a larger blackboard with the same surface, frame and shadow.
  - Each category name is chalked in Kalam 400 at 18px on desktop and 17px on phones.
  - Each drink count is chalked right-aligned in Kalam 400 at 70% opacity.
  - Rows are separated by faint chalk rules (1px `--chalk` at 15%), not boxes. Hover or focus turns a row's chalk `--glow`.
  - The board is opaque, as §8.1 requires.
- The **About** panel gets the same board. Its body text stays **Outfit** for readability, with only the heading chalked.

### 9.4 Unchanged

- The burger layers, their split distances and the scrim.
- How the menu closes: Esc, tap outside or choosing an option.
- Focus trap and focus return.
- The §8.1 phone rule: lower layers slide down when Shelves opens, and the boards move with their layers.

### 9.5 Acceptance

- [ ] With the real animation (not `still=1`), after the menu opens, all 4 boards stay at opacity 1. They stay through hovering each layer and opening and closing Shelves, at all four sizes, until Esc, tap outside or choosing an option closes the menu.
- [ ] Each board stands in front of its layer, overlapping its near edge by about 18% and covering no more than 25% of it, with chalk lettering in self-hosted Kalam.
- [ ] The Shelves and About panels are matching opaque chalkboards.
- [ ] The words are readable at 375×812: chalk contrast is at least 4.5:1 against the slate.
- [ ] Screenshots with the menu open at 1440×900, 1920×1080, 375×812 and 390×844, plus Shelves open at 1440×900 and 390×844. All are taken after a real open, not `still=1`.
- [ ] Build 0 errors, all tests pass, privacy scan clean, no commit or push.

---

## 10. Chalkboard lettering across the welcome page (2026-11-01, owner request)

Everything written on the welcome page moves to the §9.2 chalkboard look: chalk lettering on small framed blackboards, in place of the current dark pills and sans-serif labels. The menu and the bar then read as one place.

### 10.1 One shared component

Build the board once as a shared component (for example `.chalkboard`, with size modifiers) and use it for §9 and everything below. It comes in three sizes, all using the §9.2 slate, smudges, wood frame, shadow and `--chalkhand` lettering:

| Size | Used for | Frame | Lettering | Tilt | Chalk grain mask |
|---|---|---|---|---|---|
| **L** | Burger option boards, Shelves and About panels (§9) | 4px (3px on phones) | 22–30px | Yes, per §9.2 | Yes (§9.2 phone rule) |
| **M** | Status slate, counter labels, phone tabs, MENU label | 3px | 15–20px | Status slate only: −0.5° | Only at 18px or larger |
| **S** | Bottle name tags on the shelves | 2px | 14–16px | None (rows of tags stay tidy) | No; text-shadow only |

- **Minimum lettering size is 14px.** Kalam is wider than Outfit, so §8.2's 12px floor rises to 14px. Below that, the shelf shows fewer bottles per row (§8.2 rule). No tag shrinks under 14px.
- **Japanese and Korean text:** Kalam has no CJK glyphs. Japanese and Korean names (for example 純米大吟醸) fall back to `'Yu Gothic', 'Hiragino Sans', 'Noto Sans JP', 'Malgun Gothic', sans-serif` at weight 500. They keep the same chalk colour and text-shadow, so they sit on the board consistently. Don't fake a chalk CJK font.
- **Counts** (for example "· 48") are chalked at 70% opacity. The existing separators are kept.

### 10.2 What changes

1. **Category name boards under the top-shelf vessels** (`.vessel-cap`):
   - They become **S** boards, hanging just below the shelf lip like a shelf talker, centred under each vessel.
   - **They show at all times on both layouts.** On desktop they currently appear only on hover or when a vessel is selected, while phones always show them. The §5.3 parity rule settles it: always visible.
   - The selected category's board gets the chalk underline from §9.2, and its chalk turns `--glow`. This replaces the iron puck under the selected vessel.
2. **Subcategory name tags on the lower shelves:** these become **S** boards with the §8.2 fit rules at the new 14px floor. Each one sits on the shelf lip under its bottle. The Japanese name and count go on the second or third line, as now.
3. **The status slate** in the middle of the counter, which says "Pick a bottle from the top shelf." or "Sake · 10 kinds · 242 drinks": this becomes an **M** board resting on the counter, with a −0.5° tilt. The text is chalked, and the copy is unchanged.
4. **Counter zone labels** ("New arrivals", "In season: Autumn"): these become **M** boards propped at the front of each zone. The text is chalked in sentence case, not the current spaced capitals.
5. **Phone tabs** ("New", "In season"): these become two **M** boards side by side. The active tab gets the chalk underline and `--glow` chalk. The inactive tab's chalk is at 75% opacity. The tap target stays at least 44px.
6. **The MENU label** by the burger: an **M** board with "Menu" chalked on it, in sentence case.
7. **Counter bottle captions** (if a name shows on hover or focus over a counter bottle): an **S** board above the bottle.

### 10.3 States, the same everywhere

- **Hover or focus:** the board lifts 2px and the chalk turns `--glow`. The keyboard focus ring is the `--glow` outline around the frame.
- **Selected or active:** the wavy chalk underline plus `--glow` chalk.
- **Unavailable** (for example a "soon" subcategory slot): chalk at 55% opacity, no lift.
- **Motion:** only `transform` and `opacity`, no looping, and reduced motion is respected.

### 10.4 Out of scope

- The **LIQUID ASSETS sign** stays as it is in the rendered plates.
- The **footer** and the skip link stay as they are.
- Plans 02–04 pages keep their own styles. Whether they get chalkboards is a later design decision.

### 10.5 Acceptance

- [ ] Every text label on the welcome page listed in §10.2 uses the shared chalkboard component. None of the old dark pills or spaced-capital labels remain on the welcome page.
- [ ] Category boards are always visible under the top-shelf vessels, at all four sizes.
- [ ] No tag is under 14px, and no two boards overlap (the §8.2 check, rerun with the new font).
- [ ] Chalk on slate is at least 4.5:1 for every size, including the 70% count text and the 75% inactive tab. If the inactive tab fails, raise its opacity until it passes.
- [ ] Japanese and Korean names render in the fallback stack with no missing-glyph boxes.
- [ ] Screenshots at 1440×900, 1920×1080, 375×812 and 390×844 in the resting state and with Sake open, plus phone screenshots with the In season tab active.
- [ ] Build 0 errors, all tests pass, privacy scan clean, no commit or push.

---

## 11. Phone bottom shelf at rest (2026-11-01, owner approved)

- **Fault:** on the tall plate in the resting state (`#/`), shelf 3 shows a single bottle at the far right. The §8.3 rule (leave a lower-shelf slot empty where a counter bottle would cover it) empties nearly the whole shelf, because the phone counter bottles sit just below shelf 3's base.
- **Fix:**
  - On the **tall plate only**, shelf 3 at rest shows its full row of **3 mixed bottles**, as in §7.2.
  - The empty-slot rule from §8.3 **does not apply there**. The counter bottles stand in front and may overlap the bottom of the shelf-3 bottles, as bottles on a counter do in front of a back bar.
  - Stack order: counter bottles above shelf-3 bottles.
  - **The wide plate keeps the §8.3 rule unchanged.**
- **Check:**
  - At 375×812 and 390×844 in the resting state, shelf 3 shows 3 bottles.
  - No shelf-3 bottle is more than 35% covered by a counter bottle. If one would be, shift that row's scroll start so it isn't.
  - The tag-overlap check still passes. At rest there are no tags on shelf 3.
