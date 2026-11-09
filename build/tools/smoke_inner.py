"""Browser checks for the inner pages (Plan 08 sections 3 to 6 and 9). Used by smoke.py when the served site is a Phase 2 build.

Drives headless Edge through tools/cdp.py at the four sizes (1440x900, 1920x1080, 375x812, 390x844) over every page type:
the shelf list pages (Junmai Ginjo, and Makgeolli as a sparse shelf), drink pages (photo with a tasting card, no photo, had
several times), the producer page for Akebono Shuzo, the Makers index and the empty-shelf page. On each it checks:
  - no sideways scroll, and no two boards overlap
  - chalk only: every text node is on a blackboard in Kalam (or the CJK fallback stack), none in Outfit, Cormorant, Stardos
    or Rye; every text is at least 14px, body text at least 17px with no grain mask, data at least 16px
  - contrast: every chalk text, at its real opacity, is at least 4.5:1 on the slate (worst-case smudge)
  - the fixed bar: #backdrop is fixed and does not move on scroll, the right plate is used (bar-tall on phones), the sign link
    exists, and the first board starts below the sign
  - no old look: no brick wall, crate, puck, drawn bottle or paper panel left in the page
  - full height: the page fills the viewport and the footer is at the bottom
  - the drink hero has no empty half at 1024px and up
and once per size: the burger menu opens for real on an inner page with The Makers live (no "Soon"), the map has exactly one
highlighted prefecture on every Japanese producer page (or no map), the Makers map filters by one prefecture, and the
welcome page moves to an inner page and back.
"""
from __future__ import annotations

import json
import os
import time

SIZES = [(1440, 900), (1920, 1080), (375, 812), (390, 844)]

MEASURE = r"""(() => {
  const out = { problems: [], stats: {} };
  const bad = (m) => out.problems.push(m);
  const vw = innerWidth, vh = innerHeight;
  const de = document.documentElement;
  const SLATE = [38, 42, 40], CHALK = [242, 237, 228];
  // the slate under the strongest chalk smudge of its board: XL up to 10% (smudges scaled 1.4), L and M 6%, S 3% (Plan 07 section 10)
  const worstFor = (el) => { const b = el.closest('.chalkboard'); const k = !b ? 0.1 : b.classList.contains('chalkboard--xl') ? 0.1 : b.classList.contains('chalkboard--s') ? 0.03 : 0.06; return SLATE.map((v, i) => v + k * (CHALK[i] - v)); };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const rgba = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return [0, 0, 0, 1]; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const fixedAncestor = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) if (getComputedStyle(e).position === 'fixed') return true; return false; };
  const inPage = (el) => el.closest('#page, #footer, #chrome');

  // 1. no sideways scroll, and no moment during loading when the page was wider than the window (a phone would zoom out and
  //    measure the bar at the wrong size)
  if (window.__maxw && window.__maxw > vw) bad(`the layout viewport grew to ${window.__maxw}px wide while the page loaded (a phone would zoom out)`);
  if (de.scrollWidth > vw) bad(`sideways scroll: document is ${de.scrollWidth}px wide in a ${vw}px window`);
  if (document.body.scrollWidth > vw) bad(`sideways scroll: body is ${document.body.scrollWidth}px wide`);
  const wide = [...document.querySelectorAll('#page *')].filter((e) => !e.closest('.strip, .mini-row, .tile-row, .thumbs, .mm-stage, .bd') && e.getBoundingClientRect().right > vw + 1 && visible(e) && !fixedAncestor(e));
  if (wide.length) bad(`${wide.length} element(s) reach past the right edge, e.g. ${wide[0].className || wide[0].tagName}`);

  // 2. no two boards overlap (fixed things such as the menu and the filter sheet are overlays, not boards)
  const boards = [...document.querySelectorAll('#page .chalkboard, #footer')].filter((e) => visible(e) && !fixedAncestor(e) && getComputedStyle(e).position !== 'fixed');
  const rects = boards.map((e) => ({ e, r: e.getBoundingClientRect() }));
  let overlaps = 0;
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
    const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (w > 2 && h > 2) { overlaps++; if (overlaps <= 3) bad(`boards overlap: "${(a.e.textContent || '').trim().slice(0, 24)}" and "${(b.e.textContent || '').trim().slice(0, 24)}" (${Math.round(w)}x${Math.round(h)}px)`); }
  }
  out.stats.boards = boards.length;

  // 3. chalk only, sizes, contrast
  const CJK = /[　-ヿ㐀-鿿가-힯＀-￯]/;
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let minRatio = 99, minAt = '', texts = 0, minSize = 99;
  const fams = new Set();
  const seen = new Set();
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    const text = n.nodeValue.trim();
    if (!text) continue;
    const el = n.parentElement;
    if (!el || !inPage(el) || el.closest('script, style, noscript, .sr-only, option, optgroup, .b3, #live')) continue;
    if (!visible(el)) continue;
    texts++;
    const cs = getComputedStyle(el);
    const fam = cs.fontFamily;
    fams.add(fam.split(',')[0].replace(/["']/g, '').trim());
    if (/outfit|cormorant|stardos|rye/i.test(fam)) bad(`old font on "${text.slice(0, 24)}": ${fam}`);
    const primary = fam.split(',')[0].replace(/["']/g, '').trim();
    if (CJK.test(text) ? !/Yu Gothic|Hiragino|Noto Sans JP|Malgun/.test(fam) : primary !== 'Kalam') { if (!seen.has(fam + text.slice(0, 6))) { seen.add(fam + text.slice(0, 6)); bad(`not chalk: "${text.slice(0, 24)}" is in ${fam.slice(0, 40)}`); } }
    if (!el.closest('.chalkboard')) bad(`text not on a blackboard: "${text.slice(0, 30)}"`);
    const fs = parseFloat(cs.fontSize);
    minSize = Math.min(minSize, fs);
    if (fs < 14) bad(`text under 14px (${fs}px): "${text.slice(0, 30)}"`);
    // effective chalk colour: its own alpha times every opacity up the tree
    const c = rgba(cs.color);
    let a = c[3];
    for (let e = el; e && e !== document.body; e = e.parentElement) a *= parseFloat(getComputedStyle(e).opacity);
    const W = worstFor(el);
    const eff = [0, 1, 2].map((i) => c[i] * a + W[i] * (1 - a));
    const r = ratio(eff, W);
    if (r < minRatio) { minRatio = r; minAt = text.slice(0, 30); }
    if (r < 4.5) bad(`contrast ${r.toFixed(2)}:1 on "${text.slice(0, 30)}"`);
  }
  out.stats.textNodes = texts;
  out.stats.fonts = [...fams];
  out.stats.minContrast = +minRatio.toFixed(2);
  out.stats.minContrastAt = minAt;
  out.stats.minFontPx = minSize;
  for (const el of document.querySelectorAll('#page .t-body')) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    if (parseFloat(cs.fontSize) < 17) bad(`body text under 17px (${cs.fontSize})`);
    const mk = cs.webkitMaskImage || cs.maskImage;
    if (mk && mk !== 'none') bad('body text has the grain mask');
    if (parseFloat(cs.lineHeight) / parseFloat(cs.fontSize) < 1.55) bad(`body line-height under 1.6 (${cs.lineHeight})`);
    const maxCh = parseFloat(cs.maxWidth);
    if (!(maxCh > 0) && cs.maxWidth !== 'none') bad(`body text max-width ${cs.maxWidth}`);
  }
  for (const el of document.querySelectorAll('#page .t-data')) if (visible(el) && parseFloat(getComputedStyle(el).fontSize) < 16) bad('data text under 16px');

  // 4. the fixed bar behind the page
  const bd = document.getElementById('backdrop');
  if (!bd) bad('no #backdrop (the fixed bar)');
  else {
    const cs = getComputedStyle(bd), r = bd.getBoundingClientRect();
    if (cs.position !== 'fixed') bad('#backdrop is not position: fixed');
    if (Math.abs(r.width - vw) > 20 || Math.abs(r.height - vh) > 1) bad(`#backdrop does not fill the window (${Math.round(r.width)}x${Math.round(r.height)})`);
    const img = bd.querySelector('img');
    const src = (img && (img.currentSrc || img.src)) || '';
    const want = vw < 768 || vw < vh ? 'bar-tall' : 'bar-wide';
    if (!src.includes(want)) bad(`#backdrop shows ${src.split('/').pop()}, expected ${want}`);
    out.stats.plate = src.split('/').pop().split('?')[0];
    if (!img || !img.complete || img.naturalWidth === 0) bad('the plate image did not load');
  }
  const sign = document.querySelector('a.sign-link');
  if (!sign) bad('no sign link');
  else {
    if (sign.getAttribute('aria-label') !== 'Liquid Assets, back to the bar' || sign.getAttribute('href') !== '#/') bad('the sign link is wrong');
    const first = document.querySelector('#page .boards > *');
    const sr = sign.getBoundingClientRect();
    if (first && scrollY === 0) {
      const top = first.getBoundingClientRect().top;
      out.stats.firstBoardTop = Math.round(top);
      out.stats.signBottom = Math.round(sr.bottom);
      if (top < sr.bottom - 1) bad(`the first board starts at ${Math.round(top)}px, inside the sign (ends ${Math.round(sr.bottom)}px)`);
      if (top > sr.bottom + 140) bad(`the first board starts ${Math.round(top - sr.bottom)}px below the sign`);
    }
  }

  // the measured top of the page matches the plate as drawn right now (a stale number would put the first board over the sign)
  if (window.__scene && scrollY === 0) {
    const P = window.__scene.plates[document.documentElement.dataset.plate];
    const c = document.querySelector('#backdrop .plate-cover')?.getBoundingClientRect();
    const ct = parseFloat(getComputedStyle(de).getPropertyValue('--content-top'));
    if (P && c && Math.abs(ct - Math.max(0, c.top + P.content_top * c.height)) > 2) bad(`--content-top is ${ct}px but the plate puts it at ${Math.round(c.top + P.content_top * c.height)}px`);
  }

  // 5. none of the old look
  const old = document.querySelectorAll('#page .wall, #page .crate, #page .crate-tile, #page .puck, .menu-btn, .menu-overlay, #page .sketch, #page svg.bottle, #page .panel, #page .hero-bottle, #page .mini-sign');
  if (old.length) bad(`${old.length} old-look element(s) left, e.g. ${old[0].className}`);

  // 6. full height with the footer at the bottom
  const docH = de.scrollHeight;
  if (docH < vh) bad(`the page is ${docH}px tall in a ${vh}px window`);
  const ft = document.getElementById('footer');
  if (ft) {
    const fb = ft.getBoundingClientRect().bottom + scrollY;
    out.stats.footerGap = Math.round(docH - fb);
    if (docH - fb > 24) bad(`the footer ends ${Math.round(docH - fb)}px above the bottom of the page`);
    if (fb < vh - 24) bad(`the footer sits mid-screen (bottom ${Math.round(fb)}px of ${vh}px)`);
  }

  // 7. the fixed menu
  const burger = document.querySelector('#chrome [data-burger]');
  if (!burger || !visible(burger)) bad('no burger at the top right');
  else {
    const br = burger.getBoundingClientRect();
    out.stats.burgerH = Math.round(br.height);
    const wantH = vw < 768 ? 48 : 56;
    if (Math.abs(br.height - wantH) > 1.5) bad(`burger is ${br.height}px tall, expected ${wantH}px`);
    if (br.right > vw - 2 || br.top < 0) bad('the burger is not inside the top right corner');
  }
  if (/\bSoon\b/.test(document.body.innerText)) bad('"Soon" is still on the page');

  // 8. the drink hero has no empty half at 1024px and up
  const hero = document.querySelector('.hero-drink');
  if (hero && vw >= 1024) {
    const board = hero.closest('.chalkboard');
    const br = board.getBoundingClientRect();
    const cols = [...hero.children];
    const fill = cols.map((col) => {
      const kids = [...col.querySelectorAll('*')].filter((e) => visible(e) && !e.closest('.sr-only'));
      const bottom = Math.max(...kids.map((e) => e.getBoundingClientRect().bottom));
      return (bottom - br.top) / br.height;
    });
    out.stats.heroFill = fill.map((x) => +x.toFixed(2));
    if (fill.some((x) => x < 0.72)) bad(`the drink hero has an empty half (columns fill ${fill.map((x) => (x * 100).toFixed(0) + '%').join(' and ')} of the board)`);
  }
  // 9. the drink hero's action row follows the facts directly (Plan 08 section 11.1), and the column is centred on the photo
  const nav = document.querySelector('.hd-nav');
  if (nav && vw >= 768) {
    const btn = nav.querySelector('a, button');
    const prev = nav.previousElementSibling;
    if (btn && prev) {
      const gap = btn.getBoundingClientRect().top - prev.getBoundingClientRect().bottom;
      out.stats.actionGap = Math.round(gap);
      if (gap > 32) bad(`the action row is ${Math.round(gap)}px below the facts (at most 32px)`);
    }
    const a = document.querySelector('.hd-photo').getBoundingClientRect(), b = document.querySelector('.hd-copy').getBoundingClientRect();
    out.stats.heroCentreOffset = Math.round((a.top + a.bottom) / 2 - (b.top + b.bottom) / 2);
    if (Math.abs(out.stats.heroCentreOffset) > 6 && vw >= 1024) bad(`the text column is not centred on the photo (off by ${out.stats.heroCentreOffset}px)`);
  }

  // 10. Makers index on phones: the map board is short, Japan fully in it, and the search is within 1.1 screens of the top
  const mb = document.querySelector('.map-board');
  if (mb && vw < 768) {
    const r = mb.getBoundingClientRect();
    out.stats.mapBoardVh = +(r.height / vh).toFixed(2);
    if (r.height > 0.55 * vh) bad(`the map board is ${(100 * r.height / vh).toFixed(0)}% of the screen height (at most 55%)`);
    const sv = mb.querySelector('.mm-stage');
    const sr = sv && sv.getBoundingClientRect();
    if (!sr || sr.left < r.left - 1 || sr.right > r.right + 1 || sr.top < r.top - 1 || sr.bottom > r.bottom + 1 || sr.height < 180) bad('the map is not fully visible inside the map board');
    const q = document.getElementById('mq');
    if (q) {
      const top = q.getBoundingClientRect().top + scrollY;
      out.stats.searchTopVh = +(top / vh).toFixed(2);
      if (top > 1.1 * vh) bad(`the search field starts ${(top / vh).toFixed(2)} screens down (at most 1.1)`);
    }
  }
  return out;
})()"""

WIDTH_WATCH = "window.__maxw = 0; addEventListener('DOMContentLoaded', () => { const t = () => { window.__maxw = Math.max(window.__maxw, innerWidth); requestAnimationFrame(t); }; t(); addEventListener('resize', () => { window.__maxw = Math.max(window.__maxw, innerWidth); }); });"


READY_JS = """(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // every step has its own time limit and a name, so a hang is a clear failure within about 30s, never a transport timeout
  const step = async (name, ms, fn) => {
    const r = await Promise.race([Promise.resolve().then(fn).then(() => 'ok', (e) => 'threw ' + e), sleep(ms).then(() => 'timed out after ' + ms + 'ms')]);
    return r === 'ok' ? null : `step "${name}" ${r} (route ${location.hash}, ready=${document.body.dataset.ready || 'no'}, ${document.visibilityState}, ${document.querySelectorAll('.inner, .scene3').length} page(s) mounted)`;
  };
  const steps = [
    // 1. the app's own "route ready" flag: mounted, data and map in, fonts loaded, the move between pages finished
    ['route ready flag (body[data-ready])', 12000, async () => { while (document.body.dataset.ready !== '1') await sleep(25); }],
    // 2. fonts
    ['document.fonts.ready', 5000, () => document.fonts.ready],
    // 3. every image in or near the view decoded (lazy images far below the fold are not waited for)
    ['image decode()', 8000, () => Promise.all([...document.images].filter((i) => i.loading !== 'lazy' || i.getBoundingClientRect().top < innerHeight * 1.2).map((i) => i.decode().catch(() => {})))],
    // 4. only animations that are running: a paused or idle one never finishes
    ['running animations finishing', 4000, () => Promise.all(document.getAnimations().filter((a) => a.playState === 'running').map((a) => a.finished.catch(() => {})))],
    // 5. two drawn frames
    ['two animation frames', 2000, () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))],
  ];
  for (const [name, ms, fn] of steps) { const bad = await step(name, ms, fn); if (bad) return bad; }
  return 'ok';
})()"""

GO_JS = """(async (hash) => {
  const done = new Promise((resolve) => addEventListener('hashchange', resolve, { once: true }));
  location.hash = hash;
  await Promise.race([done, new Promise((r) => setTimeout(r, 4000))]);
})"""


def wait_ready(page):
    """Wait on real signals (route ready flag, fonts.ready, image decode(), finished animations), never on a fixed time."""
    r = page.eval(READY_JS, await_promise=True)
    if r != "ok":
        raise RuntimeError(r)


def go(page, hash_):
    """Change the route inside the page and wait until it is ready. The router clears the flag in its hashchange handler,
    which runs before ours, so the wait cannot see the old page's flag."""
    page.eval(f"{GO_JS}({json.dumps(hash_)})", await_promise=True)
    wait_ready(page)


def wait_for(page, js, timeout=15.0):
    """Wait for a condition inside the page (it is evaluated in the page, polling every animation frame)."""
    return bool(page.eval("""(async (expr, ms) => { const t0 = performance.now();
      while (performance.now() - t0 < ms) { if (eval(expr)) return true; await new Promise((r) => setTimeout(r, 20)); } return false; })(%s, %d)""" % (json.dumps(js), int(timeout * 1000)), await_promise=True))


def load(page, base, route):
    if not getattr(page, "_watching", False):
        page.send("Page.addScriptToEvaluateOnNewDocument", source=WIDTH_WATCH)
        page._watching = True
    page.goto(f"{base}/{route}")
    wait_ready(page)


def pick_routes(page, base):
    """Real routes for every page type, found in the data itself."""
    data = page.eval("""fetch('data/drinks.json').then(r=>r.json()).then(d=>({
      tasting: (d.find(x=>x.hasTasting&&x.thumb)||{}).id, nophoto: (d.find(x=>!x.thumb&&x.category==='sake')||{}).id,
      many: (d.find(x=>x.occasions>2)||{}).id, favourite: (d.find(x=>x.favourite&&x.thumb)||{}).id}))""", await_promise=True)
    prod = page.eval("""fetch('data/producers.json').then(r=>r.json()).then(p=>({akebono:(p.find(x=>/Akebono Shuzo/.test(x.name))||{}).key,
      jp:p.filter(x=>x.country==='Japan').map(x=>x.key)}))""", await_promise=True)
    return data, prod


def page_checks(page, base, route, label, size):
    load(page, base, route)
    page.eval("fetch('data/scene.json').then(r => r.json()).then(s => { window.__scene = s; })", await_promise=True)
    res = page.eval(MEASURE)
    probs = [f"{label}: {p}" for p in res["problems"]]
    return probs, res["stats"]


def run(base, shots_dir=None, sizes=SIZES, log=print):
    """Returns (problems, stats). `base` is the served Phase 2 site, e.g. http://127.0.0.1:8000"""
    from cdp import Browser
    problems, stats = [], {}
    with Browser() as b:
        p0 = b.page(1440, 900)
        p0.goto(base + "/", wait=0.5)
        data, prod = pick_routes(p0, base)
        p0.close()
        for w, h in sizes:
            mobile = w < 500
            page = b.page(w, h, mobile=mobile)
            if os.environ.get("SMOKE_THROTTLE"):                  # stress mode: a slow machine (CPU slowed this many times)
                page.throttle(float(os.environ["SMOKE_THROTTLE"]))
            tag = f"{w}x{h}"
            routes = [
                ("list Junmai Ginjo", "#/sake/junmai-ginjo"), ("list Makgeolli (sparse)", "#/fermented/makgeolli"),
                ("drink with photo and tasting card", f"#/drink/{data['tasting']}"), ("drink with no photo", f"#/drink/{data['nophoto']}"),
                ("drink had several times", f"#/drink/{data['many']}"), ("producer Akebono Shuzo", f"#/producer/{prod['akebono']}"),
                ("Makers index", "#/makers"), ("empty shelf", "#/sake/not-a-shelf"),
            ]
            for label, route in routes:
                probs, st = page_checks(page, base, route, f"{tag} {label}", (w, h))
                problems += probs
                stats[f"{tag} {label}"] = st
                if shots_dir:
                    page.screenshot(f"{shots_dir}/{label.split(' (')[0].replace(' ', '-').lower()}-{tag}.png")
                if page.logs:
                    problems += [f"{tag} {label}: console: {m}" for m in page.logs[:3]]
                    page.logs.clear()
            # a drink page scrolled halfway, to show the fixed bar behind the boards
            load(page, base, f"#/drink/{data['tasting']}")
            page.scroll_to(int(page.eval("document.documentElement.scrollHeight") / 3))
            mid = page.eval("""(() => { const r = document.getElementById('backdrop').getBoundingClientRect(); return [r.top, r.height, scrollY]; })()""")
            if mid[0] != 0 or abs(mid[1] - h) > 1 or mid[2] < 100:
                problems.append(f"{tag}: the backdrop moved or the page did not scroll (backdrop top {mid[0]}, scrollY {mid[2]})")
            if shots_dir:
                page.screenshot(f"{shots_dir}/drink-scrolled-{tag}.png")
            problems += producer_checks(page, base, tag)
            problems += welcome_checks(page, base, tag, shots_dir)
            problems += menu_checks(page, base, tag, shots_dir)
            problems += transition_checks(page, base, tag)
            if (w, h) == sizes[0]:
                problems += alias_checks(page, base, tag)
                problems += photo_checks(page, base, tag)
                problems += map_checks(page, base, prod, tag)
            else:
                problems += akebono_map(page, base, prod, tag)
                import smoke_map
                problems += smoke_map.map_checks(page, base, tag, full=False)
            problems += list_perf(b, base, w, h, stats, tag) if mobile else []
            page.close()
    return problems, stats


PRODUCER_JS = r"""(() => {
  const out = [];
  const bad = (m) => out.push(m);
  const title = document.querySelector('h1.t-title');
  const nat = title && title.querySelector('.native');
  if (nat) {
    const board = nat.closest('.chalkboard').getBoundingClientRect();
    const rg = document.createRange(); rg.selectNodeContents(nat);
    const tops = new Set([...rg.getClientRects()].map((r) => Math.round(r.top)));
    if (tops.size !== 1) bad('the native name is broken over ' + tops.size + ' lines');
    const r = nat.getBoundingClientRect();
    if (r.right > board.right - 4 || r.left < board.left) bad('the native name overflows its board');
    const fs = parseFloat(getComputedStyle(nat).fontSize);
    if (fs < 18) bad('the native name is ' + fs + 'px (18px at least)');
    if (innerWidth < 768 && getComputedStyle(nat).display !== 'block') bad('on a phone the native name is not on its own line');
  }
  for (const h of document.querySelectorAll('#page .t-head, #page .head-board')) {
    if (!h.getBoundingClientRect().height) continue;
    const tops = new Set();
    const tw = document.createTreeWalker(h, NodeFilter.SHOW_TEXT);
    for (let n = tw.nextNode(); n; n = tw.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) tops.add(Math.round(r.top / 6));
    }
    if (tops.size > 1) bad('the heading "' + h.textContent.trim().slice(0, 24) + '" wraps');
  }
  const site = document.querySelector('.facts .site');
  if (site) {
    const host = site.querySelector('.host');
    const board = site.closest('.chalkboard').getBoundingClientRect();
    if (host.scrollWidth > host.clientWidth + 1) bad('the website host is cut off at ' + innerWidth + 'px');
    if (site.getBoundingClientRect().right > board.right - 8) bad('the website link overflows the Facts board');
    const rg = document.createRange(); rg.selectNodeContents(host);
    if (new Set([...rg.getClientRects()].map((r) => Math.round(r.top))).size !== 1) bad('the website host wraps');
    if (!site.title) bad('the website link has no title');
  }
  // no fact value breaks inside a word
  for (const v of document.querySelectorAll('.facts .spec .val')) {
    const tw = document.createTreeWalker(v, NodeFilter.SHOW_TEXT);
    for (let n = tw.nextNode(); n; n = tw.nextNode()) {
      for (const m of n.nodeValue.matchAll(/\S+/g)) {
        const rg = document.createRange(); rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        if (new Set([...rg.getClientRects()].map((r) => Math.round(r.top))).size > 1) bad('a fact value breaks inside the word "' + m[0] + '"');
      }
    }
  }
  const story = document.querySelector('.story');
  const paras = story ? story.querySelectorAll('.t-body').length : 0;
  const src = story && story.querySelector('.sources');
  const hosts = src ? [...src.querySelectorAll('a')].map((a) => a.textContent.trim()) : [];
  if (new Set(hosts).size !== hosts.length) bad('the Sources line repeats a host: ' + hosts.join(', '));
  const facts = document.querySelector('.facts');
  const grid = document.querySelector('.facts-grid');
  let layout = null;
  if (grid && document.querySelector('#locator')) {
    const list = grid.children[0].getBoundingClientRect(), map = document.querySelector('#locator').getBoundingClientRect();
    layout = map.top >= list.bottom - 1 ? 'map below' : 'map beside';
    const inner = facts.clientWidth - 2 * parseFloat(getComputedStyle(facts).paddingLeft);
    if ((inner < 560) !== (layout === 'map below')) bad('the Facts layout (' + layout + ') does not follow its own width (' + Math.round(inner) + 'px)');
    if (layout === 'map below' && map.height > 262) bad('the map below the facts is ' + Math.round(map.height) + 'px tall (260px at most)');
  }
  return { out, paras, hosts, layout };
})()"""


def producer_checks(page, base, tag):
    probs = []
    for key, paras in (("akebono-shuzo", (3, 3)), ("swan-lake-beer", (2, 3)), ("machida-shuzoten", (2, 3))):
        load(page, base, f"#/producer/{key}")
        r = page.eval(PRODUCER_JS)
        probs += [f"{tag} producer {key}: {m}" for m in r["out"]]
        if not paras[0] <= r["paras"] <= paras[1]:
            probs.append(f"{tag} producer {key}: {r['paras']} Story paragraphs, expected {paras[0]} to {paras[1]}")
        if key == "akebono-shuzo" and r["hosts"][:2] != ["akebono-syuzou.com", "sakenowa.com"]:
            probs.append(f"{tag} producer {key}: Sources are {r['hosts']}")
    return probs


def menu_checks(page, base, tag, shots_dir):
    probs = []
    load(page, base, "#/sake/junmai-ginjo")
    page.eval("document.querySelector('#chrome [data-burger]').click()")
    if not wait_for(page, "!!document.querySelector('.bd.split')"):
        return [f"{tag}: the menu did not open on an inner page"]
    time.sleep(0.4)                       # a dwell, not a wait: the boards must still be at opacity 1 after the open has finished (Plan 07 section 9.1)
    res = page.eval("""(() => {
      const rows = [...document.querySelectorAll('.bd-row')];
      const mk = document.querySelector('.bw[data-opt=makers]');
      return { n: rows.length, op: rows.map(r => getComputedStyle(r).opacity), makersTag: mk && mk.tagName, href: mk && mk.getAttribute('href'),
               soon: /Soon/.test(document.querySelector('.bd').innerText), labels: rows.map(r => r.textContent.trim()) };
    })()""")
    if res["n"] != 4 or any(o != "1" for o in res["op"]):
        probs.append(f"{tag}: menu boards {res['n']}, opacities {res['op']}")
    if res["makersTag"] != "A" or res["href"] != "#/makers" or res["soon"]:
        probs.append(f"{tag}: The Makers is not live in the menu ({res['makersTag']} {res['href']} soon={res['soon']})")
    if shots_dir:
        page.screenshot(f"{shots_dir}/menu-open-{tag}.png")
    page.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    if not wait_for(page, "!document.querySelector('.bd')"):
        probs.append(f"{tag}: Esc did not close the menu")
    return probs


def transition_checks(page, base, tag):
    """The welcome page moves to an inner page and back with the plate staying put (Plan 08 section 5)."""
    probs = []
    load(page, base, "#/")
    first = page.eval("document.querySelector('#lower .slot.mix[href]')?.getAttribute('href')")       # at Rest a lower-shelf bottle opens a drink
    if not first or not first.startswith("#/drink/"):
        return [f"{tag}: welcome lower-shelf bottles do not open their drinks at Rest ({first})"]
    vclick(page, ".vessel[data-cat=sake]")
    tagfull = page.eval("(() => { const h = document.querySelector('#lower .slot.sub .hang'); return getComputedStyle(h).opacity + '|' + getComputedStyle(h.querySelector('.nm')).opacity; })()")
    if tagfull != "1|1":
        probs.append(f"{tag}: sub-shelf tags are not full chalk on the welcome page ({tagfull})")
    drink = page.eval("document.querySelector('.cbottle')?.getAttribute('href') || ''")
    plate = page.eval("document.querySelector('#backdrop .plate img')?.currentSrc || ''")
    go(page, first)
    if not page.eval("!!document.querySelector('.inner .boards')"):
        return probs + [f"{tag}: the list page did not open from the welcome shelf"]
    now = page.eval("document.querySelector('#backdrop .plate img')?.currentSrc || ''")
    if now != plate or not page.eval("!!document.body.dataset.dim"):
        probs.append(f"{tag}: the plate did not stay in place through the move to an inner page")
    if page.eval("!!document.querySelector('.scene3')"):
        probs.append(f"{tag}: the welcome scene is still mounted on an inner page")
    op = page.eval("[...document.querySelectorAll('.boards > *')].map(e=>getComputedStyle(e).opacity).join(',')")
    if any(o != "1" for o in op.split(",")):
        probs.append(f"{tag}: boards did not finish fading in ({op})")
    go(page, "#/")
    if not page.eval("!!document.querySelector('.scene3 .cover')"):
        return probs + [f"{tag}: the welcome page did not come back"]
    if page.eval("!!document.body.dataset.dim") or page.eval("!!document.querySelector('.inner')"):
        probs.append(f"{tag}: the move back to the bar left an inner page or the dimming behind")
    ops = page.eval("[...document.querySelectorAll('.scene3 .cover > *:not([data-empty])')].map(e=>getComputedStyle(e).opacity).filter(o=>o!=='1').length")
    if ops:
        probs.append(f"{tag}: {ops} welcome layer(s) did not fade back in")
    return probs


MAP_LOOP = """(async (keys) => {
  const bad = [];
  for (const k of keys) {
    await new Promise((resolve) => { addEventListener('hashchange', resolve, { once: true }); location.hash = '#/producer/' + k; });
    const t0 = performance.now();
    while (document.body.dataset.ready !== '1') {
      if (performance.now() - t0 > 15000) { bad.push(k + ': the page never became ready'); break; }
      await new Promise((r) => setTimeout(r, 20));
    }
    const svg = document.querySelector('#locator svg');
    const hl = document.querySelectorAll('.jp-map path.hl').length;
    const ring = document.querySelectorAll('.jp-map .ring').length;
    if (document.querySelector('#locator') && (!svg || hl !== 1 || ring !== 1)) bad.push(k + ': ' + hl + ' highlighted, ' + ring + ' ring(s)');
    if (!document.querySelector('#locator') && svg) bad.push(k + ': a map without a locator');
  }
  return bad;
})"""


def akebono_map(page, base, prod, tag):
    """A maker page map (Plan 14 section 6)."""
    import smoke_map
    return smoke_map.maker_map_checks(page, base, tag, [prod["akebono"]])


def map_checks(page, base, prod, tag):
    """The Makers map walked down and up with every level checked, and a map on a maker page in each country (Plan 14 section 9).
    smoke_map.py runs the same at all four sizes on its own; here it runs in full at the first size."""
    import smoke_map
    probs = smoke_map.map_checks(page, base, tag)
    _, by_country = smoke_map.pick(page, base)
    probs += smoke_map.maker_map_checks(page, base, tag, list(by_country.values()) + [prod["akebono"]])
    return probs


def list_perf(browser, base, w, h, stats, tag):
    """Scrolling the 74-card list on a phone with the CPU slowed 4 times: frame times while the page scrolls."""
    page = browser.page(w, h, mobile=True)
    load(page, base, "#/sake/junmai-ginjo")
    page.throttle(4)
    res = page.eval("""new Promise((resolve) => {
      const total = document.documentElement.scrollHeight - innerHeight;
      const frames = []; let last = performance.now(); let y = 0; const t0 = last;
      const tick = (now) => { frames.push(now - last); last = now; y += total / 150; scrollTo(0, y);
        if (y < total) requestAnimationFrame(tick); else resolve({ frames, ms: now - t0, total, cards: document.querySelectorAll('.card').length }); };
      requestAnimationFrame(tick);
    })""", await_promise=True)
    fr = sorted(res["frames"][2:])
    p95 = fr[int(len(fr) * 0.95)] if fr else 0
    stats[f"{tag} list scroll"] = {"cards": res["cards"], "frames": len(fr), "median_ms": round(fr[len(fr) // 2], 1), "p95_ms": round(p95, 1), "max_ms": round(fr[-1], 1), "cpu_throttle": 4}
    page.close()
    return [] if res["cards"] >= 70 else [f"{tag}: only {res['cards']} cards on the Junmai Ginjo list"]

# ---------------------------------------------------------------------------------------------- Plan 10: the welcome page's views

SETTLE_JS = """(async () => {
  const t0 = performance.now();
  while (performance.now() - t0 < 4000 && document.getAnimations().some((a) => a.playState === 'running')) await new Promise((r) => setTimeout(r, 30));
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  return true;
})()"""

# what stands on the welcome page in the current view, and whether anything collides (Plan 10 sections 4 to 6, Plan 07 section 8.2)
VIEW_STATE_JS = r"""(() => {
  const out = { problems: [] };
  const bad = (m) => out.problems.push(m);
  const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05; };
  const hit = (a, b, pad = 2) => a.left < b.right - pad && a.right > b.left + pad && a.top < b.bottom - pad && a.bottom > b.top + pad;
  const things = [];
  const add = (sel, name) => document.querySelectorAll(sel).forEach((e) => { if (vis(e)) things.push({ e, name, r: e.getBoundingClientRect() }); });
  add('#clock', 'the clock'); add('.viewcap:not([data-empty])', 'the caption'); add('.placard', 'a placard'); add('.ctab', 'a tab'); add('.slate', 'the status slate');
  add('.burger-tag', 'the Menu label'); add('.burger-anchor', 'the burger'); add('.seeall-board', 'See all'); add('.vessel-cap', 'a category tag');
  document.querySelectorAll('.slot.sub .hang').forEach((e) => { const row = e.closest('.row-items').getBoundingClientRect(); const r = e.getBoundingClientRect(); if (vis(e) && r.left >= row.left - 1 && r.right <= row.right + 1) things.push({ e, name: 'a subcategory tag', r }); }); add('.cgroup:not([hidden]) .cb-art > *', 'a counter bottle');
  for (let i = 0; i < things.length; i++) for (let j = i + 1; j < things.length; j++) {
    const a = things[i], b = things[j];
    if (a.name === 'a counter bottle' && b.name === 'a counter bottle') continue;
    if ([a.name, b.name].sort().join() === 'the burger,the status slate') continue;       // the slate sits under the burger by design (Plan 07)
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    if (hit(a.r, b.r)) bad(`${a.name} overlaps ${b.name}`);
  }
  // the clock clears every bottle on the shelves, and in a view of drinks no shelf bottle stands behind a counter bottle (wide plate)
  const arts = [...document.querySelectorAll('#lower .slot .art > *, .topshelf3 .vessel-art > *')].filter(vis).map((e) => e.getBoundingClientRect());
  const clock = document.querySelector('#clock');
  if (clock) { const c = clock.getBoundingClientRect(); if (arts.some((r) => hit(c, r))) bad('the clock overlaps a shelf bottle'); }
  const mode = document.querySelector('#lower')?.dataset.mode;
  const wide = document.querySelector('.scene3')?.dataset.plate === 'wide';
  const front = [...document.querySelectorAll('.cgroup:not([hidden]) .cb-art > *')].filter(vis).map((e) => e.getBoundingClientRect());
  if (wide && mode === 'drinks' && front.length) {
    const behind = [...document.querySelectorAll('#lower .slot.drink .art > *')].filter(vis).map((e) => e.getBoundingClientRect()).filter((r) => front.some((f) => hit(r, f, 1)));
    if (behind.length) bad(`${behind.length} shelf bottle(s) stand behind a counter bottle`);
  }
  // tap targets on phones
  if (innerWidth < 768) for (const sel of ['#clock', '.ctab']) document.querySelectorAll(sel).forEach((e) => { const r = e.getBoundingClientRect(); if (vis(e) && (r.width < 43.5 || r.height < 43.5)) bad(`${sel} is ${Math.round(r.width)}x${Math.round(r.height)}px`); });
  out.mode = mode;
  out.caption = document.querySelector('#viewcap')?.textContent || '';
  out.captionVisible = !document.querySelector('#viewcap')?.hasAttribute('data-empty');
  out.drinks = [...document.querySelectorAll('#lower .slot.drink a.art, #lower .slot.drink button.art')].map((a) => a.getAttribute('href') || a.dataset.name);
  out.subs = [...document.querySelectorAll('#lower .slot.sub')].map((b) => (b.getAttribute('href') || '').split('/').pop());
  out.seeAll = document.querySelector('.seeall-board')?.getAttribute('href') || null;
  out.hash = location.hash;
  out.hasSelection = !!document.querySelector('.scene3.has-selection');
  out.counter = { new: [...document.querySelectorAll('#cg-new .cb-art')].length, season: [...document.querySelectorAll('#cg-season .cb-art')].length,
    newIn: document.querySelector('#cg-new-h .in:not([hidden]), #tab-new .in:not([hidden])')?.textContent || '', seasonIn: document.querySelector('#cg-season-h .in:not([hidden]), #tab-season .in:not([hidden])')?.textContent || '',
    newIds: [...document.querySelectorAll('#cg-new .cbottle')].map((a) => (a.getAttribute('href') || '').replace('#/drink/', '')),
    seasonIds: [...document.querySelectorAll('#cg-season .cbottle')].map((a) => (a.getAttribute('href') || '').replace('#/drink/', '')) };
  return out;
})()"""


ROW_JS = r"""(() => {
  const row = document.querySelector('.lowrow .row-items'); if (!row) return null;
  const rr = row.getBoundingClientRect();
  const arts = [...row.querySelectorAll('.slot.drink .art > *')].map((e) => e.getBoundingClientRect()).sort((a, b) => a.left - b.left);
  const whole = arts.filter((r) => r.left >= rr.left - 1 && r.right <= rr.right + 1 && r.left >= 0 && r.right <= innerWidth).length;
  let overlaps = 0; for (let i = 1; i < arts.length; i++) if (arts[i].left < arts[i - 1].right - 0.5) overlaps++;
  const cue = document.querySelector('.lowrow .more-cue');
  return { whole, total: arts.length, overlaps, cue: cue ? parseFloat(getComputedStyle(cue).opacity) : null, more: row.scrollWidth - row.clientWidth > 4, last: row.lastElementChild ? row.lastElementChild.className : '' };
})()"""


def settle(page):
    page.eval(SETTLE_JS, await_promise=True)


def vclick(page, sel):
    ok = page.eval(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return false; e.click(); return true; }})()")
    if not ok:
        raise RuntimeError(f"nothing to press: {sel}")
    settle(page)


def view_state(page):
    return page.eval(VIEW_STATE_JS)


def welcome_checks(page, base, tag, shots_dir=None):
    """Every Plan 10 section 9 item on the welcome page, at one size."""
    probs = []
    P = lambda m: probs.append(f"{tag} welcome: {m}")
    load(page, base, "#/")
    shelf = page.eval("window.__shelf = null; fetch('data/shelf.json').then(r => r.json())", await_promise=True)
    cats = shelf["categories"]
    names = [c["name"] for c in cats]
    tall = page.eval("document.querySelector('.scene3').dataset.plate") == "tall"

    def check(label):
        s = view_state(page)
        probs.extend(f"{tag} welcome {label}: {m}" for m in s["problems"])
        if tall and s["mode"] == "drinks":                        # Plan 10 section 11.1: at least 6 whole bottles side by side on phones
            r = page.eval(ROW_JS)
            if r["whole"] < min(6, r["total"]) or r["overlaps"]:
                probs.append(f"{tag} welcome {label}: {r['whole']} whole bottle(s) of {r['total']} in view, {r['overlaps']} overlap(s)")
            if r["more"] != (r["cue"] is not None and r["cue"] > 0.5):
                probs.append(f"{tag} welcome {label}: the arrow cue is {'shown' if r['cue'] else 'hidden'} while more bottles are {'hidden' if r['more'] else 'not hidden'}")
        return s

    # top shelf, and the menu's Shelves submenu match it; Liquid is empty so it is left out
    caps = page.eval("[...document.querySelectorAll('.vessel-cap')].map(e => e.textContent.trim())")
    if caps != ["Sake", "Fermented Beverages", "Umeshu", "Wine", "Spirits", "Cocktails"] or caps != names:
        P(f"the top shelf shows {caps}, shelf.json has {names}")
    rest = check("at rest")
    links = page.eval("[...document.querySelectorAll('#lower .slot.mix')].map((e) => e.getAttribute('href'))")
    if not links or not all((h or "").startswith("#/drink/") for h in links if h) or sum(1 for h in links if h) < len(links) - 2:
        P(f"at Rest the lower-shelf bottles do not open drinks: {links[:4]}")
    if rest["mode"] != "mix" or rest["captionVisible"]:
        P(f"at rest the mode is {rest['mode']} and the caption is {'shown' if rest['captionVisible'] else 'hidden'}")
    if len(rest["counter"]["newIds"]) != 5 or len(rest["counter"]["seasonIds"]) != 5:
        P(f"the counter groups hold {len(rest['counter']['newIds'])} and {len(rest['counter']['seasonIds'])} bottles, not 5 and 5")
    # compact groups: the bottles stand close, centred over their placard (wide) or tab row (tall)
    geo = page.eval("""(() => { const out = {}; for (const id of ['new', 'season']) {
      const bs = [...document.querySelectorAll('#cg-' + id + ' .cb-art > *')].map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0).sort((a, b) => a.left - b.left);
      if (!bs.length) continue;
      const pl = document.querySelector('#cg-' + id + '-h') || document.querySelector('.ctabs'); const prect = pl && pl.getBoundingClientRect();
      const gaps = bs.slice(1).map((r, i) => r.left - bs[i].right); const w = bs.reduce((s, r) => s + r.width, 0) / bs.length;
      out[id] = { gapShare: Math.max(...gaps) / w, centre: (bs[0].left + bs[bs.length - 1].right) / 2, placard: prect ? (prect.left + prect.right) / 2 : null, width: bs[bs.length - 1].right - bs[0].left }; } return out; })()""")
    for gid, g in geo.items():
        if g["gapShare"] > 0.45:
            P(f"the {gid} group is spread out (gaps {g['gapShare']:.2f} of a bottle width)")
        if g["placard"] is not None and abs(g["centre"] - g["placard"]) > 14:
            P(f"the {gid} group is {abs(g['centre'] - g['placard']):.0f}px off the centre of its placard")
    # the top-shelf bottle opens a category; lower-shelf bottles of a category open drinks, their boards open the subcategory
    vclick(page, ".vessel[data-cat=sake]")
    s = check("sake")
    sake = next(c for c in cats if c["key"] == "sake")
    if s["mode"] != "sub" or s["subs"] != [x["key"] for x in sake["subcategories"]] or not s["hasSelection"]:
        P(f"Sake opens as {s['mode']} {s['subs']}")
    # Plan 14 section 3: the counter stays in category view, 5 and 5, with "in Sake" (Sake needs no top-up)
    if s["counter"]["new"] != 5 or s["counter"]["season"] != 5 or s["counter"]["newIn"] != "in Sake" or s["counter"]["seasonIn"] != "in Sake":
        P(f"Sake's counter: {s['counter']}")
    # in category view a bottle and its board are one link to the subcategory's list page (Plan 10 section 13)
    one = page.eval("""[...document.querySelectorAll('#lower .slot.sub')].map((s) => [s.tagName, s.querySelectorAll('a, button').length, s.getAttribute('aria-label') || '', s.getAttribute('href') || ''])""")
    want = [f"#/sake/{x['key']}" for x in sake["subcategories"]]
    if not one or [x[3] for x in one] != want or any(x[0] != "A" or x[1] != 0 or not x[2].endswith(", see all") or "drink" not in x[2] for x in one):
        P(f"a subcategory bottle and its board are not one 'see all' link to its list page: {one[:2]}")
    # tapping the bottle lands on the list page, and Back returns to the bar; tapping the board does the same
    for part in ("art", "hang"):
        page.eval(f"document.querySelector('#lower .slot.sub[href$=junmai-ginjo] .{part}').click()")
        if not wait_for(page, "location.hash === '#/sake/junmai-ginjo' && !!document.querySelector('.shelf-page h1')"):
            P(f"tapping the {'bottle' if part == 'art' else 'board'} of Junmai Ginjo did not land on its list page ({page.eval('location.hash')})")
            break
        wait_ready(page)
        if page.eval("document.querySelectorAll('.shelf-page .card').length") < 10:
            P("the Junmai Ginjo list page shows no cards")
        page.eval("history.back()")
        if not wait_for(page, "!!document.querySelector('.scene3 .cover') && location.hash === '#/sake'"):
            P(f"Back from the list page did not return to the bar ({page.eval('location.hash')})")
            break
        settle(page)
    s = check("back at the bar")
    if s["mode"] != "sub":
        P(f"back at the bar the category view is {s['mode']}")
    # New arrivals and In season still fill the shelves with drinks, with the counter at its usual set
    vclick(page, "#cg-new-h" if not tall else "#tab-new")
    s = check("New arrivals")
    if s["mode"] != "drinks" or not s["caption"].startswith("New arrivals · ") or len(s["drinks"]) <= 5:
        P(f"New arrivals view: mode {s['mode']}, caption '{s['caption']}', {len(s['drinks'])} bottles")
    if s["counter"]["newIn"]:
        P("the counter is filtered in the New arrivals view")
    if not all((d or "").startswith("#/drink/") for d in s["drinks"]):
        P("a bottle in the New arrivals view does not open its drink")
    vclick(page, "#cg-season-h" if not tall else "#tab-season")
    s = check("In season")
    if s["mode"] != "drinks" or not s["caption"].startswith("In season: ") or len(s["drinks"]) <= 5:
        P(f"In season view: mode {s['mode']}, caption '{s['caption']}', {len(s['drinks'])} bottles")
    # the clock resets any view
    # the clock resets any view
    for label, setup in (("category view", lambda: vclick(page, ".vessel[data-cat=sake]")), ("In season view", lambda: vclick(page, "#cg-season-h" if not tall else "#tab-season"))):
        setup()
        vclick(page, "#clock")
        s = check(f"after the clock from the {label}")
        if s["mode"] != "mix" or s["captionVisible"] or s["hash"] != "#/" or s["counter"]["newIn"] or s["hasSelection"]:
            P(f"the clock did not return to Rest from the {label} ({s['mode']}, hash {s['hash']}, caption '{s['caption']}')")
    # the hands show the visitor's local time
    t = page.eval("""(() => { const d = new Date(); const rot = (id) => parseFloat((document.querySelector(id).getAttribute('transform') || 'rotate(0)').match(/-?[\\d.]+/)[0]);
      return { hour: rot('#clock-h'), minute: rot('#clock-m'), eh: ((d.getHours() % 12) + d.getMinutes() / 60) * 30, em: d.getMinutes() * 6 }; })()""")
    if abs(t["minute"] - t["em"]) > 6.5 and abs(abs(t["minute"] - t["em"]) - 360) > 6.5 or abs(t["hour"] - t["eh"]) > 1.5:
        P(f"the clock shows hands {t['hour']:.0f}/{t['minute']:.0f}, local time is {t['eh']:.0f}/{t['em']:.0f}")
    # Esc returns to Rest too
    vclick(page, "#cg-new-h" if not tall else "#tab-new")
    page.eval("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}))")
    settle(page)
    s = check("after Esc")
    if s["mode"] != "mix" or s["captionVisible"]:
        P(f"Esc did not return to Rest ({s['mode']})")
    # Fermented Beverages, Spirits and Umeshu
    vclick(page, ".vessel[data-cat=fermented]")
    s = check("Fermented Beverages")
    ferm = next(c for c in cats if c["key"] == "fermented")
    keys = [x["key"] for x in ferm["subcategories"]]
    if s["subs"] != keys or keys[0] != "makgeolli":
        P(f"Fermented Beverages opens to {s['subs']}, expected Makgeolli first then {keys}")
    shells = page.eval("[...document.querySelectorAll('#lower .slot.sub')].map(s => s.dataset.shape)")
    if shells[0] != "makgeolli" or any(x != "beer" for x in shells[1:]):
        P(f"Fermented Beverages shells are {shells}")
    vclick(page, ".vessel[data-cat=spirits]")
    s = check("Spirits")
    spir = next(c for c in cats if c["key"] == "spirits")
    if s["subs"] != [x["key"] for x in spir["subcategories"]] or s["subs"][0] != "whisky":
        P(f"Spirits opens to {s['subs']}")
    vclick(page, ".vessel[data-cat=umeshu]")
    s = check("Umeshu")
    um = next(c for c in cats if c["key"] == "umeshu")
    if s["mode"] != "drinks" or len(s["drinks"]) != um["drinkCount"] or s["caption"] != f"Umeshu · {um['drinkCount']} drinks":
        P(f"Umeshu opens as {s['mode']} with {len(s['drinks'])} bottles and caption '{s['caption']}'")
    if s["counter"]["newIn"] != "in Umeshu + more" or s["counter"]["new"] != 5:       # 3 drinks: topped up from other categories (Plan 14 section 3)
        P(f"the counter lines read '{s['counter']['newIn']}' in Umeshu")
    # a top-shelf tap while in a New arrivals view goes back to that category's view
    vclick(page, ".vessel[data-cat=sake]")
    vclick(page, "#cg-new-h" if not tall else "#tab-new")
    vclick(page, ".vessel[data-cat=sake]")
    s = check("top shelf tap")
    if s["mode"] != "sub":
        P(f"a top-shelf tap in a view gave {s['mode']}, not its category view")
    vclick(page, "#clock")
    return probs


ALIAS_JS = """(async (route) => {
  await new Promise((resolve) => { addEventListener('hashchange', resolve, { once: true }); location.hash = route; setTimeout(resolve, 1500); });
  const t0 = performance.now();
  while (document.body.dataset.ready !== '1' && performance.now() - t0 < 8000) await new Promise((r) => setTimeout(r, 30));
  await new Promise((r) => setTimeout(r, 150));
  return { hash: location.hash, h1: (document.querySelector('h1') || {}).textContent || '', history: history.length };
})"""


def alias_checks(page, base, tag):
    """Every old address lands on its new page (Plan 10 section 2.5), without adding a history entry."""
    probs = []
    load(page, base, "#/")
    al = page.eval("fetch('data/aliases.json').then(r => r.json())", await_promise=True)
    first_beer = page.eval("fetch('data/shelf.json').then(r => r.json()).then(s => s.categories.find(c => c.key === 'fermented').subcategories.find(x => x.key !== 'makgeolli').key)", await_promise=True)
    cases = [("#/makgeolli", "#/fermented/makgeolli"), ("#/makgeolli/all", "#/fermented/makgeolli"), ("#/beer", "#/fermented"),
             (f"#/beer/{first_beer}", f"#/fermented/{first_beer}"), ("#/beer/all", "#/fermented"), ("#/liqueur/umeshu", "#/umeshu")]
    cases += [(f"#/producer/{old}", f"#/producer/{new}") for old, new in al["producers"].items()]
    if len(al["producers"]) != 12:
        probs.append(f"{tag} aliases: {len(al['producers'])} maker aliases, expected the 12 of Plan 09 Stage 1")
    for old, new in cases:
        page.eval("history.replaceState(null, '', '#/')")
        before = page.eval("history.length")
        r = page.eval(f"{ALIAS_JS}({json.dumps(old)})", await_promise=True)
        if r["hash"] != new:
            probs.append(f"{tag} aliases: {old} landed on {r['hash']}, expected {new}")
        elif "empty" in r["h1"].lower():
            probs.append(f"{tag} aliases: {old} shows the empty-shelf page")
        elif r["history"] - before > 1:
            probs.append(f"{tag} aliases: {old} added {r['history'] - before} history entries")
    r = page.eval(f"{ALIAS_JS}('#/liqueur')", await_promise=True)
    if "This shelf is empty" not in r["h1"]:
        probs.append(f"{tag} aliases: #/liqueur (empty) shows '{r['h1']}'")
    return probs


def photo_checks(page, base, tag):
    """Drink pages show one front photo and the data publishes no other view (Plan 10 section 7)."""
    probs = []
    load(page, base, "#/")
    r = page.eval("""fetch('data/drinks.json').then(r => r.json()).then(async (ds) => { const bad = []; let withPhoto = 0;
      for (const d of ds) { const j = await (await fetch('data/drinks/' + d.id + '.json')).json(); if (j.photos.length > 1 || j.photos.some((p) => p.kind !== 'front')) bad.push(d.id); if (j.photos.length) withPhoto++; }
      return { bad, withPhoto, total: ds.length }; })""", await_promise=True)
    if r["bad"]:
        probs.append(f"{tag} photos: {len(r['bad'])} drink(s) publish more than the front photo, e.g. {r['bad'][0]}")
    pic = page.eval("fetch('data/drinks.json').then(r => r.json()).then(ds => (ds.find(d => d.thumb) || {}).id)", await_promise=True)
    load(page, base, f"#/drink/{pic}")
    n = page.eval("({ thumbs: document.querySelectorAll('.thumbs, .thumb').length, prints: document.querySelectorAll('.hd-photo .print').length })")
    if n["thumbs"] or n["prints"] != 1:
        probs.append(f"{tag} photos: the drink page has {n['thumbs']} thumbnail element(s) and {n['prints']} photo print(s)")
    page.eval("document.querySelector('#photo-main')?.click()")
    settle(page)
    lb = page.eval("({ open: !!document.querySelector('.lightbox'), nav: [...document.querySelectorAll('.lightbox .lb-nav')].filter((b) => !b.hidden && getComputedStyle(b).display !== 'none').length })")
    if not lb["open"] or lb["nav"]:
        probs.append(f"{tag} photos: the lightbox is {'open' if lb['open'] else 'not open'} with {lb['nav']} previous/next button(s)")
    page.eval("document.querySelector('.lightbox .lb-close')?.click()")
    return probs
