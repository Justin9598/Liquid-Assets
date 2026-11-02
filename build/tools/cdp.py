"""A tiny Chrome DevTools Protocol driver for headless Edge or Chrome (used by smoke.py and for screenshots).

Needs the `websockets` package. Starts the browser with a throw-away profile, opens pages at an exact viewport size
(phone sizes included, with touch and mobile emulation) and gives three things: run JavaScript, wait, take a screenshot.

    with Browser() as b:
        page = b.page(375, 812, mobile=True)
        page.goto("http://127.0.0.1:8000/#/makers")
        print(page.eval("document.title"))
        page.screenshot("out.png")
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def browser_path():
    for p in EDGE:
        if Path(p).exists():
            return p
    return shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")


class Page:
    def __init__(self, browser, session, w, h):
        self.b, self.sid, self.w, self.h = browser, session, w, h
        self.logs = []                                   # console errors and failed requests

    def send(self, method, **params):
        return self.b._send(method, params, self.sid, self)

    def front(self):
        self.send("Page.bringToFront")

    def _navigate(self, url):
        """Navigate and wait for this navigation's own load event (matched by its loader id, so a stale event from an earlier
        page can never end the wait early)."""
        r = self.send("Page.navigate", url=url)
        lid = r.get("loaderId")
        if lid:
            self.b._wait_event("Page.lifecycleEvent", self.sid, 40, lambda p: p.get("name") == "load" and p.get("loaderId") == lid)

    def goto(self, url, wait=0.0, settle=False):
        self.front()
        self._navigate("about:blank")                        # a change of the hash alone would not be a new page load
        self._navigate(url)
        if settle:
            self.settle(wait)

    def settle(self, extra=0.4):
        """Wait for fonts, the first paint and any running animation to finish."""
        self.eval("document.fonts.ready.then(()=>1)", await_promise=True)
        time.sleep(extra)

    def eval(self, js, await_promise=False):
        r = self.b._send("Runtime.evaluate", dict(expression=js, returnByValue=True, awaitPromise=await_promise), self.sid, self, timeout=50 if await_promise else 30)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError(d.get("exception", {}).get("description") or d.get("text"))
        return r["result"].get("value")

    def screenshot(self, path, full=False):
        params = {"format": "png"}
        if full:
            m = self.send("Page.getLayoutMetrics")
            size = m.get("cssContentSize") or m["contentSize"]
            params.update(captureBeyondViewport=True, clip={"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1})
        data = self.send("Page.captureScreenshot", **params)["data"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(base64.b64decode(data))

    def scroll_to(self, y):
        """Scroll and wait until the scroll has happened and two frames have been drawn."""
        self.eval(f"new Promise(r => {{ scrollTo(0, {y}); requestAnimationFrame(() => requestAnimationFrame(r)); setTimeout(r, 1500); }})", await_promise=True)

    def emulate_media(self, **features):
        self.send("Emulation.setEmulatedMedia", features=[{"name": k, "value": v} for k, v in features.items()])

    def throttle(self, rate):
        self.send("Emulation.setCPUThrottlingRate", rate=rate)

    def close(self):
        try:
            self.b._send("Target.closeTarget", {"targetId": self.target}, None, None)
        except Exception:
            pass


class Browser:
    def __enter__(self):
        from websockets.sync.client import connect
        exe = browser_path()
        if not exe:
            raise RuntimeError("no Edge or Chrome found")
        self.profile = tempfile.mkdtemp(prefix="cdp-profile-")
        self.proc = subprocess.Popen([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=0",
                                      "--no-first-run", "--no-default-browser-check", "--mute-audio",
                                      f"--user-data-dir={self.profile}", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self.profile) / "DevToolsActivePort"
        for _ in range(100):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("the browser did not start")
        port = port_file.read_text().splitlines()[0]
        ws = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=10).read())["webSocketDebuggerUrl"]
        self._ws_cm = connect(ws, max_size=None, open_timeout=15)
        self.ws = self._ws_cm.__enter__()
        self._id = 0
        self._events = []
        self._pages = {}
        return self

    def __exit__(self, *a):
        try:
            self._ws_cm.__exit__(None, None, None)
        finally:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)   # the whole tree: no leftovers
            self.proc.kill()
            shutil.rmtree(self.profile, ignore_errors=True)

    # -- protocol plumbing
    def _on_message(self, msg):
        method = msg.get("method")
        sid = msg.get("sessionId")
        page = self._pages.get(sid)
        if page is not None:
            if method == "Runtime.exceptionThrown":
                page.logs.append("exception: " + str(msg["params"]["exceptionDetails"].get("exception", {}).get("description", ""))[:200])
            elif method == "Log.entryAdded" and msg["params"]["entry"]["level"] == "error":
                e = msg["params"]["entry"]
                page.logs.append(f"{e.get('text', '')} {e.get('url', '')}"[:200])
            elif method == "Runtime.consoleAPICalled" and msg["params"]["type"] == "error":
                page.logs.append("console.error: " + " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"])[:200])
        if method:
            self._events.append((sid, method, msg.get("params")))

    def _send(self, method, params, sid, page, timeout=60):
        self._id += 1
        mid = self._id
        msg = {"id": mid, "method": method, "params": params}
        if sid:
            msg["sessionId"] = sid
        self.ws.send(json.dumps(msg))
        end = time.time() + timeout
        while time.time() < end:
            raw = json.loads(self.ws.recv(timeout=max(0.1, end - time.time())))
            if raw.get("id") == mid:
                if "error" in raw:
                    raise RuntimeError(f"{method}: {raw['error']}")
                return raw.get("result", {})
            self._on_message(raw)
        raise TimeoutError(method)

    def _wait_event(self, name, sid, timeout, match=None):
        end = time.time() + timeout
        while time.time() < end:
            for i, (s, m, p) in enumerate(self._events):
                if m == name and s == sid and (match is None or match(p)):
                    del self._events[i]
                    return p
            try:
                raw = json.loads(self.ws.recv(timeout=0.2))
            except TimeoutError:
                continue
            self._on_message(raw)
        raise TimeoutError(name)

    def page(self, w, h, mobile=False, dpr=1, scheme=None, reduced_motion=False):
        tid = self._send("Target.createTarget", {"url": "about:blank"}, None, None)["targetId"]
        sid = self._send("Target.attachToTarget", {"targetId": tid, "flatten": True}, None, None)["sessionId"]
        p = Page(self, sid, w, h)
        p.target = tid
        self._pages[sid] = p
        for m in ("Page.enable", "Runtime.enable", "Log.enable", "Network.enable"):
            p.send(m)
        p.send("Page.setLifecycleEventsEnabled", enabled=True)
        # A tab that is not in front is hidden: no animation frames, no finished animations. Every page this driver opens is
        # told it has focus and is brought to the front, whatever other tabs exist.
        p.send("Emulation.setFocusEmulationEnabled", enabled=True)
        p.send("Page.bringToFront")
        p.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=dpr, mobile=mobile)
        if mobile:
            p.send("Emulation.setTouchEmulationEnabled", enabled=True)
        feats = {}
        if scheme:
            feats["prefers-color-scheme"] = scheme
        if reduced_motion:
            feats["prefers-reduced-motion"] = "reduce"
        if feats:
            p.emulate_media(**feats)
        return p
