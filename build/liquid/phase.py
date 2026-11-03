"""Phased launch (Plan 06 section 12). Phase 1 publishes the welcome page only; later phases turn sections on.

Phase 1: the bar, shelf swaps, label images, the scene and the menu. Nothing about drinks, shelf pages or makers.
Phase 2 and later: everything (the full site).
"""
from __future__ import annotations

import json
from pathlib import Path

FULL = {"welcome": True, "shelves": True, "drinks": True, "makers": True}
WELCOME_ONLY = {"welcome": True, "shelves": False, "drinks": False, "makers": False}


def sections(phase: int) -> dict:
    return dict(WELCOME_ONLY if phase <= 1 else FULL)


def read_phase(content_dir, default=2) -> int:
    """content/phase.json, e.g. {"phase": 1}. `--phase` on the command line overrides it."""
    p = Path(content_dir) / "phase.json"
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("phase", default))
    except (OSError, ValueError, TypeError):
        return default


def published(rel: str, sec: dict) -> bool:
    """Is this data file (path relative to docs/data) published in the given sections?"""
    if rel in ("shelf.json", "build.json", "scene.json", "aliases.json"):
        return True
    if rel == "drinks.json":
        return sec["shelves"] or sec["drinks"]
    if rel == "subcategories.json":
        return sec["shelves"]
    if rel == "glossary.json" or rel.startswith("drinks/"):
        return sec["drinks"]
    if rel.startswith("producers"):
        return sec["makers"]
    return True


def keep_job(job: dict, sec: dict) -> bool:
    """Which converted photos a phase needs: labels always, card thumbnails with shelves, drink photos with drinks."""
    t = job["type"]
    if t == "label":
        return True
    if t == "thumb":
        return sec["shelves"] or sec["drinks"]
    return sec["drinks"]
