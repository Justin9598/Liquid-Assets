# Plan 11: No prices on the site

Status: **Approved: the owner asked for this directly (2026-11-08).** Built by the shipper. No push without the owner's word.

## 1. Owner brief

> "For the live site, remove all mention of prices, only keep where they were tried from. If the same bottle was tried multiple times have the order the places in price by having the cheapest at the top but do not display the price."

This replaces Plan 03 §8.2 and its decision Q2 ("Show it").

## 2. What changes

- **The ledger keeps `Price (S$)`.** The owner still records it. It is private, like `Notes`.
- **No published file carries a price.**
  - The build drops `price` from every visit in `docs/data/drinks/*.json`, and from any other output that has it.
  - `checks.py`'s schema loses the field.
  - `money()` in `util.js` and the `.v-price` style are removed once nothing uses them.
- **The drink page's tab** (the list of times the drink was had) shows **date, size and where** for each visit. There's no price, on screen or in the screen-reader text (`visitText`).
- **Visit order:** for a drink had more than once, the tab lists visits **cheapest first.** The build sorts them before it writes the file, so the order is the only trace of price.
  - **A visit with no price counts as free** and goes first. The owner said bottles with no price were tasted at no charge.
  - **Ties,** including several free visits, go newest first.
- **"Last had", "had N times" and other tallies** are unchanged. They never used price.
- **The private build report** may keep prices for the owner.

## 3. Privacy gate

`scan_published()` gains a check, which is an error (E02):
- No published file under `docs/data` may contain a `"price"` key.
- No published file may contain an amount written as `S$` followed by a number.

## 4. Acceptance

- [ ] `grep` finds no `"price"` in `docs/data`, and the new E02 check passes.
- [ ] A drink with several visits at different prices lists them cheapest first, with no price shown. A test checks one real example from the ledger, with free tastings first.
- [ ] The drink page shows date, size and where for each visit.
- [ ] The build has 0 errors and the full pytest passes. Retake one drink page with several visits at 1440×900 and 375×812, into `reports/plan11/`.
- [ ] Commit as "Plan 11: no prices on the site; visits ordered cheapest first", ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Include `plans/11` and the Plan 03 note. **No push.**
