"""S7 Photo map: manual entries first, then exact-name auto matches. Fuzzy matches are only suggested.

Plan 05 S7 / Plan 01 section 6.1. The build never writes content/photo-map.json.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from .common import clean, norm_key

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIEW_RE = re.compile(r"(?:\s*\((back label|side label|second photo|spec panel|maker panel|\d+)\)|\.(front|back))\s*$", re.I)
VIEW_KIND = {"back label": "back", "side label": "side", "second photo": "second",
             "spec panel": "spec", "maker panel": "maker", "front": "front", "back": "back"}
KIND_CAPTION = {"front": "Front label", "back": "Back label", "side": "Side label",
                "second": "Second photo", "spec": "Spec panel", "maker": "Maker panel", "extra": "Photo"}
DEFAULT_LABEL_CROP = [0.15, 0.30, 0.70, 0.50]


def list_photos(folder: Path):
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted((p.name for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() in PHOTO_EXT), key=lambda n: (n.casefold(), n))


def split_view(stem):
    """(base stem, kind) where kind is a view kind or None for no view suffix."""
    m = VIEW_RE.search(stem)
    if not m:
        return stem, None
    label = (m.group(1) or m.group(2)).lower()
    kind = VIEW_KIND.get(label, "extra")
    return stem[:m.start()], kind


def load_manual_map(path: Path, issues):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.error("E04", f"content/photo-map.json is not valid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        issues.error("E04", "content/photo-map.json must be a JSON object keyed by drink ID")
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _valid_crop(value):
    return (isinstance(value, list) and len(value) == 4
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value)
            and value[2] > 0 and value[3] > 0 and value[0] >= 0 and value[1] >= 0
            and value[0] + value[2] <= 1.0001 and value[1] + value[3] <= 1.0001)


def build_photo_map(drinks, photo_files, manual, issues):
    """Returns (photo_map, unmatched, suggestions).

    photo_map: drink id -> {"front": file|None, "others": [{"file", "kind"}], "labelCrop", "thumbCrop", "source"}
    """
    drink_by_id = {d["id"]: d for d in drinks}
    files = set(photo_files)
    result = {}
    used = set()

    # 1. manual entries always win
    for did, entry in manual.items():
        if did not in drink_by_id:
            issues.warn("W16", f"content/photo-map.json has an entry for '{did}', which is not a drink in the "
                               f"ledger; it is ignored")
            continue
        if not isinstance(entry, dict):
            issues.error("E04", f"photo-map entry '{did}' must be an object")
            continue
        out = {"front": None, "others": [], "labelCrop": None, "thumbCrop": None, "source": "manual",
               "labelStatus": None, "labelSkip": None,
               "_fill_front": "front" not in entry, "_fill_others": "others" not in entry}
        front = entry.get("front")
        if front is not None:
            if front not in files:
                issues.error("E03", f"photo-map entry '{did}' names '{front}', which is not in Photos/",
                             drink=drink_by_id[did]["name"])
            else:
                out["front"] = front
                used.add(front)
        for o in entry.get("others", []) or []:
            f = o.get("file") if isinstance(o, dict) else None
            kind = (o.get("kind") if isinstance(o, dict) else None) or "extra"
            if f not in files:
                issues.error("E03", f"photo-map entry '{did}' names '{f}', which is not in Photos/",
                             drink=drink_by_id[did]["name"])
                continue
            out["others"].append({"file": f, "kind": kind})
            used.add(f)
        for crop_key in ("labelCrop", "thumbCrop"):
            if crop_key in entry and entry[crop_key] is not None:
                if _valid_crop(entry[crop_key]):
                    out[crop_key] = [float(x) for x in entry[crop_key]]
                else:
                    issues.error("E04", f"photo-map entry '{did}': {crop_key} must be [x, y, w, h] fractions "
                                        f"inside the image", drink=drink_by_id[did]["name"])
        status = entry.get("labelStatus")
        if status not in (None, "ok", "skip"):
            issues.error("E04", f"photo-map entry '{did}': labelStatus must be \"ok\" or \"skip\"", drink=drink_by_id[did]["name"])
        elif status == "ok" and not out["labelCrop"]:
            issues.error("E04", f"photo-map entry '{did}': labelStatus \"ok\" needs a valid labelCrop",
                         drink=drink_by_id[did]["name"])
        else:
            out["labelStatus"] = status
            out["labelSkip"] = entry.get("labelSkip") if status == "skip" else None
        result[did] = out

    # 2. exact auto matches for drinks without a manual entry
    key_to_ids = {}
    for d in drinks:
        key_to_ids.setdefault(norm_key(d["name"]), []).append(d["id"])
    auto = {}
    for name in photo_files:
        if name in used:
            continue
        stem = Path(name).stem
        # whole stem first, so a name such as "Jukyu HIRVI (19)" is not mistaken for a view suffix
        ids = key_to_ids.get(norm_key(stem))
        kind = "front"
        if not ids:
            base, view = split_view(stem)
            if view:
                ids = key_to_ids.get(norm_key(base))
                kind = view
        if not ids:
            continue
        did = ids[0]
        manual_entry = result.get(did)
        if manual_entry is not None:
            # a manual entry decides every field it states; fields it leaves out are filled by exact matches
            if kind == "front" and manual_entry["_fill_front"] and manual_entry["front"] is None:
                manual_entry["front"] = name
                used.add(name)
            elif kind != "front" and manual_entry["_fill_others"]:
                manual_entry["others"].append({"file": name, "kind": kind})
                used.add(name)
            continue
        slot = auto.setdefault(did, {"front": None, "others": []})
        if kind == "front":
            if slot["front"] is None:
                slot["front"] = name
            else:
                slot["others"].append({"file": name, "kind": "extra"})
        else:
            slot["others"].append({"file": name, "kind": kind})
        used.add(name)
    for did, slot in auto.items():
        result[did] = {"front": slot["front"], "others": slot["others"], "labelCrop": None, "labelStatus": None, "labelSkip": None,
                       "thumbCrop": None, "source": "exact"}

    for entry in result.values():
        entry.pop("_fill_front", None)
        entry.pop("_fill_others", None)
    unmatched = [n for n in photo_files if n not in used]
    suggestions = suggest(unmatched, drinks, result)
    return result, unmatched, suggestions


def suggest(unmatched, drinks, photo_map):
    """Prefix and fuzzy candidates for unmatched photos. These are never published."""
    cands = [(norm_key(d["name"]), d) for d in drinks]
    out = {}
    for name in unmatched:
        stem = Path(name).stem
        base, view = split_view(stem)
        key = norm_key(base)
        if len(key) < 4:
            continue
        found = []
        for dk, d in cands:
            reason, score = None, 0.0
            if dk.startswith(key):
                reason, score = "prefix: photo name is the start of the drink name", 0.95
            elif key.startswith(dk) and len(dk) >= 6:
                reason, score = "prefix: drink name is the start of the photo name", 0.9
            else:
                ratio = difflib.SequenceMatcher(None, key, dk).ratio()
                if ratio >= 0.72:
                    reason, score = "fuzzy: similar spelling", round(ratio, 3)
            if reason:
                found.append({"id": d["id"], "name": d["name"], "reason": reason, "score": round(score, 3),
                              "drinkHasFrontPhoto": bool(photo_map.get(d["id"], {}).get("front"))})
        found.sort(key=lambda c: (-c["score"], c["id"]))
        if found:
            out[name] = {"view": view or "front", "candidates": found[:3]}
    return out


def suggestions_document(suggestions, unmatched):
    """JSON for reports/photo-map.suggested.json: candidates plus a paste-ready block."""
    paste = {}
    for name, info in suggestions.items():
        top = info["candidates"][0]
        slot = paste.setdefault(top["id"], {"front": None, "others": []})
        if info["view"] == "front":
            if slot["front"] is None and not top["drinkHasFrontPhoto"]:
                slot["front"] = name
            else:
                slot["others"].append({"file": name, "kind": "extra"})
        else:
            slot["others"].append({"file": name, "kind": info["view"]})
    paste = {k: {kk: vv for kk, vv in v.items() if vv not in (None, [])} for k, v in paste.items()}
    return {
        "_readme": ("Suggestions only: the build never publishes these matches. Review each one, then copy the "
                    "entries you accept into Ship/content/photo-map.json. 'pasteAfterReview' uses the top "
                    "candidate for each photo."),
        "unmatchedPhotoCount": len(unmatched),
        "photos": suggestions,
        "pasteAfterReview": paste,
    }
