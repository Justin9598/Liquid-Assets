# Plan 08: Phase 2 launch (shelves, drinks, makers)

Status: **Approved by the owner (2026-11-01), revision 2.** Launch still needs a separate owner approval (§8 step 5).
- **Revision 1** (2026-11-01): written by the designer after reviewing a private Phase 2 build at 1440×900 and 375×812.
- **Revision 2** (2026-11-01): the owner directed that **the bar stays as the background on every page**, and that pages use the welcome page's scheme, with **blackboards and chalk for all words and information**. This replaces revision 1's header band and its "chalk for labels only" rule.

Phase 2 turns on the rest of the site: the shelf list pages (Plan 02), the drink pages (Plan 03), and the producer pages and Makers index (Plan 04). The code for all three exists and works behind the `sections` switch (Plan 06 §12). It was built before the welcome page moved to the rendered bar, the burger and chalkboards (Plan 07), so it still looks like the old site. This plan brings those pages into the same world, fixes the faults found in review, and sets out the launch.

Plans 02–04 stay in force for content, data, routes and behaviour. This plan changes only their **look**, plus the specific faults listed in §6. Where it conflicts with them, this plan wins.

---

## 1. Review findings (private Phase 2 build, 2026-11-01)

The private build ran with 0 errors: 265 drinks, 151 producer pages and 423 data files.

| # | Where | Finding |
|---|---|---|
| F1 | All inner pages | The header is a **CSS-drawn brick wall** with a small wooden "LIQUID ASSETS" button, and the bar disappears as soon as you leave the welcome page. |
| F2 | All inner pages | The menu is the old **iron puck plus a "Menu" pill**, not the burger, and the text sits on dark app-style panels, not chalkboards. |
| F3 | List, producer, cards | Drinks with no photo (75 of 265) and the hero bottle are **CSS-drawn bottle shapes**, not the rendered shells now on the shelves. |
| F4 | List page | The **sibling strip** is a row of tiny drawn bottles, hard to read and to tap. |
| F5 | Drink page, desktop | The hero is **half empty**: the photo frame on the left, a short info card low on the right, and bare brick filling the rest. |
| F6 | Drink page | Spec labels are mixed case ("Polishing ratio" next to "GRADE", "RICE"). |
| F7 | Empty-shelf and not-found page | The **footer sits mid-screen** and the rest of the page is blank. |
| F8 | Producer page | The **Japan map shows no visible marker** for the producer's prefecture (checked on Akebono Shuzo, Fukushima). Check it and fix it. |
| F9 | Data | **0 drinks have a story** (no `Public Notes` yet). 8 have tasting notes, 183 of 290 visits have a price, and 41 have a date. The pages handle this: empty sections are left out (Plan 03 §5). |

Working well, and kept as behaviour:
- The toolbar: search, style chips, origin, favourites and sort.
- The menu cards with photos.
- The Label panel's polish bar.
- The Makers map and grid.
- No sideways scroll on phones.

---

## 2. Concept: blackboards hung in front of the bar

The visitor never leaves the bar. **The rendered bar is the background of every page**, exactly as on the welcome page. Each page's content is a set of **blackboards hung in front of it**, with everything written in chalk: names, facts, notes, numbers and the controls' labels. Like a bar's chalkboard menu, one board per section.

- **Behind:** the rendered plate (`bar-wide`, or `bar-tall` on phones), fixed in place.
- **In front:** blackboards that scroll over the bar.
- **On the boards:** chalk (Kalam), with Japanese and Korean text in the Plan 07 §10.1 fallback stack, in chalk colour.
- **Photos** are pinned to the boards as photo prints.

---

## 3. Shared pieces for every inner page

### 3.1 The bar background (fixes F1)

- **The plate:** every inner page sits on the same rendered plate as the welcome page. Use `bar-wide` on desktop and tablet, `bar-tall` on phones (the Plan 07 §5.3 parity rule), cropped with the same cover rules as the welcome page.
- **Fixed in place:**
  - The plate does not scroll; the boards scroll over it.
  - Build it as a `position: fixed` layer holding the plate image, not `background-attachment: fixed`, which fails on iPhone.
  - Reuse the published plate files. There are no new image files.
- **Dimming:** a uniform dark overlay (`rgba(20, 12, 6, .35)`) and a blur of at most 2px, so the boards read clearly. The bar must still be recognisable: the sign, the shelves and the lanterns. No heavier blur.
- **Top of the page:**
  - At scroll position 0, the **LIQUID ASSETS sign shows in the background** above the first board. The first board starts just below the sign's bottom edge, measured as a new `content_top` value in each `scene.json` plate block.
  - A link area over the sign at the top of the page goes to `#/`, with the accessible name "Liquid Assets, back to the bar". It scrolls away with the page.
- **The bottles on the welcome shelves are not drawn here.** The empty rendered shelves stay behind the boards, so the page is calm.

### 3.2 Menu: the same burger as the counter (fixes F2; replaces Plan 07 §3.7)

- **Button:** the burger from the counter, smaller: 56px tall on desktop and 48px on phones. It's fixed at the top right of the viewport, with the "Menu" M chalkboard beside it. It stays reachable at any scroll position.
- **Same menu:** tapping it opens **the same split menu as the welcome page** (Plan 07 §3, with the §8.1 phone rules and the §9 chalkboard options and panels). One menu, one behaviour, across the whole site. This reverses Plan 07 §3.7's plain list now that every page is in the bar.
- **Phase 2:** The Makers is live, so "Soon" is removed everywhere.

### 3.3 The blackboard component

Every panel is a **blackboard**: an extension of the Plan 07 §10.1 shared `.chalkboard` component, adding a fourth size.

| Size | Used for | Frame | Notes |
|---|---|---|---|
| **XL** (new) | Content boards: the page hero, each section, cards' backs | 6px wood frame (4px on phones) with small iron hanging brackets at the top corners | Smudges scaled to the board. No tilt for content boards. |
| **L / M / S** | As in Plan 07 §10.1: headings, chips, buttons, breadcrumb, menu | As in Plan 07 | |

- **Width:** content boards use the content column (max 1120px), with a 16px gutter on phones. They hang centred in front of the bar.
- **Spacing:** 32px between boards on desktop and 20px on phones, so slivers of the bar show between them.
- **Surface:** the Plan 07 slate `#262a28`, fully opaque. The board must never be see-through, because text sits on it.

### 3.4 Chalk writing rules

The owner wants all words and information in chalk, so these rules keep long pages readable:

| Text | Chalk style |
|---|---|
| Page titles and drink or producer names | Kalam 700, `clamp(30px, 3.6vw, 48px)`, with the grain mask |
| Board headings ("The Label", "The Tab" and so on) | Kalam 700, 22–26px, with the grain mask and the wavy chalk underline |
| Body text and notes (explainer copy, The Story, visit notes) | Kalam 400, **at least 17px**, line-height 1.6, max 68 characters per line, **no grain mask** (text-shadow only) |
| Data (spec rows, counts, prices, dates) | Kalam 400, at least 16px. Numbers use the font's tabular figures if it has them; otherwise right-align them. |
| Small print (footer, credits, image notes) | Kalam 400, at least 14px, chalk at 75% |
| Japanese and Korean | The Plan 07 §10.1 fallback stack at weight 500, chalk colour and shadow |

- **Contrast:** at least 4.5:1 for every chalk style on the slate, including dimmed chalk. The 70% and 75% values passed in Plan 07. Rerun the check.
- **Chalk dividers:** use hand-drawn chalk lines (1–1.5px, slightly wavy SVG strokes, `--chalk` at 25%) in place of hard rules and borders on boards.
- **Accent:** `--glow` chalk stays the single accent, for links, the selected state and highlights.
- Fonts no longer used on these pages are dropped from them: Outfit body text, Cormorant drink names and Stardos Stencil crates. Remove any font file that ends up unused anywhere on the site, and its credit line.

### 3.5 Controls in chalk

- **Search box:** a field drawn on the board, outlined in chalk (1.5px `--chalk` at 60%, slightly irregular), with no white box. The placeholder is chalk at 55%, and the typed text is chalk. It stays a real `<input>` with its label.
- **Selects** (origin, sort): native `<select>` elements, styled the same as the search box with a chalk-drawn caret. The open option list may use the browser default. That's accepted, for accessibility.
- **Chips, Favourites, Prev and Next, Visit producer, Back to the bar:** S chalkboards with the Plan 07 §10.3 states.
- **Focus:** the `--glow` outline. Keyboard focus is always visible on the boards.

### 3.6 Photos pinned to the boards

- **Drink photos** are shown as **photo prints**: a 6px off-white border (`#efe9dd`) and a soft shadow. A small strip of chalk-white tape or a pin sits at the top centre.
- **No tilt on card grids**, so they stay tidy. The drink page's hero photo tilts −1°.
- **Photos are never recoloured.** They keep their own colour on the slate.

### 3.7 Bottles without a photo use the shells (fixes F3)

- Anywhere a drawn bottle shape appears (card fallback, list hero, producer page, related drinks), use the **Plan 07 shell for the drink's category**, standing on the board's bottom ledge. Use the same mapping as the shelves: sake, makgeolli, wine, beer, spirits, liqueur (amber), and the highball for cocktails.
- **The label on a fallback bottle:** the drink's own label crop where `labelStatus` is `ok` (Plan 01 §15.3). Otherwise the illustrated fallback label (Plan 01 §6).
- **Remove the CSS bottle drawing code** once nothing uses it.

### 3.8 Breadcrumb

An **S chalkboard** hanging below the sign at the left of the first board's top edge. For example "Bar › Sake › Junmai Ginjo". On phones, if it doesn't fit on one line, show only the parent link ("‹ Junmai Ginjo").

### 3.9 Footer and full-height layout (fixes F7)

- Every route fills at least the viewport height (`min-height: 100dvh`), with the footer at the bottom when content is short.
- The footer is a slim **M chalkboard strip** at the bottom of the page, holding the credits in small chalk.
- **The empty-shelf page:** the bar background, then one board reading "This shelf is empty", then an S board linking "Back to the bar". The footer sits at the bottom.

---

## 4. Page by page

### 4.1 Shelf list page (Plan 02)

1. **Hero board (XL):**
   - **Left:** the category's **shell** standing on the board's ledge, with the same label the welcome shelf shows for this subcategory. The bottle a visitor tapped is the bottle they see.
   - **Right, chalked:**
     - The title and its Japanese name.
     - The facts line ("74 drinks · 49 producers · 25 prefectures").
     - The explainer copy.
     - The fact chips ("No added alcohol", "Polished ≤ 60%") as S boards.
2. **Sibling strip (fixes F4):** a row of **S chalkboards** hanging under the hero board, one per sibling subcategory, with name and count.
   - The current one is underlined.
   - The row scrolls sideways with scroll-snap when it overflows, with soft fades at the ends.
   - Each board's tap target is at least 44px.
3. **Toolbar board (XL, compact):** search, style chips, origin, favourites and sort, as in §3.5. "Showing 74 of 74" is chalked.
4. **Cards:** each card is a **small blackboard** (L frame) in the grid.
   - A pinned photo print at the top, or the §3.7 shell when there's no photo.
   - Below it, chalked: name, producer, origin, ABV and size, the polish and rice line, and style chips.
   - The favourite star is chalked in `--glow` at the top corner.
   - Grid sizes stay as Plan 02 §7.

### 4.2 Drink page (Plan 03)

1. **Hero board (XL), fixes F5:**
   - **1024px and up:** two columns filling the board, both top-aligned.
     - **Left, 5/12:** the pinned photo print, tilted −1°, no wider than the column. Photos much taller than they are wide sit centred, never stretched.
     - **Right, 7/12, chalked:**
       - Name and producer link (`--glow`).
       - Origin and quick facts.
       - Style chips (S boards).
       - The one-visit line (Plan 03 §8.2).
       - Prev and Next (S boards).
   - **768–1023px:** the same layout at 6/6.
   - **Under 768px:** stacked, photo first.
   - **No photo:** the §3.7 shell, large, on the board's ledge.
2. **Section boards:** The Label, The Glass, The Story, The Maker and The Tab are separate XL boards with chalked headings.
   - On desktop, The Label and The Glass hang side by side when both exist. The rest follow at full width.
3. **The Label:** spec rows in chalk, separated by chalk dividers.
   - **Labels (fixes F6):** all in one style: Kalam 700, 14px, capitals, letter-spacing .06em. "Polishing ratio" gets this style without changing its text.
   - **The polish bar and SMV gauge are drawn in chalk:** an outline in `--chalk`, with the fill as `--glow` chalk hatching.
4. **The Glass (WSET card):** scales drawn as chalk dots or ticks, and terms chalked.
5. **The Tab:** each visit is a chalked line (date, size, where, price), like a bar tab written on the board.

### 4.3 Producer page (Plan 04)

1. **Title board (XL):** replaces the wooden crate.
   - The producer's name in large chalk, with the location under it. If an approved Producers row has a native name, it goes beside the English name.
   - The summary line ("12 drinks · 2 categories · 1 favourite · had 16 times").
   - Along the board's bottom ledge stand up to 12 of their bottles as §3.7 shells with labels, centred. Beyond 12, show a chalk "+N more".
2. **The Facts board:** facts in chalk, plus the **map drawn in chalk** (fixes F8).
   - Japan's outline in chalk strokes on the slate.
   - The producer's prefecture filled with `--glow` chalk hatching and outlined in chalk, with a chalk circle around it.
   - If the map can't place a prefecture, leave the map out rather than show an unmarked one.
   - **Check:** the smoke test checks that a Japanese producer's map has exactly one highlighted prefecture.
3. **Their bottles on my shelf:** cards as in §4.1.

### 4.4 Makers index (Plan 04)

1. **Title board:** "The Makers" in large chalk, with the facts line.
2. **Map board:** the chalk map from §4.3.
   - Prefectures with makers are lightly hatched.
   - Tapping one filters the list and fills it with `--glow` chalk.
   - "Elsewhere" country links become S boards.
3. **Maker grid:** the wooden crates become **small blackboards** (L frame).
   - Producer name chalked, with location underneath.
   - Drink count chalked in a chalk-drawn circle.
   - Favourite star in `--glow`.
   - Search, country select and sort as in §3.5.

---

## 5. The welcome page in Phase 2

With `sections` all on:
- **Subcategory tags** use full chalk (no longer the 55% unavailable state) and **link to their list pages**. Tapping a lower-shelf bottle or its tag opens `#/<cat>/<sub>`.
- **Counter bottles** link to their drink pages.
- **The burger's Makers layer** is live. "Soon" is removed, and the option goes to `#/makers`.
- **About:** the facts update to the full counts.
- **Moving between pages:** going from the welcome page to an inner page keeps the plate in place. The bottles and counter fade out (200ms) and the boards fade and rise in (240ms, `transform` and `opacity` only), so it feels like boards being hung in the same room. Coming back reverses it. Reduced motion: a plain 150ms cross-fade.
- Nothing else on the welcome page changes.

---

## 6. Faults to fix whatever the look

1. **F7:** the full-height layout and footer (§3.9).
2. **F8:** the map marker on producer pages (§4.3).
3. **F6:** spec label style (§4.2).
4. **Phase 2 privacy scan:** the build's deny-scan (E02) and the "no `Notes` text" check run over **all 423 published data files**. Phase 1 only checked 3. The build fails if any file under `docs/data/` or `docs/img/` has an original photo filename or a private marker.

---

## 7. Data readiness: what's needed before launch

| Item | Needed for launch? | Owner action | If not done |
|---|---|---|---|
| Fermenteria batch (9 drinks, `Pint` size) | **Yes, recommended** | Enter the rows as in the update note `updates/2026-11-01-fermenteria-batch.md` | The new beers and sakes are missing from the first Phase 2 release. |
| `Public Notes`, `Visit Note` columns | No | Later: the researcher drafts them from `Notes` (Plan 05 task D1) for you to approve | The Story board is left out. Visit lines show size, place and price only. |
| `Producers` sheet | No | Later (Plan 04 §8) | Producer pages show name, location and drinks only. |
| `Other Detail.Type` for the 2 older beers | No | Whenever convenient | They sit in the "Other beer" bottle. |

**Recommendation:** launch Phase 2 once the Fermenteria rows are in and §3–§6 are built. Stories, producer details and beer types arrive in later updates with no code changes.

---

## 8. Build and launch steps

1. **The owner** enters the Fermenteria rows and saves and closes Excel.
2. **The shipper** builds §3–§6.
   - Keep `content/phase.json` set to 1.
   - Preview Phase 2 using the build option `--phase 2` **into a scratch copy, not `Ship/docs/`**. The welcome-only live site stays untouched until launch.
3. **The shipper** reports with screenshots, checked against §9. It covers every page type at 1440×900, 1920×1080, 375×812 and 390×844:
   - The welcome page.
   - List pages: Junmai Ginjo, and Makgeolli as a sparse shelf.
   - Drink pages: one with a photo and a tasting card, one with no photo, and one had several times.
   - The producer page for Akebono Shuzo.
   - The Makers index.
   - The empty-shelf page.
   - The menu open on an inner page.
   - One drink page scrolled halfway, to show the fixed bar behind the boards.
4. **The designer** reviews the screenshots and checks a sample in the browser.
5. **The owner** approves the launch.
6. **The shipper** launches:
   - Set `content/phase.json` to 2, run `build.bat` and check the report.
   - Commit and push (Plan 06 §5.2).
   - Run the full Plan 06 §6 smoke test on the live URL at the four sizes.
   - Report the commit hash, the Pages status and the results.

---

## 9. Acceptance criteria

- [ ] **Bar background:** every inner page shows the rendered bar fixed behind the boards (`bar-tall` on phones), with the sign visible above the first board at the top of the page. No CSS brick, drawn bottles, iron puck, wooden crates or dark app panels remain.
- [ ] **All chalk:** every word and piece of information on inner pages is chalk on blackboards, following §3.4. The only exceptions are photos and the browser's own open-select list.
- [ ] **Readability:** body chalk is at least 17px with no grain mask. Every chalk style is at least 4.5:1 on the slate.
- [ ] **Menu:** the same split burger menu as the welcome page on every page, with The Makers live.
- [ ] **No-photo drinks:** they show their category shell with the right label rule (§3.7), everywhere.
- [ ] **Drink hero:** the drink page hero board has no empty half at 1440×900 or 1920×1080.
- [ ] **Full height:** every route fills the viewport, with the footer at the bottom on short pages.
- [ ] **Map:** every Japanese producer's chalk map shows exactly one highlighted prefecture, or no map at all.
- [ ] **Welcome page:** Phase 2 behaviour and the page-to-page transition as in §5.
- [ ] **Layout:** no sideways page scroll and no overlapping boards at the four sizes, on every page type. The Plan 07 smoke checks still pass.
- [ ] **Performance:** scrolling a list page with 74 cards on a phone stays smooth. The fixed plate is a single composited layer.
- [ ] **Privacy:** the Phase 2 privacy scan is clean over all published files, and no `Notes` text is published.
- [ ] **Build:** 0 errors and all tests pass. No commit or push until the owner approves the launch (§8 step 5).

---

## 10. Decisions log

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Inner page background | **The full rendered bar, fixed behind the boards** (owner, revision 2) | The visitor never leaves the bar. Uses images already published. |
| D2 | Inner page menu | **The same split burger menu as the counter** (revision 2) | Every page is in the bar now, so one menu everywhere. Reverses Plan 07 §3.7. |
| D3 | How far chalk goes | **All words and information** (owner, revision 2), with the §3.4 readability rules | Matches the welcome page's chalkboard scheme. The size floors and no-mask body text keep long reading comfortable. |
| D4 | Launch timing | After the Fermenteria rows; stories and producer details later | The pages are complete without them. Empty sections are left out by design. |
| D5 | Producer title | Blackboard instead of the wooden crate (revision 2) | Follows D3. The crate's stencil lettering was the last non-chalk text. |

---

## 11. Review fixes (2026-11-02, owner approved)

The designer reviewed the first Plan 08 build: the screenshot set in `reports/phase2/`, plus a browser check of a private Phase 2 preview at 375×812. Three fixes are needed before launch. The shipper's judgement calls 1–14 from the build report are accepted.

### 11.1 Drink page hero: no gap above Prev and Next

- **Fault:** at 1440×900 and 1920×1080 the right column pins "Back to …", Prev and Next to the bottom of the board. That leaves a tall empty gap under the facts when the photo is tall.
- **Fix:**
  - The action row follows the facts directly, 24px below the last fact line.
  - The right column is vertically centred against the photo. It is not stretched.
  - Keep the photo height cap. If the photo is still much taller than the facts, cap it lower (for example 60vh) rather than open a gap.
- **Check:** at both desktop sizes, the gap between the last fact line and the action row is at most 32px. Check it on the "photo and tasting card", "no photo" and "had several times" drinks.

### 11.2 Makers index on phones: shorter map

- **Fault:** at 375×812 and 390×844, the map board fills the whole screen, so the makers list starts more than a screen down.
- **Fix:**
  - On phones (under 768px), the map board is at most **55% of the viewport height**, with the map scaled to fit inside it. Japan stays fully visible.
  - Tapping a prefecture still filters the list. The list's "Showing N of 151" line then scrolls into view.
- **Check:** at both phone sizes, the top of the search box is visible without scrolling, or at most one short scroll down: the top of the search field sits within 1.1 viewport heights of the page top.

### 11.3 The Phase 2 smoke test must be reliable

- **Fault:** `test_phase_2_inner_pages_smoke_in_a_scratch_copy` failed once in a full `pytest` run, then passed when run alone.
- **Fix:**
  - Find the cause. Likely suspects: a fixed wait instead of waiting for a condition, fonts or images not loaded, the router transition still running, or a port or temp-folder clash with another test.
  - Make the test wait on real signals: `document.fonts.ready`, the image `decode()` calls, and a "route ready" flag set after the §5 transition ends.
  - Report the cause found.
- **Check:** the full suite passes **5 times in a row**. Report each run's result and time.

### 11.4 Acceptance

- [ ] §11.1, §11.2 and §11.3 checks pass, with evidence.
- [ ] Retake the screenshots for the drink pages (all three drinks) and the Makers index at the four sizes, into `reports/phase2/`.
- [ ] Phase 1 still builds with 0 errors. `content/phase.json` stays 1. No commit or push.

### 11.5 Designer check (2026-11-02): §11.3 not met yet

- **Passed:** §11.1 and §11.2. The screenshots look right. A browser check of the Phase 2 preview matched the reported numbers: the phone Makers map board is 0.46 of the screen, the search field starts 1.05 screens down, there is no sideways scroll, and there are no console errors.
- **Failed:** `test_phase_2_inner_pages_smoke_in_a_scratch_copy` failed in **3 of 3** designer runs, with no headless browsers left over from earlier runs:
  1. **Full suite**, while a separate Phase 2 build was running: `TimeoutError: timed out in 239.1s` (1 failed, 61 passed, 374s).
  2. **Alone, quiet machine:** `RuntimeError` raised from `wait_ready` (`smoke_inner.py:255`), after 114s.
  3. **Alone, quiet machine:** `TimeoutError: timed out in 239.3s`. Call path: `run` (`smoke_inner.py:336`), then `transition_checks` (374), then `load(page, base, "#/sake")` (276), then `wait_ready` (253), then `cdp.eval`.
- **Reading:** each failure is in `wait_ready`, and the clearest one is on the welcome page deep-linked to `#/sake`. A wait that never returns points at something in `READY_JS` that can hang with no time limit:
  - `a.finished` on an animation that is paused, idle or never started. Its `finished` promise never settles.
  - `document.fonts.ready`.
  - The `data-ready` flag on `#/sake` itself not being set within 25s on a cold load. That would fit run 2.
- **Fix:**
  - Every step in `READY_JS` gets its own time limit, and the message names the step that ran out. A hang must turn into a clear failure within 30s, never a 240s transport timeout.
  - Find out why the welcome `#/sake` route sometimes doesn't become ready. If it's a fault in the page (for example, `setReady` is skipped when the welcome page mounts straight into an open category), fix the page, not the test.
  - Then wait only on animations that are actually running (`playState === 'running'`).
- **Check:**
  - Run the Phase 2 smoke test alone **10 times in a row** from a cold start, plus the full suite **3 times in a row**. Every run must pass. Report each result and time.
  - Report the cause found, and what in the page or the test changed.
- Everything else in §11.4 is unchanged: Phase 1 builds with 0 errors, `content/phase.json` stays 1, and nothing is committed or pushed.
