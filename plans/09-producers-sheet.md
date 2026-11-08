# Plan 09: The Producers sheet (data task D2)

Status: **Approved by the owner (2026-11-02).** The owner answered every question in §9, recorded in §10.

Plan 05 task D2: research every producer and fill the `Producers` sheet that Plan 04 §8 defines, so maker pages get their Story, Facts and Related makers.

## 1. Where things stand

- **Code:** finished, so this is a data job.
  - The build already reads an optional `Producers` sheet (`build/liquid/ledger.py`, `producers.py`).
  - The producer page already draws the Story board, the Facts and Related makers when an approved row supplies them (`docs/assets/js/producer.js`).
  - The privacy check refuses to publish research from a `draft` row (E02 in `checks.py`).
- **Ledger:** has no `Producers` sheet yet. Core has **156 distinct `Producer` strings**, which the build turns into 155 pages today.
  - By country: Japan 136, South Korea 8, France 2, USA 2, Scotland 2, Chile 2, Taiwan 2, Vietnam 1, Singapore 1.
  - Every one currently raises W04 ("missing from the Producers sheet").
- **Already drafted:** 4 producer rows from the Fermenteria batch, in `Research/approved/2026-11-01-*.md` (Isekado, Minoh Beer, Nasu Kohgen Beer, Swan Lake Beer).

## 2. What a `draft` row already changes on the live site

The build uses some fields from **every** row, draft or approved:
- `Page Key`, which merges aliases into one page.
- `Display Name`.
- `Location` and `Region`.

So the sheet's **skeleton** (§3) changes page names, page addresses and merges as soon as it is built and pushed, even with every row still `draft`. That's why the skeleton gets its own approval, before any research.

The research fields (`Native Name`, `Brands`, `Founded`, `Master`, `Website`, `About`, `Related`, `Sources`) publish **only** when `Status = approved`.

## 3. Stage 1: the skeleton (one review, all producers)

The researcher drafts one row per distinct `Core.Producer` string. The exception is `Unknown`, which gets no row and no page (Plan 04 §2). Each row carries only:

| Column | How it's filled |
|---|---|
| `Producer` | The exact Core text, copied character for character. |
| `Page Key` | A slug of the Display Name plus the region where needed to tell two apart. It follows every case in Plan 04 §8.1: the two Asahi Shuzo pages, Dassai Blue, Date Seven merged, the Machida and Yamamoto merges, and bracketed brands. |
| `Display Name` | The clean name. A bracketed brand moves to `Brands`. |
| `Location`, `Region`, `Country` | Taken from Core (`Origin`, `Country`). Region must be one of the 47 prefectures for Japan. |
| `Status` | `draft` |

- **Review file:** `Research/pending/producers-00-skeleton.md` holds the full table, sorted by country, then region.
- **What the owner checks:** the page keys, the merges and the display names. The file lists all of them at the top, plus any page whose address changes from today's.
- **Entering it:** on the owner's approval, the researcher creates the sheet and enters the rows. This follows "Entering approved data into the ledger" in `.claude/agents/researcher.md`, with these additions:
  - The `Producers` sheet is created with the Plan 04 §8 headers in that exact order.
  - It gets a `Status` dropdown with `draft` and `approved`.
  - Its header row is frozen, and it gets an autofilter.
  - Rows run to row 400, matching the other sheets.
- **Afterwards:** the build should show **no W04**. Any W08 (aliases disagree on Region or Country) gets fixed before push.

## 4. Stage 2: research, in batches

### 4.1 Order and size (decided, §10 D1)

- **By country.** There are 8 batches:
  - **Japan:** 136 producers, in **7 batches of about 20**. They go in Core order of most drinks first, so the makers drunk most often improve first. The 4 Fermenteria producers already drafted join Japan batch 1, re-checked rather than entered unchanged.
  - **Everywhere else:** the 20 producers from South Korea, France, the USA, Scotland, Chile, Taiwan, Vietnam and Singapore, together in **one final batch**. The researcher sources these in the right language, using official sites in Korean or French where needed.
- **Review time:** about 15 to 20 minutes per batch.

### 4.2 What the researcher fills, per producer

| Field | Rule |
|---|---|
| `Native Name` | Kanji or hangul, **only** from an official source or the label. |
| `Brands` | The brand names the drinks are sold under, comma-separated. These feed search. |
| `Location` | Refined to town and prefecture when the official site gives it (for example `Iwakuni, Yamaguchi`). |
| `Founded` | A year, with a source. If sources disagree, leave it blank and list the conflict. |
| `Master` | Only if the brewery publishes the tōji's or master's name. Otherwise blank. |
| `Website` | The official site only, `https`, no shop or social links unless the brewery has no site. |
| `About` | 2 or 3 short paragraphs, 60 to 120 words in total. See §4.3. |
| `Related` | `key:relationship` pairs, set **both ways** (for example `asahi-shuzo-yamaguchi:parent company` on Dassai Blue, and `dassai-blue:sister brewery` on Asahi Shuzo). Only between producers that are in the ledger. |
| `Sources` | Every URL the row's facts came from, separated by semicolons. Official site first. |

### 4.3 About text: writing rules

- **Content:** factual and plain. Say where they are, when they started, what they're known for, and what's distinctive about how they make it (water, rice, method, people). End on something specific, not a slogan.
- **Voice:** the site's existing voice. No marketing words ("finest", "passion", "world-class"), and no em or en dashes, matching the site's taste rules.
- **Copyright:** written fresh from the sources. **Never copied or lightly reworded** from the brewery's own text, or anyone else's.
- **Privacy:** nothing about the owner. Their visits belong to the drinks, not the maker.
- **Unsure facts:** if a fact can't be sourced, leave it out. A short accurate About beats a long padded one.
- **Little information:** when a small maker has almost nothing online, give one paragraph with what is known, or leave `About` blank and say so in the review file.

### 4.4 Review file and approval

- **File:** each batch is one file, `Research/pending/producers-NN.md`. For each producer it shows:
  - the row as it will be entered,
  - the About text as it will read,
  - a sources table (field, value, URL, confidence),
  - conflicts and gaps.
- **Summary table:** the top of the file lists every producer in the batch with a confidence mark, so weak rows stand out.
- **Approving:** the owner approves the batch in chat, naming any exceptions (for example "approve batch 1 except Ryujin Shuzo, fix its founding year").
- **Entering:** the researcher applies the corrections, moves the file to `Research/approved/`, and enters the research into the existing skeleton rows.
  - It sets `Status = approved` on the approved rows.
  - Held-back rows stay `draft` with their research fields **left empty**, so unapproved text never sits in the ledger.
  - This step only **fills** cells in existing Producers rows. It never changes `Producer`, `Page Key` or `Display Name` from Stage 1 unless the owner asks.

## 5. Publishing each stage

Each stage and batch follows the Plan 06 §4 routine:

1. The owner approves.
2. The researcher enters the rows.
3. The owner runs `build.bat` and `preview.bat`.
4. The owner tells the shipper to commit and push.

The permission system blocks the shipper's push, so whoever the owner names pushes, on the owner's word. A batch is pushed on its own. It isn't held until all 8 are done.

**After batch 1, the shipper checks** one full producer page (Story, Facts with website and founding year, Related makers) at the four sizes. The Plan 08 chalkboard look has only been seen with Core-only producer pages, so this is the first test with full data. Anything that breaks the layout (a long native name, a long website address, 3 paragraphs on a phone) goes back to me as a small fix plan. It isn't patched on the spot.

## 6. Faults to guard against

| Risk | Guard |
|---|---|
| A page address changes and an old link breaks | The skeleton review file lists every page key that differs from today's. Plan 04's router already sends unknown producer keys to the Makers index, so the link lands somewhere useful. |
| The same name refers to two different makers | §8.1 cases are handled by name. The researcher also flags any new same-name pair it finds in the review file. |
| An `About` copies the source | The researcher writes from notes, not from the page. The designer spot-checks 3 per batch against their first source. |
| The year or a name is wrong | Every fact has a URL. Conflicts leave the field blank, and the owner sees the confidence column. |
| A draft's research leaks | The build already refuses with E02. Draft rows also keep research fields empty (§4.4). |
| The Fermenteria drafts go stale | They're re-checked as part of batch 1, not entered unchanged. |

## 7. Acceptance

- [ ] Stage 1: the sheet exists, has one row per Core producer string except `Unknown`, and the build shows no W04 and no W08.
- [ ] Every page key on the skeleton review list matches what the owner approved.
- [ ] After each batch, the approved rows show a Story, the Facts and Related makers on the live page, and the draft rows publish nothing beyond name, location and drinks.
- [ ] The phrases "finest", "passion", "world-class", and any em or en dash, appear in no published About (the shipper adds a build check, W22, for this as part of batch 1).
- [ ] The batch 1 four-size producer page check passes.

## 8. Effort

- Stage 1 is one researcher run plus one owner review.
- Each batch is one researcher run, about an hour of web research, then the owner's review, about 15 to 20 minutes for 20 producers.
- 8 batches in all: 7 for Japan, then 1 for everywhere else. Batches can run one after another without waiting for the previous one's push.

## 9. Questions for the owner

| # | Question | Recommendation |
|---|---|---|
| Q1 | Batch size and order | 20 per batch, most-drunk makers first |
| Q2 | How you approve | In chat, the whole batch at once, naming any exceptions |
| Q3 | Tōji or master brewer names | Only when the brewery publishes them |
| Q4 | About length | 2 or 3 short paragraphs, 60 to 120 words |

## 10. Decisions log

| # | Decision | Answer (2026-11-02) |
|---|---|---|
| D1 | Batch size and order (Q1) | **By country:** Japan in 7 batches of about 20, most drunk first, then all non-Japanese makers in one batch. |
| D2 | How the owner approves (Q2) | **In chat**, the whole batch at once, naming any exceptions. |
| D3 | Tōji or master brewer names (Q3) | **Only when the brewery publishes them.** |
| D4 | About length (Q4) | **2 or 3 short paragraphs, 60 to 120 words.** |
| D5 | Machida merge (skeleton Q1) | **`machida-shuzoten`**, shown as "Machida Shuzoten" (町田酒造店, the company name), with "Machida Shuzo" in Brands. This replaces Plan 04 §8.1's `machida-shuzo`, and keeps the address of the 3-drink page. |
| D6 | The rest of the skeleton (Q2 to Q7) | **Approved as recommended.** 3 merges, giving 151 pages. Display names Hakushika, RiceWine K.K. and Isekado. Odd spellings (Omoyashuzo, Katoukichibee Shoten) wait for Stage 2. Region is the part after the comma for "town, region" origins. The other old addresses go to the Makers index. |
| D7 | Founded when there are two years (batch 1 Q5) | **The first year the business made drinks** (Isekado 1997, Mikotsuru 1912, Minoh 1997). Older family roots and revivals go in the About. |
| D8 | Related to a partner still in `draft` (Q2) | **Link now.** The partner's page already exists. The reverse link is added in the partner's own batch. |
| D9 | The brewery spells its name differently (Q7) | **Keep the Display Name and Page Key.** Put the brewery's own spelling in `Brands` so search finds it (Huchu Homare, HATSUMOMIDI). |
| D10 | Japan batch 1 (2026-11-02) | **Approved, all 20 rows.** Ties for the last places are broken alphabetically by Page Key. Isekado's Master stays blank, because no romanisation is published. Iinuma keeps 1811. Strict Related rules (Q3). About paragraphs are separated by a blank line inside the cell, which `_paragraphs()` already splits on. |
| D11 | Japan batch 2 (2026-11-03; researched on Sonnet) | **Approved, all 20 rows.** Date Seven publishes with Founded and Website blank. Obuse Winery Founded 1942 (D7), with the 1842 sake history in the About. Instagram links count as Website for Puku Puku and Fermenteria, because they have no site (§4.2). Hiraroku's owner-brewer goes under Master. Romanised brand names (Mitsugo, Fuji Chitose, Mancho) are kept for search. Fuji Shuzo keeps 1778, on four agreeing sources. |
| D12 | A maker with no web presence (Akiu Heart Rock Sake) | **Publish from the label photos.** It gets a short About of what the labels state, with Founded, Master and Website left blank. A label photo counts as a source. |
| D13 | Japan batch 3 (2026-11-03) | **Approved, adjusted.** Website is blank for Noguchi Naohiko and Ryujin, because neither site loads for the researcher or the designer; add them later if they return. Aramasa uses `http://aramasa.jp/`: https fails its certificate check, http works. Ozawa's Founded is blank (only one weak source) and the rest of the row publishes. Naohiko Noguchi is named as Master. RiceWine Founded is 2019 (D7). |
| D14 | A Display Name that misreads the brewery's name | **Fix the Display Name and keep the Page Key.** `banno-shuzo` displays as "Tomono Shuzo" (伴野酒造), and its address doesn't change. Core's Producer text stays as the owner wrote it. A rule for later batches: only owner-approved name fixes change a Display Name. |
| D15 | Rule for websites | **Publish only a website that the researcher has loaded and confirmed as official.** A site listed only by a database, or one that doesn't load, is left blank. |
| D16 | Hirako Shuzo's website (2026-11-03) | **The owner chose to keep it.** `https://www.hirakoushuzou.jp/` loads as a blank page for both the researcher and the designer, but it stays published as an owner-approved exception to D15. |
| D17 | Japan batch 4 (2026-11-03) | **Approved.** `hamada-shoten` displays as "Hamada": the maker is 株式会社濱田, confirmed from the bottle label (濱田, 紀州石神). `katoukichibee-shoten` displays as "Kato Kichibee Shoten", with the brewery's own "Katoukichibee Shouten" in Brands. Page Keys are unchanged (D14). Iinuma Honke's Founded is blank. Gyokusendo's 無風 reading is dropped from Brands. Kameizumi's and Kato Kichibee's websites are kept, because their home pages load (D15). Miho Imada and Shinji Kawabata are Masters, romanised on the official sites. |
| D18 | New makers from the 2026-11-07 batch (owner approved) | Hara Shuzo: skeleton plus research, `approved`. Azumatsuru Shuzo, Carlsberg and Kronenbourg: skeleton only, `draft`. See `updates/2026-11-07-omu-nomu-space-box.md`. |
| D19 | New makers from the 2026-11-08 batch (owner approved) | Heiwa Shuzo, Wakanoi Shuzo, Shindo Shuzoten and Eikun Shuzo: skeleton only, `draft`. See `updates/2026-11-08-shu-kuu-sakanahikaru.md`. |
| D20 | Japan batch 5 (2026-11-08, owner approved) | **Approved, adjusted.** `moriki-shuzojo` displays as "Moriki Shuzo" (森喜酒造; key unchanged, D14). Konohana Brewery keeps its name, with "Konohanano Brewery" in Brands (D9). Kubiki Founded is 1697, when the family began brewing (D7). Koueigiku's Instagram counts as its Website (D11). `koshi-meijo` is held back as `draft` with its research left empty (its About is 55 words, under D4's 60). No Moriki to Shinkame Related link (the strict rule). |
| D21 | Japan batch 6 (2026-11-08, owner approved) | **Approved, adjusted.** `omoyashuzo` displays as "Omoya Shuzo" (key unchanged, D14). Suntory's Website is `https://www.suntory.com/` as an owner exception to D15: it returns 403 to automated checks but is plainly official, as with D16. Koshi Meijo, now 120 words, publishes with Founded 1845. Shinshu Meijo's Founded is blank (1834 and 1835 conflict). Azumatsuru uses `http://azumatsuru.com/` (as D13). |
| D22 | Japan batch 7, the last Japanese batch (2026-11-08, owner approved) | **Approved, adjusted.** Yamawa's Website is `https://www.yamawa-syuzouten.co.jp/`: the designer loaded it in a browser, and its title is 山和酒造店 in Kami, Miyagi (D15 met). It also links `date-seven:Date Seven member`. Wakakoma's site publishes although it shows a maintenance notice with the company name and address. `tajime-shuzo` displays as "Tajime Gomei" (田治米合名, key unchanged, D14) and publishes from its newspaper and importer sources, with no Founded or Website. Suigei's Founded is blank (three years on its own site). |
| D23 | Non-web entries in Sources (2026-11-08, owner approved) | **The Sources cell holds web addresses only.** A label citation stays in the private review file, because the page shows a non-URL source as a dead "source N" link. The two label notes on `yamawa-shuzoten` and `wakanoi-shuzo` were removed. |
| D24 | Batch 8, outside Japan, the final batch (2026-11-08, owner approved) | **Approved, adjusted.** Regions stay as the skeleton has them (Copenhagen, Strasbourg, Paris, Bordeaux). A named head winemaker counts as Master (D3), for Santa Helena and Casa Silva. The MÙA and Heiwa Shuzo partner link is set both ways (`partner brewery`), adding to the approved Heiwa row. There's no Orchid and Konohana mentor link (one source only). Isibo's holding-page Website is kept (as with Wakakoma). Carlsberg uses `carlsberggroup.com`. Daejeon Blues keeps its name. The four label-only Korean makers publish from their labels (D12). Dassai Blue links `asahi-shuzo-yamaguchi:parent company`, and Carlsberg and Kronenbourg link each other. |

## 11. Batch 1 review fixes (2026-11-02)

The shipper's four-size check of the first full maker pages (Akebono Shuzo, Swan Lake Beer and Machida Shuzoten) found four faults. Screenshots are in `reports/phase2/producer-*.png`. The W22 check, the W22 to W23 renumbering of the seasonal-pin warning, and the 20 approved rows are all fine.

### 11.1 The Story is always one paragraph (build fault)

- **Cause:** `ledger.py` runs `clean()` on every cell when it loads the sheet (line 101). That collapses whitespace, so the `\n\n` between paragraphs is gone before `_paragraphs()` in `producers.py` sees it. The ledger cells are correct.
- **Fix:**
  - For multi-paragraph text columns, keep the line breaks. Normalise each line (trim, collapse runs of spaces, NFC), keep `\n`, and reduce three or more newlines to two.
  - The columns are `Producers.About`, plus `Public Notes` and `Visit Note` when they arrive (Plan 05 §7). Declare them in one list so later columns join it.
  - Every other column keeps today's `clean()`.
- **Check:**
  - A unit test: a cell with two paragraphs produces two `about` entries.
  - The real build: `akebono-shuzo.json` has 3 paragraphs, and every approved maker has 2 or 3.
  - W22 still passes. Its word count runs across all paragraphs.

### 11.2 The Japanese name breaks mid-word on phones

- **Fault:** at 375 and 390 the native name wraps inside the word: "スワンレ / イクビール", "町田酒 / 造店".
- **Fix:**
  - **Never break inside a native name.** It is one unit with `white-space: nowrap`.
  - **Below 768px, it gets its own line** under the English title, at about 60% of the title size, aligned left.
  - **At 768px and up** it stays beside the title, wrapping to its own line as a whole when there's no room.
  - **If a native name is still wider than the board** on its own line, its font steps down until it fits, to no less than 18px. It never wraps or overflows.
- **Check:** the smoke test confirms that the native name's box is a single line at all four sizes on `swan-lake-beer` and `machida-shuzoten`.

### 11.3 The Facts board is squeezed beside the Story on desktop

- **Fault:** at 1440×900 on Akebono, the Facts board shares a row with the Story, and its map takes the right half. The text column is left so narrow that:
  - "The Facts" wraps to two lines;
  - the location wraps;
  - the website breaks inside its host name ("akebono- / syuzou.com").
- **Fix:**
  - **Container query:** the Facts board lays itself out by its own width, not the screen's. When its inner width is under 560px, the map goes **below** the facts list at full board width, capped at 260px tall. That's the same arrangement as on phones.
  - **Board headings never wrap:** `white-space: nowrap` for "The Facts", "The Story" and the rest.
  - **The website link never breaks inside the host.** It shows the host only (as today). If even that doesn't fit, it's cut off with an ellipsis, and the full link stays in `title`.
  - **Label column:** the facts list keeps the label column at a fixed width, about 9em, and the value column gets the rest. A value may wrap between words, never mid-word.
- **Check:** the smoke test confirms, at all four sizes on the three pages, that:
  - "The Facts" is one line;
  - the website link is one line with no overflow;
  - no fact value breaks inside a word.

### 11.4 The Sources line repeats the same site

- **Fault:** Akebono shows "akebono-syuzou.com" three times, then "sakenowa.com".
- **Fix:**
  - **Group by host.** Each host appears once, in source order (official site first), linking to its first URL. This is a display-only change in `producer.js`.
  - The full source list stays in the ledger, and in the data as it is today.
- **Check:** Akebono shows "Sources: akebono-syuzou.com · sakenowa.com".

### 11.5 Acceptance

- [ ] §11.1 to §11.4 each pass their check, with screenshots retaken for the three pages at the four sizes, into `reports/phase2/producer-<key>-<size>.png`.
- [ ] The full test suite passes, including the new checks.
- [ ] The build has 0 errors and 0 W22. 20 makers publish research and 131 publish none.
- [ ] Then commit as in the batch 1 brief (Plan 06 §5.2 checks, message "Ledger update 2026-11-02: maker stories for Japan batch 1 (20 producers), W22 about-text check", `Co-Authored-By: Claude Opus 5.5`). **No push.** The designer pushes on the owner's word.
