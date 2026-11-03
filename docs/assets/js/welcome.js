// Welcome page: the bar (Plan 01). Top shelf = categories, lower shelves = subcategory bottles.
// One scene engine (Plan 07): a rendered plate for the screen shape, wide for landscape and tall for phones, with the same live layers.
import { DEFAULT_LABEL, motifFor, randomPick, shapeFor } from './labels.js';
import { burgerHTML, mountBurger } from './burger.js';
import { clockHTML, mountClock } from './clock.js';
import { countersHTML, mountTabs, placeCounter, rowHTML, SEASON_NAMES, seasonNow, slateStyle } from './counter.js';
import { getJSON, getSections, img } from './data.js';
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
  const { ix, state } = ctx;
  const cats = ix.shelf.categories;
  let manifest = null;
  try { manifest = await getJSON('scene.json'); } catch { manifest = null; }
  const q = sceneQuery(ctx.params);
  if (!manifest?.plates?.wide || !manifest?.plates?.tall) throw new Error('scene.json');
  const debug = q.get('debug') === 'scene';

  let sel = ctx.cat || null;
  let view = 'rest';                                 // rest | sub | new | season (Plan 10 section 4); the category view is `sel` alone
  let subSel = null;                                 // { cat, sub } while view is 'sub'
  let clockCtl = null;
  const season = seasonNow(q);
  const counterData = ix.shelf.counter || {};
  let items = [];
  let token = 0;
  let mode = null;                                   // 'wide' | 'tall'
  let lower = null;
  let plaque = null;
  let burgerCtl = null;
  let tabsCtl = null;

  // ---- bottle art: the rendered shell for the shape ----------------------------------------------------------------
  const art = (shape, o) => shellBottle(manifest, shape, o) || '';

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
    const half = Math.ceil(cats.length / 2);                       // phones: two shelves of vessels, split evenly so each tag has room
    const vesselRows = kind === 'wide' ? [cats] : [cats.slice(0, half), cats.slice(half)];
    const counterOn = !!P.counter;
    const burgerOn = counterOn && !!manifest.burger;
    const rows = vesselRows.map((row, i) => `<div class="shelf-row s3 vrow" style="${shelfStyle(P.shelves[i])}"><div class="row-items" style="--n:${row.length}">${row.map(vesselHTML).join('')}</div></div>`).join('');
    // Phase 2: the plate is the fixed backdrop behind every page (backdrop.js), so the welcome page does not carry its own
    const ownPlate = !state.backdrop;
    return `<div class="bar scene3${ownPlate ? '' : ' on-backdrop'}" data-plate="${kind}">
  <h1 class="sr-only" tabindex="-1">Liquid Assets</h1>
  <div class="cover" style="--ratio:${P.ratio}">
    ${ownPlate ? plateHTML(P) : ''}
    <section class="topshelf3" aria-label="Categories. Pick one to see its shelves.">${rows}</section>
    <section class="lower" id="lower" aria-label="Shelves"></section>
    ${counterOn ? countersHTML(P, ix.shelf.counter, season, ix, art, kind === 'tall') : ''}
    ${P.clock ? clockHTML(P) : ''}
    ${viewCapHTML(P)}
    <p class="slate s3 chalkboard chalkboard--m${counterOn ? ' mid' : ''}" id="plaque" style="${counterOn ? slateStyle(P.counter) : anchorStyle(P.anchors.slate)}">${IDLE}</p>
    ${burgerOn ? burgerHTML(P, manifest.burger) : ''}
    ${debug ? debugHTML(P) : ''}
  </div>
</div>`;
  }

  /** The caption board at the left end of the bottom shelf's front edge (Plan 10 section 4.6). */
  function viewCapHTML(P) {
    const s = P.shelves[P.shelves.length - 1];
    if (P.counter?.mode === 'tabs') {                                // phones: the counter bottles stand right under the shelf, so the caption takes the status slate's place
      return `<p class="viewcap onslate chalkboard chalkboard--m" id="viewcap" data-empty aria-live="polite" style="left:${((P.counter.slate.x0 + P.counter.slate.x1) * 50).toFixed(3)}%;top:${(P.counter.slateY * 100).toFixed(3)}%"></p>`;
    }
    return `<p class="viewcap chalkboard chalkboard--s" id="viewcap" data-empty aria-live="polite" style="left:${((s.x0 + 0.032) * 100).toFixed(3)}%;top:${((s.y + 0.012) * 100).toFixed(3)}%"></p>`;
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

  /** One bottle per subcategory. It stands for a drink: the one whose label it wears, or the newest drink when it wears the
   * illustrated label (Plan 10 section 3). The choice holds until the page is reloaded. */
  function subItems(c) {
    const used = new Set();
    return c.subcategories.map((s) => {
      const label = randomPick(s.labels, used);
      state.picked = { ...state.picked, [`${c.key}/${s.key}`]: label };   // the shelf page shows the bottle the visitor tapped
      const drink = (s.drinks || []).find((d) => d.label === label) || (s.drinks || [])[0] || null;
      return {
        sub: true, cat: c.key, subKey: s.key, shape: shapeFor(c.key, s.key), label: label && img(label), native: s.native, name: s.name,
        motif: motifFor(c.key, s.key), count: s.drinkCount, drink,
      };
    });
  }

  const drinkItem = (d, cat, subKey) => {
    const info = ix.subs.get(`${cat}/${subKey}`);
    return { drink: true, id: d.id, dname: d.name, cat, subKey, shape: shapeFor(cat, subKey), label: d.label && img(d.label),
      native: info?.sub.native, name: info?.sub.name, motif: motifFor(cat, subKey) };
  };

  /** The bottle itself: a link to its drink page (Phase 1: a button that says the page opens soon). */
  function bottleLink(a, id, name, catName) {
    if (!getSections().drinks) {
      return `<button type="button" class="art" data-drink-soon data-name="${esc(name)}" data-cat="${esc(catName)}" aria-label="${esc(name)}, open drink. Its page opens soon.">${a}</button>`;
    }
    return `<a class="art" href="#/drink/${encodeURIComponent(id)}" aria-label="${esc(name)}, open drink">${a}</a>`;
  }

  function slotHTML(it) {
    if (it.seeall) {
      const label = `See all ${it.count}`;
      return getSections().shelves
        ? `<div class="slot seeall"><a class="seeall-board chalkboard chalkboard--s" href="${esc(it.href)}">${esc(label)}</a></div>`
        : `<div class="slot seeall"><button type="button" class="seeall-board chalkboard chalkboard--s" data-soon>${esc(label)}</button></div>`;
    }
    const a = art(it.shape, { label: it.label, native: it.native, name: it.name, motif: it.motif });
    if (it.mix) {
      return `<button type="button" class="slot mix" tabindex="-1" aria-hidden="true" data-cat="${esc(it.cat)}" data-shape="${it.shape}"><span class="art">${a}</span></button>`;
    }
    if (it.drink === true) {                                     // a single drink in a view: the bottle opens it, a small tag names it on hover
      return `<div class="slot drink" data-shape="${it.shape}">${bottleLink(a, it.id, it.dname, it.name || '')}<span class="hang chalkboard chalkboard--s" aria-hidden="true"><span class="nm">${esc(it.dname)}</span></span></div>`;
    }
    const second = [];
    if (it.native) second.push(`<span class="nat" lang="${langOf(it.native)}">${esc(it.native)}</span>`);
    second.push(`<span class="ct">${it.count}</span>`);
    const tagHTML = `<span class="nm">${esc(it.name)}</span><span class="l2">${second.join('<i> · </i>')}</span>`;
    // a bottle and its board are two focus stops: the bottle opens its drink, the board shows the subcategory (Plan 10 section 3)
    const bottle = it.drink ? bottleLink(a, it.drink.id, it.drink.name, it.name) : `<span class="art">${a}</span>`;
    return `<div class="slot sub" data-shape="${it.shape}">${bottle}<button type="button" class="hang chalkboard chalkboard--s" data-sub="${esc(it.subKey)}" data-cat="${esc(it.cat)}" aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}, show on the shelves">${tagHTML}</button></div>`;
  }

  // ---- placing rows ----------------------------------------------------------------------------------------------
  /** Bottles per visible shelf for the subcategory view. Wide: the fewest per row that still fits every bottle on the
   * two lower shelves, so the pitch is as wide as it can be (the tags need it). Tall: `visible` bottles in the
   * scrolling row, 3 unless their tags need more room (Plan 07 section 8.2). */
  let visible = 3;
  const kindOf = (list) => (!list.length ? 'sub' : list[0].mix ? 'mix' : list[0].sub ? 'sub' : 'drinks');
  function rowsV3(list) {
    const kind = mode;
    const P = manifest.plates[kind];
    const nTop = kind === 'wide' ? 1 : 2;
    const shelves = P.shelves.slice(nTop);
    const mixed = !!(list.length && list[0].mix);
    const drinks = kindOf(list) === 'drinks';
    let groups;
    let per;
    if (kind === 'wide' && drinks) {                    // a view of drinks: the shelf fills from the left shelf's centre outwards, measured capacity per shelf
      per = Math.max(4, P.lowerCapacity?.perShelf || 12);
      groups = [list.slice(0, per), list.slice(per)];
    } else if (kind === 'wide') {
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
    lower.dataset.mode = kindOf(list);
    if (mode === 'tall' && lower.dataset.mode === 'sub') {         // fewer bottles in view until every tag fits
      while (visible > 1 && !tagsFit()) { visible -= 1; lower.innerHTML = rowsV3(list); }
    }
    if (mode === 'tall') watchFades($('.lowrow .row-items', lower));
    clearBehindCounter();
    avoidCounter();
  }

  /** In a view of drinks the counter bottles stay up (filtered, or the usual set), so on the wide plate the lower shelves give
   * way: a row's room shrinks where a counter bottle would stand in front of it, instead of drawing one bottle behind another. */
  function avoidCounter() {
    $$('.lowrow .row-items', lower).forEach((r) => { r.style.paddingLeft = ''; r.style.paddingRight = ''; });
    if (mode !== 'wide' || lower.dataset.mode !== 'drinks') return;
    const front = frontBottles();
    if (!front.length) return;
    for (const r of $$('.lowrow .row-items', lower)) {
      const rr = r.getBoundingClientRect();
      const mid = (rr.left + rr.right) / 2;
      let padL = 0;
      let padR = 0;
      for (const f of front) {
        if (f.bottom < rr.top + rr.height * 0.18 || f.top > rr.bottom) continue;      // not level with this shelf's bottles
        const extra = r.querySelector('.seeall') ? 16 : 0;                       // the See all board is a little wider than its place
        if (f.right > rr.left && f.left < mid) padL = Math.max(padL, f.right - rr.left + 8 + extra);
        else if (f.left < rr.right && f.right > mid) padR = Math.max(padR, rr.right - f.left + 8 + extra);
      }
      r.style.paddingLeft = padL ? `${padL}px` : '';
      r.style.paddingRight = padR ? `${padR}px` : '';
    }
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

  // ---- views (Plan 10 section 4) -------------------------------------------------------------------------------
  const capacity = () => manifest.plates[mode].lowerCapacity?.total || 24;

  /** What the lower shelves show now, and the caption board's words. */
  function listFor() {
    const cap = capacity();
    if (view === 'new' || view === 'season') {
      const src = view === 'new' ? (counterData.newArrivals || []) : ((counterData.inSeason || {})[season] || []);
      const its = src.slice(0, cap).map((i) => drinkItem({ id: i.id, name: i.name, label: i.label }, i.category, i.sub));
      return { list: its, caption: view === 'new' ? `New arrivals · ${its.length}` : `In season: ${SEASON_NAMES[season]} · ${its.length}` };
    }
    const c = sel && ix.cats.get(sel);
    const eff = view === 'sub' ? subSel : (c?.direct ? { cat: c.key, sub: c.subcategories[0].key } : null);
    if (eff) {
      const info = ix.subs.get(`${eff.cat}/${eff.sub}`);
      const ds = info.sub.drinks || [];
      const over = ds.length > cap;
      const shown = ds.slice(0, over ? cap - 1 : cap).map((d) => drinkItem(d, eff.cat, eff.sub));
      if (over) shown.push({ seeall: true, count: ds.length, href: `#/${eff.cat}/${eff.sub}` });
      return { list: shown, caption: `${c?.direct ? c.name : info.sub.name} · ${plural(ds.length, 'drink')}` };
    }
    return { list: c ? subItems(c) : mixItems(), caption: '' };
  }

  function setCaption(text) {
    const el = $('#viewcap', root);
    if (!el) return;
    if (el.textContent !== text) el.textContent = text;
    if (text) el.removeAttribute('data-empty'); else el.setAttribute('data-empty', '');
    $('.bar', root).classList.toggle('captioned', !!text && el.classList.contains('onslate'));
  }

  /** The counter's two groups: the usual 5, or, when a subcategory is chosen, that subcategory's own new and seasonal bottles
   * (Plan 10 section 6.2). A group with none of its own keeps the usual set. */
  let counterKey = null;
  function updateCounter() {
    const c = sel && ix.cats.get(sel);
    const eff = view === 'sub' ? subSel : (c?.direct && view === 'rest' ? { cat: c.key, sub: c.subcategories[0].key } : null);
    const info = eff && ix.subs.get(`${eff.cat}/${eff.sub}`);
    const key = `${mode}|${eff ? `${eff.cat}/${eff.sub}` : ''}`;
    if (key === counterKey) return;
    counterKey = key;
    const rest = { new: (counterData.newArrivals || []).slice(0, 5), season: ((counterData.inSeason || {})[season] || []).slice(0, 5) };
    for (const id of ['new', 'season']) {
      const ids = info ? (id === 'new' ? info.sub.new : (info.sub.season || {})[season]) || [] : [];
      const own = ids.map((did) => (info.sub.drinks || []).find((d) => d.id === did)).filter(Boolean)
        .map((d) => ({ id: d.id, name: d.name, category: eff.cat, sub: eff.sub, label: d.label }));
      const useOwn = own.length > 0;
      const row = $(`#cg-${id} .cg-row`, root);
      if (row) row.innerHTML = rowHTML(useOwn ? own : rest[id], ix, art);
      const line = useOwn ? `in ${info.sub.name}` : '';
      for (const el of [$(`#cg-${id}-h .in`, root), $(`#tab-${id} .in`, root)]) {
        if (!el) continue;
        el.textContent = line;
        el.hidden = !line;
      }
    }
  }

  async function show(animate) {
    clearTimeout(soonTimer);
    paintSelection(sel);
    const c = sel && ix.cats.get(sel);
    const inView = view !== 'rest' || !!c?.direct;
    $('.bar', root).classList.toggle('has-selection', !!sel && !inView);          // the counter yields only to a plain category view
    plaque.textContent = c ? describe(c) : IDLE;
    setTitle(c ? c.name : '');
    const { list, caption } = listFor();
    setCaption(caption);
    updateCounter();
    if (animate) await swap(list); else { token++; setRows(list); }
    clearBehindCounter();
    avoidCounter();
    if (view === 'new' || view === 'season' || view === 'sub' || c?.direct) announce(caption);
    else if (c) announce(c.subcategories.length === 1 ? `Showing ${c.name}: ${plural(c.drinkCount, 'drink')}` : `Showing ${c.name}: ${c.subcategories.length} kinds`);
    else announce('Showing a mixed selection');
  }

  /** The category view from the hash (or no category), with any other view cleared. */
  function select(key, animate) {
    sel = key;
    view = 'rest';
    subSel = null;
    return show(animate);
  }

  /** Back to the first look from any view (the clock, or Esc). */
  function goRest() {
    if (view === 'rest' && !sel) {
      const el = $('#clock', root);
      el?.classList.add('nudge');
      setTimeout(() => el?.classList.remove('nudge'), 220);
      return;
    }
    if (location.hash.replace(/\?.*$/, '') !== '#/') history.replaceState(null, '', '#/');      // no extra history entry
    select(null, true);
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
    counterKey = null;
    tabsCtl = P.counter?.mode === 'tabs' ? mountTabs(root, { onTab: (tab) => { view = tab === 'new' ? 'new' : 'season'; subSel = null; show(true); } }) : null;
    clockCtl?.destroy();
    clockCtl = P.clock ? mountClock(root, goRest) : null;
    lower = $('#lower', root);
    plaque = $('#plaque', root);
    if (q.get('tab') === 'season') $('#tab-season', root)?.click();          // ?tab=season, for screenshots
    placeCounter(root, P, manifest.burger?.ratio);
    show(false);
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
      if (sel === v.dataset.cat && view !== 'rest') { view = 'rest'; subSel = null; show(true); return; }     // back to that category's own view
      location.hash = sel === v.dataset.cat ? '#/' : `#/${v.dataset.cat}`;
      return;
    }
    const sb = ev.target.closest('button[data-sub]');
    if (sb) { view = 'sub'; subSel = { cat: sb.dataset.cat, sub: sb.dataset.sub }; show(true); return; }
    const pv = ev.target.closest('.placard[data-view]');
    if (pv) { view = pv.dataset.view; subSel = null; show(true); return; }
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
  const onResize = () => { if (mode) { placeCounter(root, manifest.plates[mode], manifest.burger?.ratio); if (lower?.dataset.mode === 'sub' && mode === 'tall') show(false); else { clearBehindCounter(); avoidCounter(); } } };
  const onKey = (ev) => {
    if (ev.key !== 'Escape' || ev.defaultPrevented || document.body.classList.contains('menu-open')) return;
    if (view !== 'rest' || sel) goRest();
  };
  document.addEventListener('keydown', onKey);
  window.addEventListener('resize', onResize);
  wideQuery.addEventListener('change', onMq);

  render();
  // tag fit is measured in the real type: when Kalam arrives after the first layout, measure again
  let alive = true;
  document.fonts?.ready.then(() => {
    if (!alive || !mode || !items.length) return;
    if (mode === 'tall' && lower?.dataset.mode === 'sub') show(false); else setRows(items);
  });
  if (q.get('check') === '1') import('./selfcheck.js').then((m) => m.run({ manifest, ix }));      // build/tools/smoke.py

  return {
    sameTarget: () => true,
    update(c) { select(c.cat, true); },
    unmount() {
      alive = false;
      token++;
      fadeOff?.();
      clearTimeout(soonTimer);
      document.removeEventListener('keydown', onKey);
      clockCtl?.destroy();
      burgerCtl?.destroy();
      tabsCtl?.destroy();
      window.removeEventListener('resize', onResize);
      root.removeEventListener('click', onClick);
      wideQuery.removeEventListener('change', onMq);
      delete document.body.dataset.scene;
    },
  };
}
