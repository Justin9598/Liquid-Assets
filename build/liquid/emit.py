"""S9 Emit JSON (Plan 05 S9). Everything is produced in memory as {path relative to docs/data: text}."""
from __future__ import annotations

import hashlib
import json

from . import taxonomy as T
from .common import slugify, sort_key
from .model import build_facts, build_spec, build_tasting
from .photos import KIND_CAPTION


def dumps(obj) -> str:
    """Stable JSON: fixed key order (insertion), 1-space indent, UTF-8 without escaping, trailing newline."""
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def _join_location(*parts):
    out = []
    for p in parts:
        if p and p not in out:
            out.append(p)
    return ", ".join(out) or None


def has_label(photo_map, did):
    """A drink enters the welcome page label pools only with a verified label-only crop (Plan 01 section 15.3)."""
    e = photo_map.get(did, {})
    return bool(e.get("front") and e.get("labelStatus") == "ok" and e.get("labelCrop"))


def build_shelf(drinks, grades, issues):
    """Return the shelf structure: list of categories with ordered, non-empty subcategories."""
    cats = []
    for key, name, vessel in T.CATEGORIES:
        subs = {}
        for d in drinks:
            if d["category"] != key:
                continue
            s = subs.setdefault(d["sub"], {"key": d["sub"], "name": d["sub_name"], "order": d["sub_order"],
                                           "drinks": []})
            s["drinks"].append(d)
        ordered = sorted(subs.values(), key=lambda s: (s["order"], sort_key(s["name"])))
        cats.append({"key": key, "name": name, "vessel": vessel, "subs": ordered,
                     "count": sum(len(s["drinks"]) for s in ordered)})
    cats = [c for c in cats if c["count"]]                       # a category with no drinks is left out everywhere (Plan 10 section 2.1)
    # I01: sake grades without any drink
    sake = next(c for c in cats if c["key"] == "sake")
    present = {s["name"] for s in sake["subs"]}
    for g in list(grades) + ["Craft Sake", "Ungraded"]:
        if g not in present:
            issues.info("I01", f"Empty subcategory hidden: Sake / {g}")
    return cats


def _pin_fields(p):
    """Where the maker's pin is (Plan 14 section 5): coordinates to 3 decimal places, and the place names the maps group by."""
    pin = p.get("pin")
    if not pin:                                   # no map files (a test project): the keys stay, empty
        return {k: None for k in ("lat", "lon", "cid", "prov", "provName", "area", "cont", "reg", "main", "exact")}
    return {"lat": pin["lat"], "lon": pin["lon"], "cid": pin["cid"], "prov": pin["prov"], "provName": pin["provName"],
            "area": pin["area"], "cont": pin["cont"], "reg": pin["reg"], "main": pin["main"], "exact": pin["exact"]}


def emit(drinks, shelf, pages, key_by_text, photo_map, dims, ledger, generated, content, image_signatures, sections=None):
    files = {}
    drinks_sorted = sorted(drinks, key=lambda d: (sort_key(d["name"]), d["id"]))

    # prev/next within a subcategory, Name A-Z, wrapping
    prev_next = {}
    for cat in shelf:
        for sub in cat["subs"]:
            ordered = sorted(sub["drinks"], key=lambda d: (sort_key(d["name"]), d["id"]))
            n = len(ordered)
            for i, d in enumerate(ordered):
                prev_next[d["id"]] = (ordered[(i - 1) % n]["id"], ordered[(i + 1) % n]["id"])

    # ---- shelf.json
    shelf_out = {"generated": None, "categories": []}  # generated is filled in below
    for cat in shelf:
        subs_out = []
        for sub in cat["subs"]:
            native = None
            if cat["key"] == "sake":
                native = T.SAKE_NATIVE.get(sub["name"])
            elif cat["key"] == "liqueur":
                native = T.LIQUEUR_NATIVE.get(sub["name"])
            elif cat["key"] == "fermented" and sub["key"] == "makgeolli":
                native = T.MAKGEOLLI_NATIVE
            elif sub["key"] == "all":
                native = T.FALLBACK_NATIVE.get(cat["key"])
            labels = [f"img/labels/{d['id']}.webp" for d in sorted(sub["drinks"], key=lambda d: (sort_key(d["name"]), d["id"]))
                      if has_label(photo_map, d["id"])]
            entry = {"key": sub["key"], "name": sub["name"], "native": native,
                     "drinkCount": len(sub["drinks"]), "labels": labels}
            views = (content.get("sub_views") or {}).get(f"{cat['key']}/{sub['key']}")
            if views:                                                     # Plan 10 section 4.7: names and labels only
                entry.update(drinks=views["drinks"])
                if cat["key"] in T.DIRECT_CATEGORIES:                      # only Umeshu fills the shelves and filters the counter (Plan 10 section 13)
                    entry.update(new=views["new"], season=views["season"])
            subs_out.append(entry)
        cat_out = {"key": cat["key"], "name": cat["name"], "vessel": cat["vessel"],
                   "drinkCount": cat["count"], "subcategories": subs_out}
        if cat["key"] in T.DIRECT_CATEGORIES:
            cat_out["direct"] = True
        cc = (content.get("category_counters") or {}).get(cat["key"])
        if cc:
            cat_out["counter"] = cc                                  # Plan 14 section 3.2
        shelf_out["categories"].append(cat_out)

    # ---- drinks.json (index)
    def page_of(d):
        return pages.get(key_by_text.get(d["producer_raw"])) if d["producer_raw"] else None

    index = []
    for d in drinks_sorted:
        page = page_of(d)
        front = photo_map.get(d["id"], {}).get("front")
        d["_thumb"] = f"img/thumbs/{d['id']}.webp" if front else None
        d["_facts"] = build_facts(d)
        d["_tasting"] = build_tasting(d, ledger)
        index.append({
            "id": d["id"], "name": d["name"], "category": d["category"], "sub": d["sub"], "shell": d.get("shell"),
            "producer": page["name"] if page else None,
            "producerKey": page["key"] if page else None,
            "origin": d["origin"], "country": d["country"], "abv": d["abv"], "sizes": d["sizes"],
            "occasions": len(d["visits"]), "styles": d["styles"], "favourite": d["favourite"],
            "rating": d["rating"], "added": d["added"], "facts": d["_facts"],
            "hasTasting": d["_tasting"] is not None, "thumb": d["_thumb"],
            "label": f"img/labels/{d['id']}.webp" if has_label(photo_map, d["id"]) else None,
        })
    files["drinks.json"] = dumps(index)

    # ---- drinks/<id>.json
    by_page = {}
    for p in pages.values():
        for d in p["drinks"]:
            by_page.setdefault(p["key"], []).append(d["id"])
    for d in drinks_sorted:
        page = page_of(d)
        if page:
            about = page["about"][0] if page["about"] else None
            producer = {"key": page["key"], "name": page["name"], "native": page["native"],
                        "location": _join_location(page["location"], page["country"]),
                        "founded": page["founded"], "about": about, "url": page["website"]}
            more = [i for i in by_page[page["key"]] if i != d["id"]]
        else:
            producer = {"key": None, "name": None, "native": None,
                        "location": _join_location(d["origin"], d["country"]),
                        "founded": None, "about": None, "url": None}
            more = []
        # visits: cheapest first, and the price itself is never written (Plan 11). No price counts as free. Ties go
        # newest first, undated after the dated ones in ledger order (the sort is stable).
        visits = d["visits"]
        dated = sorted([v for v in visits if v["date"]], key=lambda v: v["date"], reverse=True)
        undated = [v for v in visits if not v["date"]]
        ordered_visits = sorted(dated + undated, key=lambda v: v["price"] or 0)
        visits_out = [{"date": v["date"], "size": v["size"], "where": v["where"],
                       "note": v["note"]} for v in ordered_visits]
        entry = photo_map.get(d["id"], {})
        photos = []
        n = 0
        ordered = [("front", entry["front"])] if entry.get("front") else []        # the front image only (Plan 10 section 7)
        for kind, _file in ordered:
            n += 1
            path = f"img/web/{d['id']}-{n}.webp"
            w, h = dims.get(path, (0, 0))
            photos.append({"kind": kind, "caption": KIND_CAPTION.get(kind, "Photo"), "web": path, "w": w, "h": h})
        pn = prev_next.get(d["id"], (None, None))
        doc = {
            "id": d["id"], "name": d["name"], "category": d["category"], "sub": d["sub"],
            "producer": producer, "abv": d["abv"], "styles": d["styles"], "favourite": d["favourite"],
            "rating": d["rating"], "spec": build_spec(d), "tasting": d["_tasting"], "story": d["story"],
            "visits": visits_out, "photos": photos, "moreFromProducer": more,
            "prev": pn[0], "next": pn[1],
        }
        files[f"drinks/{d['id']}.json"] = dumps(doc)

    # ---- producers.json and producers/<key>.json
    pindex = []
    for key, p in pages.items():
        pindex.append({"key": key, "name": p["name"], "native": p["native"], "region": p["region"],
                       "country": p["country"], "location": p["location"], "brands": p["brands"],
                       "drinkCount": p["drinkCount"], "favourites": p["favourites"],
                       "hasStory": bool(p["about"]), **_pin_fields(p)})
        doc = {
            "key": key, "name": p["name"], "native": p["native"], "location": p["location"],
            "region": p["region"], "country": p["country"], "founded": p["founded"], "master": p["master"],
            "website": p["website"], "brands": p["brands"], "about": p["about"], "sources": p["sources"],
            "related": p["related"],
            "tally": {"drinks": p["drinkCount"], "categories": len(p["categories"]),
                      "favourites": p["favourites"], "timesHad": p["timesHad"]},
            "drinks": [{"id": d["id"], "category": d["category"], "sub": d["sub"]} for d in p["drinks"]],
            "moreFromRegion": p["moreFromRegion"], **_pin_fields(p),
        }
        files[f"producers/{key}.json"] = dumps(doc)
    files["producers.json"] = dumps(pindex)

    # ---- subcategories.json / glossary.json: only keys in use
    sub_keys = {f"{c['key']}/{s['key']}" for c in shelf for s in c["subs"]}
    subs_content = content.get("subcategories", {})
    files["subcategories.json"] = dumps({k: v for k, v in subs_content.items() if k in sub_keys})
    used_terms = set()
    for d in drinks:
        used_terms.update(s.casefold() for s in d["styles"])
        for item in build_spec(d):
            used_terms.add(str(item["label"]).casefold())
            if isinstance(item["value"], str):
                used_terms.update(part.strip().casefold() for part in item["value"].split(","))
    if any(d["_tasting"] for d in drinks):
        used_terms.add("wset-style tasting")   # caption of the tasting card (Plan 05 section 14)
    glossary = content.get("glossary", {})
    files["glossary.json"] = dumps({k: v for k, v in glossary.items() if k.casefold() in used_terms})

    files["aliases.json"] = dumps({"routes": T.ROUTE_ALIASES, "producers": content.get("aliases", {})})   # Plan 10 section 2.5

    if content.get("scene_data"):
        files["scene.json"] = dumps(content["scene_data"])

    # ---- shelf.json needs the timestamp; build.json last
    if content.get("counter"):
        shelf_out["counter"] = content["counter"]               # Plan 07 section 4.4
    shelf_out["generated"] = generated
    files["shelf.json"] = dumps(shelf_out)
    from .phase import FULL, published
    sections = sections or dict(FULL)
    digest = hashlib.sha1()
    for rel in sorted(r for r in files if published(r, sections)):
        digest.update(rel.encode())
        digest.update(files[rel].encode("utf-8"))
    for sig in sorted(image_signatures):
        digest.update(sig.encode())
    files["build.json"] = dumps({"generated": generated, "drinkCount": len(drinks),
                                 "producerCount": len(pages), "sections": sections, "version": digest.hexdigest()[:10]})
    return files
