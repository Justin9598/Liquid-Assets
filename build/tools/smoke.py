"""Browser smoke test for the welcome page (Plan 06 section 6, Plan 07 sections 8 to 10).

Serves docs/ on a local port, opens the page in headless Edge with ?check=1 at the four sizes
(1440x900, 1920x1080, 375x812, 390x844) and reads the JSON that docs/assets/js/selfcheck.js writes. It checks:
  - category captions always visible and never overlapping, at least 14px
  - for every category: tags 14px or more, never clipped, never overlapping, inside the shelf area, counter bottles fade out
  - at rest: no lower-shelf bottle drawn behind a counter bottle; labels do not overlap
  - the burger menu opened for real (animations run, not the instant path): every board stays at opacity 1 through
    hovering each layer and opening and closing Shelves; boards overlap their layer; the panel is opaque and covers nothing
Phone sizes load the page in a same-origin iframe, because a headless window is never narrower than 500px.

    python build/tools/smoke.py                 run all four sizes, exit 1 on any problem
    python build/tools/smoke.py --shots DIR     also save screenshots of the resting and open states
    python build/tools/smoke.py --live URL      test the published site instead of docs/ (its files are fetched through a
                                                local relay so the phone frame stays same-origin); --prefix live- names shots
Console errors (including failed requests) are collected from the browser's log and fail the run.

Phase 2 (Plan 08): when the served site has its shelves, drinks and makers turned on, smoke_inner.py also checks every inner page
type at the four sizes (no sideways scroll, no overlapping boards, chalk only, contrast, the fixed bar, full height, the menu,
the maps, the move between pages). Ship/docs is a Phase 1 build until launch, so Phase 2 is previewed in a scratch copy:

    python build/tools/smoke.py --preview            build Phase 2 in a scratch copy outside Ship/ and test that
    python build/tools/smoke.py --docs DIR           test a built docs/ folder somewhere else
    python build/tools/smoke.py --preview --shots D  also save the inner-page screenshots in D (Ship/reports/phase2)
"""
from __future__ import annotations

import http.server
import json
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
BASE = None                                    # set by --live: the published site's URL
SIZES = [(1440, 900), (1920, 1080), (375, 812), (390, 844)]
EDGE = [Path(p) for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                          r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


def make_preview():
    """Copy Ship/ (without .git, reports and plans) to a scratch folder and build Phase 2 there from the real ledger and photos.
    The scratch copy persists between runs, so the image cache makes later runs quick. Returns its docs/ folder, or None."""
    ledger = ROOT.parent / "Drinks Ledger.xlsx"
    if not ledger.exists():
        print("No ledger: the Phase 2 preview is skipped")
        return None
    dst = Path(tempfile.gettempdir()) / "liquid-assets-phase2-preview" / "Ship"
    ignore = shutil.ignore_patterns(".git", "reports", "plans", "__pycache__", ".pytest_cache")
    if (dst / "docs" / "img").exists():                      # keep docs/data and docs/img: the image cache lives there
        for d in ("build", "content"):
            shutil.copytree(ROOT / d, dst / d, ignore=ignore, dirs_exist_ok=True)
        shutil.rmtree(dst / "docs" / "assets", ignore_errors=True)
        shutil.copytree(ROOT / "docs" / "assets", dst / "docs" / "assets")
        for f in ("index.html", "404.html", "favicon.png", "favicon.svg"):
            shutil.copy2(ROOT / "docs" / f, dst / "docs" / f)
    else:
        shutil.copytree(ROOT, dst, ignore=ignore, dirs_exist_ok=True)
    r = subprocess.run([sys.executable, str(dst / "build" / "build.py"), "--phase", "2", "--ledger", str(ledger),
                        "--photos", str(ROOT.parent / "Photos"), "--scene", str(ROOT.parent / "Design" / "scene"),
                        "--new", str(ROOT.parent / "New")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print("The Phase 2 preview build failed:" + chr(10) + r.stdout[-1500:] + r.stderr[-800:])
        return None
    return dst / "docs"


def is_phase2(docs):
    try:
        return bool(json.loads((Path(docs) / "data" / "build.json").read_text(encoding="utf-8")).get("sections", {}).get("shelves"))
    except (OSError, ValueError):
        return False


def edge_path():
    for p in EDGE:
        if p.exists():
            return str(p)
    return shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/__phone.html":                        # a phone-sized frame, same origin as the page
            q = parse_qs(u.query)
            w, h, target = q["w"][0], q["h"][0], q["u"][0]
            body = (f'<!doctype html><body style="margin:0;background:#111"><iframe id="f" src="{target}" '
                    f'style="width:{w}px;height:{h}px;border:0;display:block"></iframe><pre id="out"></pre>'
                    '<script>setInterval(()=>{try{const d=document.getElementById("f").contentDocument.getElementById("check-result");'
                    'if(d&&d.textContent)document.getElementById("out").textContent=d.textContent}catch(e){}},100)</script>').encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if BASE:                                             # relay the published site's files
            import urllib.request
            try:
                req = urllib.request.Request(BASE.rstrip("/") + self.path, headers={"User-Agent": "liquid-assets-smoke"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    body, ctype, status = r.read(), r.headers.get("Content-Type", "application/octet-stream"), r.status
            except Exception as exc:                          # 404 and the like: pass the status through
                code = getattr(exc, "code", 502)
                self.send_response(code)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


class Server:
    def __enter__(self):
        class Quick(socketserver.ThreadingTCPServer):
            # The default listen backlog is 5. A page that asks for dozens of images at once (the 74-card list) overflows it
            # and the browser gets ERR_CONNECTION_REFUSED, at random: a failed fetch, a page that never mounts.
            request_queue_size = 256
            allow_reuse_address = True
            daemon_threads = True

            def handle_error(self, request, client_address):      # a browser closing a connection is not news
                pass
        self.httpd = Quick(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


def run_edge(args, timeout=120):
    exe = edge_path()
    profile = tempfile.mkdtemp(prefix="smoke-profile-")
    try:
        return subprocess.run([exe, "--headless=old", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                               f"--user-data-dir={profile}", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def page_url(port, w, h, query, framed=True):
    base = f"http://127.0.0.1:{port}/"
    if w >= 500:
        # --dump-dom: headless Edge's window includes its own frame, so ask for one that leaves w x h inside;
        # --screenshot: the window size is the picture size
        return base + query, ((w + 24, h + 92) if framed else (w, h))
    return f"{base}__phone.html?w={w}&h={h}&u=" + (base + query).replace("?", "%3F").replace("&", "%26").replace("#", "%23"), (500, h)


def check_size(port, w, h):
    url, win = page_url(port, w, h, "?check=1")
    r = run_edge([f"--window-size={win[0]},{win[1]}", "--virtual-time-budget=60000", "--enable-logging=stderr", "--v=0", "--dump-dom", url])
    console = [ln.split("CONSOLE", 1)[1][:200] for ln in r.stderr.splitlines() if ":CONSOLE" in ln]
    m = re.search(r'<pre id="(?:check-result|out)"[^>]*>(\{.*?\})</pre>', r.stdout, re.S)
    if not m:
        return {"ok": False, "problems": ["no result: the page did not finish its self-check"], "stats": {}, "console": console}
    import html
    res = json.loads(html.unescape(m.group(1)))
    res["console"] = console
    errors = [c for c in console if re.search(r"error|failed|404|uncaught", c, re.I)]
    if errors:
        res["problems"] = res["problems"] + [f"console: {e.strip()}" for e in errors[:5]]
        res["ok"] = False
    return res


def shots(port, out_dir, prefix=""):
    """Resting, Sake open, and the menu open (real open, animations finished) at the four sizes."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = [("welcome", "?r=1"), ("sake-open", "?r=2#/sake"), ("inseason", "?r=5&tab=season"), ("burger-open", "?r=3&menu=open&settle=1"), ("burger-shelves", "?r=4&menu=open&settle=1&panel=shelves")]
    for w, h in SIZES:
        for name, q in plan:
            url, win = page_url(port, w, h, q, framed=False)
            dest = out_dir / f"{prefix}{name}-{'desktop' if w >= 500 else 'phone'}-{w}x{h}.png"
            run_edge([f"--window-size={win[0]},{win[1]}", "--virtual-time-budget=20000", f"--screenshot={dest}", url])
            if w < 500 and dest.exists():
                from PIL import Image
                Image.open(dest).crop((0, 0, w, h)).save(dest)


def main(argv):
    if not edge_path():
        print("No Edge or Chrome found: smoke test skipped")
        return 0
    global BASE, DOCS
    if "--live" in argv:
        BASE = argv[argv.index("--live") + 1]
    if "--docs" in argv:
        DOCS = Path(argv[argv.index("--docs") + 1]).resolve()
    if "--preview" in argv:
        DOCS = make_preview()
        if DOCS is None:
            return 1
    failed = 0
    with Server() as srv:
        for w, h in SIZES:
            res = check_size(srv.port, w, h)
            print(f"{w}x{h}: {'ok' if res['ok'] else 'FAILED'}")
            for p in res["problems"][:30]:
                print("   ", p)
            failed += 0 if res["ok"] else 1
        if "--shots" in argv:
            shots(srv.port, argv[argv.index("--shots") + 1], argv[argv.index("--prefix") + 1] if "--prefix" in argv else "")
        if (BASE is None and is_phase2(DOCS)) or (BASE and "--inner" in argv):
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                import smoke_inner
                shots_dir = argv[argv.index("--shots") + 1] if "--shots" in argv else None
                problems, stats = smoke_inner.run(f"http://127.0.0.1:{srv.port}", shots_dir)
                print("inner pages: " + ("ok" if not problems else "FAILED"))
                for pr in problems[:60]:
                    print("   ", pr)
                if "--stats" in argv:
                    print(json.dumps(stats, indent=1))
                failed += 1 if problems else 0
            except ImportError as exc:
                print(f"inner pages: skipped ({exc}; pip install websockets)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
