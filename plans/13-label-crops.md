# Plan 13: Better label crops: an owner crop tool and a check step

Status: **Approved by the owner (2026-11-08): "Approve, build it".** No push without the owner's word.

## 1. Why

- **The fault:** the owner found crops in the build report's label contact sheet that miss the label or sit off-centre.
- **How crops are made now** (Plan 01 §15.3): the shipper estimates each `labelCrop` from a downscaled photo with a grid, and never looks at the crop it produced.
- **Two other gaps:**
  - `content/photo-map.json` has no marker for which crops the owner set, so "owner-set entries are never overwritten" can't actually be enforced.
  - Today there are 213 entries: 176 `ok` and 37 `skip`.

## 2. The owner's crop tool

A small **private, local** page for drawing label boxes by hand.

### 2.1 How it runs

- **Start it:** a new `Ship/build/crop.bat` starts `build/tools/croptool.py`, a Python standard-library server **bound to 127.0.0.1 only**, port 8765. It opens `http://127.0.0.1:8765/` in the browser. Closing the window stops it.
- **What it serves:**
  - the tool page (`build/tools/crop/index.html`, plain HTML, CSS and JS with no outside libraries);
  - the photos, read-only, from `../Photos/`;
  - the current `content/photo-map.json`.
- **What it writes:** only `content/photo-map.json`, through one `POST /save` call.
  - Each save first copies the old file to `Ship/reports/photo-map-backups/photo-map-<timestamp>.json`. `reports/` is git-ignored.
  - Then it writes the new file atomically (a temp file, then a rename), keeping the existing key order and formatting.
- **Nothing is published.** The tool's code sits in `build/tools/` and holds no data. Photos are only read from the PC at run time and never copied into `Ship/`.

### 2.2 Using it

- **Lists** (tabs at the top):
  - **Needs a look:** crops the check step marked unsure (§3), and any drink with a front photo but no crop. This tab opens first.
  - **All crops:** every `ok` crop, for a quick run-through.
  - **Skipped:** the `skip` entries, in case one has a usable label after all.
- **The main view:**
  - The full photo fits the window, and the current crop is drawn as a box.
  - **Drag** on the photo to draw a new box. **Drag the edges or corners** to resize, and drag inside to move. **Arrow keys** nudge it by 0.5% (Shift for 2%).
  - **A live preview** beside the photo shows the label exactly as the site will use it. The crop is cover-fitted into the shell's label rectangle, at that rectangle's aspect ratio, so the owner can see what gets cut off.
- **Buttons and keys:**
  - **Save** (Enter) records the box, `labelStatus: "ok"` and `cropBy: "owner"`, then moves to the next drink.
  - **No usable label** (S) records `labelStatus: "skip"` and `cropBy: "owner"`.
  - **Undo** (Z) goes back to the crop as it was when the drink opened.
  - **Previous and next** (← →).
- **A counter** shows the place in the list, for example "12 of 31 to look at".
- **Fix links:** the build report's contact sheet gets a **"Fix"** link under each crop. It opens `http://127.0.0.1:8765/#<drink-id>` when the tool is running.

### 2.3 After using it

- **Publishing:** the owner runs `build.bat`, then tells the shipper to commit and push as usual (Plan 06 §5). The new crops publish at the next build.
- **Protection:** the shipper and every script treat **`cropBy: "owner"` entries as read-only.** The build check confirms none was changed by a non-owner commit, by comparing with the last commit. If one was, it raises E05 and stops.

## 3. The shipper's check step (new crops, and any re-checks)

- **Never touch owner crops.** Skip any entry with `cropBy: "owner"`.
- **Work at full size.** Propose the crop from the **full-resolution** photo, not a shrunken one.
- **Look at the result.** Run the new `build/tools/cropcheck.py <id> x y w h`. It writes `reports/crops/<id>.png`, one image showing:
  - the photo with the box drawn on it;
  - the cropped label at full size;
  - the label as it will appear on the shelf shell.
- **Then view that image and check it against all four:**
  1. The **whole label** is inside the box, with a small margin of no more than about 5% of the box on each side.
  2. The label is **centred,** with its middle within 10% of the box's middle.
  3. **Little else** is in the box: hands, glass, the bar or background together under about 10% of it.
  4. The shell preview shows the label's **main text or emblem,** not just its edge.
- **Up to 3 tries.** If a crop still fails after 3, record it with `cropCheck: "unsure"`. It then shows first in the tool's **Needs a look** list and at the top of the build report.
- **When a check passes,** record `cropBy: "shipper"` and `cropCheck: "passed"`.
- **No usable label** (a glass, a mug, or a label too blurred or turned away): record `skip`, as now.
- **Plan 01 §15.3** gets a note: this replaces its "downscaled previews with a coordinate grid" method.

## 4. Data and build changes

- **`photo-map.json`:** each entry may carry `cropBy` (`"owner"` or `"shipper"`) and `cropCheck` (`"passed"` or `"unsure"`).
  - Existing entries have neither. They count as unchecked shipper crops.
  - The build accepts both fields and rejects other values (E04).
- **The build report's contact sheet:**
  - Groups the crops: **Needs a look** first, then the rest.
  - Marks owner crops with a small "yours" tag.
  - Adds the "Fix" link under each crop (§2.2).
- **Nothing on the site changes** except the crops themselves.

## 5. Acceptance

- [ ] `crop.bat` opens the tool. Drawing, resizing, nudging, Save, No usable label, Undo and Previous/Next all work, and the preview matches what the built site shows on the shell. Check it with one drink end to end: save in the tool, run `build.bat`, and see the new label on the bar.
- [ ] Each save writes a backup to `reports/photo-map-backups/`, and `photo-map.json` stays valid, keeping its key order.
- [ ] The server listens on 127.0.0.1 only, and refuses writes to any path but `content/photo-map.json`.
- [ ] `cropcheck.py` writes the three-part check image. The shipper's check step skips owner crops, and marks failures `unsure`.
- [ ] The build accepts the new fields. E05 blocks a non-owner change to an owner crop, and the report groups the crops and shows the Fix links.
- [ ] The full pytest passes, with tests for the save endpoint, the backup and E05. Screenshots of the tool go into `reports/plan13/`.
- [ ] Commit with no push.

## 6. Decisions

| # | Question | Answer |
|---|---|---|
| D1 | Approach | Crop tool plus check step (owner, 2026-11-08). |
| D2 | Re-check the 176 existing `ok` crops with the new check step? | **Yes, all 176** (owner, 2026-11-08). The shipper fixes clear misses itself, and marks doubtful ones `unsure` for the owner's Needs a look list. This runs after the tool and check step are built and committed, as a separate commit. |
