# Update 2026-10-31: photo matches confirmed from the old site

Status: **Approved by the owner** ("for the missing photos port them here and insert into the items if they are missing", 2026-10-31).
Applies to: `Ship/content/photo-map.json` (Plan 05 §5 S7). No ledger change, and no change to `Photos/`.

## What was found

- **The old site** (`Justin9598/Alcohol-Tasting-List`, read-only) publishes 189 photos named by drink ID. **17** of those IDs have no photo on the new site.
- **All 17 originals are already in `Photos/`,** at full resolution. They just don't match by name, which is why the build left them out.
  - Each was confirmed by comparing images: 14 are pixel-identical (correlation 1.00), and 3 were checked by eye (Against The Grain, Takezumi, Wufeng). On the old site those 3 are tighter crops of the same photo.
- **Nothing needs copying from the old site.** Its versions are small thumbnails (3–21KB, at most 195×480), and the originals in `Photos/` are much better.
- **The source repo** `Alcohol-Tasting-List-Source/Past Photos` (192 files) contains nothing that isn't already in `Photos/`.

## Photo-map entries to add (owner-approved)

| Drink ID | `front` (file in `Photos/`) |
|---|---|
| against-the-grain-normat-tokubetsu-junma | Against The Grain.jpg |
| ariiso-akebono-flat | Akebono Flat.jpg |
| hamada-ume-liqueur-gold-leaf | Ume Liquer with Gold Leaf.jpg |
| kenkonichi-junmai-ginjo-tejikuri | Kenkonichi Junmai Ginjo.jpg |
| kokushimuso-junmai-ginjo-kitashizuku | Kokushimuso Junmai Daiginjo Kitashizuku.jpg |
| komesou-brocken-splash-junmai-muroka-genshu | Aoki Kometo Junmai Natsusake Brocken Splash.jpg |
| kujira-junmai-yamadanishiki-kimoto-nama-genshu-80 | Kujira Jummai Yamadanishiki Kimoto nama Genshu 80.jpg |
| raikyo-phoenix-dancong-oolong-craft-sake | Raikyo Phoenix Dacong Oolong Craft Sake.jpg |
| sugata-junmai-daiginjo-yamadanishiki-40 | Sugata MNG JDG Yamadanishiki.jpg |
| taka-sparkling | Taka Sparkling.jpg |
| takezumi-bamboo-spring | Takezumi Bamboo Spring.jpg |
| tenmei-junmai-ginjo-hiire-black-label | Tenmei Junmai Ginjo Hiire Black Label (back label).jpg |
| tenranzan-natsu-junmai | photo_2_2026-08-01_10-34-59.jpg |
| wufeng-ji-qing | Wufeng Farmers Association Winery Ji Qing Sake.jpg |
| yamamoto-midnight-blue-junmai-ginjo | Yamamoto Midnight Blue Junmai Gingo.jpg |
| yokoyama-junmai-ginjo-silver-choukara7 | Yokoyama Junmai Ginjo.jpg |
| zaruso-hourai-junmai-ginjo-oringo-kudasai | Zaruso Hourai Junmai Ginjo Origokudasai Funabajiazume Muroka Namagenshu.jpg |

### Notes

- **Tenmei Hiire Black Label:** its only photo is a back label, and the old site also used it as the main image. It's mapped as `front` so the drink gets a photo. If a front photo turns up later, swap it in.
- **Exact duplicates, not to be attached:**
  - `photo_4_2026-08-10_12-42-23.jpg` is identical to the Aoki Kometo photo.
  - `photo_8_2026-08-10_12-42-23.jpg` is identical to `Yokoyama Junmai Ginjo.jpg`.

  Leave both unmatched. They'll stay in the W01 list, which is harmless. If the photo map supports an ignore list, put them there instead.
- **Label crops** use the default (Plan 01 §6.3). Check them on the contact sheet after the build.

## Expected effect

- Drinks without a photo go from 92 to **75**.
- Unmatched photos go from 38 to about **23**: 17 files are now used, and the 2 duplicates are still listed.
- **Ginjo** keeps its fallback label, because none of these 17 is a Ginjo. **Umeshu** (Liqueur) gets its first real label from HAMADA.
