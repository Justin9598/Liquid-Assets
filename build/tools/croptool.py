"""The owner's label-crop tool (Plan 13 section 2): a small, private, local server on 127.0.0.1 only.

It serves the tool page, the front photos (read-only, from ../Photos/, found by drink id and never by a path the browser
sends) and the current content/photo-map.json. Its only write is POST /save, which updates content/photo-map.json after
copying the old file to reports/photo-map-backups/. Nothing here is published and the module holds no data.

Run it with build/crop.bat, or `python build/tools/croptool.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
SHIP = HERE.parents[1]
PORT = 8765
MAX_BODY = 20_000
SAVE_KEYS = {"id", "status", "crop", "reason"}
LOCK = threading.Lock()


# ------------------------------------------------------------------ the photo map file

def map_path(root: Path) -> Path:
    return Path(root) / "content" / "photo-map.json"


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def load_map(root: Path) -> dict:
    p = map_path(root)
    return json.loads(_read_text(p)) if p.exists() else {}


def dump_map(data: dict, like: str = "") -> str:
    """Same format as the file already has: one-space indent, key order kept, its line ending, no trailing newline added."""
    text = json.dumps(data, indent=1, ensure_ascii=False)
    if "\r\n" in like:
        text = text.replace("\n", "\r\n")
    if like.endswith("\n"):
        text += "\r\n" if "\r\n" in like else "\n"
    return text


def entry_hash(entry: dict) -> str:
    """The decision part of an entry: what E07 compares. Anything else (front, others, thumbCrop) can change freely."""
    keys = ("labelStatus", "labelCrop", "labelSkip", "cropBy")
    payload = json.dumps([entry.get(k) for k in keys], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _sidecar(root: Path) -> Path:
    return Path(root) / "reports" / "owner-saves.json"


def read_owner_saves(root: Path) -> dict:
    try:
        return json.loads(_sidecar(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def valid_crop(c) -> bool:
    return (isinstance(c, list) and len(c) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in c)
            and c[0] >= 0 and c[1] >= 0 and c[2] > 0.01 and c[3] > 0.01
            and c[0] + c[2] <= 1.0001 and c[1] + c[3] <= 1.0001)


def write_map_atomically(root: Path, data: dict) -> Path:
    """Back up the current file, then write the new one through a temp file and a rename. Returns the backup path."""
    root = Path(root)
    p = map_path(root)
    like = _read_text(p) if p.exists() else ""
    backups = root / "reports" / "photo-map-backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backups / f"photo-map-{stamp}.json"
    if p.exists():
        shutil.copy2(p, backup)
    fd, tmp = tempfile.mkstemp(prefix=".photo-map-", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dump_map(data, like).encode("utf-8"))
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return backup


def apply_decision(entry: dict, by: str, status: str, crop=None, reason=None, check=None) -> dict:
    """Update one entry in place (existing keys keep their place, new keys go at the end) and return it."""
    if status == "ok":
        entry["labelCrop"] = [round(float(v), 4) for v in crop]
        entry["labelStatus"] = "ok"
        entry.pop("labelSkip", None)
    else:
        entry["labelStatus"] = "skip"
        entry["labelSkip"] = reason or "no usable label"
        entry.pop("labelCrop", None)
    entry["cropBy"] = by
    if check:
        entry["cropCheck"] = check
    else:
        entry.pop("cropCheck", None)
    return entry


def record_decision(root: Path, did: str, by: str, status: str, crop=None, reason=None, check=None) -> Path:
    """One locked read-modify-write of the map. Owner entries are never changed by anyone but the owner."""
    with LOCK:
        data = load_map(root)
        entry = data.get(did)
        if by != "owner" and isinstance(entry, dict) and entry.get("cropBy") == "owner":
            raise PermissionError(f"{did} is an owner crop: it is read-only")
        if entry is None:
            entry = data[did] = {}
        apply_decision(entry, by, status, crop, reason, check)
        backup = write_map_atomically(root, data)
        if by == "owner":
            saves = read_owner_saves(root)
            saves[did] = entry_hash(entry)
            sc = _sidecar(root)
            sc.write_text(json.dumps(saves, indent=1), encoding="utf-8")
        return backup


# ------------------------------------------------------------------ what the tool shows

def candidates(root: Path) -> dict:
    """drink id -> {name, category, sub, front}. The build writes reports/crop-candidates.json (every drink with a front
    photo, including the auto-matched ones). Without it, fall back to the map's own fronts and the published index."""
    root = Path(root)
    out = {}
    try:
        out = json.loads((root / "reports" / "crop-candidates.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        index = {}
        try:
            for d in json.loads((root / "docs" / "data" / "drinks.json").read_text(encoding="utf-8")):
                index[d["id"]] = d
        except (OSError, ValueError):
            pass
        for did, e in load_map(root).items():
            if isinstance(e, dict) and e.get("front"):
                d = index.get(did, {})
                out[did] = {"name": d.get("name", did), "category": d.get("category", "sake"), "sub": d.get("sub"),
                            "front": e["front"]}
    return out


def shells(root: Path) -> dict:
    try:
        return json.loads((Path(root) / "docs" / "data" / "scene.json").read_text(encoding="utf-8")).get("shells", {})
    except (OSError, ValueError):
        return {}


def safe_child(base: Path, name: str) -> Path | None:
    """A file directly inside `base` with exactly this name, or None. No separators, no parents, no links out."""
    if not name or "/" in name or "\\" in name or name in (".", "..") or "\x00" in name:
        return None
    p = (base / name)
    try:
        if p.is_file() and p.resolve().parent == base.resolve():
            return p
    except OSError:
        return None
    return None


# ------------------------------------------------------------------ the server

class Handler(BaseHTTPRequestHandler):
    server_version = "CropTool"
    root: Path = SHIP
    photos: Path = SHIP.parent / "Photos"
    port: int = PORT

    def log_message(self, fmt, *args):            # quiet
        pass

    # -- helpers
    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        return host in (f"127.0.0.1:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}")

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    # -- GET (read only)
    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "bad host"})
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._send(200, (HERE / "crop" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/map":
            p = map_path(self.root)
            return self._send(200, p.read_bytes() if p.exists() else b"{}")
        if path == "/api/info":
            return self._json(200, {"drinks": candidates(self.root), "shells": shells(self.root),
                                    "ownerSaves": read_owner_saves(self.root)})
        if path.startswith("/photo/"):
            did = path[len("/photo/"):]
            c = candidates(self.root).get(did)
            f = safe_child(self.photos, c["front"]) if c else None
            if not f:
                return self._json(404, {"error": "no such photo"})
            ctype = "image/webp" if f.suffix.lower() == ".webp" else "image/jpeg"
            return self._send(200, f.read_bytes(), ctype)
        if path.startswith("/shell/"):                  # the rendered shell images the site uses, read-only
            name = path[len("/shell/"):]
            files = {(v.get("files") or {}).get("2x", "").split("/")[-1] for v in shells(self.root).values()}
            f = safe_child(self.root / "docs" / "img" / "scene", name) if name in files else None
            if not f:
                return self._json(404, {"error": "no such shell"})
            return self._send(200, f.read_bytes(), "image/webp")
        return self._json(404, {"error": "not found"})

    # -- POST: exactly one path
    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "bad host"})
        if urlparse(self.path).path != "/save":
            return self._json(404, {"error": "the only write is POST /save"})
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{self.server.server_address[1]}",
                                     f"http://localhost:{self.server.server_address[1]}"):
            return self._json(403, {"error": "bad origin"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                raise ValueError("body size")
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(body, dict) or not set(body) <= SAVE_KEYS:
                raise ValueError("unexpected fields: only id, status, crop, reason are accepted")
            did, status = body.get("id"), body.get("status")
            if not isinstance(did, str) or did not in candidates(self.root):
                raise ValueError("unknown drink id")
            if status not in ("ok", "skip"):
                raise ValueError('status must be "ok" or "skip"')
            if status == "ok" and not valid_crop(body.get("crop")):
                raise ValueError("crop must be [x, y, w, h] fractions inside the photo")
            reason = body.get("reason")
            if reason is not None and (not isinstance(reason, str) or len(reason) > 200):
                raise ValueError("reason must be short text")
        except (ValueError, UnicodeDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        backup = record_decision(self.root, did, "owner", status, body.get("crop"), reason)
        return self._json(200, {"ok": True, "backup": backup.name, "entry": load_map(self.root).get(did)})

    def do_PUT(self):
        self._json(405, {"error": "read only"})

    do_DELETE = do_PATCH = do_PUT


def make_server(root: Path = SHIP, photos: Path | None = None, port: int = PORT) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"root": Path(root), "photos": Path(photos) if photos else Path(root).parent / "Photos"})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)       # loopback only, never 0.0.0.0


def main(argv):
    port = PORT
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    try:
        srv = make_server(port=port)
    except OSError as exc:
        print(f"Cannot start on 127.0.0.1:{port}: {exc}\nIs the crop tool already running?")
        return 1
    url = f"http://127.0.0.1:{port}/"
    print(f"Liquid Assets crop tool: {url}\nOnly content/photo-map.json is ever written. Close this window to stop.")
    if "--no-browser" not in argv:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
