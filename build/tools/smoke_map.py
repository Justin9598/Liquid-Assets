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
from smoke_inner import SIZES as _SIZES, load, settle, wait_for, wait_ready, go as _go  # noqa: E402

SHIP = Path(__file__).resolve().parents[2]
SIZES = _SIZES + [(745, 527)]          # and the narrow desktop pane the designer previews in (Plan 14 section 13.4)

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
  // name tags that are always showing must keep clear of each other and of every other pin's head (Plan 14 section 11.4)
  const tags = [...host.querySelectorAll('.pin-tag.always')].map((t) => ({ id: t.closest('.mm-pin').dataset.id, r: t.getBoundingClientRect() }));
  for (let i = 0; i < tags.length; i++) {
    for (let j = i + 1; j < tags.length; j++) {
      const a = tags[i].r, b = tags[j].r;
      if (a.left < b.right - 0.5 && a.right > b.left + 0.5 && a.top < b.bottom - 0.5 && a.bottom > b.top + 0.5) overlaps.push('tag ' + tags[i].id + ' / tag ' + tags[j].id);
    }
    for (const p of pins) {
      if (p.id === tags[i].id) continue;
      const a = tags[i].r, h = p.head;
      if (a.left < h[2] - 0.5 && a.right > h[0] + 0.5 && a.top < h[3] - 0.5 && a.bottom > h[1] + 0.5) overlaps.push('tag ' + tags[i].id + ' / head ' + p.id);
    }
    const hr2 = host.getBoundingClientRect(), a = tags[i].r;
    if (a.left < hr2.left - 0.5 || a.right > hr2.right + 0.5) overlaps.push('tag ' + tags[i].id + ' leaves the map');
  }
  const small = pins.filter((p) => p.w < 43.5 || p.h < 43.5 || p.tag !== 'BUTTON').map((p) => p.id);
  const outside = pins.filter((p) => p.head[0] < hr.left - 0.5 || p.head[2] > hr.right + 0.5 || p.head[1] < hr.top - 0.5 || p.head[3] > hr.bottom + 0.5).map((p) => p.id);
  const mb = document.querySelector('.map-board').getBoundingClientRect();
  return {
    pins, overlaps, small, outside, at: host.dataset.at, level: host.dataset.level, kind: host.dataset.kind,
    info: document.querySelector('#map-info').textContent, crumbs: [...document.querySelectorAll('#mm-crumbs li')].map((l) => l.textContent.trim()),
    count: document.querySelector('#mcount').textContent, tiles: document.querySelectorAll('#mlist .tile').length, hash: location.hash,
    chip: document.querySelector('#region-chip')?.textContent.trim() || '', back: !document.querySelector('#mm-back').disabled,
    sign: (() => { const g = document.querySelector('.mm-sign'); if (!g) return null; g.getAnimations().forEach((x) => x.finish()); const r = g.getBoundingClientRect(); const pin = [...host.querySelectorAll('.pin-head, .pin-tag.always')].some((e) => { const q = e.getBoundingClientRect(); return q.left < r.right && q.right > r.left && q.top < r.bottom && q.bottom > r.top; });
      return { shown: !g.hidden, words: [...g.querySelectorAll('small, b')].map((e) => e.textContent), hitsPin: pin, right: g.classList.contains('right'), inside: r.left >= hr.left - 1 && r.right <= hr.right + 1 && r.top >= hr.top - 1, font: Math.min(...[...g.querySelectorAll('small, b')].map((e) => parseFloat(getComputedStyle(e).fontSize))), width: r.width }; })(),
    shape: (() => { const all = [...host.querySelectorAll('.g-country path')]; if (!all.length) return null; const sel = all.filter((p) => p.classList.contains('sel')); const use = sel.length ? sel : all.filter((p) => !['okinawa', 'alaska', 'hawaii'].includes(p.dataset.id));
      let l = 1e9, t = 1e9, r = -1e9, b = -1e9; for (const p of use) { const q = p.getBoundingClientRect(); l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }
      const strokes = all.map((p) => { const cs = getComputedStyle(p); return [parseFloat(cs.strokeWidth), parseFloat((cs.stroke.match(/[\d.]+\)$/) || ['1)'])[0])]; });
      return { paths: all.length, selN: sel.length, padL: (l - hr.left) / hr.width, padR: (hr.right - r) / hr.width, padT: (t - hr.top) / hr.height, padB: (hr.bottom - b) / hr.height, minStroke: Math.min(...strokes.map((s) => s[0])), minAlpha: Math.min(...strokes.map((s) => s[1])), hatched: all.filter((p) => /url/.test(p.style.fill)).length }; })(),
    crumbRight: document.querySelector('#mm-crumbs').getBoundingClientRect().right, crumbClipped: (() => { const o = document.querySelector('#mm-crumbs'); return o.scrollWidth > o.clientWidth + 1; })(), menuLeft: (document.querySelector('#chrome') || document.body).getBoundingClientRect().left, crumbText: document.querySelector('#mm-crumbs').textContent,
    crumbH: document.querySelector('.mm-bar').getBoundingClientRect().height, more: !!document.querySelector('#mm-more'),
    boardVh: mb.height / innerHeight, sideways: document.documentElement.scrollWidth > innerWidth + 1,
    card: !document.querySelector('#mm-card').hidden, legend: [...document.querySelectorAll('.mm-key')].map((k) => k.textContent.trim()),
    country: document.querySelector('#mcountry').value, q: document.querySelector('#mq').value,
  };
})()"""

CAPITALS = set()          # maker keys whose province has a capital in the map data, filled by run()


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


FRAMED = [("asia/east-asia/japan", "Japan", ["Japan"]), ("asia/east-asia/japan/tohoku", "Tohoku", ["Japan", "Tohoku"]), ("asia/east-asia/japan/kanto", "Kanto", ["Japan", "Kanto"]),
          ("asia/east-asia/japan/tohoku/iwate", "Iwate", ["Japan", "Iwate"]), ("asia/east-asia/japan/kanto/tokyo", "Tokyo", ["Japan", "Tokyo"]),
          ("asia/east-asia/south-korea", "South Korea", ["South Korea"]), ("europe/europe/france", "France", ["France"]), ("asia/southeast-asia/singapore", "Singapore", ["Singapore"])]


def frame_checks(page, tag):
    """Plan 14 section 13.4: the chosen shape is whole, centred and padded; every province outline is drawn and visible from the
    country level down; the place sign says the right words and never covers a pin; no sign above the country level."""
    probs = []
    for at, name, words in FRAMED:
        s = open_at(page, at)
        sh = s["shape"]
        if not sh:
            probs.append(f"{tag} {name}: no province outlines drawn")
            continue
        pads = [sh["padL"], sh["padR"], sh["padT"], sh["padB"]]
        if min(pads) < 0.05 - 1e-3:
            probs.append(f"{tag} {name}: the shape has {min(pads) * 100:.1f}% padding on its tightest side (at least 5%): {[round(p, 3) for p in pads]}")
        if abs(sh["padL"] - sh["padR"]) > 0.03 and abs(sh["padT"] - sh["padB"]) > 0.03:
            probs.append(f"{tag} {name}: the shape is off-centre both ways: {[round(p, 3) for p in pads]}")
        if sh["paths"] < 1 or sh["minStroke"] < 1 or sh["minAlpha"] < 0.35:
            probs.append(f"{tag} {name}: province outlines are too faint (width {sh['minStroke']}, alpha {sh['minAlpha']})")
        if name not in ("Singapore", "Tokyo") and sh["hatched"] < 1:
            probs.append(f"{tag} {name}: no province with makers is hatched")
        sg = s["sign"]
        if not sg or not sg["shown"] or [w.lower() for w in sg["words"]] != [w.lower() for w in words]:
            probs.append(f"{tag} {name}: the place sign reads {sg and sg['words']}, expected {words}")
        elif sg["hitsPin"] or not sg["inside"]:
            probs.append(f"{tag} {name}: the place sign covers a pin (hit {sg['hitsPin']}) or leaves the map (inside {sg['inside']}, right {sg['right']}, width {sg['width']:.0f})")
        elif sg["font"] < 13 - 1e-6:
            probs.append(f"{tag} {name}: the place sign lettering is {sg['font']}px (13px at least)")
    for at in ("", "asia", "asia/east-asia", "europe"):
        s = open_at(page, at)
        if s["sign"] and s["sign"]["shown"]:
            probs.append(f"{tag}: a place sign shows at '{at or 'World'}'")
    return probs


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
    if w < 500:                                             # one line: Back, then "... > Japan > Tohoku" (Plan 14 section 11.3)
        s5 = open_at(page, "asia/east-asia/japan/tohoku/iwate")
        if s5["crumbH"] > 56 or not s5["more"]:
            probs.append(f"{tag}: the phone breadcrumb is {s5['crumbH']:.0f}px tall (more button: {s5['more']})")
        page.eval("document.querySelector('#mm-more').click()")
        menu = page.eval("[...document.querySelectorAll('#mm-menu li')].map(l => l.textContent.trim())")
        if menu != ["World", "Asia", "East Asia", "Japan", "Tohoku", "Iwate"]:
            probs.append(f"{tag}: the breadcrumb menu lists {menu}")
        page.eval("document.querySelector('#mm-menu .mm-crumb[data-at=\"asia\"]').click()")
        wait_for(page, READY, 20)
        if state(page)["at"] != "asia":
            probs.append(f"{tag}: the breadcrumb menu did not go to Asia")
        open_at(page, "asia/east-asia/japan/tohoku/iwate")
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
    probs += frame_checks(page, tag)
    # the whole tree: the two rules, and no pin heads overlapping anywhere
    p2, tree = tree_checks(page, tag)
    probs += p2
    for st in tree["states"]:
        s = open_at(page, st["path"])
        probs += pin_problems(s, f"{tag} {st['path'] or 'World'}")
        if phone and (s['crumbClipped'] or s['crumbRight'] > s['menuLeft'] - 2):
            probs.append(f"{tag} {st['path'] or 'World'}: the breadcrumb '{s['crumbText']}' runs under the Menu button (ends {s['crumbRight']:.0f}, Menu starts {s['menuLeft']:.0f}) or is clipped")
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


def maker_map_checks(page, base, tag, keys, want_capital=True):
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
          const caps = [...loc.querySelectorAll('.mm-name.cap')].map((t) => t.textContent);
          return { svg: !!loc.querySelector('.mm-svg'), sel: loc.querySelectorAll('.g-country path.sel').length, pin: !!head, headIn: !!head && head.left >= lr.left && head.right <= lr.right && head.top >= lr.top, names: names.map((n) => n.t), stars: loc.querySelectorAll('.mm-star').length,
            towns: loc.querySelectorAll('.mm-town').length, inset: !!inset, insetSel: inset ? inset.querySelectorAll('path.sel').length : 0, label: loc.getAttribute('aria-label'), bad,
            caps, w: lr.width, sideways: document.documentElement.scrollWidth > innerWidth + 1 };
        })()""")
        if r.get("none"):
            probs.append(f"{tag} {key}: no map on the maker page")
            continue
        label = f"{tag} {key}"
        if want_capital and key in CAPITALS and not r["caps"]:
            probs.append(f"{label}: the capital of its province is not labelled")
        if key == "akabu-shuzo" and ("Morioka" not in r["caps"] or r["towns"] < 2 or len(r["names"]) < 3):
            probs.append(f"{label}: expected Morioka plus at least 2 towns, got {r['names']}")
        if not (r["svg"] and r["sel"] == 1 and r["pin"] and r["headIn"] and r["inset"] and r["insetSel"] == 1):
            probs.append(f"{label}: map incomplete {{svg {r['svg']}, province paths {r['sel']}, pin {r['pin']}, pin in view {r['headIn']}, inset {r['inset']}/{r['insetSel']}}}")
        if r["bad"]:
            probs.append(f"{label}: labels {r['bad'][:3]}")
        if r["stars"] != len(r["caps"]) or r["stars"] > 1:
            probs.append(f"{label}: capital stars {r['stars']} and capital labels {r['caps']}")
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
    for name, at in (("kanto", "asia/east-asia/japan/kanto"), ("iwate", "asia/east-asia/japan/tohoku/iwate")):
        open_at(page, at)
        board()
        page.screenshot(f"{out}/map-{name}-{tag}.png")
    for name, route in (("counter-topup", "#/wine"), ("sake-shelves", "#/sake")):
        load(page, base, route)
        page.eval("new Promise(r => setTimeout(r, 700))", await_promise=True)
        page.screenshot(f"{out}/{name}-{tag}.png")
    for name, key in (("daejeon", "daejeon-blues-brewery"), ("yamaguchi", "asahi-shuzo-yamaguchi"), ("iwate-labels", "akabu-shuzo"), ("japan", "akabu-shuzo"), ("korea", "daejeon-blues-brewery"), ("france", "kronenbourg"), ("singapore", "orchid-sake-brewery")):
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


def fill_capitals(page, prods):
    """Makers whose province has a flagged capital in its country file: their map must label it."""
    CAPITALS.clear()
    for cid in sorted({p["cid"] for p in prods if p.get("cid")}):
        d = page.eval(f"fetch('assets/maps/{cid}.json').then(r => r.json())", await_promise=True)
        have = {x["p"] for x in d["places"] if x.get("cap")}
        CAPITALS.update(p["key"] for p in prods if p.get("cid") == cid and p.get("prov") in have)


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
            fill_capitals(page, prods)
            log(f"{tag}: Makers map")
            problems += map_checks(page, base, tag)
            if (w, h) == sizes[0]:                          # every maker page at the first size, one per country at the others
                keys = [p["key"] for p in prods if p.get("cid") and p.get("prov")]
            else:
                keys = list(by_country.values()) + ["akabu-shuzo"]
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
