"""E07: an owner crop changed by anyone but the owner (Plan 13 sections 2.3 and 4).

An entry with `cropBy: "owner"` was drawn by hand in the crop tool. The build compares content/photo-map.json with the one
in the last commit. If an owner entry in that commit has since changed (its crop, its skip decision, or its owner mark) the
change must have been made by the tool, which logs a fingerprint of everything it saves in reports/owner-saves.json (local,
never committed). A change the tool did not make stops the build.

(The plan numbers this check E05, which the image encoder already uses, so it is E07 here.)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def entry_hash(entry: dict) -> str:
    """Must match croptool.entry_hash."""
    keys = ("labelStatus", "labelCrop", "labelSkip", "cropBy")
    payload = json.dumps([entry.get(k) for k in keys], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def head_map(root: Path):
    """content/photo-map.json as of the last commit, or None when there is no repository or no such file."""
    try:
        r = subprocess.run(["git", "-C", str(root), "show", "HEAD:content/photo-map.json"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def check_owner_crops(head: dict | None, current: dict, saved: dict, issues) -> int:
    """Raise E07 for every owner entry of the last commit that now differs, unless the tool saved the current state.
    Returns how many were raised."""
    if not head:
        return 0
    raised = 0
    for did, old in head.items():
        if not isinstance(old, dict) or old.get("cropBy") != "owner":
            continue
        new = current.get(did)
        if isinstance(new, dict) and entry_hash(new) == entry_hash(old):
            continue
        if isinstance(new, dict) and new.get("cropBy") == "owner" and saved.get(did) == entry_hash(new):
            continue                                         # the owner changed it again in the tool
        what = "was removed" if not isinstance(new, dict) else "was changed"
        issues.error("E07", f"Owner crop '{did}' {what} by something other than the crop tool. Owner crops are read-only: "
                            f"restore it from the last commit (git checkout content/photo-map.json) or redraw it in the tool")
        raised += 1
    return raised
