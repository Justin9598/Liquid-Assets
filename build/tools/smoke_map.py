"""Browser checks for the pin maps (Plan 14 sections 5 and 6, acceptance in section 9), and the screenshots into reports/plan14/.

    python build/tools/smoke_map.py                 all four sizes, exit 1 on any problem
    python build/tools/smoke_map.py --shots DIR     also save the screenshots (default Ship/reports/plan14)

smoke_inner.py calls map_checks() and maker_map_checks() too, so the Phase 2 smoke test covers all of this.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_inner import SIZES, load, settle, wait_for, wait_ready, go as _go  # noqa: E402

SHIP = Path(__file__).resolve().parents[2]

MAP_STATE = r"""(() => {
  const host = document.querySelector('#mapbox');
  if (!host) return null;
  const hr = host.getBoundingClientRect();
  const pins = [...host.querySelectorAll('.mm-pin')].map((p) => {
    const h = p.querySelector('.pin-head').getBoundingClientRect();
    const b = p.getBoundingClientRect();
    return { id: p.dataset.id, kind: p.className.replace('mm-pin', '').trim(), head: [h.left, h.top, h.right, h.bottom], w: b.width, h: b.height, tag: p.tagName, label: p.getAttribute('aria-label') };
  });
  const overlaps = [];
  for (let i = 0; i < pins.length; i++) for (let j = i + 1; j < pins.length; j++) {
    const a = pins[i].head, b = pins[j].head;
    if (a[0] < b[2] - 0.5 && a[2] > b[0] + 0.5 && a[1] < b[3] - 0.5 && a[3] > b[1] + 0.5) overlaps.push(pins[i].id + ' / ' + pins[j].id);
  }
  const small = pins.filter((p) => p.w < 43.5 || p.h < 43.5 || p.tag !== 'BUTTON').map((p) => p.id);
  const outside = pins.filter((p) => p.head[0] < hr.left - 0.5 || p.head[2] > hr.right + 0.5 || p.head[1] < hr.top - 0.5 || p.head[3] > hr.bottom + 0.5).map((p) => p.id);
  const mb = document.querySelector('.map-board').getBoundingClientRect();
  return {
    pins, overlaps, small, outside, at: host.dataset.at, level: host.dataset.level, kind: host.dataset.kind,
    info: document.querySelector('#map-info').textContent, crumbs: [...document.querySelectorAll('#mm-crumbs li')].map((l) => l.textContent.trim()),
    count: document.querySelector('#mcount').textContent, tiles: document.querySelectorAll('#mlist .tile').length, hash: location.hash,
    chip: document.querySelector('#region-chip')?.textContent.trim() || '', back: !document.querySelector('#mm-back').disabled,
    boardVh: mb.height / innerHeight, sideways: document.documentElement.scrollWidth > innerWidth + 1,
    card: !document.querySelector('#mm-card').hidden, legend: [...document.querySelectorAll('.mm-key')].map((k) => k.textContent.trim()),
    country: document.querySelector('#mcountry').value, q: document.querySelector('#mq').value,
  };
})()"""

def go(page, route):
    """smoke_inner.go, with one retry: a headless tab now and then goes a few seconds without an animation frame."""
    try:
        _go(page, route)
    except RuntimeError as e:
        if "animation frames" not in str(e):
            raise
        page.send("Page.bringToFront")
        _go(page, route)


READY = "(() => { const h = document.querySelector('#mapbox'); return !!h && h.dataset.ready === '1' && h.dataset.moving !== '1'; })()"


def state(page):
    wait_for(page, READY, 20)
    return page.eval(MAP_STATE)


def open_at(page, at, extra=""):
    go(page, f"#/makers?at={at}{extra}" if at else f"#/makers{('?' + extra.lstrip('&')) if extra else ''}")
    wait_for(page, READY, 20)
    return page.eval(MAP_STATE)


def click(page, sel):
    ok = page.eval(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return false; e.click(); return true; }})()")
    if not ok:
        raise RuntimeError(f"nothing to press: {sel}")
    wait_for(page, "document.querySelector('#mapbox').dataset.ready === '0' || true", 1)
    page.eval("new Promise(r => setTimeout(r, 40))", await_promise=True)
    wait_for(page, READY, 20)


def esc(page):
    page.eval("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}))")
    page.eval("new Promise(r => setTimeout(r, 40))", await_promise=True)
    wait_for(page, READY, 20)


TREE_JS = r"""(async () => {
  const t = await import('./assets/js/maptree.js');
  const prods = await (await fetch('data/producers.json')).json();
  const root = t.buildTree(prods);
  const out = { problems: [], states: [], world: root.children.map((c) => [c.name, c.producers.length]) };
  const seen = new Set();
  for (const { node, view } of t.walk(root)) {
    const n = node.producers.length;
    const label = node.path || 'world';
    seen.add(label);
    if (n < t.MIN_GROUP && view.kind !== 'makers') out.problems.push(label + ': fewer than 10 makers but it breaks down');
    if (view.kind === 'groups') {
      if (view.groups.length < 2) out.problems.push(label + ': one child was not skipped');
      const sum = view.groups.reduce((a, g) => a + g.producers.length, 0) + view.makers.length;
      if (sum !== view.node.producers.length) out.problems.push(label + ': the groups add up to ' + sum + ', not ' + view.node.producers.length);
      if (view.node.producers.length < t.MIN_GROUP) out.problems.push(label + ': groups for fewer than 10 makers');
    } else {
      if (view.makers.length !== view.node.producers.length) out.problems.push(label + ': makers view misses makers');
    }
    out.states.push({ path: node.path, name: node.name, n, kind: view.kind, groups: view.kind === 'groups' ? view.groups.map((g) => [g.name, g.producers.length]) : [] });
  }
  const pins = prods.filter((p) => p.lat != null).length;
  if (root.producers.length !== pins) out.problems.push('the tree holds ' + root.producers.length + ' makers, ' + pins + ' have pins');
  out.total = prods.length;
  return out;
})()"""


def tree_checks(page, tag):
    r = page.eval(TREE_JS, await_promise=True)
    return [f"{tag}: tree: {m}" for m in r["problems"]], r


def pin_problems(s, label):
    out = []
    if s["overlaps"]:
        out.append(f"{label}: pin heads overlap: {s['overlaps'][:3]}")
    if s["small"]:
        out.append(f"{label}: pins under 44px or not buttons: {s['small'][:3]}")
    if s["outside"]:
        out.append(f"{label}: pin heads outside the map: {s['outside'][:3]}")
    if s["sideways"]:
        out.append(f"{label}: sideways scroll")
    return out


def map_checks(page, base, tag, full=True):
    """The Makers map: World to a prefecture and back up, the two rules, no overlaps at any level, map and list together."""
    probs = []
    w, h = page.w, page.h
    phone = w < 768
    load(page, base, "#/makers")
    s = state(page)
    if s is None:
        return [f"{tag}: the Makers page has no map"]
    probs += pin_problems(s, f"{tag} World")
    ids = sorted(p["id"] for p in s["pins"])
    if ids != ["g:asia", "g:europe", "g:north-america", "g:south-america"]:
        probs.append(f"{tag} World shows pins {ids}")
    if s["crumbs"] != ["World"] or not s["info"].startswith("Everywhere · "):
        probs.append(f"{tag} World: crumbs {s['crumbs']}, info '{s['info']}'")
    if phone and s["boardVh"] > 0.55 + 1e-3:
        probs.append(f"{tag}: the map board is {s['boardVh'] * 100:.0f}% of the screen height (at most 55%)")
    # down: Asia, East Asia, Japan, Tohoku, Iwate
    steps = [("g:asia", "asia", ["g:asia/east-asia", "g:asia/southeast-asia"], "Asia"),
             ("g:asia/east-asia", "asia/east-asia", ["g:asia/east-asia/japan", "g:asia/east-asia/south-korea", "g:asia/east-asia/taiwan"], "East Asia"),
             ("g:asia/east-asia/japan", "asia/east-asia/japan", None, "Japan"),
             ("g:asia/east-asia/japan/tohoku", "asia/east-asia/japan/tohoku", None, "Tohoku")]
    for pid, at, want, name in steps:
        click(page, f'.mm-pin[data-id="{pid}"]')
        s = state(page)
        if s["at"] != at:
            probs.append(f"{tag}: pressing {pid} gave place '{s['at']}'")
            break
        probs += pin_problems(s, f"{tag} {name}")
        got = sorted(p["id"] for p in s["pins"])
        if want and got != sorted(want):
            probs.append(f"{tag} {name}: pins {got}, expected {sorted(want)}")
        if f"at={at}" not in s["hash"]:
            probs.append(f"{tag} {name}: the address is {s['hash']}")
        if s["tiles"] != int(s["count"].split()[0]) or not s["info"].split(" · ")[1].startswith(s["count"]):
            probs.append(f"{tag} {name}: list shows {s['tiles']} tiles, count '{s['count']}', info '{s['info']}'")
        if name == "Japan":
            names = sorted(p["label"].split(",")[0] for p in s["pins"])
            if names != sorted(["Hokkaido", "Tohoku", "Kanto", "Chubu", "Kansai", "Chugoku", "Shikoku", "Kyushu"]):
                probs.append(f"{tag} Japan: pins {names}")
        if name == "Tohoku":
            if not all(p["id"].startswith("g:") for p in s["pins"]) or len(s["pins"]) != 6:
                probs.append(f"{tag} Tohoku: {len(s['pins'])} pins, expected 6 prefecture pins")
            if "Tohoku" not in s["chip"] or not s["info"].startswith("Tohoku · "):
                probs.append(f"{tag} Tohoku: chip '{s['chip']}', info '{s['info']}'")
    click(page, '.mm-pin[data-id="g:asia/east-asia/japan/tohoku/iwate"]')
    s = state(page)
    probs += pin_problems(s, f"{tag} Iwate")
    if s["kind"] != "makers" or not s["pins"] or not all(p["id"].startswith(("m:", "stack:")) for p in s["pins"]):
        probs.append(f"{tag} Iwate: expected maker pins, got {[p['id'] for p in s['pins']][:4]}")
    # a maker card
    mk = next((p for p in s["pins"] if p["id"].startswith("m:")), None)
    if mk is None:                                          # a stack: spread it, then pick one
        stack = s["pins"][0]["id"]
        click(page, f'.mm-pin[data-id="{stack}"]')
        s2 = state(page)
        probs += pin_problems(s2, f"{tag} fanned stack")
        mk = next((p for p in s2["pins"] if p["id"].startswith("m:")), None)
    if mk:
        click(page, f'.mm-pin[data-id="{mk["id"]}"]')
        s3 = state(page)
        card = page.eval("(() => { const c = document.querySelector('#mm-card'); const a = c.querySelector('a'); const r = c.getBoundingClientRect(); const h = document.querySelector('#mapbox').getBoundingClientRect(); return { hidden: c.hidden, text: c.textContent, href: a && a.getAttribute('href'), inside: r.left >= h.left - 1 && r.right <= h.right + 1 && r.top >= h.top - 1 && r.bottom <= h.bottom + 1 }; })()")
        if card["hidden"] or not card["href"] or not card["href"].startswith("#/producer/") or "Open maker" not in card["text"] or not card["inside"]:
            probs.append(f"{tag}: maker card {card}")
        if s3["info"] != s["info"]:
            probs.append(f"{tag}: the info line changed on a maker card")
        esc(page)
        if state(page)["card"]:
            probs.append(f"{tag}: Esc did not close the maker card")
    # up: Esc goes up a level, Back too, the breadcrumb jumps
    esc(page)
    s = state(page)
    if s["at"] != "asia/east-asia/japan/tohoku":
        probs.append(f"{tag}: Esc from Iwate gave '{s['at']}'")
    click(page, "#mm-back")
    s = state(page)
    if s["at"] != "asia/east-asia/japan":
        probs.append(f"{tag}: Back from Tohoku gave '{s['at']}'")
    click(page, '.mm-crumb[data-at="asia"]')
    s = state(page)
    if s["at"] != "asia" or s["crumbs"] != ["World", "Asia"]:
        probs.append(f"{tag}: the breadcrumb jump gave '{s['at']}' {s['crumbs']}")
    click(page, '.mm-crumb[data-at=""]')
    s = state(page)
    if s["at"] != "" or s["back"]:
        probs.append(f"{tag}: back to the World gave '{s['at']}'")
    if not full:
        return probs
    # the whole tree: the two rules, and no pin heads overlapping anywhere
    p2, tree = tree_checks(page, tag)
    probs += p2
    for st in tree["states"]:
        s = open_at(page, st["path"])
        probs += pin_problems(s, f"{tag} {st['path'] or 'World'}")
        if st["kind"] == "groups" and not all(p["id"].startswith("g:") or p["id"].startswith("m:") for p in s["pins"]):
            probs.append(f"{tag} {st['path']}: group view shows {[p['id'] for p in s['pins']][:3]}")
        if st["kind"] == "makers" and s["pins"] and any(p["id"].startswith("g:") for p in s["pins"]):
            probs.append(f"{tag} {st['path']}: makers view shows group pins")
        if st["kind"] == "groups" and sorted(p["label"].split(",")[0] for p in s["pins"] if p["id"].startswith("g:")) != sorted(g[0] for g in st["groups"]):
            probs.append(f"{tag} {st['path']}: pins do not match the groups {st['groups']}")
    # map and list together
    s = open_at(page, "asia/east-asia/japan/tohoku")
    if s["count"] != "37 makers" and not s["count"].endswith(" makers"):
        probs.append(f"{tag}: count '{s['count']}'")
    page.eval("(() => { const q = document.querySelector('#mq'); q.value = 'akabu'; q.dispatchEvent(new Event('input', { bubbles: true })); })()")
    page.eval("new Promise(r => setTimeout(r, 400))", await_promise=True)
    s = state(page)
    if s["tiles"] != 1 or s["count"] != "1 maker" or not s["info"].split(" · ")[1].startswith("1 maker") or s["crumbs"][-1] != "Iwate":
        probs.append(f"{tag}: search 'akabu': tiles {s['tiles']}, count '{s['count']}', info '{s['info']}', crumbs {s['crumbs']}")
    probs += pin_problems(s, f"{tag} search")
    page.eval("(() => { const q = document.querySelector('#mq'); q.value = ''; q.dispatchEvent(new Event('input', { bubbles: true })); })()")
    page.eval("new Promise(r => setTimeout(r, 400))", await_promise=True)
    s = state(page)
    if s["at"] != "asia/east-asia/japan/tohoku" or s["crumbs"][-1] != "Tohoku":
        probs.append(f"{tag}: clearing the search left place '{s['at']}' {s['crumbs']}")
    page.eval("(() => { const c = document.querySelector('#mcountry'); c.value = 'south-korea'; c.dispatchEvent(new Event('change', { bubbles: true })); })()")
    s = state(page)
    if s["at"] != "asia/east-asia/south-korea" or s["country"] != "south-korea" or s["tiles"] != 8:
        probs.append(f"{tag}: choosing South Korea: place '{s['at']}', {s['tiles']} makers")
    for old, want_at, want_n in (("country=japan", "asia/east-asia/japan", None), ("region=iwate", "asia/east-asia/japan/tohoku/iwate", None), ("country=south-korea", "asia/east-asia/south-korea", 8)):
        go(page, f"#/makers?{old}")
        s = state(page)
        if s["at"] != want_at or (want_n and s["tiles"] != want_n):
            probs.append(f"{tag}: old link ?{old} gave place '{s['at']}' with {s['tiles']} makers")
    return probs


def maker_map_checks(page, base, tag, keys):
    """A maker page: the province hatched, the pin, the capital, towns and no overlapping labels."""
    probs = []
    for key in keys:
        go(page, f"#/producer/{key}")
        wait_for(page, "!!document.querySelector('#locator .mm-labels') || !document.querySelector('#locator')", 15)
        r = page.eval(r"""(() => {
          const loc = document.querySelector('#locator');
          if (!loc) return { none: true };
          const lr = loc.getBoundingClientRect();
          const names = [...loc.querySelectorAll('.mm-name')].map((t) => ({ t: t.textContent, cap: t.classList.contains('cap'), r: t.getBoundingClientRect() }));
          const head = loc.querySelector('.mm-maker-pin .pin-head')?.getBoundingClientRect();
          const tip = loc.querySelector('.mm-maker-pin')?.getBoundingClientRect();
          const bad = [];
          for (let i = 0; i < names.length; i++) {
            const a = names[i].r;
            if (a.left < lr.left - 1 || a.right > lr.right + 1 || a.top < lr.top - 1 || a.bottom > lr.bottom + 1) bad.push(names[i].t + ' leaves the map');
            for (let j = i + 1; j < names.length; j++) { const b = names[j].r; if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) bad.push(names[i].t + ' / ' + names[j].t + ' overlap'); }
            if (head && a.left < head.right && a.right > head.left && a.top < head.bottom && a.bottom > head.top) bad.push(names[i].t + ' covers the pin');
          }
          const inset = loc.querySelector('.mm-inset');
          return { svg: !!loc.querySelector('.mm-svg'), sel: loc.querySelectorAll('.g-country path.sel').length, pin: !!head, headIn: !!head && head.left >= lr.left && head.right <= lr.right && head.top >= lr.top, names: names.map((n) => n.t), stars: loc.querySelectorAll('.mm-star').length,
            towns: loc.querySelectorAll('.mm-town').length, inset: !!inset, insetSel: inset ? inset.querySelectorAll('path.sel').length : 0, label: loc.getAttribute('aria-label'), bad,
            w: lr.width, sideways: document.documentElement.scrollWidth > innerWidth + 1 };
        })()""")
        if r.get("none"):
            probs.append(f"{tag} {key}: no map on the maker page")
            continue
        label = f"{tag} {key}"
        if not (r["svg"] and r["sel"] == 1 and r["pin"] and r["headIn"] and r["inset"] and r["insetSel"] == 1):
            probs.append(f"{label}: map incomplete {{svg {r['svg']}, province paths {r['sel']}, pin {r['pin']}, pin in view {r['headIn']}, inset {r['inset']}/{r['insetSel']}}}")
        if r["bad"]:
            probs.append(f"{label}: labels {r['bad'][:3]}")
        if r["stars"] > 1 or r["towns"] > 4:
            probs.append(f"{label}: {r['stars']} capital stars, {r['towns']} towns")
        if not r["label"] or not r["label"].startswith("Map of ") or "showing" not in r["label"]:
            probs.append(f"{label}: screen-reader words '{r['label']}'")
        if r["sideways"]:
            probs.append(f"{label}: sideways scroll")
    return probs


def shoot(page, base, tag, out):
    """The screenshots Plan 14 section 9 asks for, one pass after the checks (a scroll and a capture in the middle of a walk
    can stall the next route change in headless Edge)."""
    Path(out).mkdir(parents=True, exist_ok=True)

    def board():
        page.scroll_to(int(page.eval("(document.querySelector('.map-board').getBoundingClientRect().top + scrollY) - 8")))
        page.eval("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))", await_promise=True)

    for name, at in (("world", ""), ("asia", "asia"), ("japan", "asia/east-asia/japan"), ("tohoku", "asia/east-asia/japan/tohoku")):
        open_at(page, at)
        board()
        page.screenshot(f"{out}/map-{name}-{tag}.png")
    open_at(page, "asia/east-asia/japan/tohoku/iwate")
    s = state(page)
    pin = next((p for p in s["pins"] if p["id"].startswith("stack:")), None)
    if pin:
        click(page, f'.mm-pin[data-id="{pin["id"]}"]')
        s = state(page)
    mk = next((p for p in s["pins"] if p["id"].startswith("m:")), None)
    if mk:
        click(page, f'.mm-pin[data-id="{mk["id"]}"]')
    board()
    page.screenshot(f"{out}/map-card-{tag}.png")
    for name, route in (("counter-topup", "#/wine"), ("sake-shelves", "#/sake")):
        load(page, base, route)
        page.eval("new Promise(r => setTimeout(r, 700))", await_promise=True)
        page.screenshot(f"{out}/{name}-{tag}.png")
    for name, key in (("japan", "akabu-shuzo"), ("korea", "daejeon-blues-brewery"), ("france", "kronenbourg"), ("singapore", "orchid-sake-brewery")):
        go(page, f"#/producer/{key}")
        wait_for(page, "!!document.querySelector('#locator .mm-labels')", 15)
        page.scroll_to(int(page.eval("(document.querySelector('.facts').getBoundingClientRect().top + scrollY) - 8")))
        page.eval("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))", await_promise=True)
        page.screenshot(f"{out}/maker-{name}-{tag}.png")


def weight(page, base, docs):
    """Bytes the Makers page needs at the World level (Plan 14 section 9: under 300 KB): the data, script, style and map files it
    loads, as gzip would send them (GitHub Pages compresses text). Returns (kilobytes, [(file, bytes)])."""
    import gzip
    load(page, base, "#/makers")
    state(page)
    names = page.eval("performance.getEntriesByType('resource').map((e) => e.name)")
    seen, rows = set(), []
    for n in names:
        path = n.split(base, 1)[-1].split("?")[0].lstrip("/")
        if path in seen or not path.startswith(("data/", "assets/js/", "assets/css/", "assets/maps/")):
            continue
        seen.add(path)
        f = Path(docs) / path
        if f.exists():
            rows.append((path, len(gzip.compress(f.read_bytes(), 6))))
    return sum(r[1] for r in rows) / 1024, sorted(rows, key=lambda r: -r[1])


def pick(page, base):
    """One maker per country (the first with a capital shown), plus Akabu Shuzo, from producers.json."""
    prods = page.eval("fetch('data/producers.json').then(r => r.json())", await_promise=True)
    by_country = {}
    for p in prods:
        if p.get("cid") and p.get("prov"):
            by_country.setdefault(p["cid"], p["key"])
    return prods, by_country


def run(base, shots_dir=None, sizes=SIZES, log=print):
    from cdp import Browser
    problems = []
    with Browser() as b:
        for w, h in sizes:
            page = b.page(w, h, mobile=w < 500)
            tag = f"{w}x{h}"
            load(page, base, "#/makers")
            prods, by_country = pick(page, base)
            log(f"{tag}: Makers map")
            problems += map_checks(page, base, tag)
            keys = list(by_country.values()) + [k for k in ("akabu-shuzo", "daejeon-blues-brewery", "kronenbourg", "orchid-sake-brewery") if k not in by_country.values()]
            log(f"{tag}: {len(keys)} maker page maps")
            problems += maker_map_checks(page, base, tag, keys)
            if shots_dir:
                shoot(page, base, tag, shots_dir)
            if page.logs:
                problems += [f"{tag}: console: {m}" for m in page.logs[:3]]
                page.logs.clear()
            page.close()
    return problems


def main():
    import argparse
    import http.server
    import socketserver
    import threading
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", nargs="?", const=str(SHIP / "reports" / "plan14"), default=None)
    ap.add_argument("--docs", default=str(SHIP / "docs"))
    ap.add_argument("--all-makers", action="store_true", help="check every maker page's map, not one per country")
    a = ap.parse_args()
    import smoke
    smoke.DOCS = Path(a.docs)
    with smoke.Server() as srv:
        probs = run(f"http://127.0.0.1:{srv.port}", a.shots)
    for p in probs:
        print("PROBLEM:", p)
    print("OK" if not probs else f"{len(probs)} problems")
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
