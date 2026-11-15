# Update note: the 2026-11-15 batch (gifts, Mirai Sake Hall, Sake Mama, Jeju)

Status: **The owner approved the proposals (2026-11-15).** The researcher entered the rows (backup `Research/backups/Drinks Ledger 2026-11-15 1344.xlsx`), and the photos are moved into `Photos/`. This note is for the shipper's data update. No push without the owner's word.

## 1. What changed in the ledger

- **Core, 11 new rows (317–327):**
  - **9 new drinks:**

    | ID | Category |
    |---|---|
    | `kiku-masamune-hoken-junmai-ginjo` | Sake |
    | `rachelle-the-rabbit-chrysanthemum-mead` | Wine |
    | `fijian-sea-snake-contemporary-gin` | Spirit |
    | `kagura-mitsugo-kabosu-japanese-pepper` | **Liqueur**, the first row in this category |
    | `koshinohomare-qn-miton-junmai-muroka-genshu` | Sake |
    | `yoshidagura-u-night-and-dance-improvisation-2-0-united-arrows` | Sake |
    | `gardians-riz-fermente-sec` | Craft Sake |
    | `hagi-no-tsuru-junmai-daiginjo-miyamanishiki-singapore-kuroneko` | Sake |
    | `jeju-beer-barrel-series-blueberry-stout` | Beer |

  - **2 repeat occasions:** `kubota-senju-ginjo` and `yoshidagura-u-night-and-dance-junmai`.
- **Detail sheets:**
  - Sake Detail: 5 rows.
  - Other Detail: 3 rows (gin, Kagura, Jeju stout).
  - Wine Detail: 1 row (the mead, Colour empty).
- **Producers, 3 new rows,** all `draft` with coordinates:
  - Rachelle the Rabbit Distillery (Singapore)
  - **Vodco Pacific (Fiji, a new country)**
  - Le Guishu (France)
- **Validation lists:** `Liqueur` was added to Category, and `710ml Bottle` to Size.

## 2. Photos (already in `Photos/`)

The owner's move put 30 files in place. Fronts are named exactly as each drink's Name, with ` (back label)`, ` (side label)` and ` (second photo)` for extra views. The files cover:

- **The new drinks:** each has a front and a back, except the Jeju stout, which has a **back label only**. It will show its shell until a front exists. That's expected, not a fault.
- **First photos** for Kubota Senju, Night & Dance Junmai, `dassai-blue-type-50-junmai-daiginjo` and `ichigoya-hana-strawberry-doburoku`.
- **Second photos** for Dio Abita, Haccoba Jam, Sugata and Kinoene.

## 3. Knock-on work for the shipper

1. **Fiji map (E08):**
   - add Fiji to `COUNTRIES` in `build/tools/makemaps.py`;
   - give it the region and continent the world map already uses for Oceania (Australia/Oceania), or add Oceania if none exists;
   - rerun the tool, reading the Natural Earth files from `Research/mapdata/`.

   Fiji crosses the 180° meridian, so check that the country file and the world drawing don't smear across the map. Shift its longitudes so the islands stay together.
2. **Liqueur:** the first Liqueur row turns on the Liqueur category. Check:
   - that its shelf appears on the welcome page and the shelf page;
   - that Kagura Mitsugo's `Other Detail.Type` is valid for Liqueur, with no W03. If it's invalid, report it rather than editing the ledger.
3. **Label crops (Plan 13 §3):** make and check crops for every new front photo in §2, using the check step. Owner-set crops are never overwritten.
4. **Bottle shells:** add these to `content/bottles.json` (Plan 15 §4.1). The designer picked them from the photos:

   | ID | Shell |
   |---|---|
   | `kiku-masamune-hoken-junmai-ginjo` | `sake-green` |
   | `kubota-senju-ginjo` | `sake-brown` |
   | `koshinohomare-qn-miton-junmai-muroka-genshu` | `sake-green` |
   | `yoshidagura-u-night-and-dance-improvisation-2-0-united-arrows` | `sake-clear` |
   | `yoshidagura-u-night-and-dance-junmai` | `sake-black` |
   | `gardians-riz-fermente-sec` | `sake-cobalt` |
   | `hagi-no-tsuru-junmai-daiginjo-miyamanishiki-singapore-kuroneko` | `sake-green` |
   | `dassai-blue-type-50-junmai-daiginjo` | `sake-black` |
   | `ichigoya-hana-strawberry-doburoku` | `sake-frosted` |
   | `rachelle-the-rabbit-chrysanthemum-mead` | `spirit-clear` (a squat clear bottle; the Wine default would wrongly give a red wine bottle) |
   | `kagura-mitsugo-kabosu-japanese-pepper` | `sake-green` (a tall green bottle; the Liqueur default is amber) |

   The gin and the Jeju stout keep their defaults (`gin`, `beer-bottle`).
5. **Tests:** update `test_real_counts` to the new drink count. The ledger has 298 drinks now; confirm the exact number from the build.
6. **Build and checks:**
   - the full pytest passes;
   - the build has **0 errors**;
   - the privacy scan is clean;
   - the smoke checks pass.

   Also check that no Notes, prices or original filenames appear in `docs/`.
7. **Screenshots** in `reports/updates/2026-11-15/`:
   - the welcome page (1440×900 and 390×844);
   - the drink pages for Kagura Mitsugo, the gin and Gardian's;
   - the Makers map at the world level (Fiji's pin);
   - the Vodco Pacific maker page (its map).
8. **Commit:** "Data: 2026-11-15 batch (gifts, Mirai Sake Hall, Sake Mama, Jeju)". **No push.**
