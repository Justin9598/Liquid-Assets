"""Counter displays (Plan 07 section 4): the 5 newest drinks, and 5 seasonal picks for each Japanese season.

Both are decided at build time from the ledger and written into shelf.json (`counter`); the page only chooses the season
from the visitor's month. Only names, categories and published label paths go into the data (Plan 05 privacy rules).
"""
from __future__ import annotations

import re

from .emit import has_label

SEASONS = ["spring", "summer", "autumn", "winter"]
SEASON_MONTHS = {"spring": "Mar to May", "summer": "Jun to Aug", "autumn": "Sep to Nov", "winter": "Dec to Feb"}
COUNT = 5                  # the counter's own set at rest
LIMIT = 24                 # how many the shelf views can show (Plan 10 section 4.7)


def arrival_key(d):
    """Latest occasion: the newest dated visit (Acquired, else Added), ties to the later ledger row; undated come last."""
    return max(((v["date"] or ""), v["_row"]) for v in d["visits"])


def rank_recent(drinks):
    """Drinks newest first, one entry per drink."""
    return sorted(drinks, key=lambda d: arrival_key(d), reverse=True)


def _item(d, photo_map):
    return {"id": d["id"], "name": d["name"], "category": d["category"], "sub": d["sub"],
            "label": f"img/labels/{d['id']}.webp" if has_label(photo_map, d["id"]) else None}


def _keywords(raw):
    out = []
    for k in raw:
        out += [p.strip() for p in k.split("/") if p.strip()]
    return out


def _matcher(word):
    if re.search(r"[^\x00-\x7f]", word):                 # Japanese: match anywhere
        return re.compile(re.escape(word.casefold()))
    return re.compile(r"(?<![a-z0-9])" + re.escape(word.casefold()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])")


def _haystack(d):
    parts = [d["name"], " ".join(d.get("styles") or []), d.get("story") or "", (d["detail"].get("Other Detail") or {}).get("Type") or ""]
    return " \n ".join(str(p) for p in parts).casefold()


def _scored(drinks, photo_map, cfg, season, recent_ids):
    """Every drink scored for one season as (drink, score, matched keywords, flags), as in Plan 07 section 4.3."""
    exclude = set(cfg.get("exclude") or [])
    matchers = [(w, _matcher(w)) for w in _keywords(cfg["keywords"].get(season, []))]
    out = []
    for d in drinks:
        if d["id"] in exclude or not d["category"]:
            continue
        hay = _haystack(d)
        hits = []
        for w, rx in matchers:
            if w.casefold() not in {h.casefold() for h in hits} and rx.search(hay):
                hits.append(w)
        if season == "summer" and d["abv"] is not None and d["abv"] <= cfg.get("summerAbvMax", 13):
            hits.append(f"ABV {d['abv']:g}%")
        score = 3.0 * len(hits)
        flags = []
        if d["favourite"]:
            score += 2
            flags.append("favourite")
        if has_label(photo_map, d["id"]):
            score += 1
            flags.append("label photo")
        if d["id"] in recent_ids:
            score += 0.5
            flags.append("recent")
        out.append((d, score, hits, flags))
    return out


def season_picks(drinks, photo_map, cfg, issues, limit=LIMIT):
    """{season: [(drink, score, matched keywords, flags)]}: the first 5 are the counter's picks (at most 3 from one category);
    the rest, up to `limit`, follow in score order for the shelf view."""
    recent = rank_recent(drinks)
    recent_ids = {d["id"] for d in recent[: cfg.get("recentWindow", 30)]}
    by_id = {d["id"]: d for d in drinks}
    exclude = set(cfg.get("exclude") or [])
    cap = cfg.get("maxPerCategory", 3)
    rank = {d["id"]: i for i, d in enumerate(recent)}
    out = {}
    for season in SEASONS:
        scored = _scored(drinks, photo_map, cfg, season, recent_ids)
        picks, cats = [], {}
        lim = [COUNT]

        def take(entry, why=None, respect_cap=True):
            d = entry[0]
            if d["id"] in {p[0]["id"] for p in picks} or len(picks) >= lim[0]:
                return False
            if respect_cap and cats.get(d["category"], 0) >= cap:
                return False
            picks.append((d, entry[1], entry[2], entry[3] + ([why] if why else [])))
            cats[d["category"]] = cats.get(d["category"], 0) + 1
            return True

        for did in (cfg.get("pins") or {}).get(season, []):
            d = by_id.get(did)
            if d is None:
                issues.warn("W23", f"content/seasonal.json pins unknown drink ID '{did}' for {season}")
            elif did not in exclude:
                e = next(x for x in scored if x[0]["id"] == did)
                take(e, "pinned", respect_cap=False)
        key = lambda e: (-e[1], rank[e[0]["id"]], e[0]["id"])
        matched = sorted([e for e in scored if e[2]], key=key)
        for e in matched:
            take(e)
        if len(picks) < COUNT:
            for e in sorted([e for e in scored if e[0]["favourite"] and not e[2]], key=key):
                take(e, "filler: favourite")
        if len(picks) < COUNT:
            for e in sorted([e for e in scored if not e[2]], key=lambda e: rank[e[0]["id"]]):
                take(e, "filler: recent")
        if len(picks) < COUNT:                           # last resort: relax the category cap
            for e in sorted(scored, key=key):
                take(e, "filler", respect_cap=False)
        lim[0] = limit                                   # the shelf view: on in score order, no category cap
        for e in matched:
            take(e, respect_cap=False)
        for e in sorted([e for e in scored if e[0]["favourite"] and not e[2]], key=key):
            take(e, "filler: favourite", respect_cap=False)
        for e in sorted([e for e in scored if not e[2]], key=lambda e: rank[e[0]["id"]]):
            take(e, "filler: recent", respect_cap=False)
        out[season] = picks
    return out


def validate_seasonal(cfg, issues):
    """E04 when content/seasonal.json is malformed. Returns True when usable."""
    ok = True

    def bad(msg):
        nonlocal ok
        issues.error("E04", f"content/seasonal.json: {msg}")
        ok = False

    kw = cfg.get("keywords")
    if not isinstance(kw, dict) or any(not isinstance(kw.get(s), list) or not all(isinstance(k, str) and k.strip() for k in kw[s])
                                       for s in SEASONS):
        bad("'keywords' must list words for spring, summer, autumn and winter")
    for field in ("pins",):
        v = cfg.get(field) or {}
        if not isinstance(v, dict) or any(not isinstance(v.get(s, []), list) for s in SEASONS):
            bad(f"'{field}' must map each season to a list of drink IDs")
    if not isinstance(cfg.get("exclude") or [], list):
        bad("'exclude' must be a list of drink IDs")
    for field, lo in (("summerAbvMax", 0), ("recentWindow", 1), ("maxPerCategory", 1)):
        if field in cfg and not (isinstance(cfg[field], (int, float)) and not isinstance(cfg[field], bool) and cfg[field] >= lo):
            bad(f"'{field}' must be a number of at least {lo}")
    return ok


def sub_views(drinks, photo_map, cfg):
    """Per subcategory (key 'cat/sub'): its drinks newest first, its 5 newest, and its 5 picks for each season (only drinks
    with a season keyword match), as ids (Plan 10 sections 4.7 and 6.2)."""
    recent = rank_recent(drinks)
    recent_ids = {d["id"] for d in recent[: (cfg or {}).get("recentWindow", 30)]}
    by_sub = {}
    for d in recent:
        if d["category"] and d["sub"]:
            by_sub.setdefault(f"{d['category']}/{d['sub']}", []).append(d)
    seasonal = {s: {x[0]["id"]: x for x in _scored(drinks, photo_map, cfg, s, recent_ids)} for s in SEASONS} if cfg else {s: {} for s in SEASONS}
    rank = {d["id"]: i for i, d in enumerate(recent)}
    out = {}
    for key, ds in by_sub.items():
        entry = {"drinks": [{"id": d["id"], "name": d["name"], "label": f"img/labels/{d['id']}.webp" if has_label(photo_map, d["id"]) else None} for d in ds],
                 "new": [d["id"] for d in ds[:COUNT]], "season": {}}
        for s in SEASONS:
            hit = [seasonal[s][d["id"]] for d in ds if d["id"] in seasonal[s] and seasonal[s][d["id"]][2]]
            hit.sort(key=lambda e: (-e[1], rank[e[0]["id"]], e[0]["id"]))
            entry["season"][s] = [e[0]["id"] for e in hit[:COUNT]]
        out[key] = entry
    return out


def build_counter(drinks, photo_map, cfg, issues):
    """The `counter` object for shelf.json, plus the report data."""
    arrivals = rank_recent(drinks)[:LIMIT]
    picks = season_picks(drinks, photo_map, cfg, issues) if cfg else {s: [] for s in SEASONS}
    counter = {"newArrivals": [_item(d, photo_map) for d in arrivals],
               "inSeason": {s: [_item(p[0], photo_map) for p in picks[s]] for s in SEASONS}}
    report = {"arrivals": [(d["id"], d["name"], arrival_key(d)) for d in arrivals[:COUNT]], "seasons": {
        s: [{"id": p[0]["id"], "name": p[0]["name"], "category": p[0]["category"], "score": p[1], "hits": p[2], "flags": p[3]}
           for p in picks[s][:COUNT]] for s in SEASONS}}
    return counter, report
