# Plan 01: Welcome page ("The Bar")

Status: **Approved design, revision 3 (2026-10-31):** full-bleed rendered scene and counter menu (§2, §7, §12, §13; §10 Q11–Q12). **Waiting on the owner's images (§12).** Earlier: rustic direction and Liqueur (Q7–Q10). Two ledger updates are needed (§10.1).
Author: Claude (designer). This is a plan only. Nothing here is built yet.
Data snapshot: `Drinks Ledger.xlsx` as of 2026-10-30. That's 290 Core rows and 265 unique drinks.

---

## 1. Concept

The welcome page puts you at a **rustic brick-and-timber bar**, modelled on the owner's reference image (`Design/welcome-reference.jpg`, kept privately outside `Ship/`).

- **The room:** exposed brick walls and heavy timber ceiling beams with small recessed spotlights. A stone-tile floor shows at the bottom edge.
- **The back-bar:** open shelving in light, natural wood, divided into bays. The back panel of each bay glows warmly from behind.
- **The counter:** a thick reclaimed-plank counter on a black iron base, with round bar stools in front.
- **The sign:** a reclaimed-wood sign hangs from the beam across the top, with **LIQUID ASSETS** carved into it.

On that scene:

- The **top shelf** works as the menu: seven display vessels, one per category. In order: **Sake, Makgeolli, Liqueur, Beer, Wine, Spirits** and a **Cocktail glass**.
- The **lower shelves** react to it. Click a vessel on the top shelf and the bottles below are swapped for that category's **subcategories**. All of the new bottles share one shape, the shape of their parent category. Each one wears a label taken from a real photo of a drink in that subcategory.
- The **counter** in the foreground shows the selected category on a small **slate** at the left. At the right sits the **menu button**, a hamburger on the counter that opens site navigation (§13). It replaces the v2 "The Makers" board, because two controls with the same purpose on one page is a design fault.

The page needs to work in one glance. Someone who has never seen the site should understand within a few seconds that the top shelf is clickable and that the shelves below are its contents.

---

## 2. Scene layout (v3: full bleed)

*Revised 2026-10-31 (v3). The owner judged the hand-drawn scene amateurish and asked for the bar to fill the whole page. The design read and design rules come from the taste skill.*

**Design read:** an immersive showcase of a personal collection, for friends and fellow drinkers, with a warm, photoreal rustic-bar language. It's built with native CSS over rendered scene images, with restrained motion that has a reason.

**Dials:** design variance 6 (one fixed scene composition), motion 5 (motion only for feedback and state changes), visual density 3 (airy, with the scene doing the work).

### 2.1 What was wrong with v2

These are the tells that made v2 look amateur:
- Clip-art brick.
- Flat pastel shelf panels.
- Bottles about 35% of shelf height, floating in empty beige.
- A footer strip cutting across the scene.
- Decorative dots on the counter boards.
- An outlined sign.

v3 removes every one of them.

### 2.2 The scene fills the viewport

- The scene covers **100% of the viewport** at every size (`min-height: 100dvh`). There's no letterboxing, no page margin and no footer strip, and the welcome page doesn't scroll.
- **Credits move into the menu** (§13). The old footer ("Last updated…, fonts…, map…") is gone from the welcome page.
- **The scene is one rendered image (the plate) plus live layers on top:**
  1. Plate
  2. Bottles and vessels
  3. Tags
  4. Counter controls (status slate and menu button)
  5. Menu overlay

  Code draws **no scenery**. The SVG/CSS brick, beams, shelving, sign, counter, stools, barrel, print and glasses from v2 are all retired.

### 2.3 Keeping live layers aligned with the plate

- The plate is scaled to cover the viewport, like `background-size: cover`.
- The live layers sit in a **cover box**:
  - It's a box with the plate's exact aspect ratio, `width: max(100vw, 100dvh × ratio)`, centred, with the overflow clipped.
  - Everything inside is positioned in **plate percentages**, so the bottles stay on the painted shelves at any window size.
- **Scene manifest:** `Ship/content/scene.json` records, for each plate, the measured fractions of:
  - the shelf lines (y, x-start, x-end) and the clear height above each,
  - the sign rectangle,
  - the counter-top line,
  - the anchors for the status slate and the menu button.

  The shipper measures these once from the delivered images.
- **`?debug=scene`** draws the manifest's lines over the plate, so alignment can be checked by eye.
- **Safe zone:** every interactive element sits inside the central **62% of the wide plate's width and 8–90% of its height**. Cropping between 4:3 and 21:9 therefore only ever cuts brick and decor at the sides, never a shelf.

### 2.4 Plates per screen shape

| Viewport | Plate | Notes |
|---|---|---|
| Landscape, ≥ 768px wide | **Wide plate** (16:9) | Desktop and landscape tablet. Cover-cropped at the sides as needed. |
| Portrait, or < 768px wide | **Tall plate** (about 9:19.5) | Phones and portrait tablets. |

### 2.5 Bottle scale (the biggest single fix)

- Each bottle stands **on** its painted shelf line, and its height is **about 82% of the clear height** of that shelf. The space between bottles comes from the shelf width divided by the bottle count, capped so a single bottle doesn't float alone in the middle of a 6-slot shelf.
- **Wide plate:** the top shelf holds the 7 vessels, and the two lower shelves hold up to 6 subcategory bottles each, so 12 in total. Sake needs 10 today, plus Ungraded.
- **Tall plate:**
  - The two upper shelves hold the vessels (4 + 3).
  - The two lower shelves hold subcategories, 3 visible per shelf. When a category has more, each lower shelf **scrolls sideways inside the shelf** with scroll-snap, and the page still doesn't scroll.
  - A soft fade at the shelf ends shows there's more.

---

## 3. Top shelf: category vessels

Each vessel is a distinct illustrated object, and none of them uses a photo. They form the fixed vocabulary of the site.

| Vessel | Shape (also used for its subcategory bottles below) | Default label art |
|---|---|---|
| **Sake** | 720ml *yotsugōbin*: tall, sloping shoulders, long neck, screw cap; dark brown or green glass | Washi-paper label with 酒 |
| **Makgeolli** | 750ml PET bottle: ribbed body, short neck, coloured cap; milky white liquid | Label with 막걸리 |
| **Liqueur** | Squat, round-shouldered 500–720ml bottle: wide body, short neck; clear glass with amber liquid | Small oval label with LIQUEUR. The Umeshu subcategory's fallback label carries 梅酒 and a plum-blossom motif. |
| **Beer** | 330ml longneck: brown glass, crown cap | Oval label with BEER |
| **Wine** | 750ml Bordeaux bottle: high square shoulders, punt, foil capsule; dark green glass | Cream label with a vine motif |
| **Spirits** | Square-shouldered spirits bottle: heavy base, short neck, cork stopper; amber liquid | Small rectangular label |
| **Cocktail** | Coupe/martini glass with garnish (on the top shelf only) | None |

The seven shapes have to stay distinct when seen side by side. In particular, keep the squat Liqueur bottle, the tall sloping Sake bottle and the square-shouldered Wine bottle clearly different from one another.

**States**

- *Idle:* still. There's no looping shine, because an animation with no purpose is a tell (v3).
- *Hover/focus:* the vessel lifts about 6px, the beam spotlight above it brightens into a warm cone, and a hand-lettered tag shows its name.
- *Selected:* the vessel stays lifted and lit, and a small black iron tab appears on the shelf edge beneath it. The other vessels dim slightly (about 80% brightness).
- Clicking the selected vessel again deselects it, and the shelves return to the default mixed display (§5.1).

---

## 4. Taxonomy: category → subcategories

This section maps the owner's brief onto the ledger as it stands. The counts are unique drinks (unique `ID`s).

**Shared rule:** a subcategory with 0 drinks is **hidden** and reappears once it has a drink. When a category's sub-type field hasn't been filled in yet, its drinks still get a bottle, so nothing goes missing from the shelf. Which bottle depends on the category:

- **No drink in the category has a sub-type yet** (Beer and Cocktails today): all of them go into a **single bottle named after the category**, for example one "Beer" bottle, with key `all`.
- **Some drinks in the category have sub-types** (Spirits today, where Whisky, Shochu and Soju are known but 2 Spirit drinks have no Type): the drinks without one go into an **"Other {category}"** bottle, for example "Other spirits", with key `other`, placed last.

*(Amended 2026-10-30 after the first build. The single-bottle rule was ambiguous for mixed categories.)*

### 4.1 Sake: 242 drinks, 11 bottles

There is one bottle per **grade**, using `Sake Detail.Grade`, plus **Craft Sake**, which comes from `Core.Category = "Craft Sake"`, plus **Ungraded** for sakes that have no grade yet.

They go in the classic order: the junmai line first, then the line with added alcohol, then the rest.

| # | Bottle | Kanji (for the fallback label and the tag) | Drinks |
|---|---|---|---|
| 1 | Junmai Daiginjo | 純米大吟醸 | 48 |
| 2 | Junmai Ginjo | 純米吟醸 | 74 |
| 3 | Tokubetsu Junmai | 特別純米 | 11 |
| 4 | Junmai | 純米 | 48 |
| 5 | Daiginjo | 大吟醸 | 6 |
| 6 | Ginjo | 吟醸 | 3 |
| 7 | Tokubetsu Honjozo | 特別本醸造 | 0 (hidden) |
| 8 | Honjozo | 本醸造 | 2 |
| 9 | Futsushu | 普通酒 | 3 |
| 10 | Craft Sake | クラフトサケ | 25 |
| 11 | Ungraded | 日本酒 | 22 |

The Ungraded bottle always comes last. It shrinks as the owner fills in grades and disappears once it's empty (the hidden-when-empty rule). The list of grades comes from the ledger's data-validation list on `Sake Detail!C`, so a new grade added there shows up without any code change.

### 4.2 Makgeolli: 5 drinks, one bottle

Makgeolli is standalone. When it's selected, the lower shelf shows **one makgeolli bottle**, centred and spotlit, with the tag *"Makgeolli · 막걸리 · 5"*. Its label is a random pick from the 5 makgeolli front photos, all of which are matched. Clicking it opens the Makgeolli list page (Plan 02).

### 4.3 Liqueur: 3 drinks, one bottle per **kind of liqueur**

*Changed 2026-10-30: this category was "Umeshu". The owner renamed it **Liqueur**, with one bottle per kind of liqueur.*

The kind comes from the same two places as the Spirits types (§4.6):

| Bottle | Source | Native | Drinks |
|---|---|---|---|
| Umeshu | `Core.Category = Umeshu` | 梅酒 | 3 |
| Yuzushu | `Core.Category = Liqueur` + `Other Detail.Type = Yuzushu` | 柚子酒 | 0 (hidden) |
| Fruit liqueur | `… Type = Fruit liqueur` (peach, lychee, plum wine that isn't umeshu…) | | 0 (hidden) |
| Herbal | `… Type = Herbal` | | 0 (hidden) |
| Cream | `… Type = Cream` | | 0 (hidden) |
| Coffee & tea | `… Type = Coffee & tea` | | 0 (hidden) |
| Other liqueurs | `Core.Category = Liqueur` with no Type (the shared rule's `other` bottle) | | 0 (hidden) |

- **Today the Liqueur shelf shows one bottle, Umeshu** (key `umeshu`, route `#/liqueur/umeshu`). That's because all 3 drinks have `Core.Category = Umeshu`. It's a real subcategory, not the `all` fallback.
- **The umeshu flavour/base list** from the earlier version of this section (Classic, Fruit Blend, Tea, Sake-based, Brandy-based, Aged, Other) stays in `Other Detail.Type` for umeshu rows. It becomes a **fact on the menu card and drink page** (Plan 02 §7.2) instead of a subcategory.

  | Drink | Suggested flavour/base (owner to confirm) |
  |---|---|
  | Akebono Color Umeshu Brown Label | *to confirm* (possibly Aged) |
  | HAMADA Ume Liqueur with Gold Leaf | Classic? |
  | Kabosu & Umeshu Sakurayama | Fruit Blend |
- **The first non-umeshu liqueur** needs `Liqueur` added to the Core Category dropdown list (§10.1).
- **Order:** Umeshu first, then the other kinds alphabetically, then Other liqueurs last.

### 4.4 Beer: 2 drinks, one bottle per **beer style**

The style comes from `Other Detail.Type`, using these values: Lager, Pilsner, Pale Ale, IPA, Wheat, Stout/Porter, Sour, Saison, Specialty.

| Drink | Style |
|---|---|
| Under 15M (Jeju Beer Company) | *to fill in* |
| Underwater Sake Yeast Beer (Nara Brewing) | *to fill in* (Specialty is likely) |

### 4.5 Wine: 3 drinks, one bottle per **grape variety**

The variety comes from `Wine Detail.Grape(s)`.

| Bottle | Drinks |
|---|---|
| Cabernet Sauvignon | 1 (Santa Helena Varietal, 2025) |
| Merlot | 1 (Casa Silva, 2025) |
| Blend | 1 (Pierre Jean Colombard Chardonnay, 2025) |

**Blend rule (designer's call; the owner can override it):** a wine with exactly one grape goes under that grape. A wine listing two or more grapes goes under a single **Blend** bottle. The alternative, filing a wine under every grape it lists, would show one wine on several bottles and inflate the counts. On Blend wines, the drink's own page lists the grapes.

**Order:** single-grape bottles sorted alphabetically, then Blend last.

**Grape name hygiene:** the implementer should treat names the same regardless of case and spacing ("Cabernet Sauvignon" equals "cabernet sauvignon"). A **Grape(s) data-validation list** is optional; it's a free-text column today.

### 4.6 Spirits: 8 drinks, one bottle per **type of liquor**, soju included

| Bottle | Source | Drinks |
|---|---|---|
| Whisky | `Core.Category = Whisky` | 4 |
| Gin | `Category = Spirit` + `Other Detail.Type = Gin` | 1 (The Botanist) |
| Brandy | `Category = Spirit` + `Type = Brandy` | 1 (Chusa 40, an apple brandy) |
| Shochu | `Core.Category = Shochu` | 1 |
| Soju | `Core.Category = Soju` | 1 |

Liqueurs, umeshu included, aren't part of Spirits; they have their own category (§4.3). Any type added later (Rum, Vodka, Tequila, Baijiu…) slots in alphabetically after Whisky, Gin and Brandy, which stay first.

### 4.7 Cocktails: 2 drinks, one glass per **cocktail type**

The type comes from `Other Detail.Type`, using these values: Highball, Sour, Martini, Old Fashioned, Spritz, Other.

Both of today's cocktails are canned Kavalan highballs, so there is one glass, **Highball**.

Glasses don't carry labels, so a cocktail subcategory is drawn as a **highball glass with a paper tag tied around it**, and the photo label goes on the tag. Every cocktail subcategory uses the same glass shape, which satisfies the "all the same shape" rule.

---

## 5. Lower shelves: behaviour

### 5.1 Default state, before anything is clicked

The shelves are "filled with various bottles", as the brief describes. Show a **mixed selection** of 12 bottles across the two shelves, cycling through the seven categories so neighbouring bottles differ: a sake, a makgeolli, a liqueur, a beer and so on. Each bottle is in its own category's shape with a random label from that category. This is the only state where shapes are mixed, which makes the change on click obvious.

The status slate on the counter reads: *"Pick a bottle from the top shelf."*

### 5.2 Selecting a category

1. The bottles currently on the lower shelves are **lifted off** in a stagger from left to right: each rises 12px and fades out over about 180ms, starting 30ms after the one before.
2. The new bottles, all in the selected category's shape, **slide in from behind** in the same stagger: they rise from 8px below and fade in.
3. The status slate updates, for example *"Sake · 11 kinds · 242 drinks"*. It counts only the visible subcategories.
4. The URL hash changes to one of `#/sake`, `#/makgeolli`, `#/liqueur`, `#/beer`, `#/wine`, `#/spirits` or `#/cocktails`. That lets the Back button, refreshing and sharing a link all keep the selection, which matters because GitHub Pages has no server-side routing.

The whole swap takes under 500ms. If the user has *prefers-reduced-motion* turned on, it becomes a single 150ms crossfade.

### 5.3 A subcategory bottle

- Under each bottle is a small **slate tag**: an off-black iron-framed tag with off-white text, which reads clearly against light oak. It shows the subcategory name, the kanji or hangul where it applies, and the drink count, for example *"Junmai Ginjo · 純米吟醸 · 74"*. This tag is always visible, because a cropped photo label won't be readable as a name.
- *Hover/focus:* the bottle tilts forward slightly (3°) and lifts, and the label gets brighter.
- *Click:* it goes to that subcategory's listing page (to be defined in Plan 02, "Shelf list page"), at URLs like `#/sake/junmai-ginjo` or `#/wine/merlot`. For Makgeolli, which has one bottle, the URL is `#/makgeolli/all`. Until Plan 02 exists, the bottles link to a placeholder.

---

## 6. Labels from photos

The brief says: if there are photos for a subcategory in `Photos/`, use them as bottle labels, picked at random.

### 6.1 Which photos are eligible

- **Pool for a subcategory** = the **front photo** of every drink in it. A front photo is one whose filename has no `(back label)`, `(side label)`, `(second photo)`, `(n)`, `(spec panel)` or `(maker panel)` suffix. Back labels are mostly text, so they make poor bottle labels.
- Each photo is matched to a drink through a **photo map** (`Ship/content/photo-map.json`; the format is in Plan 05 §5 S7). The owner curates it by hand. The build step fills gaps with exact name matches (case, accents and punctuation ignored), and writes prefix or fuzzy matches to a suggestions file for review instead of using them (Plan 05 §5 S7).

### 6.2 Coverage today, with automatic matching only

| Subcategory | Drinks | With a front photo |
|---|---|---|
| Junmai Ginjo | 74 | 61 |
| Junmai Daiginjo | 48 | 31 |
| Junmai | 48 | 29 |
| Craft Sake | 25 | 13 |
| Ungraded sake | 22 | 11 |
| Tokubetsu Junmai | 11 | 7 |
| Daiginjo | 6 | 3 |
| Honjozo | 2 | 2 |
| **Ginjo** | 3 | **0** |
| **Futsushu** | 3 | **0** |
| Makgeolli | 5 | 5 |
| **Umeshu** (Liqueur) | 3 | **0** |
| Beer, Wine, Cocktail, Shochu, Soju, Gin, Brandy | all | all |
| Whisky | 4 | 3 |

41 photos don't match anything automatically. Some are obvious and just need a manual entry in the photo map, for example `Ume Liquer with Gold Leaf.jpg` → HAMADA Ume Liqueur (that alone gives Umeshu a label), `Woodford Reserve Distillers Select.jpg` → Woodford Reserve, and `Taka Sparkling.jpg`. Others are generic phone exports (`photo_2026-…jpg`) that the owner needs to identify. A one-time review pass would fix most of the gaps above.

### 6.3 Turning a photo into a label

The photos are handheld phone shots, mostly portrait, between 654×784 and 4000×2252, about 128MB in total. They include hands, tables and room backgrounds, and the label sits in a different place in each one. They can't go on the bottles as they are.

- **Crop:** each photo gets a **label rectangle** in the photo map (`labelCrop`, as fractions of the image). *Superseded by §15.3 (2026-10-31): there is no default crop. Only verified label-only crops enter the label pools.* That default suits most of the upright bottle shots seen so far, but each crop gets checked on a contact sheet the build step generates (one page showing every crop).
- **Output:** for each eligible photo, the build step writes one small label image at about 320px wide in WebP at around 75% quality, which is roughly 20–40KB. The welcome page **never loads an original photo**.
- **Fit on the bottle:** the label fills the bottle's label area, using cover-style scaling inside an SVG clip path. A soft inner shadow and a slight horizontal shading gradient on top make it look wrapped around a curved bottle instead of pasted flat on it.

### 6.4 Random choice (decided: re-pick on every visit)

- The page loads a small manifest (`Ship/docs/data/shelf.json`) listing each subcategory's pool of label images. **Every page load, and every time a category is selected**, the visitor's browser picks one label at random per bottle on the shelf.
- The same photo never appears twice on the shelves at once, which can happen in the default mixed view. Skip any photo that's already in use.

### 6.5 Fallback when a pool is empty

The bottle gets an **illustrated paper label** instead: off-white washi texture, the subcategory's kanji or hangul set large in a brush-style font, and the English name small underneath. For subcategories with no native name, such as Merlot or IPA, the English name is set large instead. Today this applies to Ginjo, Futsushu and Umeshu, until their photos are mapped. It's meant to look intended, not like an error.

---

## 7. Art direction (v3: rendered scene)

*Revised 2026-10-31 (v3). This replaces the v2 hand-drawn direction. The materials and mood still follow `Design/welcome-reference.jpg`.*

### 7.1 How it's made

- **The plates and the bottle shells are rendered images supplied by the owner,** from the brief in §12. The build optimises them. The code adds only live content: bottles, labels, tags and controls.
- **Bottle shells** are one transparent image per vessel shape, rendered front-on with a **plain white label**. Each bottle is assembled in four layers:
  1. The shell image.
  2. The label photo crop (§6), clipped to the shell's label rectangle (stored in `scene.json`).
  3. Blend mode `multiply`, so the shell's own shading and highlights show through the label. That makes the label look wrapped round the glass instead of pasted on.
  4. Optionally, a faint highlight strip from the shell above the label.
- **Fallback labels** (§6.5) use the same compositing.
- **Sign:** the plate includes the carved **LIQUID ASSETS** sign. The owner checks the lettering before delivery.
  - If the image tool can't letter it cleanly, the plate is rendered with a **blank** sign, and the shipper overlays the words in Rye with a carved-text filter.
  - Either way, a visually hidden `<h1>Liquid Assets</h1>` carries the name for screen readers.

### 7.2 Colour

The colours come from the plate itself, so the UI belongs to the scene. The brief is genuinely rustic and warm, from the owner's own reference, which is why a warm palette is justified here.

| Token | Value | Used for |
|---|---|---|
| `--iron` | #201d1b | Slate tags, the status slate, the menu button, overlay text on light surfaces |
| `--chalk` | #f2ede4 | Text on iron and slate |
| `--oak` | sampled from the plate's shelf front | Overlay panel accents |
| `--glow` | #f4c27a | **The single accent:** spotlight on hover and select, focus ring, active menu item |
| `--paper` | #efe6d2 | Plan 02–04 menu cards only |

- **No brass on the welcome page.** The v2 `--brass` token remains only for small accents on Plans 02–04 (drop caps, stars), and the quality stamp also uses it.
- **Theme:** the welcome page is one theme, the warm evening bar. Plans 02–04 content pages respect `prefers-color-scheme`. In dark mode their paper cards become a dark-oak surface with chalk text, at WCAG AA contrast.

### 7.3 Type

- **UI text: Outfit.** It replaces Inter, which the taste skill marks as an AI-default font. It's used for tags, the slate, the menu, and all metadata on Plans 02–04.
- **Drink names on Plans 02–04: Cormorant Garamond.** It replaces Fraunces, which the taste skill bans as a default display serif. The serif is justified because the cards are styled as a heritage bar menu.
- **Sign: Rye.** It appears only as the fallback overlay (§7.1).
- **All fonts are self-hosted** as WOFF2 files in `docs/assets/fonts/`, with `font-display: swap` and their OFL licences. There are no Google Fonts `<link>` tags. Plan 06 §8's font credits move into the menu (§13).

### 7.4 Motion (each animation has a stated purpose)

| Motion | Purpose | Spec |
|---|---|---|
| Vessel lift plus spotlight brighten on hover/focus | Feedback | `transform` and `opacity` only, 220ms, `cubic-bezier(0.16,1,0.3,1)` |
| Shelf swap stagger (§5.2) | State change | As §5.2 |
| Menu panel rising from the counter | State change | 320ms with the same curve. The scene behind dims and blurs. |
| Tag fade-in after the swap | Hierarchy | 120ms, delayed until the bottles have landed |

- Nothing loops.
- With `prefers-reduced-motion`, everything becomes instant or a 150ms crossfade.

### 7.5 Pre-flight checks for the shipper

These come from the taste skill:
- **No em dashes or en dashes in any visible text,** including content files, tags, the menu and alt text. Use hyphens, commas or full stops. The shipper audits `docs/` and `content/`.
- **No decorative dots** on the slate, tags or menu.
- **One corner-radius system:** tags and slate at 4px, the menu button round, and the overlay panel's top corners at 16px.
- **Every icon** (the menu, the close button, arrows) comes from **Phosphor Icons**, using the official pinned web package or its copied official SVGs. No hand-drawn icon paths.
- **Contrast:** chalk on iron at 4.5:1 or more everywhere.

### 7.6 Asset pipeline

- **Owner's originals** go in **`Design/scene/`**, which is private and never committed. File names are in §12.
- The build converts them to `docs/img/scene/`:
  - Plates as AVIF plus WebP at widths 1920, 2880 and 3840 (wide) or 1170 (tall).
  - Shells as WebP at 1x and 2x.
  - Metadata stripped, as in Plan 05 S8.
- **The wide plate is preloaded,** to keep the largest paint fast (target under 2.5s). The budget is about 450KB for the first view on desktop and 250KB on phone.
- **Until the assets arrive,** the build keeps the current v2 illustrated scene, so nothing breaks. The v3 engine (cover box, manifest, compositing, menu) can be built and checked using a plain placeholder plate.

---

## 8. Build and data contract (for the implementer)

The welcome page reads **only** `Ship/docs/data/shelf.json` and the label images. It never reads the ledger directly. The build step ([Plan 05](05-data-build-step.md)) produces:

```jsonc
// Ship/docs/data/shelf.json
{
  "generated": "2026-10-30T20:00:00+08:00",
  "categories": [
    {
      "key": "sake", "name": "Sake", "vessel": "sake", "drinkCount": 242,
      "subcategories": [
        { "key": "junmai-ginjo", "name": "Junmai Ginjo", "native": "純米吟醸",
          "drinkCount": 74, "labels": ["img/labels/dassai-45-junmai-daiginjo.webp", "…"] }
        // … in display order, empty subcategories already left out, "ungraded" last
      ]
    },
    {
      "key": "makgeolli", "name": "Makgeolli", "vessel": "makgeolli", "drinkCount": 5,
      "subcategories": [
        { "key": "all", "name": "Makgeolli", "native": "막걸리", "drinkCount": 5, "labels": ["…"] }
      ]
    },
    {
      "key": "wine", "name": "Wine", "vessel": "wine", "drinkCount": 3,
      "subcategories": [
        { "key": "cabernet-sauvignon", "name": "Cabernet Sauvignon", "drinkCount": 1, "labels": ["…"] },
        { "key": "merlot", "name": "Merlot", "drinkCount": 1, "labels": ["…"] },
        { "key": "blend", "name": "Blend", "drinkCount": 1, "labels": ["…"] }
      ]
    }
    // liqueur, beer, spirits, cocktails … (7 categories in top-shelf order)
  ]
}
```

- Every category has the same shape, a list of subcategories, so the page needs no special case for single-bottle categories.
- How the build step assigns each drink to a category:

  | Category | Rule |
  |---|---|
  | Sake | `Core.Category` = Sake or Craft Sake |
  | Makgeolli | Makgeolli |
  | Liqueur | Umeshu or Liqueur |
  | Beer | Beer |
  | Wine | Wine |
  | Spirits | Whisky, Shochu, Soju or Spirit |
  | Cocktails | Cocktail |

  A drink whose Category matches none of these is listed as a warning in the build output. It is never silently dropped.
- Label images are named after the drink **ID**, not the original filename. The original filenames contain spaces, `&`, quotes, Unicode and fullwidth brackets.
- **GitHub Pages:** a repo name can't contain spaces, so the site will be served from a sub-path such as `/Liquid-Assets/`. Every asset path must be **relative**; no leading `/`.
- No framework is needed: one HTML page, one stylesheet, one small script, and the seven SVG bottle symbols inline. The page should be usable with JavaScript turned off, showing the top shelf as plain links to the category pages.

---

## 9. Accessibility and performance

- The top-shelf vessels are real `<button>`s with `aria-pressed`. The subcategory bottles are `<a>` links whose accessible name comes from the tag text, for example "Junmai Ginjo, 74 drinks". Labels are decorative (`alt=""`).
- Keyboard: Tab moves along the top shelf and then the lower shelves, in reading order. Enter or Space selects. A visible warm-amber focus ring that stays clear against both wood and brick.
- A screen-reader live region announces "Showing Sake: 11 kinds" after each swap.
- Budget: the first load is ≤ 300KB plus fonts, and no more than about 12 label images (~400KB) are loaded at once. Labels load lazily for the category the visitor selects.

---

## 10. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | Where do Umeshu and Wine go? | **Both get their own top-shelf category.** Umeshu is split by flavour/base (§4.3). Wine is split by grape variety (§4.5). |
| Q2 | Sakes with no grade? | **Show an Ungraded bottle** for now (§4.1). |
| Q3 | What Makgeolli shows on the shelf | **One Makgeolli bottle** (§4.2). |
| Q4 | Where beer, spirit, cocktail and umeshu types are stored | **`Other Detail.Type`** (§10.1). |
| Q5 | How often labels are re-picked | **Every visit** (§6.4). |
| Q6 | Font for the sign | **Rye** (§7). |
| — | Wines with more than one grape | Designer's call: a single **Blend** bottle (§4.5). The owner can override this. |
| Q7 | Welcome page look | **Rustic brick-and-timber bar** from the owner's reference image, **illustrated** in that style rather than using the photo (§7). |
| Q8 | Sign style | **Carved into reclaimed oak planks** on black iron brackets, still in Rye (§7.2). |
| Q9 | Decor | **Bar stools, whisky barrel, framed print, and glasses on the counter.** No plants (§7.4). |
| Q11 | Scene artwork (v3) | **Rendered images supplied by the owner** (plates plus bottle shells, §12). The live layers are composited over them, and the hand-drawn scene is retired (§2, §7). |
| Q12 | Navigation | **A hamburger menu button on the bar counter** opening a full-screen menu (§13). It replaces the Makers board, and the same button appears in every page header. |
| - | Fonts, tags, footer, motion (v3) | Designer's calls under the taste skill: Outfit plus Cormorant Garamond, self-hosted; slate tags; footer moved into the menu; no idle animation; dark mode on content pages (§7). |
| Q10 | Umeshu category | **Renamed Liqueur**, with one bottle per **kind of liqueur** (Umeshu first). The umeshu flavour/base becomes a card fact (§4.3). Q1's "split by flavour/base" for umeshu is superseded. |

### 10.1 Ledger updates needed (owner)

1. **`Other Detail.Type`:** fill in a value for every Beer, Spirit, Cocktail, Umeshu and Liqueur drink, and add one combined dropdown list to `Other Detail!H2:H400`. Excel can't change a dropdown list per row by category, so it's one list holding:

   > Lager, Pilsner, Pale Ale, IPA, Wheat, Stout/Porter, Sour, Saison, Specialty, Gin, Brandy, Rum, Vodka, Tequila, Baijiu, Highball, Martini, Old Fashioned, Spritz, Classic, Fruit Blend, Tea, Sake-based, Brandy-based, Aged, Yuzushu, Fruit liqueur, Herbal, Cream, Coffee & tea, Other

   The build step checks that each value suits the drink's category, for example that "IPA" isn't set on an umeshu, and warns when it doesn't. Umeshu doesn't have a row in `Other Detail` yet, so add rows for its 3 drinks.
   - **When the first non-umeshu liqueur arrives,** add `Liqueur` to the Core Category dropdown list (`Core!C2:C400` and `New Entry!C2:C400`).
2. **Photo map review:** match the 41 unmatched photos to drinks, especially `Ume Liquer with Gold Leaf.jpg`, which gives Umeshu its first label.

---

## 11. Acceptance criteria

- [ ] The welcome page shows the rustic scene: brick, beams with spots, backlit light-oak bays, the carved reclaimed-plank sign on iron brackets, the plank counter on its iron base, and stools, barrel, print and glasses. All of it, with the 7 vessels and mixed lower shelves, fits on one 1440×900 screen without scrolling.
- [ ] A side-by-side check against `Design/welcome-reference.jpg` shows the same materials, palette and lighting character.
- [ ] Selecting each top-shelf vessel swaps the lower shelves to that category's subcategories, all in that category's shape, in display order, with empty subcategories hidden. Makgeolli shows a single bottle.
- [ ] Every bottle with photos available shows a random label cropped from those photos, re-picked on every load and every selection, and no photo appears twice at once. Bottles without photos show the illustrated fallback label.
- [ ] All 7 category hashes (`#/sake`, `#/makgeolli`, `#/liqueur`, `#/beer`, `#/wine`, `#/spirits`, `#/cocktails`) load directly into that category, and Back/Forward move between selections.
- [ ] Every drink in the ledger lands in exactly one top-level category, and the build output lists any that don't.
- [ ] It works at 375px wide (top shelf in two rows; stools, barrel, print and glasses hidden) with no sideways scrolling, keyboard-only use works, and reduced-motion is respected.
- [ ] The Liqueur shelf shows an **Umeshu** bottle at `#/liqueur/umeshu`. `#/umeshu` links from before the rename redirect to `#/liqueur`.
- [ ] **v3, full bleed:** the scene covers the whole viewport at 1440×900, 1920×1080, 2560×1080, 1024×768 and 375×812, with no letterbox, no footer strip and no page scroll. Shelves stay inside the safe zone at every size.
- [ ] **v3, alignment:** with `?debug=scene`, every bottle base sits on its painted shelf line within 0.5% of plate height, at all sizes above.
- [ ] **v3, scale:** bottles are about 82% of shelf clear height, and labels are composited with the shell's shading visible through them.
- [ ] **v3, menu:** the counter menu button opens and closes the menu with mouse, touch, Enter, Space and Esc. Focus is trapped while it's open and returns to the button. Every link works, and there's no separate "The Makers" control left on the welcome page.
- [ ] **v3, pre-flight:** no em or en dashes in visible text, no decorative dots, only Phosphor icons, self-hosted fonts, and nothing looping.
- [ ] The welcome page never requests anything from `Photos/`.


---

## 12. Image brief for the owner (v3)

Save the finished images to **`Design/scene/`** in the project root. That folder is private and never pushed. Use these exact file names. The shipper then measures them into `scene.json`.

### 12.1 Rules for every image

- **Camera:** straight-on, eye level with the middle shelf, with minimal perspective. Shelves must be **level and parallel to the image edges**, because the live bottles are placed on them.
- **Empty shelves:** completely empty. No bottles, plants, glasses or objects on any shelf. The site adds the bottles.
- **One lighting setup across all images:** warm evening interior, soft backlight glowing from the shelf bays, small warm recessed ceiling spots, no harsh shadows.
- **No people,** and no text except the sign.
- **Style:** photoreal interior render matching `Design/welcome-reference.jpg`. Exposed red brick, dark timber beams, light natural-oak shelving, a thick reclaimed-plank counter on a black iron base, and seagrass-and-iron stools.

### 12.2 Files and prompts

**A. `bar-wide.png`**, 3840×2160 (16:9)
> Photorealistic interior render, straight-on frontal view at eye level, of a rustic neighbourhood bar in the evening. Exposed red brick back wall. Heavy dark timber ceiling beams with small recessed warm spotlights. Centred and filling the middle 60% of the width: a wide open shelving unit in light natural oak with three long, level, completely empty horizontal shelves, each bay backlit by a softly glowing warm panel. Above the shelving, a sign of three weathered reclaimed oak planks hangs from the front beam on two black iron brackets, with the words LIQUID ASSETS carved into the wood in bold western slab-serif capitals. Foreground across the full width: a thick reclaimed-plank bar counter with a vertical-board front on a black iron base, its top clear and uncluttered. Four round bar stools with woven seagrass seats and black iron frames, cropped by the bottom edge. At the far left, a wooden whisky barrel and a framed vintage typographic print on the brick. Warm, soft, inviting light, no people, no text other than the sign, no bottles or objects on the shelves.

Keep the outer 19% on each side to brick and decor only. Those strips get cropped on narrower screens.

**B. `bar-tall.png`**, 1290×2796 (phone portrait)
> The same bar, same materials and lighting, as a tall portrait composition. The carved LIQUID ASSETS sign hangs at the top. Below it, a tall, narrow light-oak shelving unit with four level, completely empty shelves, each backlit by a warm glowing panel. At the bottom, the thick reclaimed-plank counter on a black iron base with a clear top, and one seagrass stool cropped at the bottom edge. Straight-on view, no people, no objects on the shelves.

**C. Bottle shells.** Seven images, transparent PNG, 1024px tall, each bottle upright and centred.
> Studio product render of an empty [BOTTLE], perfectly front-on orthographic view, upright and centred, with a plain matte white rectangular paper label wrapped around the body (no text or graphics on the label). Soft warm key light from the upper left, matching a warm evening bar interior, subtle realistic glass reflections. Transparent background.

| File | [BOTTLE] |
|---|---|
| `shell-sake.png` | 720ml Japanese sake bottle, tall with long sloping shoulders, dark green glass, silver screw cap |
| `shell-makgeolli.png` | 750ml Korean makgeolli bottle, ribbed translucent PET plastic, milky white liquid, short neck, green cap |
| `shell-liqueur.png` | 500ml squat, round-shouldered clear glass bottle with amber liquid, short neck, cork stopper |
| `shell-beer.png` | 330ml brown glass longneck beer bottle with a gold crown cap |
| `shell-wine.png` | 750ml Bordeaux wine bottle, high square shoulders, dark green glass, dark red foil capsule |
| `shell-spirits.png` | square-shouldered heavy-based spirits bottle, clear glass, amber liquid, wooden cork stopper |
| `glass-cocktail.png` | coupe cocktail glass with a pale golden drink and an olive garnish, *no label* |
| `glass-highball.png` | tall highball glass with a pale golden drink and ice, with a small blank white paper tag tied round it with twine (the tag is the label area) |

- If your tool can't make transparent backgrounds, render on a plain mid-grey background and remove it with a background-removal tool before saving.
- Check that the sign reads exactly **LIQUID ASSETS**. If it doesn't, re-render with a blank sign and tell the designer (§7.1 fallback).

---

## 13. Counter menu (v3)

### 13.1 The control

- **Where:** a **hamburger button resting on the bar counter**, at the right, on the counter-top anchor from `scene.json`.
- **Look:** a round iron puck, at least 48px, with a Phosphor `List` icon in chalk. On desktop the word **Menu** sits beside it.
- **Hover/focus:** the button lifts 1px, and the `--glow` focus ring appears. It presses down on `:active`.
- **On every other page** (Plans 02–04), the same button sits at the top right of the header, so navigation works the same everywhere.

### 13.2 The menu

A full-screen overlay. The scene behind dims to 40% and blurs, with a solid fallback when reduced transparency is set. A dark-oak panel rises from the counter.

| Group | Links |
|---|---|
| **The Bar** | Home (`#/`) |
| **Shelves** | Sake · Makgeolli · Liqueur · Beer · Wine · Spirits · Cocktails, each with its drink count. They link to `#/<category>`, which opens the bar with that shelf selected. |
| **The Makers** | `#/makers` |
| **About** | One short line ("A personal log of 265 drinks, updated {date}"), then the credits: map source, font licences. |

- **Layout:** desktop, two columns (Shelves left; The Bar, The Makers and About right). Phone, a single column.
- **Link text:** Cormorant Garamond for the group names and Outfit for the links. Every link is a tap target of at least 44px. The current page shows `--glow` and `aria-current`.
- **Behaviour:**
  - The button carries `aria-expanded` and `aria-controls`. The overlay is a `role="dialog"` with `aria-modal`.
  - Focus is trapped inside while it's open. Esc, the close button (Phosphor `X`) or a backdrop click closes it, and focus returns to the menu button.
  - Choosing a link closes the menu and navigates.
- **Menu only:** the menu contains only pages that already exist. New pages (favourites, search) need their own plan first.

---

## 14. Notes for when the images arrive (designer, 2026-10-31)

These answer the shipper's open questions from the v3 engine build:

| Question | Answer |
|---|---|
| `scene.json` holds placeholder numbers | Measure every value from the delivered images: shelf lines, clear heights, sign rectangle, counter-top line, slate and menu anchors, and each shell's `labelRect` (the white label area, as fractions of the shell image). Check with `?debug=scene` at the §11 sizes. |
| Vessel placement on the tall plate | Upper shelf: Sake, Makgeolli, Liqueur, Beer. Second shelf: Wine, Spirits, Cocktail. Each row is evenly spaced across its shelf's measured x-range, with the same 82% height rule (§2.5). The two lower shelves hold the subcategories. |
| A shell's white label may be smaller than the label crop | The label crop is **cover-fitted** into `labelRect`: scaled to fill it, centre-cropped to its aspect ratio, never stretched. `labelCrop` in the photo map still chooses the region of the photo first. |
| The placeholder sign is blank but the real plate will have one | Use the plate's sign when the owner confirms it reads LIQUID ASSETS. Otherwise use the §7.1 Rye overlay on a blank-sign plate. Either way, keep the hidden `<h1>`. |
| Phosphor icon weight | **Regular** weight for every icon on the site, at the same size scale. |
| The v2 phone view still scrolls | Accepted as temporary. The no-scroll rule (§2.2) applies from the moment v3 goes live. |

**Switching to v3:** when `Design/scene/` holds both plates and all 8 shells, the shipper measures `scene.json`, makes v3 the default (no `?scene=v3` needed), retires the v2 scene code, regenerates the share image from the v3 scene, and re-runs every §11 v3 criterion.

---

## 15. Revision 3.1: the owner's bar image and label-only crops (2026-10-31)

### 15.1 The wide plate is delivered

- **File:** `Design/scene/bar-wide.webp`, 1672×941 (16:9).
- **Contents:** an izakaya-style rustic bar.
  - Brick wall and timber beams with spotlights.
  - The carved sign reading **LIQUID ASSETS** in brush-style capitals. It's used as painted, so the Rye overlay isn't needed.
  - A light-oak backlit shelving unit with **three level, empty shelves**, spanning about x 22–80% and y 26–62%.
  - A clear plank counter top (about y 67–74%).
  - Four seagrass stools.
  - Decor: paper lanterns reading 居酒屋, a 酒 scroll with Mt Fuji, a sake taru, shoji screens and bamboo.

  **The owner chose this image,** so its decor supersedes the §7.4 decor list.
- **Checked against §12:** straight-on camera, level shelves, empty shelves, correct sign, shelves inside the safe zone. All pass.
- **Resolution is below the §12 minimum** (2560 wide). It's accepted for now, and will look slightly soft on large or high-density screens. The build serves it at its native size and **never upscales**. The owner can later replace it with the original or a 2× upscale under the same name.

### 15.2 Going live with what exists (interim)

| Piece | Interim rule |
|---|---|
| Landscape / desktop | **v3 becomes the default now,** on `bar-wide.webp`. The shipper measures `scene.json` from it (shelf lines, clear heights, counter-top line, slate and menu anchors). The menu button goes on the counter top at the right, and the status slate on the left. |
| Bottles | **No shells yet,** so the current SVG vessel shapes stand on the painted shelves at the §2.5 scale. They switch automatically to the rendered shells when `shell-*.png` / `glass-*.png` arrive. |
| Portrait / phone | **No tall plate yet,** so phones keep the v2 illustrated scene until `bar-tall` arrives. A cover-cropped wide plate would cut off the shelves. |
| Build input | `Design/scene/` accepts `.png` **or** `.webp` for every file in §12. |

### 15.3 Labels: label-only crops (owner's rule, 2026-10-31)

*The owner asked that welcome page bottle labels be cropped to just the label from each bottle photo, and that bottles whose label can't be cropped properly be skipped. This replaces the default-crop rule in §6.3.*

- **A label is the bottle's printed or paper label only.** No hand, background, table, glass beyond the label's edge, or neck and cap. The crop is a rectangle inside the label's visible face.
- **No more default crop.** A photo enters a welcome page label pool **only** if its photo-map entry has a **verified** `labelCrop`:

  ```jsonc
  "labelStatus": "ok"    // or "skip"
  "labelSkip": "…"       // the reason when skipped
  ```
- **Skip a photo when** the label:
  - is mostly covered by a hand or glare,
  - is too curved or angled to show a flat face,
  - is too small or blurry at 320px,
  - is a back label that's all text,
  - doesn't exist (for example a fully printed bottle or bare glass).

  A skipped photo is **left out of the label pools only**. It still appears as the card thumbnail (Plan 02) and in the drink page gallery (Plan 03).
- **How the crops are made:** the shipper looks at every matched front photo, using downscaled previews with a coordinate grid, and records `labelCrop` plus `labelStatus` in `Ship/content/photo-map.json`. Owner-set entries are never overwritten.
- **Owner review:** the build report shows a **label contact sheet** of each accepted crop, plus a separate list of skipped photos with reasons. The owner can flip any decision in the photo map.
- **Empty pool:** a subcategory left with no `ok` labels uses the §6.5 illustrated fallback label. The build report lists these subcategories.
- **Scope:** this applies to **welcome page bottle labels only.** Card thumbnails and drink page photos are unchanged.

### 15.4 Still wanted from the owner

1. `bar-tall` (§12 prompt B), with `bar-wide.webp` attached as the style reference so the two match.
2. The 8 bottle shells (§12 prompts C).
3. Optionally, a higher-resolution `bar-wide`.

### 15.5 Acceptance (additions)

- [ ] At 1440×900, 1920×1080 and 2560×1080, the welcome page shows `bar-wide` full-bleed. Bottles stand on the three painted shelves (checked with `?debug=scene`), the menu button is on the counter top, and nothing scrolls.
- [ ] Every label on a welcome page bottle is label-only. No photo with `labelStatus: "skip"` (or without a verified crop) appears in any label pool.
- [ ] The build report shows the label contact sheet, the skip list with reasons, and the subcategories left on fallback labels.
