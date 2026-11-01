"""Derive the mask polygons in content/shells.json from the picture in Design/scene/shells-sheet.webp.

Run once, then edit the points by hand if a cut needs fixing (the build trusts the stored polygon).
    python build/tools/derive_shell_masks.py [--force]
Cells that already have a polygon are left alone unless --force is given. liqueur shares the spirits polygon.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from liquid import shells  # noqa: E402

ROOT = HERE.parents[1]                                  # Ship/
CFG = ROOT / "content" / "shells.json"
SHEET = ROOT.parent / "Design" / "scene" / "shells-sheet.webp"


def main(force=False):
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    with Image.open(SHEET) as im:
        sheet = im.convert("RGB")
    done = {}
    for key, spec in cfg["shells"].items():
        if spec.get("maskPolygon") and not force:
            continue
        sig = (spec["cell"], tuple(spec["crop"]))
        if sig in done:
            spec["maskPolygon"] = done[sig]
            continue
        x0, y0, x1, y1 = spec["crop"]
        rgb = np.asarray(sheet.crop((x0, y0, x1, y1)))
        poly = shells.derive_polygon(rgb, spec.get("thr", 14))
        spec["maskPolygon"] = poly
        done[sig] = poly
        print(f"{key}: {len(poly)} points")
    # one line per shell, polygon on its own line, so the file stays readable and diffs stay small
    lines = ["{", f' "_readme": {json.dumps(cfg["_readme"], ensure_ascii=False)},', f' "version": {cfg["version"]},',
             f' "source": {json.dumps(cfg["source"])},', ' "shells": {']
    keys = list(cfg["shells"])
    for i, k in enumerate(keys):
        s = dict(cfg["shells"][k])
        poly = s.pop("maskPolygon", None)
        body = json.dumps(s, ensure_ascii=False)
        if poly:
            body = body[:-1] + ', "maskPolygon": ' + json.dumps(poly) + "}"
        lines.append(f'  {json.dumps(k)}: {body}{"," if i < len(keys) - 1 else ""}')
    lines += [" }", "}", ""]
    CFG.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main("--force" in sys.argv)
