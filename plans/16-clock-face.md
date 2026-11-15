# Plan 16: The new clock face

Status: **Approved by the owner (2026-11-15): "use the new clock face too".** No push without the owner's word.

## 1. Brief

- **Today:** the reset clock on the welcome page (Plan 10 §5) is drawn in SVG by `docs/assets/js/clock.js`: a brass rim, a cream face, twelve ticks and two dark hands. The hands show the visitor's local time and move once a minute.
- **The change:** the owner made a rendered clock face in Gemini (`Design/scene/clock.jpg`, from the prompt in `Design/gemini-prompts.md` §C).
  - **What it shows:** a brass outer rim, a walnut ring, an aged cream dial with minute ticks, the numerals 1–12 and a brass centre cap. It has **no hands**.
  - **What changes:** the site shows this picture as the clock and draws only the hands on top.
- **Backgrounds:** the owner chose to keep the site's current backgrounds, so this plan changes **only the clock**.

## 2. The source picture

**File:** `Design/scene/clock.jpg`. It's 1024×1024, on pure black. It's private and read at build time only.

The designer measured it by eye and from pixels; the shipper checks these:

| Measure | Value |
|---|---|
| Outer rim circle | centre (511.5, 511), radius about 466 px (bounding box x 45–978, y 45–977) |
| Cream dial | radius about 372 px, which is 0.80 of the outer radius |
| Numerals | centred about 290 px from the centre (0.62) |
| Brass centre cap | radius about 25 px (0.055), exactly at the centre |

## 3. Building the clock image

- **Cut out a circle:** crop to the outer rim circle, and make everything outside it transparent, with a 1 px feather.
  - The rim's black outer edge must not show as a dark ring on the brick wall. Erode by 1 px if needed, and check it over the plate.
- **Output:** `docs/img/scene/clock@1x.webp` and `clock@2x.webp`, square.
  - **Sizes:** the clock shows at about 6% of the plate height (Plan 10 §5). That's about 55 CSS px on a 900 px tall desktop, and about 65 px on 1080 p. So 1x is **128 px** and 2x is **256 px**.
  - **Sharpening:** apply a light unsharp mask after downscaling, so the numerals stay crisp.
- **Wiring:** add it to the scene build (`liquid/scene.py`) next to the plates, so it's regenerated with them and named in `data/scene.json` as `clock: { "1x": …, "2x": … }`.
- **Build check (W30):** the clock picture is missing, or isn't square.

## 4. Drawing the hands (`clock.js`)

- **The button stays the same:** same button, same position and size from `scene.json`, the same "Reset" tag on hover, and the same once-a-minute update.
- **Inside the button:**
  1. An `<img>` of the clock face (1x/2x), filling the button.
  2. The existing `<svg viewBox="0 0 100 100">` on top, holding **only the hands and a cap**. Remove the drawn rim, face and `TICKS`.
- **Hands**, in viewBox units, where the outer rim is radius 50 and the dial is about 40:

  | Part | Size | Style |
  |---|---|---|
  | Hour hand | from the centre to radius **21** | stroke 4.2, colour `#2a1a0e`, round cap |
  | Minute hand | from the centre to radius **33**, just inside the minute ticks | stroke 2.8, same colour, round cap |
  | Centre cap | r **3.2**, drawn on top of both hands | fill `#a07a35` with a 0.6 stroke `#6b4b1b`, matching the picture's brass cap |
  | Shadow | | `drop-shadow(0 0.4px 0.6px rgba(0,0,0,.45))` on the hands group, so they read as standing off the dial |

- **Fallback:** if the image fails to load, the old drawn face shows instead. Keep the old SVG face as the fallback, shown only when the `<img>` fires `error`.
- **The clock's own drop shadow:** keep the existing button filter.

## 5. Acceptance

- [ ] **Look:** at 1440×900 and 1920×1080 the clock shows the new face with the current time's hands. The hands point at the right numerals at a few set times, checked with a fixed `Date` in the smoke test: 3:00, 7:30 and 10:10.
- [ ] **Edges:** no black ring around the rim on the brick wall; checked in a close-up screenshot.
- [ ] **Phones:** at 375×812 and 390×844 the clock still shows wherever it shows today, with the same position rules. It must stay tappable at no less than 44×44 px, as now.
- [ ] **Behaviour:** hover/focus shows "Reset", tapping resets the bar, and keyboard focus has its outline, all as before.
- [ ] **Screenshots:** in `reports/plan16/`: `clock-closeup-1440x900.png`, `welcome-1440x900.png`, `welcome-1920x1080.png` and `welcome-390x844.png`.
- [ ] **Tests:** the full pytest passes, the build has 0 errors, the privacy scan is clean, and no `Design/` path appears in `docs/`.
- [ ] **Commit** as "Plan 16: the new clock face". **No push.**
