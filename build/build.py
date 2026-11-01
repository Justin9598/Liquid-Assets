"""Liquid Assets data build (Plan 05).

Turns the private ledger and photos into the public site data in docs/data and docs/img.
    python Ship/build/build.py [--check] [--force-images] [--ledger PATH] [--photos PATH]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from liquid.pipeline import format_summary, run  # noqa: E402


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Build the Liquid Assets site data.")
    ap.add_argument("--check", action="store_true", help="validate and report only; write nothing to docs/")
    ap.add_argument("--force-images", action="store_true", help="re-encode every image")
    ap.add_argument("--ledger", help="path to the ledger (default ../Drinks Ledger.xlsx relative to Ship/)")
    ap.add_argument("--photos", help="path to the photos folder (default ../Photos relative to Ship/)")
    ap.add_argument("--phase", type=int, help="1 = welcome page only; 2 = the full site (default: content/phase.json)")
    ap.add_argument("--scene", help="folder with the rendered scene images (default ../Design/scene relative to Ship/)")
    ap.add_argument("--new", help="path to the inbox folder (default ../New relative to Ship/)")
    args = ap.parse_args(argv)
    root = HERE.parent  # Ship/
    res = run(root, ledger_path=args.ledger, photos_dir=args.photos, new_dir=args.new, scene_dir=args.scene, phase=args.phase,
              check=args.check, force_images=args.force_images)
    print(format_summary(res, check=args.check))
    return res.exit_code


if __name__ == "__main__":
    sys.exit(main())
