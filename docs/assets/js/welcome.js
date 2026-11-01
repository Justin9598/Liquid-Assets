// Welcome page: the bar (Plan 01). Top shelf = categories, lower shelves = subcategory bottles.
// One scene engine (Plan 07): a rendered plate for the screen shape, wide for landscape and tall for phones, with the same live layers.
import { bottleSVG, DEFAULT_LABEL, motifFor, randomPick, shapeFor } from './bottles.js';
import { burgerHTML, mountBurger } from './burger.js';
import { countersHTML, mountTabs, placeCounter, seasonNow, slateStyle } from './counter.js';
import { getJSON, getSections, img } from './data.js';
import { menuButton } from './menu.js';
import { anchorStyle, debugHTML, plateHTML, plateKind, sceneQuery, shelfStyle, shellBottle, wideQuery } from './scene3.js';
import { $, $$, announce, esc, plural, reducedMotion, setTitle } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');
const langOf = (s) => (isHangul(s) ? 'ko' : 'ja');


/** Balanced row sizes: 10 bottles on rows of up to 6 become 5 + 5. */
function distribute(n, per) {
  if (n <= 0) return [];
  const rows = Math.ceil(n / per);
  const base = Math.floor(n / rows);
  const extra = n % rows;
  return Array.from({ length: rows }, (_, i) => base + (i < extra ? 1 : 0));
}

const IDLE = 'Pick a bottle from the top shelf.';

export async function mount(root, ctx) {
  const { ix } = ctx;
  const cats = ix.shelf.categories;
  let manifest = null;
  try { manifest = await getJSON('scene.json'); } catch { manifest = null; }
  const q = sceneQuery(ctx.params);
  if (!manifest?.plates?.wide || !manifest?.plates?.tall) throw new Error('scene.json');
  const debug = q.get('debug') === 'scene';

  let sel = ctx.cat || null;
  let items = [];
  let token = 0;
  let mode = null;                                   // 'wide' | 'tall'
  let lower = null;
  let plaque = null;
  let burgerCtl = null;
  let tabsCtl = null;

  // ---- bottle art: rendered shell when one exists, otherwise the SVG bottle -------------------------------------
  const art = (shape, o) => shellBottle(manifest, shape, o) || bottleSVG(shape, o);

  const vesselHTML = (c) => {
    const def = DEFAULT_LABEL[c.vessel] || {};
    return `<button type="button" class="vessel" data-cat="${esc(c.key)}" aria-pressed="false">
  <span class="vessel-art">${art(c.vessel, { native: def.native, name: def.name, motif: def.motif })}</span>
  <span class="vessel-cap chalkboard chalkboard--s"><span class="chalk">${esc(c.name)}</span></span>
</button>`;
  };

  // ---- skeleton --------------------------------------------------------------------------------------------------
  function skeletonV3(kind) {
    const P = manifest.plates[kind];
    const vesselRows = kind === 'wide' ? [cats] : [cats.slice(0, 4), cats.slice(4)];
    const counterOn = !!P.counter;
    const burgerOn = counterOn && !!manifest.burger;
    const season = seasonNow(q);
    const rows = vesselRows.map((row, i) => `<div class="shelf-row s3 vrow" style="${shelfStyle(P.shelves[i])}"><div class="row-items" style="--n:${row.length}">${row.map(vesselHTML).join('')}</div></div>`).join('');
    return `<div class="bar scene3" data-plate="${kind}">
  <h1 class="sr-only" tabindex="-1">Liquid Assets</h1>
  <div class="cover" style="--ratio:${P.ratio}">
    ${plateHTML(P)}
    <section class="topshelf3" aria-label="Categories. Pick one to see its shelves.">${rows}</section>
    <section class="lower" id="lower" aria-label="Shelves"></section>
    ${counterOn ? countersHTML(P, ix.shelf.counter, season, ix, art, kind === 'tall') : ''}
    <p class="slate s3 chalkboard chalkboard--m${counterOn ? ' mid' : ''}" id="plaque" style="${counterOn ? slateStyle(P.counter) : anchorStyle(P.anchors.slate)}">${IDLE}</p>
    ${burgerOn ? burgerHTML(P, manifest.burger) : `<div class="menu-anchor" style="${anchorStyle(P.anchors.menu)}">${menuButton('on-counter')}</div>`}
    ${debug ? debugHTML(P) : ''}
  </div>
</div>`;
  }

  // ---- items ---------------------------------------------------------------------------------------------------
  function mixItems() {
    const used = new Set();
    const out = [];
    for (let i = 0; i < 12; i++) {
      const c = cats[i % cats.length];
      const pool = c.subcategories.flatMap((s) => s.labels);
      const label = randomPick(pool, used);
      const def = DEFAULT_LABEL[c.key] || {};
      out.push({ mix: true, cat: c.key, shape: shapeFor(c.key), label: label && img(label), native: def.native, name: def.name, motif: def.motif });
    }
    return out;
  }

  function subItems(c) {
    const used = new Set();
    return c.subcategories.map((s) => {
      const label = randomPick(s.labels, used);
      return {
        cat: c.key, sub: s.key, shape: shapeFor(c.key), label: label && img(label), native: s.native, name: s.name,
        motif: motifFor(c.key, s.key), count: s.drinkCount, href: `#/${c.key}/${s.key}`,
      };
    });
  }

  function slotHTML(it) {
    const a = art(it.shape, { label: it.label, native: it.native, name: it.name, motif: it.motif });
    if (it.mix) {
      return `<button type="button" class="slot mix" tabindex="-1" aria-hidden="true" data-cat="${esc(it.cat)}" data-shape="${it.shape}"><span class="art">${a}</span></button>`;
    }
    const second = [];
    if (it.native) second.push(`<span class="nat" lang="${langOf(it.native)}">${esc(it.native)}</span>`);
    second.push(`<span class="ct">${it.count}</span>`);
    const tagHTML = `<span class="nm">${esc(it.name)}</span><span class="l2">${second.join('<i> · </i>')}</span>`;
    const inner = `<span class="art">${a}</span>
  <span class="hang chalkboard chalkboard--s" aria-hidden="true">${tagHTML}</span>`;
    // Phase 1: the shelf pages aren't published, so the bottles are buttons that say so on the slate (Plan 06 section 12.1)
    if (!getSections().shelves) {
      return `<button type="button" class="slot sub soon" data-soon aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}. This shelf opens soon." data-shape="${it.shape}">${inner}</button>`;
    }
    return `<a class="slot sub" href="${esc(it.href)}" aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}" data-shape="${it.shape}">${inner}</a>`;
  }

  // ---- placing rows ----------------------------------------------------------------------------------------------
  /** Bottles per visible shelf for the subcategory view. Wide: the fewest per row that still fits every bottle on the
   * two lower shelves, so the pitch is as wide as it can be (the tags need it). Tall: `visible` bottles in the
   * scrolling row, 3 unless their tags need more room (Plan 07 section 8.2). */
  let visible = 3;
  function rowsV3(list) {
    const kind = mode;
    const P = manifest.plates[kind];
    const nTop = kind === 'wide' ? 1 : 2;
    const shelves = P.shelves.slice(nTop);
    const mixed = !!(list.length && list[0].mix);
    let groups;
    let per;
    if (kind === 'wide') {
      per = mixed ? 6 : Math.max(3, Math.ceil(list.length / shelves.length));
      const sizes = distribute(list.length, per);
      let k = 0;
      groups = sizes.map((n) => { const g = list.slice(k, k + n); k += n; return g; });
    } else {
      groups = [list];                                  // phones: one shelf, a few visible, scrolling sideways
      per = mixed ? 3 : visible;
    }
    return shelves.map((s, i) => {
      const g = groups[i] || [];
      return `<div class="shelf-row s3 lowrow${g.length === 1 ? ' single' : ''}" data-shelf="${nTop + i}" style="${shelfStyle(s)};--per:${per}"><div class="row-items">${g.map(slotHTML).join('')}</div></div>`;
    }).join('');
  }

  /** Do all the subcategory tags fit at the smallest type size: no wrapped Japanese line, at most 2 name lines, and a
   * height that stays inside the room under their shelf (Plan 07 section 8.2)? */
  function tagsFit() {
    const P = manifest.plates[mode];
    const H = $('.cover', root).getBoundingClientRect().height;
    const shelves = P.shelves;
    const low = shelves[shelves.length - 1];
    return $$('.hang', lower).every((h) => {
      const nm = $('.nm', h);
      const lh = parseFloat(getComputedStyle(nm).lineHeight) || 15;
      if (h.scrollWidth > h.clientWidth + 1 || nm.getBoundingClientRect().height > lh * 2 + 1) { lower.dataset.fitFail = `${nm.textContent}: w ${h.scrollWidth}/${h.clientWidth}, nm ${Math.round(nm.getBoundingClientRect().height)}/${lh}`; return false; }
      const idx = Number(h.closest('.lowrow').dataset.shelf);
      const room = (idx === shelves.length - 1
        ? P.counterTop - low.y
        : shelves[idx + 1].y - shelves[idx + 1].clear * 0.82 - shelves[idx].y) * H;
      const ok = h.getBoundingClientRect().height <= room + (mode === 'tall' ? 15 : 0);
      if (!ok) lower.dataset.fitFail = `${nm.textContent}: height ${Math.round(h.getBoundingClientRect().height)} > room ${Math.round(room)}`;
      return ok;
    });
  }

  function setRows(list) {
    items = list;
    visible = 3;
    lower.innerHTML = rowsV3(list);
    lower.dataset.mode = list.length && list[0].mix ? 'mix' : 'sub';
    if (mode === 'tall' && lower.dataset.mode === 'sub') {         // fewer bottles in view until every tag fits
      while (visible > 1 && !tagsFit()) { visible -= 1; lower.innerHTML = rowsV3(list); }
    }
    if (mode === 'tall') watchFades($('.lowrow .row-items', lower));
    clearBehindCounter();
  }

  /** Share of a bottle's picture that the counter bottles stand in front of. */
  const coveredShare = (a, front) => {
    const area = a.width * a.height;
    if (!area) return 0;
    let sum = 0;
    for (const f of front) {
      const w = Math.min(a.right, f.right) - Math.max(a.left, f.left);
      const h = Math.min(a.bottom, f.bottom) - Math.max(a.top, f.top);
      if (w > 0 && h > 0) sum += w * h;
    }
    return Math.min(1, sum / area);
  };
  const frontBottles = () => $$('.cgroup:not([hidden]) .cb-art > *', root).map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0);

  /** At rest the lower shelves keep their mixed display.
   * Wide: a slot is left empty where a counter bottle stands in front of it, rather than drawing one bottle behind
   * another (Plan 07 section 8.3). Tall: shelf 3 keeps its full row of 3 and the counter bottles simply stand in front,
   * but no bottle may be more than 35% covered, so the row's scroll start moves if one would be (section 11). */
  function clearBehindCounter() {
    if (!lower) return;
    $$('.slot.blocked', lower).forEach((e) => e.classList.remove('blocked'));
    if (lower.dataset.mode !== 'mix') return;
    const front = frontBottles();
    if (!front.length) return;
    if (mode === 'tall') { fixScrollStart(front); return; }
    $$('.slot.mix', lower).forEach((s) => {
      const a = $('.art > *', s)?.getBoundingClientRect();
      if (a && front.some((f) => a.left < f.right + 3 && a.right > f.left - 3 && a.top < f.bottom && a.bottom > f.top)) s.classList.add('blocked');
    });
  }

  function fixScrollStart(front) {
    const row = $('.lowrow .row-items', lower);
    if (!row) return;
    const worst = () => {
      const rr = row.getBoundingClientRect();
      let w = 0;
      for (const s of $$('.slot.mix', lower)) {
        const sr = s.getBoundingClientRect();
        if (sr.left < rr.left - 1 || sr.right > rr.right + 1) continue;               // not in view
        const a = $('.art > *', s)?.getBoundingClientRect();
        if (a) w = Math.max(w, coveredShare(a, front));
      }
      return w;
    };
    const slotW = row.clientWidth / 3;
    const max = row.scrollWidth - row.clientWidth;
    for (let left = 0; left <= max + 1; left += slotW) {
      row.scrollTo({ left, behavior: 'instant' });
      if (worst() <= 0.35) return;
    }
    row.scrollTo({ left: 0, behavior: 'instant' });
  }

  /** Soft fades at the ends of the scrolling shelf, only on the side where there is more (Plan 07 section 7.2). */
  let fadeOff = null;
  let blockRaf = 0;
  function watchFades(el) {
    fadeOff?.();
    fadeOff = null;
    if (!el) return;
    const upd = () => {
      const max = el.scrollWidth - el.clientWidth;
      el.style.setProperty('--fl', el.scrollLeft > 4 ? '9%' : '0%');
      el.style.setProperty('--fr', max - el.scrollLeft > 4 ? '9%' : '0%');
      cancelAnimationFrame(blockRaf);
      blockRaf = requestAnimationFrame(clearBehindCounter);
    };
    upd();
    el.addEventListener('scroll', upd, { passive: true });
    const ro = new ResizeObserver(upd);
    ro.observe(el);
    fadeOff = () => { el.removeEventListener('scroll', upd); ro.disconnect(); };
  }

  const slotAnim = (el, from, to, delay, dur, easing) =>
    el.animate([from, to], { duration: dur, delay, fill: 'both', easing }).finished.catch(() => {});

  async function swap(list) {
    const mine = ++token;
    if (reducedMotion()) {
      await lower.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 75, fill: 'forwards' }).finished.catch(() => {});
      if (mine !== token) return;
      setRows(list);
      lower.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 75, fill: 'forwards' });
      return;
    }
    const ease = 'cubic-bezier(0.16, 1, 0.3, 1)';
    const old = $$('.slot', lower);
    const st = Math.min(30, 90 / Math.max(1, old.length - 1));
    await Promise.all(old.map((el, i) => slotAnim(el, { opacity: 1, transform: 'translateY(0)' }, { opacity: 0, transform: 'translateY(-12px)' }, i * st, 140, 'ease-in')));
    if (mine !== token) return;
    setRows(list);
    const fresh = $$('.slot', lower);
    const st2 = Math.min(30, 90 / Math.max(1, fresh.length - 1));
    fresh.forEach((el) => { el.style.opacity = '0'; });
    fresh.forEach((el, i) => slotAnim(el, { opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }, i * st2, 170, ease)
      .then(() => { el.style.opacity = ''; el.getAnimations().forEach((a) => a.cancel()); }));
  }

  // ---- selection ------------------------------------------------------------------------------------------------
  function paintSelection(key) {
    $$('.vessel', root).forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cat === key)));
    $('.bar', root).classList.toggle('has-selection', !!key);
  }

  function describe(c) {
    const kinds = c.subcategories.length;
    if (kinds === 1) return `${c.name} · ${plural(c.drinkCount, 'drink')}`;
    return `${c.name} · ${kinds} kinds · ${plural(c.drinkCount, 'drink')}`;
  }

  let soonTimer = null;
  const slateText = () => { const c = sel && ix.cats.get(sel); return c ? describe(c) : IDLE; };
  function soon(msg = 'This shelf opens soon.') {
    clearTimeout(soonTimer);
    plaque.textContent = msg;
    announce(msg);
    soonTimer = setTimeout(() => { plaque.textContent = slateText(); }, 3000);
  }

  async function select(key, animate) {
    clearTimeout(soonTimer);
    sel = key;
    paintSelection(key);
    const c = key && ix.cats.get(key);
    plaque.textContent = c ? describe(c) : IDLE;
    setTitle(c ? c.name : '');
    const list = c ? subItems(c) : mixItems();
    if (animate) await swap(list); else { token++; setRows(list); }
    clearBehindCounter();
    if (c) announce(c.subcategories.length === 1 ? `Showing ${c.name}: ${plural(c.drinkCount, 'drink')}` : `Showing ${c.name}: ${c.subcategories.length} kinds`);
    else announce('Showing a mixed selection');
  }

  // ---- render ----------------------------------------------------------------------------------------------------
  function render() {
    mode = plateKind();
    root.innerHTML = skeletonV3(mode);
    document.body.dataset.scene = 'v3';
    burgerCtl?.destroy();
    tabsCtl?.destroy();
    const P = manifest.plates[mode];
    burgerCtl = manifest.burger && P.counter ? mountBurger(root, { B: manifest.burger, ix }) : null;
    tabsCtl = P.counter?.mode === 'tabs' ? mountTabs(root, { onTab: () => { if (sel) location.hash = '#/'; requestAnimationFrame(clearBehindCounter); } }) : null;
    lower = $('#lower', root);
    plaque = $('#plaque', root);
    if (q.get('tab') === 'season') $('#tab-season', root)?.click();          // ?tab=season, for screenshots
    placeCounter(root, P, manifest.burger?.ratio);
    select(sel, false);
    if (burgerCtl && q.get('menu') === 'open') {                    // ?menu=open&panel=shelves, for screenshots and checks
      const opened = burgerCtl.open(q.get('panel'), { instant: q.get('still') === '1' });
      if (q.get('settle') === '1') {                                // a real open whose animations are finished for a still capture
        let done = false;
        opened.then(() => { done = true; });
        const tick = setInterval(() => { document.getAnimations().forEach((a) => { try { a.finish(); } catch { /* ignore */ } }); if (done) clearInterval(tick); }, 30);
      }
    }
  }

  const onClick = (ev) => {
    const v = ev.target.closest('.vessel');
    if (v) {
      location.hash = sel === v.dataset.cat ? '#/' : `#/${v.dataset.cat}`;
      return;
    }
    const cb = ev.target.closest('[data-drink-soon]');
    if (cb) { soon(`${cb.dataset.name}, ${cb.dataset.cat}. Its page opens soon.`); return; }
    if (ev.target.closest('[data-soon]')) { soon(); return; }
    const mix = ev.target.closest('.slot.mix');
    if (mix) location.hash = `#/${mix.dataset.cat}`;
  };
  root.addEventListener('click', onClick);
  const onMq = () => {
    if (plateKind() !== mode) render(); else if (items.length) setRows(items);
  };
  const onResize = () => { if (mode) { placeCounter(root, manifest.plates[mode], manifest.burger?.ratio); if (lower?.dataset.mode === 'sub' && mode === 'tall') select(sel, false); else clearBehindCounter(); } };
  window.addEventListener('resize', onResize);
  wideQuery.addEventListener('change', onMq);

  render();
  if (q.get('check') === '1') import('./selfcheck.js').then((m) => m.run({ manifest, ix }));      // build/tools/smoke.py

  return {
    sameTarget: () => true,
    update(c) { select(c.cat, true); },
    unmount() {
      token++;
      fadeOff?.();
      clearTimeout(soonTimer);
      burgerCtl?.destroy();
      tabsCtl?.destroy();
      window.removeEventListener('resize', onResize);
      root.removeEventListener('click', onClick);
      wideQuery.removeEventListener('change', onMq);
      delete document.body.dataset.scene;
    },
  };
}
