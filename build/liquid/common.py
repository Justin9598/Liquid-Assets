"""Shared helpers: text normalisation, slugs and the issue collector."""
from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def clean(value):
    """Trim, collapse whitespace, NFC-normalise. Empty strings become None.

    Non-string values are returned unchanged (numbers, dates)."""
    if value is None:
        return None
    if isinstance(value, str):
        text = unicodedata.normalize("NFC", value)
        text = _WS.sub(" ", text.replace(" ", " ")).strip()
        return text or None
    return value


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm_key(text) -> str:
    """Case, accent, spacing and punctuation insensitive comparison key."""
    if text is None:
        return ""
    text = strip_accents(str(text)).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def slugify(text, fallback="x") -> str:
    text = strip_accents(str(text or "")).casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def sort_key(text) -> tuple:
    """Name A-Z ordering that ignores case and accents."""
    return (strip_accents(str(text or "")).casefold(), str(text or ""))


class Issues:
    """Collects warnings (W..), info (I..) and errors (E..)."""

    def __init__(self):
        self.items = []  # dicts: level, code, message, sheet, row, drink
        self._once = set()

    def add(self, level, code, message, sheet=None, row=None, drink=None):
        self.items.append({"level": level, "code": code, "message": message,
                           "sheet": sheet, "row": row, "drink": drink})

    def warn(self, code, message, sheet=None, row=None, drink=None):
        self.add("warning", code, message, sheet, row, drink)

    def info(self, code, message, sheet=None, row=None, drink=None):
        self.add("info", code, message, sheet, row, drink)

    def error(self, code, message, sheet=None, row=None, drink=None):
        self.add("error", code, message, sheet, row, drink)

    def warn_once(self, key, code, message, **kw):
        if key in self._once:
            return
        self._once.add(key)
        self.warn(code, message, **kw)

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]

    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "warning"]

    def by_code(self, level=None):
        out = {}
        for i in self.items:
            if level and i["level"] != level:
                continue
            out.setdefault(i["code"], []).append(i)
        return dict(sorted(out.items()))

    def counts(self, level):
        return {code: len(v) for code, v in self.by_code(level).items()}


class BuildError(Exception):
    """Fatal problem (cannot continue)."""
