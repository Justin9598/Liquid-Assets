"""Derive the mask polygons in content/shells.json from the pictures on the Gemini sheets (Plan 15 section 5).

Run once after measure_shell_cells.py, then edit the points by hand if a cut needs fixing (the build trusts the stored
polygon). Each shell names its `source` sheet, which is read from Design/scene/shells/ (a private folder, never published).
    python build/tools/derive_shell_masks.py [--force]
Shells that already have a polygon are left alone unless --force is given.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from liquid import shells  # noqa: E402
import measure_shell_cells as M  # noqa: E402

CFG = M.CFG
SHEETS_DIR = M.SHEETS_DIR


def main(force=False):
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    sheets = {}
    for key, spec in cfg["shells"].items():
        if spec.get("maskPolygon") and not force:
            continue
        src = spec["source"]
        if src not in sheets:
            with Image.open(SHEETS_DIR / cfg["sources"][src]["file"]) as im:
                sheets[src] = im.convert("RGB")
        x0, y0, x1, y1 = spec["crop"]
        rgb = np.asarray(sheets[src].crop((x0, y0, x1, y1)))
        poly = shells.derive_polygon(rgb, spec.get("thr", 14))
        spec["maskPolygon"] = poly
        print(f"{key}: {len(poly)} points")
    M.write(cfg)


if __name__ == "__main__":
    main("--force" in sys.argv)
