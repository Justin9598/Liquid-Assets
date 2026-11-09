"""S10 Checks: privacy scan (E02), references (E03) and schema (E04) over the emitted data."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

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
        "visits": [{"date": "s?", "size": "s?", "where": "s?", "note": "s?"}],
        "photos": [{"kind": "s", "caption": "s", "web": "s", "w": "i", "h": "i"}],
        "moreFromProducer": ["s"], "prev": "s?", "next": "s?"},
    "producers.json": [{
        "key": "s", "name": "s", "native": "s?", "region": "s?", "country": "s?", "location": "s?",
        "brands": ["s"], "drinkCount": "i", "favourites": "i", "hasStory": "b",
        "lat": "n?", "lon": "n?", "cid": "s?", "prov": "s?", "provName": "s?", "area": "s?", "cont": "s?", "reg": "s?",
        "main": "s?", "exact": "b?"}],
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


def _norm_text(s):
    return " ".join(str(s).split()).casefold()


def load_private_notes(ledger_path):
    """The ledger's private `Notes` text, read only so the build can look for it in what it publishes (a deny-list).

    Nothing read here is ever copied into an output. Returns a list of (row, normalised text), leaving out notes that
    are short or that the owner has deliberately made public by writing the same text in that row's `Public Notes` or
    `Visit Note`. Returns [] when the ledger or the column is missing."""
    import openpyxl
    try:
        data = Path(ledger_path).read_bytes()
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb["Core"]
        rows = ws.iter_rows(values_only=True)
        head = [str(c).strip().casefold() if c is not None else "" for c in next(rows)]
    except Exception:
        return []
    col = {name: head.index(name) for name in ("notes", "public notes", "visit note") if name in head}
    if "notes" not in col:
        return []
    out = []
    for n, row in enumerate(rows, start=2):
        def cell(name):
            i = col.get(name)
            return _norm_text(row[i]) if i is not None and i < len(row) and row[i] else ""
        note = cell("notes")
        if len(note) >= 20 and note not in (cell("public notes"), cell("visit note")):
            out.append((n, note))
    wb.close()
    return out


def _scan_data_text(rel, text, markers, filenames, notes, issues, where="data/"):
    """E02 over one published data file: private markers, original photo filenames, Notes text, notes fields."""
    low = text.casefold()
    squashed = _norm_text(text)
    for m in markers:
        if m in low:
            issues.error("E02", f"Privacy leak: '{m}' found in published file {where}{rel}")
    for f in filenames:
        if f.casefold() in low:
            issues.error("E02", f"Privacy leak: an original photo filename ('{f}') appears in {where}{rel}")
    for row, note in notes:
        if note in squashed:
            issues.error("E02", f"Privacy leak: the Notes text of Core row {row} appears in {where}{rel}")
    try:
        data = json.loads(text)
    except ValueError:
        return
    for p, k in _walk_keys(data):
        if k.casefold() in ("notes", "public notes", "publicnotes") and rel not in ("subcategories.json",):
            issues.error("E02", f"Privacy leak: a '{k}' field is published in {where}{rel}{p}")


def check_privacy(files, photo_files, pages, issues, extra_markers=(), notes=()):
    """Fail (E02) when any published file holds private markers, a notes field, or draft research."""
    markers = [m.casefold() for m in list(PRIVATE_MARKERS) + list(extra_markers)]
    filenames = sorted({f for f in photo_files if len(f) >= 5})
    for rel, text in files.items():
        _scan_data_text(rel, text, markers, filenames, notes, issues)
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


_META_BYTES = (b"Exif" + bytes(2), b"<x:xmpmeta", b"http://ns.adobe.com/xap/", b"ICC_PROFILE")
_WEBP_META = {b"EXIF", b"XMP ", b"ICCP"}


def _webp_chunks(raw):
    """The chunk names of a WebP file (RIFF), or [] when it is not one."""
    if raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
        return []
    out, i = [], 12
    while i + 8 <= len(raw):
        out.append(raw[i:i + 4])
        size = int.from_bytes(raw[i + 4:i + 8], "little")
        i += 8 + size + (size & 1)
    return out


_PRICE_KEY = re.compile(r'"price"\s*:')
_PRICE_AMOUNT = re.compile(r"S\$\s*\d")


def scan_published(docs_dir, photo_files, notes, issues, extra_markers=()):
    """The last gate (Plan 08 section 6): everything actually on disk under docs/data and docs/img.

    Data files: private markers, original photo filenames, `Notes` text and notes fields (the same rules as the in-memory
    scan, so a stale file left from an earlier build is caught too). Image files: an original photo filename used as a
    file name or found in the file's bytes, and any EXIF, XMP or ICC metadata. Returns the number of files scanned."""
    docs = Path(docs_dir)
    markers = [m.casefold() for m in list(PRIVATE_MARKERS) + list(extra_markers)]
    filenames = sorted({f for f in photo_files if len(f) >= 5})
    names = {f.casefold() for f in filenames}
    name_re = re.compile(b"|".join(re.escape(f.encode("utf-8")) for f in filenames), re.I) if filenames else None
    count = 0
    for sub in ("data", "img"):
        base = docs / sub
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            count += 1
            rel = p.relative_to(docs).as_posix()
            if p.name.casefold() in names:                 # a published file is never called by an original photo's name
                issues.error("E02", f"Privacy leak: published file {rel} is named like an original photo")
            if p.suffix == ".json":
                if _PRICE_KEY.search(p.read_text(encoding="utf-8")) or _PRICE_AMOUNT.search(p.read_text(encoding="utf-8")):
                    issues.error("E02", f"Privacy leak: a price appears in published file {rel} (Plan 11)")
                _scan_data_text(p.relative_to(base).as_posix(), p.read_text(encoding="utf-8"), markers, filenames, notes,
                                issues, where=sub + "/")
                continue
            raw = p.read_bytes()
            bad = [m.decode("latin-1") for m in _META_BYTES if m in raw]
            bad += [c.decode("latin-1").strip() for c in _webp_chunks(raw) if c in _WEBP_META]
            if bad:
                issues.error("E02", f"Image metadata is not stripped in {rel} ({', '.join(sorted(set(bad)))})")
            if name_re is not None:
                hit = name_re.search(raw[:16384]) or name_re.search(raw[-16384:])
                if hit:
                    issues.error("E02", f"Privacy leak: an original photo filename appears inside {rel}")
    return count


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
