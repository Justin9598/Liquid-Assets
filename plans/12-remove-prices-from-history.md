# Plan 12: Remove prices from the GitHub history

Status: **Approved by the owner (2026-11-08): "Approve Plan 12".** The force-push in step 6 still needs a separate "push" from the owner. This rewrites the public repository's history and force-pushes it. That can't be undone once others have the new history, so it runs only on an explicit "approve" for this plan, and then a separate "push" for step 6.

## 1. Owner brief (2026-11-08)

> "plan to remove all prices from the github and live site"

## 2. Where things stand

| Place | Prices? |
|---|---|
| **Live site** (`docs/` at `be50022`) | **None.** Plan 11 is live. A designer check of the live data on 2026-11-08 found no `price` key and no `S$` amount. The Plan 11 privacy gate blocks any return. |
| **Current files on GitHub** (`main` at `be50022`) | **None.** The plan files were cleaned on 2026-11-08 (Plan 11 §4). |
| **GitHub history** | **Yes.** 13 of the repo's 15 commits hold prices: `docs/data/drinks/*.json` from the Phase 2 launch (`67a6dc5`) to `4fabd5a`, about 168 files per commit, plus the price examples in `plans/03` and the price columns in three update notes. Anyone can open an old commit on GitHub and read them. |

- **The repo has 0 forks** and one branch (`main`), with no tags.

## 3. Approach

Rewrite every commit so it carries no price, keeping everything else exactly as it was. Use **`git filter-repo`**, the tool the git project recommends for this.
- It isn't installed yet: `pip install git-filter-repo`, from PyPI. The owner's approval of this plan covers that install.
- **No hand edits of history and no other tool.**

### 3.1 The rewrite rules (path by path, using `--file-info-callback`)

| Paths | Rule |
|---|---|
| `docs/data/**/*.json` | Remove every `"price": <number or null>` member from visit objects, keeping the JSON valid and its key order and spacing otherwise unchanged. Remove any `S$<number>` text. |
| `plans/updates/*.md` | Drop the `Price (S$)` column from every Markdown table, handling escaped `\|` inside cells, and replace any `S$<number>` or `$<number>` amount with nothing. |
| `plans/*.md` | Replace `S$<number>` amounts and the example `"price": …` members. Generic words like "price" or `Price (S$)` as a column name stay. |
| Everything else | Unchanged. |

### 3.2 What stays the same

- **The current files:** the rewritten history's last commit must have a **tree identical to today's `be50022`**, because today's files already have no prices. If even one file differs, stop.
- **Commit messages, authors and dates** are unchanged. Commit IDs (hashes) do change. References to old hashes in plans and reports (for example "commit `743a4ad`") become stale. That's accepted and needs no edits.

## 4. Steps

Run by the shipper, except the push in step 6.

1. **Backup:** make a full mirror clone of the current GitHub repo into the private folder `Research/backups/repo-before-plan12-YYYY-MM-DD.git`. It keeps the old history, with prices, on the owner's PC only, in case anything goes wrong. It never goes back to GitHub.
2. **Rewrite in a scratch clone,** never in `Ship/` itself: a fresh mirror clone in the scratchpad, then `git filter-repo` with the §3.1 rules.
3. **Verify the rewrite:**
   - `git log -p --all` on the rewritten repo has **no** `"price": <number>`, no `S$<number>`, and no `Price (S$)` column with values in any version of any file.
   - The last commit's tree equals `be50022`'s tree (`git diff --stat be50022-tree new-tip` is empty).
   - Every rewritten commit's `docs/data` JSON still parses.
   - There are still 15 commits, with the same messages, in the same order.
4. **Report to the designer,** who reviews it.
5. **Owner approval for the push.** This is the point of no return.
6. **The designer force-pushes** the rewritten `main` with `git push --force-with-lease`, on the owner's word only.
7. **Re-point `Ship/`:** `git fetch`, then `git reset --hard origin/main`. Do it only after confirming `Ship/` has no uncommitted work. The files on disk don't change, because the trees are identical.
8. **Check:**
   - GitHub Pages rebuilds and the live site is unchanged. The four-size smoke test passes.
   - A sample of old commit URLs no longer shows prices. Their hashes no longer resolve.
   - `gh api repos/Justin9598/Liquid-Assets/forks` is still 0.

## 5. Limits to know

- **Cached copies:** GitHub can keep unreachable old commits viewable by their exact hash for a while, until its own clean-up. Anyone who already cloned the repo, or a web archive, keeps what they have. GitHub Support can be asked to purge cached views. That's optional, and the owner would file it.
- **Old builds:** the Pages deployment history in GitHub's interface lists old deploy hashes. Those builds aren't browsable as files.
- **The private backup** in step 1 still holds prices, on purpose. The owner can delete it once happy.

## 6. Keeping prices out from now on

- **A test:** the shipper adds a check that fails if any file in `plans/` has an `S$<number>` amount, or a `Price (S$)` table column holding values. It runs with the normal test suite before every commit.
- **The Plan 11 privacy gate** already covers `docs/data`.
- **Update notes** leave prices out (Plan 11 §4). Prices live only in the ledger and the private `Research/` proposals.

## 7. Acceptance

- [ ] The step 3 checks all pass, and the rewritten tip's tree is identical to `be50022`.
- [ ] After the push, no version of any file on GitHub's `main` history contains a price, and the live site is unchanged and passes the smoke test.
- [ ] `Ship/` points at the new history, with no uncommitted work lost.
- [ ] The §6 test is in place and passing.

## 8. Done (2026-11-08)

- **Backup:** `Research/backups/repo-before-plan12-2026-11-08.git` (15 commits, old tip `be50022`, private).
- **Rewrite:** `git filter-repo` with the §3.1 rules, plus one extra rule for amounts in `build/tests/*.py` comments.
- **Designer checks on the rewrite:**
  - 0 price matches across all history (the backup has 401).
  - The tip's tree is identical to the pre-rewrite tree.
  - All 17 commits keep their authors, dates and messages.
- **Force-pushed on the owner's word** ("Force-push it"), with `--force-with-lease` against `be50022`. GitHub's `main` went from `be50022` to `a0eeb3f`. `Ship/` was reset to it, with no work lost.
- **Hash map:** old `be50022` is new `20d4184`. The §6 test commits are `c6f6191` and `a0eeb3f`. Older hashes quoted in Plans 08 to 11 now refer to the old history.
