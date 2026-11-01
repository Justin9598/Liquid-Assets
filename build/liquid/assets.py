"""Version-stamp the JS and CSS URLs (Plan 06 section 7).

The build rewrites the block between the `build:assets` markers in docs/index.html: an import map that gives every
module a `?v=<hash>` URL (so static and dynamic imports are stamped too), the stylesheet link and the entry script.
The hash covers docs/assets (js, css, svg), so it only changes when the site code does. No bundler is involved.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

BLOCK = re.compile(r"<!-- build:assets -->.*?<!-- /build:assets -->", re.S)


def asset_version(docs_dir) -> str:
    docs = Path(docs_dir)
    h = hashlib.sha1()
    for p in sorted((docs / "assets").rglob("*")):
        if p.is_file() and p.suffix in (".js", ".css", ".svg"):
            h.update(p.relative_to(docs).as_posix().encode())
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:10]


def _preloads(docs: Path) -> str:
    """Preload the plate for the visitor's screen shape once the rendered scene exists (Plan 01 section 7.6)."""
    try:
        scene = json.loads((docs / "data" / "scene.json").read_text(encoding="utf-8"))
        v = json.loads((docs / "data" / "build.json").read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError):
        return ""
    if not scene.get("ready"):
        return ""
    out = ""
    for kind, media in (("wide", "(orientation: landscape) and (min-width: 768px)"),
                        ("tall", "not ((orientation: landscape) and (min-width: 768px))")):
        files = scene["plates"][kind].get("files", {})
        fmt = "avif" if files.get("avif") else "webp"
        lst = files.get(fmt) or []
        if not lst:
            continue
        srcset = ", ".join(f"{f['url']}?v={v} {f['w']}w" for f in lst)
        ratio = scene["plates"][kind]["ratio"]
        out += (f'<link rel="preload" as="image" type="image/{fmt}" imagesrcset="{srcset}" '
                f'imagesizes="max(100vw, calc(100dvh * {ratio}))" media="{media}">\n')
    return out


def block_html(docs_dir, version) -> str:
    docs = Path(docs_dir)
    mods = sorted(p.relative_to(docs).as_posix() for p in (docs / "assets" / "js").glob("*.js"))
    imports = {f"./{m}": f"./{m}?v={version}" for m in mods}
    imap = json.dumps({"imports": imports}, indent=1)
    return ("<!-- build:assets -->\n"
            f'<script type="importmap">\n{imap}\n</script>\n'
            f'{_preloads(docs)}'
            f'<link rel="stylesheet" href="assets/css/app.css?v={version}">\n'
            f'<script type="module" src="assets/js/main.js?v={version}"></script>\n'
            "<!-- /build:assets -->")


def stamp(docs_dir) -> list:
    """Rewrite the marked block in index.html and 404.html. Returns the files that changed."""
    docs = Path(docs_dir)
    if not (docs / "assets" / "js").exists():
        return []
    version = asset_version(docs)
    changed = []
    for name in ("index.html", "404.html"):
        path = docs / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if not BLOCK.search(text):
            continue
        new = BLOCK.sub(lambda m: block_html(docs, version), text)
        if new != text:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new)
            changed.append(name)
    return changed
