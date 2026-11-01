"""S1 Load and S2 Normalise: read the ledger through an allow-list (Plan 05 sections 5 and 8).

The ledger is opened from an in-memory copy of its bytes, so it is never written to and an open
Excel session cannot interfere. Columns that are not on an allow-list are never copied out,
which is how `Notes` stays out of the model altogether.
"""
from __future__ import annotations

import datetime as dt
import io
import re
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string, range_boundaries

from .common import BuildError, clean

# Allow-lists per sheet (canonical header names). Order is irrelevant: headers are read by name.
CORE_FIELDS = ["ID", "Name", "Category", "Size", "ABV %", "Producer", "Origin", "Country", "Style(s)",
               "Acquired", "Bought From", "Price (S$)", "Rating", "Favourite", "Added",
               "Public Notes", "Visit Note"]
CORE_REQUIRED = ["ID", "Name", "Category"]
CORE_OPTIONAL = ["Public Notes", "Visit Note"]

SHEET_FIELDS = {
    "Sake Detail": ["ID", "Grade", "Milling % (RPR)", "Rice", "Yeast", "SMV", "Acidity"],
    "Whisky Detail": ["ID", "Age Statement", "Cask Type", "Region", "Bottler", "Single Cask or Blend",
                      "Cask Strength", "Peated (ppm)"],
    "Wine Detail": ["ID", "Vintage", "Grape(s)", "Appellation", "Colour", "Sweetness", "Oak"],
    "Shochu Detail": ["ID", "Base Ingredient", "Koji", "Distillation", "Maturation"],
    "Other Detail": ["ID", "Base", "Flavouring or Botanicals", "Maturation", "Sweetness", "Yeast", "Type"],
    "Tasting Notes": ["ID", "Clarity", "App Intensity", "Colour", "App Other", "Nose Condition",
                      "Nose Intensity", "Aroma", "Sweetness", "Acidity", "Umami", "Alcohol", "Body",
                      "Mousse", "Flavour Intensity", "Flavour", "Palate Other", "Finish", "Quality",
                      "Category", "Ginjo?", "Production", "Special Style"],
    "Producers": ["Producer", "Page Key", "Display Name", "Native Name", "Brands", "Location", "Region",
                  "Country", "Founded", "Master", "Website", "About", "Related", "Sources", "Status"],
}
OPTIONAL_SHEETS = ["Producers"]
OPTIONAL_COLUMNS = {"Other Detail": ["Type"]}

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$")


class Ledger:
    """Loaded ledger: rows are (row_number, dict) tuples keyed by canonical header name."""

    def __init__(self):
        self.core = []                   # list[(rownum, dict)]
        self.sheets = {}                 # detail sheet name -> list[(rownum, dict)]
        self.validation = {}             # sheet name -> {header: [values]}
        self.saved = None                # datetime of last save (document properties)
        self.present_sheets = set()


def validation_lists(ws):
    """Return {header: [allowed values]} from a worksheet's list-type data validations."""
    headers = {}
    for cell in ws[1]:
        if cell.value is not None:
            headers[cell.column] = str(cell.value).strip()
    out = {}
    for dv in ws.data_validations.dataValidation:
        if dv.type != "list" or not dv.formula1:
            continue
        f = dv.formula1.strip()
        if not (f.startswith('"') and f.endswith('"')):
            continue  # a cell-range list; not used by this ledger
        values = [v.strip() for v in f[1:-1].split(",") if v.strip()]
        for rng in str(dv.sqref).split():
            try:
                min_col, _, _, _ = range_boundaries(rng)
            except ValueError:
                continue
            header = headers.get(min_col)
            if header and header not in out:
                out[header] = values
    return out


def _read_sheet(ws, allowed, sheet_name, issues, optional_cols=()):
    """Read rows by header name, copying only allow-listed columns. Skips rows with no key."""
    canon = {a.casefold(): a for a in allowed}
    col_for = {}
    for cell in ws[1]:
        if cell.value is None:
            continue
        name = canon.get(str(cell.value).strip().casefold())
        if name and name not in col_for:
            col_for[name] = cell.column
    missing = [a for a in allowed if a not in col_for]
    key_field = "Producer" if sheet_name == "Producers" else "ID"
    if key_field in missing:
        raise BuildError(f"Sheet '{sheet_name}' has no '{key_field}' column")
    rows = []
    max_col = max(col_for.values())
    for rownum, values in enumerate(ws.iter_rows(min_row=2, max_col=max_col, values_only=True), start=2):
        record = {}
        for name, col in col_for.items():
            record[name] = clean(values[col - 1]) if col - 1 < len(values) else None
        if record.get(key_field) in (None, ""):
            continue
        if not isinstance(record[key_field], str):
            record[key_field] = str(record[key_field])
        rows.append((rownum, record))
    return rows, missing


def load_ledger(path: Path, issues) -> Ledger:
    path = Path(path)
    if not path.exists():
        raise BuildError(f"Ledger not found: {path}")
    lock = path.with_name("~$" + path.name)
    if lock.exists():
        issues.warn("W14", "Excel has the ledger open (lock file present): unsaved edits are not included "
                           "in this build")
    data = path.read_bytes()
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=False, data_only=False)
    ledger = Ledger()
    try:
        ledger.saved = wb.properties.modified
    except Exception:  # pragma: no cover - property missing
        ledger.saved = None
    ledger.present_sheets = set(wb.sheetnames)

    if "Core" not in wb.sheetnames:
        raise BuildError("The ledger has no 'Core' sheet")
    ws = wb["Core"]
    rows, missing = _read_sheet(ws, CORE_FIELDS, "Core", issues)
    for field in missing:
        if field in CORE_REQUIRED:
            raise BuildError(f"Core has no '{field}' column")
        if field in CORE_OPTIONAL:
            issues.warn_once(("col", "Core", field), "W13",
                            f"Core has no '{field}' column yet (optional, treated as empty)", sheet="Core")
        else:
            issues.warn_once(("col", "Core", field), "W13",
                             f"Core has no '{field}' column (treated as empty)", sheet="Core")
    ledger.core = rows
    ledger.validation["Core"] = validation_lists(ws)

    for sheet, fields in SHEET_FIELDS.items():
        if sheet not in wb.sheetnames:
            issues.warn_once(("sheet", sheet), "W13",
                             f"Sheet '{sheet}' is missing from the ledger (treated as empty)", sheet=sheet)
            ledger.sheets[sheet] = []
            continue
        ws = wb[sheet]
        rows, missing = _read_sheet(ws, fields, sheet, issues)
        for field in missing:
            issues.warn_once(("col", sheet, field), "W13",
                             f"{sheet} has no '{field}' column (treated as empty)", sheet=sheet)
        ledger.sheets[sheet] = rows
        ledger.validation[sheet] = validation_lists(ws)
    wb.close()
    return ledger


# ---------------------------------------------------------------- S2 normalise helpers

def to_number(value, issues=None, where=None):
    """Number or None. Strings that parse as numbers are accepted."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else float(value)
    if isinstance(value, str):
        try:
            f = float(value.replace(",", ""))
            return int(f) if f.is_integer() else f
        except ValueError:
            pass
    if issues is not None and where:
        issues.warn("W15", f"Value '{value}' is not a number", **where)
    return None


def to_price(value, issues=None, where=None):
    n = to_number(value, issues, where)
    return None if n is None else round(float(n), 2)


def to_date(value, issues=None, where=None):
    """ISO date (YYYY-MM-DD) from a datetime or 'YYYY-MM-DD[ HH:MM]' string, else None."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str):
        m = _DATE_RE.match(value.strip())
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            except ValueError:
                pass
    if issues is not None and where:
        issues.warn("W15", f"Date '{value}' could not be parsed", **where)
    return None


_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ml|l)\b", re.I)


def size_ml(label):
    """Volume in ml from a size label ('1.8L Magnum' = 1800), or None when unknown ('Bottle')."""
    if not label:
        return None
    m = _SIZE_RE.match(label)
    if not m:
        return None
    n = float(m.group(1))
    ml = n * 1000 if m.group(2).lower() == "l" else n
    return int(round(ml))


def split_styles(value):
    if not value:
        return []
    seen, out = set(), []
    for part in str(value).split(","):
        part = clean(part)
        if part and part.casefold() not in seen:
            seen.add(part.casefold())
            out.append(part)
    return out
