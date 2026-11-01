# Update 2026-11-01: Fermenteria batch (9 drinks)

Status: **Approved by the owner** (2026-11-01). Researched by the `researcher` agent. The full proposals, with sources and the draft Public Notes text, are in the private folder `Research/approved/2026-11-01-*.md`.

All 9 come from one visit to **Fermenteria by Sake Mama** on 2026-11-01:
- Three free sake tastings (60ml, no price).
- Six beers the owner bought.

## 1. Ledger changes, in this order (owner)

1. **New Size value:** add `Pint` to the Size dropdown list on `Core!D2:D400` and `New Entry!D2:D400`. The 5 tap beers use it.
2. **Core rows:** 9 new rows, in the table below. Leave `Notes` empty. `Public Notes` and `Visit Note` go in once those columns exist (Plan 05 §7). Until then, keep the Public Notes text in the proposal files.
3. **Detail rows:** 2 `Sake Detail` rows and 6 `Other Detail` rows, below.
4. **Producers:** 4 new producers have draft rows in their proposals (Isekado, Minoh Beer, Nasu Kohgen Beer, Swan Lake Beer). Add them when the `Producers` sheet is created (Plan 04 §8), with `Status = draft`.

### Core rows

| ID | Name | Category | Size | ABV % | Producer | Origin | Country | Acquired | Bought From |
|---|---|---|---|---|---|---|---|---|---|
| yamamoto-sunset-orange-junmai-ginjo | Yamamoto Sunset Orange Junmai Ginjo | Sake | 60ml Tasting | 14 | Yamamoto Shuzoten | Akita | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| oze-no-yukidoke-junmai-daiginjo-halloween | Oze no Yukidoke Junmai Daiginjo Halloween | Sake | 60ml Tasting | 15 | Ryujin Shuzo | Gunma | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| hagi-no-tsuru-betsu-shikomi *(repeat, existing ID)* | Hagi no Tsuru Betsu-shikomi | Sake | 60ml Tasting | 15 | Hagino Shuzo | Miyagi | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| underwater-luminous-sake-yeast-beer | Underwater Luminous Sake Yeast Beer | Beer | 350ml Can | 6 | Nara Brewing Co. | Nara | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| nara-eighty-eight | Nara Eighty Eight | Beer | Pint | 6 | Nara Brewing Co. | Nara | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| minoh-hoppy-weizen | Minoh Hoppy Weizen | Beer | Pint | 5 | Minoh Beer | Osaka | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| nasu-kohgen-ai | Nasu Kohgen Ai | Beer | Pint | 5 | Nasu Kohgen Beer | Tochigi | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| swanlake-amber-swan-ale | Swanlake Amber Swan Ale | Beer | Pint | 5 | Swan Lake Beer | Niigata | Japan | 2026-11-01 | Fermenteria by Sake Mama |
| isekado-mr-dank | Isekado Mr. DANK | Beer | Pint | 7 | Isekado | Mie | Japan | 2026-11-01 | Fermenteria by Sake Mama |

Style(s), Rating and Favourite are empty on every row.

### Sake Detail rows

| ID | Grade | Milling % (RPR) | Rice | Yeast | SMV | Acidity |
|---|---|---|---|---|---|---|
| yamamoto-sunset-orange-junmai-ginjo | Junmai Ginjo | 55 | Miyamanishiki | Kyokai No.6 | | |
| oze-no-yukidoke-junmai-daiginjo-halloween | Junmai Daiginjo | 50 | | | | |

Hagi no Tsuru gets no detail row, because it's a repeat and the label gives no grade.

### Other Detail rows

| ID | Base | Flavouring or Botanicals | Yeast | Type |
|---|---|---|---|---|
| underwater-luminous-sake-yeast-beer | Pilsner malt | No hops; sugar, lactose, lactic acid water, malic acid | Sake yeast (Kaze no Mori, Yucho Shuzo) | Specialty |
| nara-eighty-eight | Pilsner malt (all Japanese-grown, 2026) | Shinshu Wase hops; first-flush tencha green tea | Saison yeast | Saison |
| minoh-hoppy-weizen | Wheat and barley malt | Nelson Sauvin hops | Weizen yeast | Wheat |
| nasu-kohgen-ai | | | | Lager |
| swanlake-amber-swan-ale | Caramel malt | American hops | | Pale Ale |
| isekado-mr-dank | Barley malt | Strata, Citra, Mosaic (double dry-hopped); Incognito in the whirlpool | | IPA |

## 2. Photos (done by the designer at the owner's request)

All 13 inbox photos were moved from `New/` to `Photos/`, byte-identical. `New/` is now empty.
- **Drink photos:** front and back labels for Underwater Luminous, Yamamoto Sunset Orange and Oze no Yukidoke, plus a front photo each for Minoh, Nara Eighty Eight, Nasu Kohgen Ai and Swanlake.
- **Reference only:** two Hagi no Tsuru tasting shots and `Fermenteria by Sake Mama menu 2026-11-01.jpg`. Their names deliberately don't match a drink, so they're never shown.
- **Isekado Mr. DANK has no photo.**

## 3. Effect on the site

- **Sake shelf:** Junmai Ginjo goes from 74 to 75 drinks, and Junmai Daiginjo from 48 to 49. Hagi no Tsuru gains a second visit.
- **Beer shelf:** goes from 1 bottle to 7. Six drinks now have a style, but the 2 older beers don't. Under the mixed-category rule (Plan 01 §4), the shelf shows these bottles in the §4.4 list order: **Lager · Pale Ale · IPA · Wheat · Saison · Specialty · Other beer** (the last holds Under 15M and the original Underwater).
  - Filling `Type` for those 2 beers removes the "Other beer" bottle. The original Underwater is probably Specialty.
- **Labels:**
  - The four beer photos show glasses, not labels, so the label-only rule (Plan 01 §15.3) will probably skip them. Those style bottles then use the illustrated fallback label.
  - The Underwater Luminous can should qualify, since printed cans count as labels.
  - The two new sakes have proper labels.
- **Phase 1:** only the welcome page is public (Plan 06 §12), so these drinks show up as bottles and counts on the shelves. Their own pages arrive in a later phase.
- **No code changes needed.**

## 4. Publishing

After the ledger rows are in and Excel is saved and closed:
1. Run `build.bat` with `--phase 1`, and check the report. The label contact sheet should cover the new photos, and the skip list should show which beer photos were skipped.
2. Run `preview.bat` and check the Beer and Sake shelves.
3. Tell the shipper to commit and push (Plan 06 §5.2).
