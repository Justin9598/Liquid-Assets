"""The build pipeline (Plan 05 section 5), end to end."""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from . import assets as assets_mod, phase as phase_mod, scene as scene_mod, checks, emit as emit_mod, images, og as og_mod, model, photos as photos_mod, producers as producers_mod
from . import burger as burger_mod, counter as counter_mod, report as report_mod, scene_report
from .common import BuildError, Issues
from .ledger import load_ledger


class Result:
    def __init__(self):
        self.issues = Issues()
        self.summary = {}
        self.files = {}
        self.exit_code = 0
        self.report_path = None


def _load_json(path, default, issues, label, code="W20"):
    path = Path(path)
    if not path.exists():
        issues.warn(code, f"content/{label} not found; the site will have no {label.split('.')[0]} copy")
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        issues.error("E04", f"content/{label} is not valid JSON: {exc}")
        return default
    if not isinstance(data, dict):
        issues.error("E04", f"content/{label} must be a JSON object")
        return default
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _generated(ledger, ledger_path):
    """Timestamp of the ledger's last save (file modification time, UTC), not the build time."""
    try:
        saved = dt.datetime.fromtimestamp(Path(ledger_path).stat().st_mtime, dt.timezone.utc).replace(tzinfo=None)
    except OSError:
        saved = ledger.saved
    return saved.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(root, ledger_path=None, photos_dir=None, new_dir=None, check=False, force_images=False, scene_dir=None, phase=None):
    root = Path(root)
    res = Result()
    issues = res.issues
    ledger_path = Path(ledger_path) if ledger_path else root.parent / "Drinks Ledger.xlsx"
    photos_dir = Path(photos_dir) if photos_dir else root.parent / "Photos"
    new_dir = Path(new_dir) if new_dir else root.parent / "New"
    scene_dir = Path(scene_dir) if scene_dir else root.parent / "Design" / "scene"
    docs, data_dir = root / "docs", root / "docs" / "data"
    content_dir, reports_dir = root / "content", root / "reports"
    cache_path = root / "build" / ".image-cache.json"
    phase = phase if phase is not None else phase_mod.read_phase(content_dir)
    sections = phase_mod.sections(phase)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # S1 - S5
    try:
        ledger = load_ledger(ledger_path, issues)
    except BuildError as exc:
        issues.error("E01", str(exc))
        res.exit_code = 1
        return res
    drinks = model.combine_drinks(ledger, issues)
    model.join_details(ledger, drinks, issues)
    grades = model.classify(ledger, drinks, issues)

    # S6
    pages, key_by_text = producers_mod.build_producers(ledger, drinks, issues)

    # S7
    photo_files = photos_mod.list_photos(photos_dir)
    manual = photos_mod.load_manual_map(content_dir / "photo-map.json", issues)
    photo_map, unmatched, suggestions = photos_mod.build_photo_map(drinks, photo_files, manual, issues)
    for name in unmatched:
        issues.warn("W01", f"Photo not matched to any drink: {name}", sheet="Photos")
    for d in drinks:
        e = photo_map.get(d["id"], {})
        if not e.get("front"):
            issues.warn("W02", "Drink has no front photo", sheet="Core", row=d["_row"], drink=d["name"])
        elif e.get("labelStatus") is None:
            issues.warn("W21", "Front photo has no label judgement yet: add labelCrop plus labelStatus "
                               "(ok or skip) to content/photo-map.json", sheet="Photos", drink=d["name"])
        elif e["labelStatus"] == "skip":
            issues.info("I03", f"Label skipped: {e.get('labelSkip') or 'no reason given'}", sheet="Photos", drink=d["name"])
    (reports_dir / "photo-map.suggested.json").write_text(
        emit_mod.dumps(photos_mod.suggestions_document(suggestions, unmatched)), encoding="utf-8")

    content = {"subcategories": _load_json(content_dir / "subcategories.json", {}, issues, "subcategories.json"),
               "glossary": _load_json(content_dir / "glossary.json", {}, issues, "glossary.json"),
               "aliases": _load_json(content_dir / "aliases.json", {}, issues, "aliases.json").get("producers", {})}

    shelf = emit_mod.build_shelf(drinks, grades, issues)

    # counter displays (Plan 07 section 4): new arrivals and the seasonal picks go into shelf.json
    seasonal = _load_json(content_dir / "seasonal.json", None, issues, "seasonal.json", code="W20")
    if seasonal and not counter_mod.validate_seasonal(seasonal, issues):
        seasonal = None
    if not issues.errors:
        content["counter"], counter_report = counter_mod.build_counter(drinks, photo_map, seasonal, issues)
        content["sub_views"] = counter_mod.sub_views(drinks, photo_map, seasonal)
    else:
        counter_report = None

    # S8
    jobs_all = images.plan_outputs(photo_map)
    jobs = [j for j in jobs_all if phase_mod.keep_job(j, sections)]
    if issues.errors:
        dims, src_hash, stats, img_errors = {}, {}, {"encoded": 0, "skipped": 0, "deleted": 0}, []
    else:
        dims, src_hash, stats, img_errors = images.run_images(
            jobs, photos_dir, docs, cache_path, force=force_images, write=not check)
    for src, msg in img_errors:
        issues.error("E05", f"{msg} ({src})")

    # scene plates and shells (Plan 01 section 7.6): read-only from Design/scene, converted into docs/img/scene
    scene_manifest = content["scene"] = _load_json(content_dir / "scene.json", None, issues, "scene.json", code="W20")
    scene_sigs = []
    if scene_manifest and not scene_mod.validate_manifest(scene_manifest, issues):
        scene_manifest = None
    if scene_manifest and not issues.errors:
        shells_cfg = _load_json(content_dir / "shells.json", None, issues, "shells.json", code="W20")
        if shells_cfg and not scene_mod.validate_shells(shells_cfg, issues):
            shells_cfg = None
        burger_cfg = _load_json(content_dir / "burger.json", None, issues, "burger.json", code="W20")
        if burger_cfg and not burger_mod.validate(burger_cfg, issues):
            burger_cfg = None
        scene_info, scene_sigs, scene_stats = scene_mod.convert(scene_dir, docs, root / "build" / ".scene-cache.json",
                                                                 force=force_images, write=not check, shells_cfg=shells_cfg,
                                                                 burger_cfg=burger_cfg)
        scene_mod.check_parity(scene_manifest, scene_info, issues)
        content["scene_data"] = scene_mod.merge(scene_manifest, scene_info)
        if not content["scene_data"]["ready"]:
            issues.info("I02", "Design/scene has no plates yet: the page keeps the v2 illustrated scene")

    # S9
    generated = _generated(ledger, ledger_path)
    files = emit_mod.emit(drinks, shelf, pages, key_by_text, photo_map, dims, ledger, generated, content,
                          images.job_signatures(jobs, src_hash) + scene_sigs, sections)
    res.files = files

    # S10
    expected = {j["out"] for j in jobs_all}
    checks.check_schema(files, issues)
    private_notes = checks.load_private_notes(ledger_path)          # a deny-list only: never copied into any output
    checks.check_privacy(files, photo_files, pages, issues, notes=private_notes)
    checks.check_references(files, expected, issues, docs_dir=None if (check or phase < 2) else docs)

    # golden counts and change tracking
    counts = {"drinks": len(drinks), "categories": {}, "subcategories": {}}
    for cat in shelf:
        counts["categories"][cat["name"]] = cat["count"]
        for s in cat["subs"]:
            counts["subcategories"][f"{cat['key']}/{s['key']}"] = len(s["drinks"])
    counts["unshelved"] = sum(1 for d in drinks if d["category"] is None)
    last_path = reports_dir / "last-build.json"
    previous = None
    if last_path.exists():
        try:
            previous = json.loads(last_path.read_text(encoding="utf-8"))
        except ValueError:
            previous = None
    if previous:
        prev_total = previous.get("counts", {}).get("drinks", 0)
        if prev_total and len(drinks) <= prev_total - max(3, int(prev_total * 0.1)):
            issues.warn("W12", f"Drink count dropped from {prev_total} to {len(drinks)} since the last build")
        for name, n in previous.get("counts", {}).get("categories", {}).items():
            now = counts["categories"].get(name, 0)
            if n >= 3 and now <= n * 0.8:
                issues.warn("W12", f"{name} dropped from {n} to {now} drinks since the last build")

    matched_photos = sorted({e["front"] for e in photo_map.values() if e.get("front")} |
                            {o["file"] for e in photo_map.values() for o in e.get("others", [])})
    state = {"drinks": {d["id"]: d["name"] for d in drinks}, "photos": matched_photos, "counts": counts}
    res.summary = {"counts": counts, "photos_total": len(photo_files), "photos_matched": len(matched_photos),
                   "photos_unmatched": len(unmatched), "images": stats, "drinks_without_photo":
                       sum(1 for d in drinks if not photo_map.get(d["id"], {}).get("front")),
                   "producers": len(pages), "generated": generated, "phase": phase,
                   "published": sorted(r for r in files if phase_mod.published(r, sections))}

    # write (only when clean)
    if not check and not issues.errors:
        if data_dir.exists():
            shutil.rmtree(data_dir)
        for rel, text in files.items():
            if not phase_mod.published(rel, sections):
                continue                      # Phase 1 writes only what the welcome page needs
            target = data_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)

    # the last gate (Plan 08 section 6): every file actually on disk under docs/data and docs/img, in every phase
    scanned = 0
    if not check and not issues.errors:
        scanned = checks.scan_published(docs, photo_files, private_notes, issues)
        if issues.errors:
            shutil.rmtree(data_dir, ignore_errors=True)         # nothing stays published after a leak
    res.summary["scanned"] = scanned

    if not check and not issues.errors:
        assets_mod.stamp(docs)                                  # Plan 06 section 7
        og_mod.generate(docs, root / "build" / "fonts" / "Rye-Regular.ttf")   # Plan 06 section 8

    extras = {"counter": counter_report, "shells_sheet": None, "burger_sheet": None}
    if not check and not issues.errors and content.get("scene_data", {}).get("ready"):
        sd = content["scene_data"]
        extras["shells_sheet"] = scene_report.shells_on_plate(docs, sd, reports_dir / "shells-on-plate.png")
        extras["burger_sheet"] = scene_report.burger_layers(docs, sd, reports_dir / "burger-layers.png")
    res.report_path = report_mod.write_report(
        reports_dir, root, drinks, shelf, photo_map, suggestions, unmatched, issues, state, previous,
        photos_dir, new_dir, res.summary, check, extras)
    if not check and not issues.errors:
        last_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    res.exit_code = 1 if issues.errors else 0
    return res


def format_summary(res: Result, check=False) -> str:
    s = res.summary
    lines = []
    lines.append("")
    lines.append("Liquid Assets build " + ("(check only, nothing written to docs/)" if check else "complete"))
    if not s:
        for e in res.issues.errors:
            lines.append(f"  ERROR {e['code']}: {e['message']}")
        return "\n".join(lines)
    c = s["counts"]
    lines.append(f"  Phase {s['phase']}: publishing {len(s['published'])} data files"
                 + (f"; privacy scan read {s['scanned']} files in docs/data and docs/img" if s.get("scanned") else ""))
    lines.append(f"  Drinks: {c['drinks']}   Producers (pages): {s['producers']}")
    for name, n in c["categories"].items():
        lines.append(f"    {name:<10} {n}")
    if c["unshelved"]:
        lines.append(f"    (not on any shelf: {c['unshelved']})")
    lines.append(f"  Photos: {s['photos_total']} files, {s['photos_matched']} matched, "
                 f"{s['photos_unmatched']} unmatched; {s['drinks_without_photo']} drinks without a front photo")
    st = s["images"]
    lines.append(f"  Images: {st['encoded']} encoded, {st['skipped']} unchanged, {st['deleted']} deleted")
    warns = res.issues.counts("warning")
    lines.append("  Warnings: " + (", ".join(f"{k} x{v}" for k, v in warns.items()) if warns else "none"))
    infos = res.issues.counts("info")
    if infos:
        lines.append("  Info: " + ", ".join(f"{k} x{v}" for k, v in infos.items()))
    errs = res.issues.errors
    lines.append(f"  Errors: {len(errs)}")
    for e in errs[:20]:
        lines.append(f"    {e['code']}: {e['message']}")
    if res.report_path:
        lines.append(f"  Report: {res.report_path}")
    return "\n".join(lines)
