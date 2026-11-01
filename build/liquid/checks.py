"""S10 Checks: privacy scan (E02), references (E03) and schema (E04) over the emitted data."""
from __future__ import annotations

import json
import re

PRIVATE_MARKERS = ["Invoice", "Sweep batch", "converted at", "mid-market", "corrected from"]
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# ---------------------------------------------------------------- schema
# "s" string, "s?" nullable string, "n" number, "n?" nullable number, "i" int, "b" bool, "any".
# A list means "list of": ["s"]. A dict is an object with required keys (extra keys are allowed).

TASTING_SCALES = "any"
SCHEMAS = {
    "drinks.json": [{
        "id": "s", "name": "s", "category": "s?", "sub": "s?", "producer": "s?", "producerKey": "s?",
        "origin": "s?", "country": "s?", "abv": "n?", "sizes": ["s"], "occasions": "i", "styles": ["s"],
        "favourite": "b", "rating": "n?", "added": "s?", "facts": ["s"], "hasTasting": "b", "thumb": "s?", "label": "s?"}],
    "drink": {
        "id": "s", "name": "s", "category": "s?", "sub": "s?",
        "producer": {"key": "s?", "name": "s?", "native": "s?", "location": "s?", "founded": "n?",
                     "about": "s?", "url": "s?"},
        "abv": "n?", "styles": ["s"], "favourite": "b", "rating": "n?",
        "spec": [{"label": "s", "value": "any"}], "tasting": "any", "story": "s?",
        "visits": [{"date": "s?", "size": "s?", "where": "s?", "price": "n?", "note": "s?"}],
        "photos": [{"kind": "s", "caption": "s", "web": "s", "w": "i", "h": "i"}],
        "moreFromProducer": ["s"], "prev": "s?", "next": "s?"},
    "producers.json": [{
        "key": "s", "name": "s", "native": "s?", "region": "s?", "country": "s?", "location": "s?",
        "brands": ["s"], "drinkCount": "i", "favourites": "i", "hasStory": "b"}],
    "producer": {
        "key": "s", "name": "s", "native": "s?", "location": "s?", "region": "s?", "country": "s?",
        "founded": "n?", "master": "s?", "website": "s?", "brands": ["s"], "about": ["s"], "sources": ["s"],
        "related": [{"key": "s", "name": "s", "relationship": "s?"}],
        "tally": {"drinks": "i", "categories": "i", "favourites": "i", "timesHad": "i"},
        "drinks": [{"id": "s", "category": "s?", "sub": "s?"}], "moreFromRegion": ["s"]},
    "shelf.json": {
        "generated": "s?",
        "categories": [{"key": "s", "name": "s", "vessel": "s", "drinkCount": "i",
                        "subcategories": [{"key": "s", "name": "s", "native": "s?", "drinkCount": "i",
                                           "labels": ["s"]}]}]},
    "build.json": {"generated": "s?", "drinkCount": "i", "producerCount": "i", "sections": "any", "version": "s"},
    "subcategories.json": "any", "glossary.json": "any",
}


def _check(value, spec, path, errs):
    if spec == "any":
        return
    if isinstance(spec, str):
        nullable = spec.endswith("?")
        kind = spec.rstrip("?")
        if value is None:
            if not nullable:
                errs.append(f"{path}: null where a value is required")
            return
        ok = {"s": isinstance(value, str),
              "n": isinstance(value, (int, float)) and not isinstance(value, bool),
              "i": isinstance(value, int) and not isinstance(value, bool),
              "b": isinstance(value, bool)}[kind]
        if not ok:
            errs.append(f"{path}: expected {kind}, got {type(value).__name__}")
        return
    if isinstance(spec, list):
        if not isinstance(value, list):
            errs.append(f"{path}: expected a list")
            return
        for i, item in enumerate(value):
            _check(item, spec[0], f"{path}[{i}]", errs)
        return
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            errs.append(f"{path}: expected an object")
            return
        for k, sub in spec.items():
            if k not in value:
                errs.append(f"{path}.{k}: missing")
            else:
                _check(value[k], sub, f"{path}.{k}", errs)


def check_schema(files, issues):
    for rel, text in files.items():
        try:
            data = json.loads(text)
        except ValueError as exc:
            issues.error("E04", f"{rel} is not valid JSON: {exc}")
            continue
        if rel.startswith("drinks/"):
            spec = SCHEMAS["drink"]
        elif rel.startswith("producers/"):
            spec = SCHEMAS["producer"]
        else:
            spec = SCHEMAS.get(rel, "any")
        errs = []
        _check(data, spec, rel, errs)
        for e in errs[:5]:
            issues.error("E04", f"Schema violation: {e}")
        if len(errs) > 5:
            issues.error("E04", f"{rel}: {len(errs) - 5} more schema violations")
        if rel.startswith("drinks/") and not SAFE_ID.match(rel[len("drinks/"):-len(".json")]):
            issues.error("E04", f"Drink ID '{rel}' is not safe to use as a file name")
        if rel.startswith("producers/") and not SAFE_ID.match(rel[len("producers/"):-len(".json")]):
            issues.error("E04", f"Producer key '{rel}' is not safe to use as a file name")


# ---------------------------------------------------------------- privacy

def _walk_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}", k
            yield from _walk_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{path}[{i}]")


def check_privacy(files, photo_files, pages, issues, extra_markers=()):
    """Fail (E02) when any published file holds private markers, a notes field, or draft research."""
    markers = [m.casefold() for m in list(PRIVATE_MARKERS) + list(extra_markers)]
    filenames = sorted({f for f in photo_files if len(f) >= 5})
    for rel, text in files.items():
        low = text.casefold()
        for m in markers:
            if m in low:
                issues.error("E02", f"Privacy leak: '{m}' found in published file data/{rel}")
        for f in filenames:
            if f.casefold() in low:
                issues.error("E02", f"Privacy leak: an original photo filename ('{f}') appears in data/{rel}")
        try:
            data = json.loads(text)
        except ValueError:
            continue
        for p, k in _walk_keys(data):
            if k.casefold() in ("notes", "public notes", "publicnotes") and rel not in ("subcategories.json",):
                issues.error("E02", f"Privacy leak: a '{k}' field is published in data/{rel}{p}")
    # draft (non-approved) producers must publish none of their research
    for page in pages.values():
        if page["approved"]:
            continue
        # structural check on the emitted producer page
        doc_text = files.get(f"producers/{page['key']}.json")
        if doc_text:
            doc = json.loads(doc_text)
            for field in ("native", "founded", "master", "website"):
                if doc.get(field) not in (None, ""):
                    issues.error("E02", f"Draft producer '{page['name']}' publishes {field} in producers/{page['key']}.json")
            for field in ("brands", "about", "sources", "related"):
                if doc.get(field):
                    issues.error("E02", f"Draft producer '{page['name']}' publishes {field} in producers/{page['key']}.json")
        # text scan for the long free-text research fields (short fields such as Brands legitimately
        # overlap with drink names, so they are covered by the structural check only)
        for label in ("About", "Website", "Master", "Sources"):
            raw = page["raw_gated"].get(label)
            if raw is None:
                continue
            splitter = ";" if label == "Sources" else "\n"
            for part in str(raw).replace("\r", "").split(splitter):
                part = part.strip()
                if len(part) < 6:
                    continue
                for rel, text in files.items():
                    if part.casefold() in text.casefold():
                        issues.error("E02", f"Draft producer research leaked: {label} of '{page['name']}' "
                                            f"appears in data/{rel}")
                        break


# ---------------------------------------------------------------- references

def check_references(files, expected_images, issues, docs_dir=None):
    """E03: every id, key, sub and image path points to something that exists."""
    def load(rel):
        return json.loads(files[rel])

    try:
        index = load("drinks.json")
        shelf = load("shelf.json")
        producers = load("producers.json")
    except (KeyError, ValueError):
        return
    ids = {d["id"] for d in index}
    pkeys = {p["key"] for p in producers}
    routes = {(c["key"], s["key"]) for c in shelf["categories"] for s in c["subcategories"]}

    def image_ok(path):
        if path is None:
            return True
        if path not in expected_images:
            return False
        if docs_dir is not None and not (docs_dir / path).exists():
            return False
        return True

    for d in index:
        if f"drinks/{d['id']}.json" not in files:
            issues.error("E03", f"Missing drinks/{d['id']}.json")
        if d["category"] is not None and (d["category"], d["sub"]) not in routes:
            issues.error("E03", f"Drink '{d['id']}' points at a shelf that does not exist "
                                f"({d['category']}/{d['sub']})")
        if d["producerKey"] is not None and d["producerKey"] not in pkeys:
            issues.error("E03", f"Drink '{d['id']}' points at producer '{d['producerKey']}', which has no page")
        if not image_ok(d["thumb"]):
            issues.error("E03", f"Drink '{d['id']}' thumbnail {d['thumb']} does not exist")
        if not image_ok(d.get("label")):
            issues.error("E03", f"Drink '{d['id']}' label {d.get('label')} does not exist")
    in_use = {(d["category"], d["sub"]) for d in index}
    for route in sorted(routes):
        if route not in in_use:
            issues.error("E03", f"Shelf route {route[0]}/{route[1]} has no drinks")
    for c in shelf["categories"]:
        for s in c["subcategories"]:
            for lab in s["labels"]:
                if not image_ok(lab):
                    issues.error("E03", f"Label image {lab} does not exist")
    for rel, text in files.items():
        if rel.startswith("drinks/"):
            doc = json.loads(text)
            for field in ("prev", "next"):
                if doc[field] is not None and doc[field] not in ids:
                    issues.error("E03", f"{rel}: {field} '{doc[field]}' is not a drink")
            for mid in doc["moreFromProducer"]:
                if mid not in ids:
                    issues.error("E03", f"{rel}: moreFromProducer '{mid}' is not a drink")
            pk = doc["producer"]["key"]
            if pk is not None and pk not in pkeys:
                issues.error("E03", f"{rel}: producer key '{pk}' has no page")
            for ph in doc["photos"]:
                if not image_ok(ph["web"]):
                    issues.error("E03", f"{rel}: photo {ph['web']} does not exist")
        elif rel.startswith("producers/"):
            doc = json.loads(text)
            for dd in doc["drinks"]:
                if dd["id"] not in ids:
                    issues.error("E03", f"{rel}: drink '{dd['id']}' does not exist")
            for r in doc["related"]:
                if r["key"] not in pkeys:
                    issues.error("E03", f"{rel}: related '{r['key']}' has no page")
            for k in doc["moreFromRegion"]:
                if k not in pkeys:
                    issues.error("E03", f"{rel}: moreFromRegion '{k}' has no page")
    for p in producers:
        if f"producers/{p['key']}.json" not in files:
            issues.error("E03", f"Missing producers/{p['key']}.json")
