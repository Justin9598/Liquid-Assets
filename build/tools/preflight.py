"""Pre-flight audit (Plan 01 section 7.5): visible strings must have no em or en dashes.

Scans the site code (docs/ except generated data, fonts and icons) and the hand-edited content/ files.
Usage: python preflight.py   (exits 1 when it finds any)
"""
import re
import sys
from pathlib import Path

SHIP = Path(__file__).resolve().parents[2]
DASHES = re.compile("[–—]|\\\\u201[34]")
SKIP_PARTS = {"fonts", "icons", "data", "img"}


def scan(ship=SHIP):
    hits = []
    for root in ("docs", "content"):
        base = Path(ship) / root
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in (".js", ".html", ".css", ".json", ".txt", ".svg"):
                continue
            if SKIP_PARTS & set(p.relative_to(base).parts[:-1]):
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for m in DASHES.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append((str(p.relative_to(ship)), line, text[max(0, m.start() - 30):m.end() + 20].replace("\n", " ")))
    return hits


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    found = scan()
    for f, line, ctx in found:
        print(f"{f}:{line}: {ctx}")
    print(f"{len(found)} dash(es) found")
    sys.exit(1 if found else 0)
