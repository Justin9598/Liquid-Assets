"""Which bottle shell each drink stands in (Plan 15 section 4).

`content/bottles.json` is the hand-checked list (drink ID -> shell key). Any drink the list does not name gets a default
worked out from its category, subcategory, sizes and wine colour (section 4.2). The result is `d["shell"]`, published on
drinks.json records and on the counter and shelf-view items. Nothing but IDs and shell keys is in the list.
"""
from __future__ import annotations

import json
from pathlib import Path

from .ledger import size_ml

# Used only when content/shells.json is not there (a test project): the keys section 2 of Plan 15 names.
SHELL_KEYS = [
    "sake-green", "sake-black", "sake-brown", "sake-clear", "sake-frosted", "sake-cobalt", "sake-skyblue", "sake-pink",
    "sake-isshobin", "sake-small", "sake-sparkling", "sake-craft",
    "beer-bottle", "beer-can", "beer-can-tall", "beer-pint", "beer-tulip", "beer-weizen", "beer-stout",
    "wine-red", "wine-white", "wine-rose", "champagne", "shochu", "shochu-jar", "soju",
    "whisky", "whisky-round", "gin", "brandy", "spirit-clear", "makgeolli", "makgeolli-tall",
    "cocktail-highball", "cocktail-rocks", "cocktail-coupe", "cocktail-martini", "cocktail-can",
    "liqueur", "liqueur-round", "umeshu", "yuzu", "tasting-glass",
]

BEER_GLASS = {"wheat": "beer-weizen", "ipa": "beer-tulip", "specialty": "beer-tulip", "saison": "beer-tulip",
              "stout-porter": "beer-stout", "stout": "beer-stout", "porter": "beer-stout"}
WINE_COLOUR = {"red": "wine-red", "white": "wine-white", "rose": "wine-rose", "sparkling": "champagne"}
USA = {"usa", "us", "u.s.a.", "united states", "united states of america"}


def _containers(sizes):
    """The bottles and cans among a drink's sizes as (kind, ml) pairs. A 60 ml tasting, a pour or a pint is never one."""
    out = []
    for s in sizes or []:
        low = str(s).casefold()
        ml = size_ml(s) or 0
        if "can" in low:
            out.append(("can", ml))
        elif "bottle" in low or "magnum" in low:
            out.append(("bottle", ml))
    return out


def _largest(sizes):
    """The largest bottle or can decides (Plan 15 section 4.2); None when the drink only came by the glass."""
    c = _containers(sizes)
    return max(c, key=lambda k: k[1]) if c else None


def _norm(text):
    return (str(text or "")).casefold().replace("é", "e").replace("ï", "i").strip()


def default_shell(d):
    """The section 4.2 default for a drink record (needs category, sub, sizes, country, detail)."""
    cat, sub = d.get("category"), d.get("sub")
    if cat is None:
        return None
    if cat == "sake":
        return "sake-green"
    if cat == "fermented":
        if sub == "makgeolli":
            return "makgeolli"
        big = _largest(d.get("sizes"))
        if big and big[0] == "bottle":
            return "beer-bottle"
        if big and big[0] == "can":
            return "beer-can-tall" if big[1] >= 400 else "beer-can"
        return BEER_GLASS.get(sub, "beer-pint")
    if cat == "wine":
        colour = _norm((d.get("detail", {}).get("Wine Detail") or {}).get("Colour"))
        return WINE_COLOUR.get(colour, "wine-red")
    if cat == "spirits":
        if sub == "whisky":
            return "whisky-round" if _norm(d.get("country")) in USA else "whisky"
        return {"gin": "gin", "brandy": "brandy", "shochu": "shochu", "soju": "soju"}.get(sub, "spirit-clear")
    if cat == "umeshu":
        return "umeshu"
    if cat == "liqueur":
        return "liqueur"
    if cat == "cocktails":
        big = _largest(d.get("sizes"))
        if big and big[0] == "can":
            return "cocktail-can"
        return "cocktail-highball" if sub == "highball" else "cocktail-coupe"
    return None


def load_bottles(content_dir, issues):
    """The ID -> shell key mapping from content/bottles.json (absent or broken: warn and use defaults only)."""
    path = Path(content_dir) / "bottles.json"
    if not path.exists():
        issues.warn("W20", "content/bottles.json not found; every drink gets its default bottle shell")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        issues.error("E04", f"content/bottles.json is not valid JSON: {exc}")
        return {}
    b = data.get("bottles") if isinstance(data, dict) else None
    if not isinstance(b, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in b.items()):
        issues.error("E04", "content/bottles.json needs a 'bottles' object of drink ID -> shell key")
        return {}
    return b


def known_shells(content_dir):
    path = Path(content_dir) / "shells.json"
    try:
        keys = list(json.loads(path.read_text(encoding="utf-8"))["shells"])
    except (OSError, ValueError, KeyError, TypeError):
        keys = []
    return set(keys) if keys else set(SHELL_KEYS)


def assign(drinks, content_dir, issues):
    """Set d["shell"] on every drink. E09 for a shell key the list names that does not exist, W28 for an ID that is not in Core.
    Returns the report data: counts by shell, and the sakes standing on the default."""
    bottles = load_bottles(content_dir, issues)
    known = known_shells(content_dir)
    ids = {d["id"] for d in drinks}
    for did, key in bottles.items():
        if did not in ids:
            issues.warn("W28", f"bottles.json names '{did}', which is not a drink in Core; the entry is ignored")
        if key not in known:
            issues.error("E09", f"bottles.json names the shell '{key}' for '{did}', which is not a shell in content/shells.json")
    counts, sakes_default = {}, []
    for d in drinks:
        key = bottles.get(d["id"])
        listed = key in known if key else False
        d["shell"] = key if listed else default_shell(d)
        if d["shell"]:
            counts[d["shell"]] = counts.get(d["shell"], 0) + 1
        if d.get("category") == "sake" and not listed:
            sakes_default.append(d["name"])
    return {"counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))), "sakes_default": sakes_default,
            "listed": sum(1 for d in drinks if bottles.get(d["id"]) in known)}
