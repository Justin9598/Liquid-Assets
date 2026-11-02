# Plan 06: Deployment and updates ("Last orders")

Status: **Approved design. The owner has answered every open question (§10).**
Author: Claude (designer). This is a plan only. Nothing here is built or pushed yet. Implementation belongs to the `shipper` subagent. Every step that touches GitHub needs the owner's explicit go-ahead in that task.
Depends on: [05-data-build-step.md](05-data-build-step.md) (folder layout, local build).

---

## 1. Where things stand (checked 2026-10-30)

| Item | State |
|---|---|
| GitHub account | `Justin9598`. The `gh` CLI is installed and logged in. |
| Target repo | **`Justin9598/Liquid-Assets`**: public, **empty** (no commits, no default branch), Pages not enabled |
| Future site URL | **https://justin9598.github.io/Liquid-Assets/** |
| Existing site | `Justin9598/Alcohol-Tasting-List` is a **live** Pages site at https://justin9598.github.io/Alcohol-Tasting-List/, served from `main` at the repo root, with `index.html`, `css/`, `js/` and `photos/`. A private `Alcohol-Tasting-List-Source` repo also exists. **Both are left untouched** (§10 Q1). |
| Local `Ship/` | Not a git repo yet |
| Git credentials | `git config` has no credential helper, so pushes would prompt for login. `gh auth setup-git` fixes that (§3 step 2). |

---

## 2. Deployment model

```
Owner's PC                                          GitHub
──────────                                          ──────
Drinks Ledger.xlsx ─┐
Photos/ ────────────┼─► build.bat ─► Ship/docs/ ──git push──► Liquid-Assets (main)
Ship/content/ ──────┘    (Plan 05)                              │
                                                                ▼
                                                   GitHub Pages: deploy from
                                                   branch main, folder /docs
                                                                │
                                                                ▼
                                          justin9598.github.io/Liquid-Assets/
```

- **Classic "deploy from a branch"** Pages: branch `main`, folder `/docs`. There are no GitHub Actions, as decided in Plan 05 Q3. Pages publishes about a minute after each push.
- **One branch: `main`.** It's a one-person site, so no feature branches or pull requests are needed. Experiments can use a short-lived branch, which Pages ignores.
- **What's in the repo:** everything in `Ship/` except git-ignored files. **What's served:** only `Ship/docs/`. Pages serves nothing outside `docs/`, but because the repo is public, everything committed is still *visible on GitHub* (§10 Q4).

---

## 3. One-time setup

Steps 2–6 change GitHub or push code, so the shipper runs them only when the owner says go, or the owner runs them.

1. **Repo files** (shipper, local):
   - `Ship/.gitignore`:
     ```
     reports/
     build/.image-cache.json
     __pycache__/
     .pytest_cache/
     ~$*
     *.xlsx
     Thumbs.db
     desktop.ini
     ```
     `*.xlsx` is a safety net in case the ledger is ever copied into `Ship/` by mistake.
   - `Ship/.gitattributes`: `* text=auto eol=lf`, with `*.bat text eol=crlf` (batch files break with LF endings), and `*.webp`, `*.png`, `*.jpg` and `*.woff2` marked `binary`. This avoids Windows line-ending churn. *(Amended 2026-10-30.)*
   - `Ship/README.md`: one paragraph on what the site is, the live link, and "built from a private ledger; see `plans/`".
   - `Ship/docs/.nojekyll`: an empty file. It stops Pages running Jekyll, which would hide files starting with `_` and slow builds.
   - `Ship/docs/404.html`: the "This shelf is empty" scene from Plan 02 §2, linking to `./`. Hash routes never hit it, but mistyped paths do.
2. **Credentials** (owner, once): `gh auth setup-git`, so `git push` uses the existing `gh` login.
3. **Initialise and connect** (shipper, with go-ahead):
   ```bash
   git -C Ship init -b main
   git -C Ship remote add origin https://github.com/Justin9598/Liquid-Assets.git
   ```
   The remote is empty, so there's nothing to pull or merge first.
4. **First commit and push** (shipper, with go-ahead): run the build, check that the report has **0 errors**, run the pre-push check (§5), then commit everything and `git push -u origin main`.
5. **Enable Pages** (owner in GitHub settings, or the shipper via `gh api` with go-ahead): Settings → Pages → Source: *Deploy from a branch* → `main` / `/docs`. Turn on **Enforce HTTPS**.
6. **Smoke test** the live URL (§6).

---

## 4. Everyday update: adding a drink

This is the routine the owner follows after drinking something new. It's built around the folders that already exist, and three agents each have one job:

- The **researcher** (Opus, `.claude/agents/researcher.md`) gathers the data.
- The **designer** (the main session) plans what changes.
- The **shipper** (Sonnet, `.claude/agents/shipper.md`) builds and publishes.

Nothing reaches the ledger or the site without the owner's approval. The researcher writes to the ledger only after the owner approves a proposal.

| Step | Who | What |
|---|---|---|
| 1 | Owner | Drop the photo(s) into **`New/`**. Next time the build runs, they appear in its report as "waiting to be logged" (Plan 05 S11). |
| 2 | Owner → researcher | Ask the researcher to research the new bottle(s). For each one, it reads the label photos, checks the ledger for repeats and existing producers, researches the rest with a source for every fact, and writes a proposal to **`Research/pending/`**. The proposal contains: the Core row, the detail-sheet rows, the `Other Detail.Type`, a draft `Public Notes`, a `Producers` row with `Status = draft` (new producers only), photo renames, sources, conflicts, and questions for the owner. |
| 3 | Owner | **Review the proposal.** Answer its questions (date, venue, price, rating, favourite, visit note), correct anything wrong, then **approve** or **reject** it. On approval the researcher moves the file to `Research/approved/` and enters its rows into the ledger (step 5). `Research/` sits outside `Ship/`, so drafts are never pushed. |
| 4 | Owner → designer | Ask the designer to plan the update. The designer reads the approved proposal and writes an **update note** at `Ship/plans/updates/YYYY-MM-DD-<id>.md` containing: the exact ledger entries, the photo renames, and any knock-on effect on the site. Examples of knock-on effects: a new subcategory bottle appearing on a shelf, a new `Type` value that needs adding to a validation list, or a new producer page. A plain new bottle usually needs **data only, no code**. Anything that changes the design goes through a plan amendment and the owner's approval as usual. |
| 5 | Researcher, then owner | **Changed 2026-11-02 at the owner's request:** the researcher enters the approved rows into the ledger itself, following the update note's tables when there is one (`.claude/agents/researcher.md`, "Entering approved data into the ledger"). It refuses while Excel has the file open, backs it up to `Research/backups/` first, adds rows only and never changes existing ones, then reopens the file and checks it, restoring the backup if anything is off. **Keep Excel closed while it runs.** The owner then moves the photos from `New/` to **`Photos/`** with the names from the note: **exactly the drink's `Name`**, plus ` (back label)`, ` (side label)` or ` (second photo)` for extra views. |
| 6 | Owner | Run **`build.bat`**, then **`preview.bat`**, and check the build report and the local site (§5). |
| 7 | Owner → shipper | When happy, tell the shipper to **commit and push** (§5). If the update note calls for code changes, the shipper makes those first. |
| 8 | Owner | Glance at the live site after about a minute. |

**Producer research** in a proposal stays `Status = draft` in the ledger until the owner marks it `approved`. Until then, the producer page shows only the facts derived from Core (Plan 04 §8).

**Name characters Windows forbids** (`\ / : * ? " < > |`): when the drink name contains one, for example a `"` in *Ryujin "Dragon God"*, the file can't match exactly. Name it as close as possible and add a manual entry to `content/photo-map.json`. The build's suggestions file (Plan 05 S7) will propose the match.

---

## 5. Publishing: the owner checks, then the shipper commits and pushes

**Decided (§10 Q2):** nothing reaches GitHub until the owner has checked it and explicitly tells the shipper to commit and push. There is **no** automatic publish script.

### 5.1 Owner: build and check locally

1. **`build.bat`** (Plan 05 §4) regenerates `docs/` and opens `reports/build-report.html`. The owner reads the summary, the warnings and the changes since the last publish (drinks added or removed, photos added).
2. **`preview.bat`** (new, in `Ship/build/`) serves `Ship/docs/` on a local web server (`http://localhost:8000/`) and opens it in the browser. The site behaves exactly as it will on GitHub Pages, hash routes included. Closing the window stops the server.
3. When everything looks right, the owner tells the shipper something like *"commit and push"*.

### 5.2 Shipper: commit and push, only when told

When asked, the shipper runs these steps in order, and stops and reports at the first failure:

1. **Excel check:** if `~$Drinks Ledger.xlsx` exists, report that the ledger may have unsaved changes, and ask before continuing.
2. **Fresh build:** re-run the Plan 05 build, to be sure `docs/` matches the ledger the owner checked. **Stop on any error** (E02 privacy, E03 references, E04 schema).
3. **Show what will be committed:** a short list of changed files grouped by type (data, images, site code, content, plans), plus the build summary. If the owner's request named specific changes and the diff contains anything else, ask before continuing.
4. **Pre-push check:**
   - Nothing outside `Ship/` is staged.
   - No `.xlsx` file, and no file from `Photos/`, `New/` or `reports/`, is staged.
   - No staged file is over 10MB. Anything that large points to an original photo copied by mistake.
5. **Commit:** the message is `Ledger update YYYY-MM-DD: +N drinks, +M photos`, or a plain description of a code change, followed by the standard co-author line. If nothing has changed, report "Nothing new to publish" and stop.
6. **Push:** `git push`. On failure (offline, or authentication), keep the commit locally and report it. It will be pushed next time the owner asks.
7. **Report back:** the commit hash, the live URL, and when the change should appear (about 1 minute for Pages, plus up to 10 minutes of caching, §7).

**Undoing a bad publish:** the owner asks the shipper to revert the commit, and the same §5.2 checks apply before pushing the revert.

---

## 6. Post-deploy smoke test (first launch and any big change)

The shipper runs this with a browser on the live URL and reports the results.

- [ ] `https://justin9598.github.io/Liquid-Assets/` loads the bar scene, with no console errors and no 404s in the network log.
- [ ] Every top-shelf category swaps the shelves, and every subcategory bottle opens its list (`#/…`).
- [ ] A sample of drink pages opens, including one with a tasting card, one without a photo, and one had several times.
- [ ] A producer page and the Makers index open, and the map responds.
- [ ] Reloading on a deep link (for example `#/sake/junmai-ginjo?style=nama`) restores the view.
- [ ] Layout checked at **1440×900, 1920×1080 and 375×812** on every push, with screenshots of both desktop and phone attached to the report (Plan 07 §5.3 parity rule).
- [ ] **No requests to `Photos/`,** and no published JSON contains `Notes` text. This repeats Plan 05's privacy scan against the live files.

---

## 7. Caching and freshness

GitHub Pages caches files for about 10 minutes and doesn't allow custom headers.

- The page fetches `data/build.json` with `cache: "no-cache"`, so the browser checks with the server every time. It's tiny.
- Every other data file and image URL gets `?v=<version>` from `build.json`. A new publish therefore loads fresh data at once, and unchanged visits stay cached.
- The build sets `version` to a short hash of the generated `docs/data/` contents, so it only changes when the data does.

---

## 8. Site-wide extras

| Item | Plan |
|---|---|
| `<title>` and description | "Liquid Assets", plus a one-line description. Each route updates `document.title` (for example "Junmai Ginjo · Liquid Assets"). |
| Favicon | A small bottle silhouette from the Sake vessel (Plan 01 §3), in SVG with a PNG fallback |
| Share preview (Open Graph) | `og:image` and `og:url` are the **only absolute URLs** on the site (`https://justin9598.github.io/Liquid-Assets/…`), because share previews require them. If the domain ever changes, they have to change too. The image is drawn at build time with one real label on the lower shelf, so it changes when the photo map changes. |
| Share preview (original note) | One static 1200×630 image of the bar scene with the carved sign, created once at build time from the SVG artwork, plus `og:title` and `og:description`. Hash routes can't have their own previews on a static host, so every link shares the bar. |
| Search engines | **Link-only (§10 Q3).** Every page, `404.html` included, carries `<meta name="robots" content="noindex">`. There's deliberately **no** `robots.txt` that blocks crawling, because a crawler that's blocked never sees the `noindex` tag and can still list the bare URL. |
| Analytics | **None.** No trackers or cookies, so no consent banner is needed. |
| Footer | **Moved into the menu's About group** (Plan 01 §13, v3): last updated date, drink count, map licence credit and font credits. The welcome page has no footer strip. Plans 02–04 may keep a slim footer with the same text. Fonts are **self-hosted** (Plan 01 §7.3), with no Google Fonts links. |

---

## 9. Repo hygiene

- **Repo size:** about 50MB of WebP plus about 1MB of JSON at launch, growing by roughly 0.5MB per new drink. That's well within GitHub's limits for many years.
- **Image churn:** re-encoding unchanged photos would bloat git history. The Plan 05 image cache prevents it. Pin Pillow's version in `requirements.txt`, because a new encoder version could change every image's bytes. Run `--force-images` only on purpose, and say so in the commit message.
- **No secrets in the repo.** Authentication goes through `gh` and the Windows credential manager.

---

## 10. Decisions log

| # | Question | Owner's decision (2026-10-30) |
|---|---|---|
| Q1 | What happens to the old `Alcohol-Tasting-List` site | **Leave it as is.** Both sites stay live independently, and neither the shipper nor the build touches the old repos. |
| Q2 | How updates are published | **The owner checks manually** (build report plus local preview), then **tells the shipper to commit and push** (§5). No automatic publish script. |
| Q3 | Search engine indexing | **No:** link-only, with `noindex` on every page (§8). |
| Q4 | Plans in the public repo | **Keep them** in `Ship/plans/`. |
| Q5 | Custom domain | **None for launch.** The site lives at https://justin9598.github.io/Liquid-Assets/. |

---

## 11. Acceptance criteria

- [ ] `Ship/` is a git repo on `main`, connected to `Justin9598/Liquid-Assets`, with `.gitignore`, `.gitattributes`, `README.md`, `docs/.nojekyll` and `docs/404.html`.
- [ ] No `.xlsx` file, nothing from `Photos/`, `New/` or `reports/`, and no file over 10MB has ever been committed.
- [ ] Pages serves `main:/docs` over HTTPS at https://justin9598.github.io/Liquid-Assets/.
- [ ] `preview.bat` serves `docs/` locally, and the site works there exactly as on Pages, hash routes included.
- [ ] The shipper commits and pushes **only** when the owner asks. It refuses when the build has errors, the pre-push check fails, or there's nothing to publish, and it shows what will be committed first.
- [ ] Every page carries `noindex`, and there's no blocking `robots.txt`.
- [ ] After a publish, new data appears on the live site within about 10 minutes without a hard refresh (§7).
- [ ] All §6 smoke-test items pass on the live URL.
- [ ] `Alcohol-Tasting-List` and `Alcohol-Tasting-List-Source` are unchanged.

---

## 12. Phased launch: Phase 1 is the welcome page only (owner, 2026-10-31)

*The owner said: "Launch the site and ship till welcome page for now." That is the go-ahead for the §3 launch steps, with only the welcome page public.*

### 12.1 What Phase 1 publishes

| Part | Phase 1 |
|---|---|
| **Welcome page** | Live. The bar scene (v3 on desktop and landscape, v2 on phones until `bar-tall` arrives), the top shelf, shelf swaps by category, label-only bottle labels (Plan 01 §15.3), the status slate and the counter menu. |
| **Subcategory bottles** | Don't navigate. A click or tap shows a short message on the status slate, *"This shelf opens soon."*, for about 3 seconds. The bottle keeps its hover and focus feedback. In markup they're buttons, not links. |
| **Menu** | The Bar and the Shelves (each selects that category on the bar) stay. **The Makers** shows as plain text marked *"Soon"* and isn't a link. About stays. |
| **Other routes** | `#/<cat>/<sub>`, `#/drink/…`, `#/producer/…` and `#/makers` all go to the welcome page, with the category selected when there is one. No error pages. |
| **Published data** | Only what the welcome page needs: `shelf.json`, `build.json`, `glossary.json` (if used), the label images and the scene images. **Not published yet:** `drinks.json`, `drinks/`, `producers*`, card thumbnails and drink page photos. |

### 12.2 How it's switched

- `build.json` gets a `sections` object, for example `{ "welcome": true, "shelves": false, "drinks": false, "makers": false }`.
- The build option `--phase 1` sets the sections and writes only the outputs those sections need. The page code reads `sections` to decide whether bottles and the menu link out.
- **Phase 2 and later** turn sections on with no code changes: rebuild with the new phase, then commit and push as in §5.
- Leftover generated files from the full local build are deleted from `docs/` by the Phase 1 build, so they never reach the repo.

### 12.3 Launch run (shipper, with the owner's go-ahead above)

Work through these in order, and stop and report at the first failure:

1. Finish the open Plan 01 §15 task (wide plate plus label-only crops).
2. Implement §12.1–12.2, and build with `--phase 1`.
3. Check locally (preview) at 1440×900, 1920×1080 and 375×812:
   - The menu works, and bottles show "This shelf opens soon".
   - Deep links redirect to the welcome page.
   - The network log shows no requests for unpublished data.
   - The privacy scan and the dash audit pass.
4. **§3 steps 1–4:**
   - Repo files (already done).
   - Set up git in `Ship/`: `git init -b main` and add the `origin` remote for `Justin9598/Liquid-Assets`.
   - Run the §5.2 pre-push checks.
   - First commit.
   - Push using a credential helper for that command only: `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push -u origin main`. This uses the existing `gh` login **without changing the owner's global git config**. `gh auth setup-git` isn't needed.
   - Enable Pages (`main`, `/docs`, HTTPS) with `gh api`.
5. **§6 smoke test** on https://justin9598.github.io/Liquid-Assets/, adapted for Phase 1:
   - The welcome page loads with v3 on desktop.
   - Shelf swaps and the menu work.
   - Bottles don't navigate.
   - No 404s and no console errors.
   - `noindex` is present.
6. Report the commit hash, the live URL and the smoke-test results.

The old `Alcohol-Tasting-List` repos stay untouched (§10 Q1).

### 12.4 Launch record

- **Phase 1 went live on 2026-11-01** at https://justin9598.github.io/Liquid-Assets/.
  - Commit: `a38ac09` (257 files).
  - Pages: `main` `/docs`, HTTPS enforced.
  - The global git config is unchanged.
- **Designer check:**
  - No `.xlsx` file, nothing from `Photos/`, `Design/` or `reports/`, and no private markers in tracked files.
  - The live page renders the v3 plate at 1440×900, and the v2 scene on a 375px phone with no sideways scroll.
  - No console errors.
  - The old repos are untouched.
- **Known gaps, to close in later updates:**
  - Phones stay on v2 until `bar-tall` arrives.
  - The bottles are drawn shapes until the shells arrive.
  - The plate is below the target resolution.
  - The bottles are small because the plate's shelves are close together (clear height about 8–10% of the plate). Recheck when the plate is replaced.
