"""S6 Producers (Plan 04 sections 8 and 9, Plan 05 S6).

Research fields are published only for rows with Status = approved. Draft rows publish only the
fields that come from Core (name, location, region, country, drinks) plus the structural Page Key.
"""
from __future__ import annotations

import re

from . import taxonomy as T
from .common import clean, norm_key, slugify, sort_key
from .ledger import to_number

GATED = ("native", "brands", "founded", "master", "website", "about", "sources", "related")
_PREF_KEYS = {norm_key(p) for p in T.PREFECTURES}


def is_unknown(name):
    return name is None or norm_key(name) in ("", "unknown")


def _split(value, sep):
    if not value:
        return []
    return [p for p in (clean(x) for x in str(value).split(sep)) if p]


_BANNED = re.compile(r"finest|passion|world-class", re.I)


def check_about(name, paragraphs, issues, key=None):
    """W22 (Plan 09 section 7, D4): an approved maker's published About must have no em or en dash, none of the words
    finest, passion or world-class, 60 to 120 words, and at most 3 paragraphs."""
    if not paragraphs:
        return
    text = " ".join(paragraphs)
    words = len(text.split())
    problems = []
    if "—" in text or "–" in text:
        problems.append("an em or en dash")
    banned = sorted({m.group(0).casefold() for m in _BANNED.finditer(text)})
    if banned:
        problems.append("the word " + ", ".join(f"'{b}'" for b in banned))
    if words < 60 or words > 120:
        problems.append(f"{words} words (60 to 120 wanted)")
    if len(paragraphs) > 3:
        problems.append(f"{len(paragraphs)} paragraphs (3 at most)")
    for pr in problems:
        issues.warn("W22", f"About of '{name}' has {pr}", sheet="Producers", drink=name)


def check_sources(name, sources, issues):
    """W24 (Plan 09 D23): every Sources entry of an approved maker must be a web address (http or https)."""
    for s in sources or []:
        if not str(s).strip().lower().startswith(("http://", "https://")):
            issues.warn("W24", f"Sources of '{name}' has an entry that is not a web address: '{str(s).strip()[:60]}'",
                        sheet="Producers", drink=name)


def _paragraphs(text):
    if not text:
        return []
    parts = [clean(p) for p in str(text).replace("\r\n", "\n").split("\n\n")]
    parts = [p for p in parts if p]
    if len(parts) == 1 and "\n" in str(text):
        parts = [p for p in (clean(x) for x in str(text).split("\n")) if p]
    return parts


def build_producers(ledger, drinks, issues):
    """Returns (pages, key_by_producer_text). `pages` is a dict key -> page dict (insertion = A-Z)."""
    sheet_rows = {}
    sheet_present = "Producers" in ledger.present_sheets
    for rownum, row in ledger.sheets.get("Producers", []):
        text = row["Producer"]
        if text in sheet_rows:
            issues.warn("W17", f"Producers sheet lists '{text}' twice; the first row is used",
                        sheet="Producers", row=rownum)
            continue
        sheet_rows[text] = (rownum, row)

    # distinct producer strings in first-seen order
    texts = []
    seen = set()
    for d in drinks:
        p = d["producer_raw"]
        if is_unknown(p) or p in seen:
            continue
        seen.add(p)
        texts.append(p)

    # synthetic fallback info from Core
    core_info = {}
    for d in drinks:
        p = d["producer_raw"]
        if is_unknown(p):
            continue
        info = core_info.setdefault(p, {"origin": d["origin"], "country": d["country"]})
        info["origin"] = info["origin"] or d["origin"]
        info["country"] = info["country"] or d["country"]

    entries = []  # one per producer text
    used_fallback_keys = {}
    for text in texts:
        info = core_info[text]
        found = sheet_rows.get(text)
        if found:
            rownum, row = found
            key = slugify(row.get("Page Key") or text)
            entry = {"text": text, "row": row, "rownum": rownum, "key": key, "from_sheet": True}
        else:
            if sheet_present:
                issues.warn("W04", f"Producer '{text}' is missing from the Producers sheet; "
                                   f"using Core fields only", sheet="Producers", drink=text)
            else:
                issues.warn("W04", f"Producer '{text}' is not in the Producers sheet (sheet not created yet); "
                                   f"using Core fields only", sheet="Producers", drink=text)
            key = slugify(text)
            if key in used_fallback_keys and used_fallback_keys[key] != text:
                key = f"{key}-{slugify(info['origin'] or 'x')}"
                n = 2
                while key in used_fallback_keys and used_fallback_keys[key] != text:
                    key = f"{slugify(text)}-{n}"
                    n += 1
            used_fallback_keys[key] = text
            entry = {"text": text, "row": {}, "rownum": None, "key": key, "from_sheet": False}
        entry.update(info_origin=info["origin"], info_country=info["country"])
        entries.append(entry)

    groups = {}
    for e in entries:
        groups.setdefault(e["key"], []).append(e)

    drinks_by_text = {}
    for d in drinks:
        drinks_by_text.setdefault(d["producer_raw"], []).append(d)

    pages = {}
    key_by_text = {}
    for key, group in groups.items():
        sheet_group = [e for e in group if e["from_sheet"]]
        # facts row: the row whose Producer equals the Display Name, else the first row in sheet order
        facts = None
        if sheet_group:
            sheet_group.sort(key=lambda e: e["rownum"])
            for e in sheet_group:
                dn = e["row"].get("Display Name")
                if dn and e["text"] == dn:
                    facts = e
                    break
            if facts is None:
                facts = next((e for e in sheet_group if e["row"].get("Display Name") == e["text"]), None)
            if facts is None:
                facts = sheet_group[0]
        base = facts or group[0]
        row = base["row"] if facts else {}
        approved = bool(facts) and str(row.get("Status") or "").strip().casefold() == "approved"

        # alias disagreement (W08)
        if len(group) > 1:
            for fld, label in (("Region", "Region"), ("Country", "Country")):
                vals = {norm_key(e["row"].get(fld) or (e["info_origin"] if fld == "Region" else e["info_country"]))
                        for e in group}
                vals.discard("")
                if len(vals) > 1:
                    issues.warn("W08", f"Producers sharing Page Key '{key}' disagree on {label}",
                                sheet="Producers", row=base["rownum"], drink=base["text"])

        region = row.get("Region") or base["info_origin"]
        country = row.get("Country") or base["info_country"]
        location_text = row.get("Location") or base["info_origin"]
        name = row.get("Display Name") or base["text"]
        if norm_key(country) == "japan" and region and norm_key(region) not in _PREF_KEYS:
            issues.warn("W05", f"Region '{region}' for '{name}' is not one of the 47 prefectures",
                        sheet="Producers" if facts else "Core", row=base["rownum"], drink=name)

        member_texts = [e["text"] for e in group]
        for t in member_texts:
            key_by_text[t] = key
        member_drinks = []
        for t in member_texts:
            member_drinks.extend(drinks_by_text[t])

        brands = []
        if approved:
            for e in group:
                for b in _split(e["row"].get("Brands"), ","):
                    if b.casefold() not in {x.casefold() for x in brands}:
                        brands.append(b)
        page = {
            "key": key, "name": name, "region": region, "country": country,
            "location": location_text, "approved": approved,
            "native": row.get("Native Name") if approved else None,
            "brands": brands,
            "founded": to_number(row.get("Founded")) if approved else None,
            "master": row.get("Master") if approved else None,
            "website": row.get("Website") if approved else None,
            "about": _paragraphs(row.get("About")) if approved else [],
            "sources": _split(row.get("Sources"), ";") if approved else [],
            "related_raw": _split(row.get("Related"), ";") if approved else [],
            "lat_raw": row.get("Latitude"), "lon_raw": row.get("Longitude"),          # Plan 14 section 5.1
            "texts": member_texts,
            "drinks": member_drinks,
            "raw_gated": {k: row.get(k) for k in ("About", "Founded", "Master", "Website", "Native Name",
                                                  "Brands", "Sources", "Related")} if (facts and not approved) else {},
        }
        if approved:
            check_about(name, page["about"], issues)
            check_sources(name, page["sources"], issues)
        pages[key] = page

    # sort A-Z for stable output
    pages = dict(sorted(pages.items(), key=lambda kv: sort_key(kv[1]["name"]) + (kv[0],)))
    _finish(pages, drinks, issues)
    return pages, key_by_text


def _finish(pages, drinks, issues):
    """Tallies, related makers and 'more from region'."""
    for page in pages.values():
        ds = sorted(page["drinks"], key=lambda d: (sort_key(d["name"]), d["id"]))
        page["drinks"] = ds
        page["drinkCount"] = len(ds)
        page["favourites"] = sum(1 for d in ds if d["favourite"])
        page["timesHad"] = sum(len(d["visits"]) for d in ds)
        page["categories"] = sorted({d["category"] for d in ds if d["category"]},
                                    key=[c[0] for c in T.CATEGORIES].index)
        rel = []
        for item in page["related_raw"]:
            if ":" in item:
                k, rel_name = item.split(":", 1)
            else:
                k, rel_name = item, ""
            k, rel_name = slugify(k.strip()), clean(rel_name)
            if k not in pages or k == page["key"]:
                issues.warn("W18", f"Related maker '{item}' of '{page['name']}' does not match any producer "
                                   f"page and is dropped", sheet="Producers", drink=page["name"])
                continue
            rel.append({"key": k, "name": pages[k]["name"], "relationship": rel_name})
        page["related"] = rel
    # more from region
    by_region = {}
    for k, p in pages.items():
        if p["region"]:
            by_region.setdefault((norm_key(p["country"]), norm_key(p["region"])), []).append(k)
    for k, p in pages.items():
        peers = [x for x in by_region.get((norm_key(p["country"]), norm_key(p["region"])), []) if x != k]
        peers.sort(key=lambda x: (-pages[x]["drinkCount"], sort_key(pages[x]["name"]), x))
        p["moreFromRegion"] = peers[:12]
    # more-from-producer for drinks
    for p in pages.values():
        for d in p["drinks"]:
            d["_producer_key"] = p["key"]
