"""S11 Report: reports/build-report.html (local only, never published)."""
from __future__ import annotations

import html
import os
import urllib.parse
from pathlib import Path

from .photos import PHOTO_EXT

CODE_TITLES = {
    "E01": "Cannot read the ledger", "E02": "Privacy leak in output", "E03": "Broken reference",
    "E04": "Schema violation", "E05": "Image could not be processed",
    "W01": "Photo not matched to any drink", "W02": "Drink has no front photo",
    "W03": "Other Detail Type not valid for the category", "W04": "Producer missing from Producers sheet",
    "W05": "Japanese Region is not one of the 47 prefectures", "W06": "Rows sharing an ID disagree",
    "W07": "Unknown Core.Category", "W08": "Alias rows disagree", "W09": "Sake grade not in the validation list",
    "W10": "Category falling back to a single bottle (Type unfilled)", "W11": "Detail row with no matching Core ID",
    "W12": "Count dropped sharply since the last build", "W13": "Optional ledger column or sheet missing",
    "W14": "Ledger is open in Excel", "W15": "Value could not be parsed", "W16": "photo-map entry for an unknown drink",
    "W17": "Duplicate row", "W18": "Related maker not found", "W20": "Content file missing", "W22": "Seasonal pin names an unknown drink",
    "I01": "Empty subcategory hidden", "I02": "No rendered scene images yet", "I03": "Label skipped (not used on bottles)", "W21": "Front photo has no label judgement yet",
}

CSS = """
body{font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:24px auto;max-width:1200px;padding:0 16px;color:#2a1d14;background:#faf6ee}
h1{margin:0 0 4px}h2{margin-top:36px;border-bottom:2px solid #c9a24a;padding-bottom:4px}
table{border-collapse:collapse}td,th{padding:3px 12px 3px 0;text-align:left;vertical-align:top}
.err{color:#9b1c1c;font-weight:600}.ok{color:#2c6b2f;font-weight:600}.muted{color:#6b5a4a}
details{margin:8px 0;background:#fff;border:1px solid #d8ccb3;border-radius:6px;padding:6px 12px}
summary{cursor:pointer;font-weight:600}li{margin:2px 0}
.sheet{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.cell{background:#fff;border:1px solid #d8ccb3;border-radius:6px;padding:8px;font-size:13px}
.cell .imgs{display:flex;gap:8px;align-items:flex-start}.cell img{border:1px solid #ccc;background:#eee}
.orig{width:110px;height:auto}.crop{position:relative;display:block;line-height:0}.crop i{position:absolute;border:2px solid #e8351e;box-sizing:border-box}.lab{width:160px;height:auto}.thm{width:90px;height:120px;object-fit:cover}
.inbox{display:flex;flex-wrap:wrap;gap:10px}.inbox figure{margin:0;width:140px;font-size:12px}
.inbox img{width:140px;height:140px;object-fit:cover;border:1px solid #ccc}
code{background:#f0e8d6;padding:1px 4px;border-radius:3px}
"""


def e(text):
    return html.escape(str(text if text is not None else ""))


def _rel(target: Path, start: Path) -> str:
    rel = os.path.relpath(target, start).replace("\\", "/")
    return "/".join(urllib.parse.quote(part) for part in rel.split("/"))


def write_report(reports_dir, root, drinks, shelf, photo_map, suggestions, unmatched, issues, state, previous,
                 photos_dir, new_dir, summary, check, extras=None):
    reports_dir = Path(reports_dir)
    docs = Path(root) / "docs"
    out = []
    add = out.append
    counts = summary["counts"]
    errs = issues.errors
    add(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Liquid Assets build report</title>"
        f"<style>{CSS}</style></head><body>")
    add("<h1>Liquid Assets build report</h1>")
    add(f"<p class='muted'>Ledger last saved {e(summary['generated'])}"
        f"{' · check only: nothing was written to docs/' if check else ''}</p>")
    status = (f"<span class='err'>{len(errs)} error(s): the site was NOT updated</span>" if errs
              else "<span class='ok'>0 errors</span>")
    add(f"<p>{status} · {len(issues.warnings)} warning(s)</p>")

    # 1. summary
    add("<h2>1. Summary</h2><table>")
    add(f"<tr><th>Drinks</th><td>{counts['drinks']}</td></tr>")
    for name, n in counts["categories"].items():
        add(f"<tr><td class='muted'>&nbsp;&nbsp;{e(name)}</td><td>{n}</td></tr>")
    if counts["unshelved"]:
        add(f"<tr><td class='muted'>&nbsp;&nbsp;Not on any shelf</td><td>{counts['unshelved']}</td></tr>")
    add(f"<tr><th>Producer pages</th><td>{summary['producers']}</td></tr>")
    add(f"<tr><th>Photos</th><td>{summary['photos_total']} files · {summary['photos_matched']} matched · "
        f"{summary['photos_unmatched']} unmatched</td></tr>")
    add(f"<tr><th>Drinks without a front photo</th><td>{summary['drinks_without_photo']}</td></tr>")
    st = summary["images"]
    add(f"<tr><th>Images</th><td>{st['encoded']} encoded · {st['skipped']} unchanged · {st['deleted']} deleted</td></tr>")
    add("</table>")
    add("<h3>Subcategories</h3><table>")
    for c in shelf:
        for s in c["subs"]:
            add(f"<tr><td>{e(c['name'])} / {e(s['name'])}</td><td>{len(s['drinks'])}</td></tr>")
    add("</table>")
    add("<h3>Changes since the last build</h3>")
    if previous:
        old = previous.get("drinks", {})
        new = state["drinks"]
        added = [new[i] for i in new if i not in old]
        removed = [old[i] for i in old if i not in new]
        photos_added = sorted(set(state["photos"]) - set(previous.get("photos", [])))
        add(f"<p>Drinks added: {len(added)} · removed: {len(removed)} · photos matched since: {len(photos_added)}</p>")
        for label, items in (("Added", added), ("Removed", removed), ("Photos added", photos_added)):
            if items:
                add(f"<details><summary>{label} ({len(items)})</summary><ul>" +
                    "".join(f"<li>{e(i)}</li>" for i in items) + "</ul></details>")
    else:
        add("<p class='muted'>First build, nothing to compare with.</p>")

    # 2. to do
    add("<h2>2. To do for the owner</h2>")
    if errs:
        add("<h3 class='err'>Errors</h3><ul>" + "".join(
            f"<li><b>{e(i['code'])}</b> {e(i['message'])}</li>" for i in errs) + "</ul>")
    by_code = issues.by_code()
    for code, items in by_code.items():
        if code.startswith("E"):
            continue
        title = CODE_TITLES.get(code, "")
        add(f"<details><summary>{e(code)} · {e(title)} ({len(items)})</summary><ul>")
        for i in items:
            where = " · ".join(x for x in (
                i["sheet"], f"row {i['row']}" if i["row"] else None, i["drink"]) if x)
            add(f"<li>{('<span class=muted>' + e(where) + '</span> · ') if where else ''}{e(i['message'])}</li>")
        add("</ul></details>")
    if not by_code:
        add("<p class='ok'>Nothing to do.</p>")
    add("<p class='muted'>Suggested photo matches are in <code>reports/photo-map.suggested.json</code>. "
        "Copy the ones you accept into <code>content/photo-map.json</code>.</p>")

    # 3. label contact sheet, skip list, fallback subcategories (Plan 01 section 15.3)
    names = {d["id"]: d["name"] for d in drinks}
    order = sorted(photo_map, key=lambda i: names.get(i, i).casefold())
    oks = [i for i in order if photo_map[i].get("front") and photo_map[i].get("labelStatus") == "ok"]
    skips = [i for i in order if photo_map[i].get("front") and photo_map[i].get("labelStatus") == "skip"]
    todo = [i for i in order if photo_map[i].get("front") and photo_map[i].get("labelStatus") is None]
    add(f"<h2>3. Welcome page labels</h2><p>{len(oks)} accepted · {len(skips)} skipped · {len(todo)} not judged yet. "
        "Only accepted crops enter the bottle label pools. Flip any decision by editing <code>labelStatus</code>, "
        "<code>labelCrop</code> [x, y, w, h as fractions] and <code>labelSkip</code> in <code>content/photo-map.json</code>.</p>")
    fallback = []
    for cat in shelf:
        for sub in cat["subs"]:
            n = sum(1 for d in sub["drinks"] if d["id"] in oks)
            if n == 0:
                fallback.append(f"{cat['name']} / {sub['name']} ({len(sub['drinks'])} drinks)")
    add("<h3>Subcategories on the illustrated fallback label</h3>")
    add("<ul>" + "".join(f"<li>{e(x)}</li>" for x in fallback) + "</ul>" if fallback else "<p class='ok'>None.</p>")
    add("<h3>Label contact sheet</h3><p class='muted'>Original with the crop outlined, then the label as published.</p><div class='sheet'>")
    for did in oks:
        entry = photo_map[did]
        x, y, w, h = entry["labelCrop"]
        orig = _rel(Path(photos_dir) / entry["front"], reports_dir)
        lab = _rel(docs / "img" / "labels" / f"{did}.webp", reports_dir)
        add(f"<div class='cell'><b>{e(names.get(did, did))}</b><br><span class='muted'>{e(did)}</span><div class='imgs'>"
            f"<span class='crop'><img class='orig' loading='lazy' src='{orig}' alt=''>"
            f"<i style='left:{x * 100:.1f}%;top:{y * 100:.1f}%;width:{w * 100:.1f}%;height:{h * 100:.1f}%'></i></span>"
            f"<img class='lab' loading='lazy' src='{lab}' alt=''></div></div>")
    add("</div>")
    add("<h3>Skipped photos</h3>")
    if skips:
        add("<div class='sheet'>")
        for did in skips:
            entry = photo_map[did]
            orig = _rel(Path(photos_dir) / entry["front"], reports_dir)
            add(f"<div class='cell'><b>{e(names.get(did, did))}</b><br><span class='muted'>{e(entry.get('labelSkip') or 'no reason given')}</span>"
                f"<div class='imgs'><img class='orig' loading='lazy' src='{orig}' alt=''></div></div>")
        add("</div>")
    else:
        add("<p class='ok'>None skipped.</p>")
    if todo:
        add("<h3>Not judged yet</h3><ul>" + "".join(f"<li>{e(names.get(i, i))}</li>" for i in todo) + "</ul>")
    add("<h3>Unmatched photos</h3>")
    if unmatched:
        add("<div class='inbox'>")
        for name in unmatched:
            sug = suggestions.get(name)
            top = f"<br>maybe: {e(sug['candidates'][0]['name'])}" if sug else ""
            add(f"<figure><img loading='lazy' src='{_rel(Path(photos_dir) / name, reports_dir)}' alt=''>"
                f"<figcaption>{e(name)}{top}</figcaption></figure>")
        add("</div>")
    else:
        add("<p class='ok'>Every photo is matched.</p>")

    # 5. scene art and counter picks (Plan 07)
    extras = extras or {}
    add("<h2>5. Welcome page scene</h2>")
    for key, title, note in (("shells_sheet", "Shells on the plates",
                              "Each cut-out standing on the lowest shelf of the wide plate and the third shelf of the tall plate, enlarged. "
                              "A dark halo or a missing rim would show here."),
                             ("burger_sheet", "Burger layers",
                              "Left: the burger on its plate as it rests on the counter. Right: the same layers split apart.")):
        if extras.get(key):
            add(f"<h3>{title}</h3><p class='muted'>{note}</p><img style='max-width:100%;border:1px solid #d8ccb3' src='{_rel(extras[key], reports_dir)}' alt=''>")
        else:
            add(f"<h3>{title}</h3><p class='muted'>Not made in this run.</p>")
    c = extras.get("counter")
    if c:
        add("<h3>New arrivals (counter, left)</h3><p class='muted'>Latest occasion first: Acquired, else Added; ties go to the later ledger row.</p><ol>"
            + "".join(f"<li>{e(n)} <span class='muted'>({e(k[0] or 'undated')}, ledger row {k[1]})</span></li>" for _id, n, k in c["arrivals"]) + "</ol>")
        add("<h3>In season (counter, right): the 5 picks per season</h3><p class='muted'>Edit <code>content/seasonal.json</code> to change keywords, pins or exclusions.</p>")
        for season, picks in c["seasons"].items():
            add(f"<h4>{e(season.title())}</h4><ol>")
            for p in picks:
                why = ", ".join([f"matches {e(' / '.join(p['hits']))}" if p["hits"] else "no keyword match"] + [e(f) for f in p["flags"]])
                add(f"<li><b>{e(p['name'])}</b> <span class='muted'>({e(p['category'])}, score {p['score']:g}: {why})</span></li>")
            add("</ol>")

    # 4. inbox
    add("<h2>6. Inbox: photos waiting to be logged</h2>")
    inbox = []
    if Path(new_dir).exists():
        inbox = sorted(p.name for p in Path(new_dir).iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXT)
    if inbox:
        add("<div class='inbox'>")
        for name in inbox:
            add(f"<figure><img loading='lazy' src='{_rel(Path(new_dir) / name, reports_dir)}' alt=''>"
                f"<figcaption>{e(name)}</figcaption></figure>")
        add("</div>")
    else:
        add("<p class='muted'>The New/ folder is empty.</p>")
    add("</body></html>")
    path = reports_dir / "build-report.html"
    path.write_text("\n".join(out), encoding="utf-8")
    return path
