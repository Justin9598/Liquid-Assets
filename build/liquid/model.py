"""S2 - S5: normalise, combine occasions into drinks, join detail sheets, classify.

Also builds the per-category spec list (Plan 03 section 5), the card facts (Plan 02 section 7.2)
and the tasting card (Plan 03 section 6), so that the pages need no logic per category.
"""
from __future__ import annotations

import re

from . import taxonomy as T
from .common import clean, norm_key, slugify, sort_key
from .ledger import size_ml, split_styles, to_date, to_number, to_price

COMPARE_FIELDS = ["Name", "Category", "ABV %", "Producer", "Origin", "Country", "Style(s)"]


# ------------------------------------------------------------------ S3 combine

def _norm_compare(field, value):
    if field == "ABV %":
        n = to_number(value)
        return None if n is None else round(float(n), 4)
    if field == "Style(s)":
        return tuple(s.casefold() for s in split_styles(value))
    return None if value is None else str(value)


def combine_drinks(ledger, issues):
    """Group Core rows by ID into drinks (Plan 05 S3). Returns a list in first-seen ledger order."""
    groups = {}
    order = []
    for rownum, row in ledger.core:
        did = row["ID"]
        if did not in groups:
            groups[did] = []
            order.append(did)
        groups[did].append((rownum, row))

    drinks = []
    for did in order:
        rows = groups[did]
        first_num, first = rows[0]
        name = first.get("Name") or did
        # W06 disagreement
        for field in COMPARE_FIELDS:
            base = _norm_compare(field, first.get(field))
            for rownum, row in rows[1:]:
                if _norm_compare(field, row.get(field)) != base:
                    issues.warn("W06", f"Rows sharing ID '{did}' disagree on {field} "
                                       f"('{first.get(field)}' vs '{row.get(field)}'); the first row is used",
                                sheet="Core", row=rownum, drink=name)
        visits = []
        added_dates = []
        sizes = []
        for rownum, row in rows:
            where_ctx = {"sheet": "Core", "row": rownum, "drink": name}
            added = to_date(row.get("Added"), issues, where_ctx)
            acquired = to_date(row.get("Acquired"), issues, where_ctx)
            if added:
                added_dates.append(added)
            bought = row.get("Bought From")
            if bought is not None and str(bought).strip().casefold() == "unknown":
                bought = None
            size = row.get("Size")
            if size:
                sizes.append(size)
            visits.append({
                "date": acquired or added,
                "size": size,
                "where": bought,
                "price": to_price(row.get("Price (S$)"), issues, where_ctx),
                "note": row.get("Visit Note"),
                "_row": rownum,
            })
        sizes = sorted(set(sizes), key=lambda s: (size_ml(s) is None, size_ml(s) or 0, s))
        story = next((r.get("Public Notes") for _, r in rows if r.get("Public Notes")), None)
        ctx = {"sheet": "Core", "row": first_num, "drink": name}
        drinks.append({
            "id": did,
            "name": name,
            "core_category": first.get("Category"),
            "abv": to_number(first.get("ABV %"), issues, ctx),
            "producer_raw": first.get("Producer"),
            "origin": first.get("Origin"),
            "country": first.get("Country"),
            "styles": split_styles(first.get("Style(s)")),
            "favourite": any(r.get("Favourite") == "★" for _, r in rows),
            "rating": to_number(first.get("Rating"), issues, ctx),
            "added": max(added_dates) if added_dates else None,
            "sizes": sizes,
            "visits": visits,
            "story": story,
            "_row": first_num,
        })
    return drinks


# ------------------------------------------------------------------ S4 join details

DETAIL_SHEETS = ["Sake Detail", "Whisky Detail", "Wine Detail", "Shochu Detail", "Other Detail", "Tasting Notes"]


def join_details(ledger, drinks, issues):
    """Attach `detail` dicts keyed by sheet name. Orphan detail rows give W11 and are dropped."""
    by_id = {d["id"]: d for d in drinks}
    for d in drinks:
        d["detail"] = {}
    for sheet in DETAIL_SHEETS:
        for rownum, row in ledger.sheets.get(sheet, []):
            did = row["ID"]
            drink = by_id.get(did)
            if drink is None:
                issues.warn("W11", f"{sheet} row has ID '{did}' which is not in Core; the row is ignored",
                            sheet=sheet, row=rownum)
                continue
            if sheet in drink["detail"]:
                issues.warn("W17", f"{sheet} has more than one row for '{did}'; the first is used",
                            sheet=sheet, row=rownum, drink=drink["name"])
                continue
            drink["detail"][sheet] = {k: v for k, v in row.items() if k != "ID"}
            drink["detail"][sheet]["_row"] = rownum


# ------------------------------------------------------------------ S5 classify

GRAPE_SPLIT = re.compile(r"\s*(?:,|;|/|&|\band\b)\s*", re.I)


def _grape_display(text):
    text = clean(text) or ""
    return text.title() if text.islower() or text.isupper() else text


def _match_type(value, valid):
    """Canonical type from `valid` matching value case/accent-insensitively, else None."""
    k = norm_key(value)
    for v in valid:
        if norm_key(v) == k:
            return v
    return None


def classify(ledger, drinks, issues):
    """Assign category, sub and sub_name to each drink. Returns the ordered sake grade list."""
    grades = ledger.validation.get("Sake Detail", {}).get("Grade") or T.DEFAULT_SAKE_GRADES
    for d in drinks:
        raw = d["core_category"]
        cat = T.CORE_TO_CATEGORY.get(raw)
        d["category"] = cat
        d["sub"] = d["sub_name"] = None
        d["sub_order"] = (0, "")
        ctx = {"sheet": "Core", "row": d["_row"], "drink": d["name"]}
        if cat is None:
            issues.warn("W07", f"Unknown Core.Category '{raw}': the drink is left out of the shelves but "
                               f"still gets a drink page", **ctx)
            continue
        other = d["detail"].get("Other Detail", {})
        typ = other.get("Type")
        if cat == "sake":
            if raw == "Craft Sake":
                d["sub"], d["sub_name"], d["sub_order"] = "craft-sake", "Craft Sake", (len(grades), "")
                continue
            grade = d["detail"].get("Sake Detail", {}).get("Grade")
            matched = _match_type(grade, grades) if grade else None
            if grade and not matched:
                issues.warn("W09", f"Sake grade '{grade}' is not in the validation list; filed under Ungraded",
                            sheet="Sake Detail", row=d["detail"]["Sake Detail"].get("_row"), drink=d["name"])
            if matched:
                d["sub"], d["sub_name"], d["sub_order"] = slugify(matched), matched, (grades.index(matched), "")
            else:
                d["sub"], d["sub_name"], d["sub_order"] = "ungraded", "Ungraded", (len(grades) + 1, "")
        elif cat == "makgeolli":
            _fallback(d, cat, issues, warn=False)
        elif cat == "wine":
            grape = d["detail"].get("Wine Detail", {}).get("Grape(s)")
            parts = [p for p in GRAPE_SPLIT.split(grape or "") if p.strip()]
            uniq = {}
            for p in parts:
                uniq.setdefault(norm_key(p), _grape_display(p))
            if len(uniq) == 1:
                name = next(iter(uniq.values()))
                d["sub"], d["sub_name"], d["sub_order"] = slugify(name), name, (0, sort_key(name)[0])
            elif len(uniq) >= 2:
                d["sub"], d["sub_name"], d["sub_order"] = "blend", "Blend", (1, "")
            else:
                _fallback(d, cat, issues, reason="Grape(s) is empty")
        elif cat == "spirits":
            if raw in T.SPIRIT_CORE_SUBS:
                name = T.SPIRIT_CORE_SUBS[raw]
                _spirit_sub(d, name)
            else:  # Core.Category = Spirit
                if not typ:
                    _fallback(d, cat, issues, reason="Other Detail.Type is empty")
                else:
                    matched = _match_type(typ, T.TYPE_VALUES["spirit"])
                    if matched:
                        _spirit_sub(d, matched)
                    else:
                        issues.warn("W03", f"Type '{typ}' is not a valid spirit type "
                                           f"({', '.join(T.TYPE_VALUES['spirit'])})",
                                    sheet="Other Detail", row=other.get("_row"), drink=d["name"])
                        _fallback(d, cat, issues, reason=f"Type '{typ}' is not valid", warn=False)
        elif cat == "liqueur":
            if raw == "Umeshu":
                d["sub"], d["sub_name"], d["sub_order"] = "umeshu", "Umeshu", (0, "")
                if typ and not _match_type(typ, T.TYPE_VALUES["umeshu"]):
                    issues.warn("W03", f"Type '{typ}' is not a valid umeshu flavour/base "
                                       f"(allowed: {', '.join(T.TYPE_VALUES['umeshu'])})",
                                sheet="Other Detail", row=other.get("_row"), drink=d["name"])
            else:  # Core.Category = Liqueur: the kind comes from Other Detail.Type
                valid = T.TYPE_VALUES["liqueur"]
                if not typ:
                    _fallback(d, cat, issues, reason="Other Detail.Type is empty")
                else:
                    matched = _match_type(typ, valid)
                    if matched:
                        d["sub"], d["sub_name"], d["sub_order"] = slugify(matched), matched, (1, sort_key(matched)[0])
                    else:
                        issues.warn("W03", f"Type '{typ}' is not valid for Liqueur (allowed: {', '.join(valid)})",
                                    sheet="Other Detail", row=other.get("_row"), drink=d["name"])
                        _fallback(d, cat, issues, reason=f"Type '{typ}' is not valid", warn=False)
        else:  # beer, cocktails: sub-type from Other Detail.Type
            valid = T.TYPE_VALUES[cat]
            if not typ:
                _fallback(d, cat, issues, reason="Other Detail.Type is empty")
            else:
                matched = _match_type(typ, valid)
                if matched:
                    d["sub"], d["sub_name"], d["sub_order"] = slugify(matched), matched, (valid.index(matched), "")
                else:
                    issues.warn("W03", f"Type '{typ}' is not valid for {T.CATEGORY_NAMES[cat]} "
                                       f"(allowed: {', '.join(valid)})",
                                sheet="Other Detail", row=other.get("_row"), drink=d["name"])
                    _fallback(d, cat, issues, reason=f"Type '{typ}' is not valid", warn=False)
    _name_fallbacks(drinks)
    return grades


def _name_fallbacks(drinks):
    """Plan 01 section 4 shared rule: where some drinks in a category have a sub-type, the ones without go into
    an 'Other {category}' bottle (key `other`); where none do, the single `all` bottle stays."""
    by_cat = {}
    for d in drinks:
        if d["category"]:
            by_cat.setdefault(d["category"], []).append(d)
    for cat, ds in by_cat.items():
        if any(d["sub"] != "all" for d in ds):
            for d in ds:
                if d["sub"] == "all":
                    d["sub"], d["sub_name"] = "other", T.OTHER_NAME.get(cat, f"Other {T.CATEGORY_NAMES[cat].lower()}")


def _spirit_sub(d, name):
    d["sub"], d["sub_name"] = slugify(name), name
    if name in T.SPIRIT_FIRST:
        d["sub_order"] = (T.SPIRIT_FIRST.index(name), "")
    else:
        d["sub_order"] = (len(T.SPIRIT_FIRST), sort_key(name)[0])


def _fallback(d, cat, issues, reason=None, warn=True):
    d["sub"], d["sub_name"] = "all", T.FALLBACK_NAME[cat]
    d["sub_order"] = (10_000, "")
    if warn and reason:
        issues.warn("W10", f"{reason}: filed under the fallback bottle ('{T.FALLBACK_NAME[cat]}' or 'Other ...')",
                    sheet="Core", row=d["_row"], drink=d["name"])


# ------------------------------------------------------------------ spec list (Plan 03 section 5)

def _put(items, label, value, **extra):
    if value is None or value == "" or value == []:
        return
    item = {"label": label, "value": value}
    item.update(extra)
    items.append(item)


def build_spec(d):
    detail = d["detail"]
    cat = d["category"]
    raw = d["core_category"]
    items = []
    if cat == "sake":
        s = detail.get("Sake Detail", {})
        _put(items, "Grade", s.get("Grade"))
        rpr = to_number(s.get("Milling % (RPR)"))
        _put(items, "Polishing ratio", rpr, unit="%", viz="polish")
        _put(items, "Rice", s.get("Rice"))
        _put(items, "Yeast", s.get("Yeast"))
        _put(items, "SMV", to_number(s.get("SMV")), viz="smv")
        _put(items, "Acidity", to_number(s.get("Acidity")))
    elif cat == "wine":
        w = detail.get("Wine Detail", {})
        _put(items, "Vintage", w.get("Vintage"))
        _put(items, "Grape(s)", w.get("Grape(s)"))
        _put(items, "Appellation", w.get("Appellation"))
        _put(items, "Colour", w.get("Colour"))
        _put(items, "Sweetness", w.get("Sweetness"))
        _put(items, "Oak", w.get("Oak"))
    elif raw == "Whisky":
        w = detail.get("Whisky Detail", {})
        _put(items, "Age statement", w.get("Age Statement"))
        _put(items, "Cask type", w.get("Cask Type"))
        _put(items, "Region", w.get("Region"))
        _put(items, "Bottler", w.get("Bottler"))
        _put(items, "Single cask or blend", w.get("Single Cask or Blend"))
        _put(items, "Cask strength", w.get("Cask Strength"))
        _put(items, "Peat (ppm)", to_number(w.get("Peated (ppm)")))
    elif raw in ("Shochu", "Soju"):
        s = detail.get("Shochu Detail", {})
        _put(items, "Base ingredient", s.get("Base Ingredient"))
        _put(items, "Kōji", s.get("Koji"))
        _put(items, "Distillation", s.get("Distillation"))
        _put(items, "Maturation", s.get("Maturation"))
    else:  # makgeolli, liqueur, beer, spirit (gin, brandy), cocktail
        o = detail.get("Other Detail", {})
        _put(items, "Type", o.get("Type"))
        _put(items, "Base", o.get("Base"))
        _put(items, "Flavouring or botanicals", o.get("Flavouring or Botanicals"))
        _put(items, "Maturation", o.get("Maturation"))
        _put(items, "Sweetness", o.get("Sweetness"))
        _put(items, "Yeast", o.get("Yeast"))
    _put(items, "ABV", d["abv"], unit="%")
    _put(items, "Size", ", ".join(d["sizes"]) if d["sizes"] else None)
    return items


# ------------------------------------------------------------------ card facts (Plan 02 section 7.2)

def _fmt(v):
    if v is None or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def build_facts(d):
    detail = d["detail"]
    raw = d["core_category"]
    cat = d["category"]
    facts = []
    if cat == "sake" and raw != "Craft Sake":
        s = detail.get("Sake Detail", {})
        rpr = _fmt(to_number(s.get("Milling % (RPR)")))
        facts = [f"Polished {rpr}%" if rpr else None, _fmt(s.get("Rice"))]
    elif raw == "Craft Sake":
        o = detail.get("Other Detail", {})
        facts = [_fmt(o.get("Flavouring or Botanicals")) or _fmt(o.get("Base")),
                 d["styles"][0] if d["styles"] else None]
    elif cat == "makgeolli":
        o = detail.get("Other Detail", {})
        facts = [_fmt(o.get("Base")), _fmt(o.get("Flavouring or Botanicals"))]
    elif cat == "liqueur":
        o = detail.get("Other Detail", {})
        if raw == "Umeshu":   # flavour/base (Type), then base (Plan 02 section 7.2)
            facts = [_fmt(o.get("Type")), _fmt(o.get("Base"))]
        else:
            facts = [_fmt(o.get("Base")), _fmt(o.get("Flavouring or Botanicals"))]
    elif cat == "beer":
        o = detail.get("Other Detail", {})
        facts = [_fmt(o.get("Type")), _fmt(o.get("Yeast"))]
    elif cat == "wine":
        w = detail.get("Wine Detail", {})
        facts = [_fmt(w.get("Vintage")), _fmt(w.get("Appellation"))]
    elif raw == "Whisky":
        w = detail.get("Whisky Detail", {})
        facts = [_fmt(w.get("Age Statement")) or _fmt(w.get("Single Cask or Blend")),
                 _fmt(w.get("Region")) or _fmt(w.get("Cask Type"))]
    elif raw in ("Shochu", "Soju"):
        s = detail.get("Shochu Detail", {})
        facts = [_fmt(s.get("Base Ingredient")), _fmt(s.get("Koji"))]
    elif raw == "Spirit":
        o = detail.get("Other Detail", {})
        facts = [_fmt(o.get("Base")), _fmt(o.get("Maturation"))]
    elif cat == "cocktails":
        o = detail.get("Other Detail", {})
        facts = [_fmt(o.get("Base"))]
    return [f for f in facts if f][:2]


# ------------------------------------------------------------------ tasting card (Plan 03 section 6)

_TASTING_SCALE_FIELDS = {
    "clarity": "Clarity", "appearanceIntensity": "App Intensity", "colour": "Colour",
    "noseCondition": "Nose Condition", "noseIntensity": "Nose Intensity", "sweetness": "Sweetness",
    "acidity": "Acidity", "umami": "Umami", "alcohol": "Alcohol", "body": "Body", "mousse": "Mousse",
    "flavourIntensity": "Flavour Intensity", "finish": "Finish", "quality": "Quality",
    "category": "Category", "ginjo": "Ginjo?",
}


def _tags(value):
    if not value:
        return []
    return [p for p in (clean(x) for x in str(value).split(",")) if p]


def _compact(obj):
    out = {}
    for k, v in obj.items():
        if v is None or v == "" or v == []:
            continue
        out[k] = v
    return out


def build_tasting(d, ledger):
    t = d["detail"].get("Tasting Notes")
    if not t:
        return None
    appearance = _compact({"clarity": t.get("Clarity"), "intensity": t.get("App Intensity"),
                           "colour": t.get("Colour"), "other": t.get("App Other")})
    nose = _compact({"condition": t.get("Nose Condition"), "intensity": t.get("Nose Intensity"),
                     "aroma": _tags(t.get("Aroma"))})
    palate = _compact({"sweetness": t.get("Sweetness"), "acidity": t.get("Acidity"), "umami": t.get("Umami"),
                       "body": t.get("Body"), "flavourIntensity": t.get("Flavour Intensity"),
                       "finish": t.get("Finish"), "alcohol": t.get("Alcohol"), "mousse": t.get("Mousse"),
                       "flavour": _tags(t.get("Flavour")), "other": t.get("Palate Other")})
    conclusion = _compact({"quality": t.get("Quality"), "category": t.get("Category"),
                           "ginjo": t.get("Ginjo?"), "production": t.get("Production"),
                           "special": t.get("Special Style")})
    out = {}
    for key, block in (("appearance", appearance), ("nose", nose), ("palate", palate),
                       ("conclusion", conclusion)):
        if block:
            out[key] = block
    if not out:
        return None
    lists = ledger.validation.get("Tasting Notes", {})
    out["scales"] = {k: lists[h] for k, h in _TASTING_SCALE_FIELDS.items() if h in lists}
    return out
