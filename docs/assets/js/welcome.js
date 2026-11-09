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
  let view = 'rest';                                 // rest | new | season (Plan 10 section 4); the category view is `sel` alone
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
      const owner = new Map(c.subcategories.flatMap((s) => (s.drinks || []).filter((d) => d.label).map((d) => [d.label, d])));   // label -> the drink it belongs to
      const label = randomPick([...owner.keys()], used);
      const def = DEFAULT_LABEL[c.key] || {};
      out.push({ mix: true, cat: c.key, shape: shapeFor(c.key), label: label && img(label), native: def.native, name: def.name, motif: def.motif, drink: label ? owner.get(label) : null, catName: c.name });
    }
    return out;
  }

  /** One bottle per subcategory; tapping it shows that subcategory's drinks (Plan 10 section 12). */
  function subItems(c) {
    const used = new Set();
    return c.subcategories.map((s) => {
      const label = randomPick(s.labels, used);
      state.picked = { ...state.picked, [`${c.key}/${s.key}`]: label };   // the shelf page shows the bottle the visitor tapped
      return {
        sub: true, cat: c.key, subKey: s.key, shape: shapeFor(c.key, s.key), label: label && img(label), native: s.native, name: s.name,
        motif: motifFor(c.key, s.key), count: s.drinkCount,
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
      const label = it.text || `See all ${it.count}`;
      return getSections().shelves
        ? `<div class="slot seeall"><a class="seeall-board chalkboard chalkboard--s" href="${esc(it.href)}">${esc(label)}</a></div>`
        : `<div class="slot seeall"><button type="button" class="seeall-board chalkboard chalkboard--s" data-soon>${esc(label)}</button></div>`;
    }
    const a = art(it.shape, { label: it.label, native: it.native, name: it.name, motif: it.motif });
    if (it.mix) {                                                // at Rest a lower-shelf bottle opens the drink whose label it wears
      if (it.drink && getSections().drinks) {
        return `<a class="slot mix" href="#/drink/${encodeURIComponent(it.drink.id)}" aria-label="${esc(it.drink.name)}, open drink" data-cat="${esc(it.cat)}" data-shape="${it.shape}"><span class="art">${a}</span></a>`;
      }
      if (it.drink) {
        return `<button type="button" class="slot mix" data-drink-soon data-name="${esc(it.drink.name)}" data-cat="${esc(it.catName)}" aria-label="${esc(it.drink.name)}, open drink. Its page opens soon." data-shape="${it.shape}"><span class="art">${a}</span></button>`;
      }
      return `<button type="button" class="slot mix" tabindex="-1" aria-hidden="true" data-cat="${esc(it.cat)}" data-shape="${it.shape}"><span class="art">${a}</span></button>`;
    }
    if (it.drink === true) {                                     // a single drink in a view: the bottle opens it, a small tag names it on hover
      return `<div class="slot drink" data-shape="${it.shape}">${bottleLink(a, it.id, it.dname, it.name || '')}<span class="hang chalkboard chalkboard--s" aria-hidden="true"><span class="nm">${esc(it.dname)}</span></span></div>`;
    }
    const second = [];
    if (it.native) second.push(`<span class="nat" lang="${langOf(it.native)}">${esc(it.native)}</span>`);
    second.push(`<span class="ct">${it.count}</span>`);
    const tagHTML = `<span class="nm">${esc(it.name)}</span><span class="l2">${second.join('<i> · </i>')}</span>`;
    // in category view a bottle and its board are one link to that subcategory's list page, the page "See all" opens (Plan 10 section 13)
    const inner = `<span class="art">${a}</span><span class="hang chalkboard chalkboard--s" aria-hidden="true">${tagHTML}</span>`;
    if (!getSections().shelves) {                                                    // Phase 1: the list pages are not published yet
      return `<button type="button" class="slot sub" data-soon data-shape="${it.shape}" aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}. This shelf opens soon.">${inner}</button>`;
    }
    return `<a class="slot sub" href="#/${esc(it.cat)}/${esc(it.subKey)}" data-shape="${it.shape}" aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}, see all">${inner}</a>`;
  }

  // ---- placing rows ----------------------------------------------------------------------------------------------
  /** Bottles per visible shelf for the subcategory view. Wide: the fewest per row that still fits every bottle on the
   * two lower shelves, so the pitch is as wide as it can be (the tags need it). Tall: `visible` bottles in the
   * scrolling row, 3 unless their tags need more room (Plan 07 section 8.2). */
  let visible = 3;
  let drinkPer = 9;                                  // phones, a view of drinks: bottles across the row (Plan 10 section 11.1)
  const kindOf = (list) => (!list.length ? 'sub' : list[0].mix ? 'mix' : list[0].sub ? 'sub' : 'drinks');
  function rowsV3(list, plan = null) {
    const kind = mode;
    const P = manifest.plates[kind];
    const nTop = kind === 'wide' ? 1 : 2;
    const shelves = P.shelves.slice(nTop);
    const mixed = !!(list.length && list[0].mix);
    const drinks = kindOf(list) === 'drinks';
    let groups;
    let per;
    if (plan) {                                         // category view on the wide plate: shelf 2 first, shelf 3 only what fits clear of the counter (Plan 14 section 4)
      groups = plan.groups;
      per = plan.pers[0];
    } else if (kind === 'wide' && drinks) {                    // a view of drinks: the shelf fills from the left shelf's centre outwards, measured capacity per shelf
      per = Math.max(4, P.lowerCapacity?.perShelf || 12);
      groups = [list.slice(0, per), list.slice(per)];
    } else if (kind === 'wide') {
      per = mixed ? 6 : Math.max(3, Math.ceil(list.length / shelves.length));
      const sizes = distribute(list.length, per);
      let k = 0;
      groups = sizes.map((n) => { const g = list.slice(k, k + n); k += n; return g; });
    } else {
      groups = [list];                                  // phones: one shelf, a few visible, scrolling sideways
      per = mixed ? 3 : drinks ? drinkPer : visible;
    }
    return shelves.map((s, i) => {
      const g = groups[i] || [];
      const cue = kind === 'tall' && drinks ? '<span class="more-cue chalkboard chalkboard--s" aria-hidden="true">→</span>' : '';
      return `<div class="shelf-row s3 lowrow${g.length === 1 ? ' single' : ''}${drinks ? ' drinks' : ''}" data-shelf="${nTop + i}" style="${shelfStyle(s)};--per:${plan ? +plan.pers[i].toFixed(4) : per}"><div class="row-items"${plan?.pads[i] ? ` style="padding-left:${plan.pads[i][0]}px;padding-right:${plan.pads[i][1]}px"` : ''}>${g.map(slotHTML).join('')}</div>${cue}</div>`;
    }).join('');
  }

  /** Do all the subcategory tags fit at the smallest type size: no wrapped Japanese line, at most 2 name lines, and a
   * height that stays inside the room under their shelf (Plan 07 section 8.2)? */
  function tagsFit() {
    if (mode === 'wide') {                                   // wide: no clipped or 3-line tag, and no two tags on a shelf touching (the shelf area is checked by selfcheck)
      const ok = $$('.hang', lower).every((h) => {
        const nm = $('.nm', h);
        const lh = parseFloat(getComputedStyle(nm).lineHeight) || 15;
        return h.scrollWidth <= h.clientWidth + 1 && nm.getBoundingClientRect().height <= lh * 2 + 1;
      });
      const apart = $$('.lowrow', lower).every((row) => {
        const rs = $$('.hang', row).map((h) => h.getBoundingClientRect()).sort((a, b) => a.left - b.left);
        return rs.every((r, i) => i === 0 || r.left >= rs[i - 1].right + 2);
      });
      return ok && apart;
    }
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
    if (mode === 'tall' && lower.dataset.mode === 'drinks') {      // tighter spacing for drinks: about 1.15 bottle widths apart, never fewer than 6 across
      const row = $('.lowrow .row-items', lower);
      const widest = Math.max(0, ...$$('.art > *', row).map((e) => e.getBoundingClientRect().width));
      const per = widest && row.clientWidth ? Math.max(6, Math.floor(row.clientWidth / (1.15 * widest))) : drinkPer;
      if (per !== drinkPer) { drinkPer = per; lower.innerHTML = rowsV3(list); }
    }
    if (mode === 'tall') watchFades($('.lowrow .row-items', lower));
    if (mode === 'wide' && lower.dataset.mode === 'sub') fitSubShelves(list);
    clearBehindCounter();
    avoidCounter();
  }

  /** Room a row must leave on each side so its bottles do not stand behind the counter bottles level with it. */
  function counterPads(r, front, seeall = false) {
    const rr = r.getBoundingClientRect();
    const mid = (rr.left + rr.right) / 2;
    let padL = 0;
    let padR = 0;
    for (const f of front) {
      if (f.bottom < rr.top + rr.height * 0.18 || f.top > rr.bottom) continue;      // not level with this shelf's bottles
      const extra = seeall ? 16 : 0;                                              // the See all board is a little wider than its place
      if (f.right > rr.left && f.left < mid) padL = Math.max(padL, f.right - rr.left + 8 + extra);
      else if (f.left < rr.right && f.right > mid) padR = Math.max(padR, rr.right - f.left + 8 + extra);
    }
    return [Math.ceil(padL), Math.ceil(padR)];
  }

  /** Category view, wide plate (Plan 14 section 4): the counter groups stand in front of the ends of shelf 3. Shelf 3 gets only
   * the room between them, at the same bottle pitch as shelf 2, and shelf 2 takes the rest, filling first. The widest pitch
   * that holds every kind on the two shelves wins. If none does at a pitch where the tags still fit, the last place on
   * shelf 3 becomes a "See all {n} kinds" board. */
  function fitSubShelves(list) {
    const rowEls = $$('.lowrow .row-items', lower);
    const front = frontBottles();
    if (rowEls.length < 2) return;
    rowEls.forEach((r) => { r.style.paddingLeft = ''; r.style.paddingRight = ''; });
    const w2 = rowEls[0].clientWidth;
    const [padL, padR] = counterPads(rowEls[1], front);
    const clear3 = rowEls[1].clientWidth - padL - padR;
    const n = list.length;
    const cap3Of = (per2) => Math.max(0, Math.floor(clear3 / (w2 / per2) + 1e-6));
    const make = (per2, seeAll) => {
      const p = w2 / per2;
      const cap3 = cap3Of(per2);
      let g3 = list.slice(per2);
      if (seeAll) {
        g3 = list.slice(per2, per2 + Math.max(0, cap3 - 1));
        const c = ix.cats.get(sel);
        g3.push({ seeall: true, count: list.length, text: `See all ${list.length} kinds`, href: `#/${c.key}` });
      }
      const empty = !g3.length;
      return { groups: [list.slice(0, per2), g3], pers: [per2, empty ? per2 : clear3 / p], pads: [null, empty ? null : [padL, padR]] };
    };
    let per2 = 3;
    while (per2 + cap3Of(per2) < n && per2 < 16) per2++;
    const fits = per2 + cap3Of(per2) >= n;
    let plan = make(per2, !fits);
    lower.innerHTML = rowsV3(list, plan);
    if (!fits || !tagsFit()) {                                // the tags cannot use so narrow a pitch: fewer bottles and a See all board
      lower.dataset.fitFail = '';
      for (let k = Math.min(per2, 16); k >= 3; k--) {
        plan = make(k, true);
        lower.innerHTML = rowsV3(list, plan);
        if (tagsFit()) break;
      }
    }
    lower.dataset.shelf2 = String(plan.groups[0].length);
    lower.dataset.shelf3 = String(plan.groups[1].length);
  }

  /** In a view of drinks the counter bottles stay up (filtered, or the usual set), so on the wide plate the lower shelves give
   * way: a row's room shrinks where a counter bottle would stand in front of it, instead of drawing one bottle behind another. */
  function avoidCounter() {
    if (mode === 'wide' && lower.dataset.mode === 'sub') return;          // fitSubShelves places its own padding
    $$('.lowrow .row-items', lower).forEach((r) => { r.style.paddingLeft = ''; r.style.paddingRight = ''; });
    if (mode !== 'wide' || lower.dataset.mode !== 'drinks') return;
    const front = frontBottles();
    if (!front.length) return;
    for (const r of $$('.lowrow .row-items', lower)) {
      const [padL, padR] = counterPads(r, front, !!r.querySelector('.seeall'));
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
      el.parentElement?.classList.toggle('has-more', max - el.scrollLeft > 4);         // the chalk arrow shows only while more bottles are hidden
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
    const eff = c?.direct ? { cat: c.key, sub: c.subcategories[0].key } : null;               // only Umeshu fills the shelves with its drinks
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

  /** The counter's two groups: the usual whole-bar 5, or, in a category view, that category's own 5 topped up from other
   * categories by the build (Plan 14 section 3). The placard's second line says "in Sake" or "in Wine + more". */
  let counterKey = null;
  function updateCounter() {
    const c = sel && view === 'rest' ? ix.cats.get(sel) : null;
    const data = c?.counter || null;
    const key = `${mode}|${data ? c.key : ''}`;
    if (key === counterKey) return;
    counterKey = key;
    const rest = { new: (counterData.newArrivals || []).slice(0, 5), season: ((counterData.inSeason || {})[season] || []).slice(0, 5) };
    for (const id of ['new', 'season']) {
      const own = data ? (id === 'new' ? data.new : (data.season || {})[season]) || [] : [];
      const more = data ? !!(id === 'new' ? data.newMore : (data.seasonMore || {})[season]) : false;
      const useOwn = own.length > 0;
      const row = $(`#cg-${id} .cg-row`, root);
      if (row) row.innerHTML = rowHTML(useOwn ? own : rest[id], ix, art, useOwn ? c.key : null);
      const line = useOwn ? `in ${c.name}${more ? ' + more' : ''}` : '';
      for (const el of [$(`#cg-${id}-h .in`, root), $(`#tab-${id} .in`, root)]) {
        if (!el) continue;
        el.textContent = line;
        el.hidden = !line;
      }
      if (id === 'season') $('#tab-season', root)?.setAttribute('aria-label', `In season: ${SEASON_NAMES[season]}${line ? `, ${line}` : ''}`);
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
    if (view === 'new' || view === 'season' || c?.direct) announce(caption);
    else if (c) announce(c.subcategories.length === 1 ? `Showing ${c.name}: ${plural(c.drinkCount, 'drink')}` : `Showing ${c.name}: ${c.subcategories.length} kinds`);
    else announce('Showing a mixed selection');
  }

  /** The category view from the hash (or no category), with any other view cleared. */
  function select(key, animate) {
    sel = key;
    view = 'rest';
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
    tabsCtl = P.counter?.mode === 'tabs' ? mountTabs(root, { onTab: (tab) => { view = tab === 'new' ? 'new' : 'season'; show(true); } }) : null;
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
      if (sel === v.dataset.cat && view !== 'rest') { view = 'rest'; show(true); return; }     // back to that category's own view
      location.hash = sel === v.dataset.cat ? '#/' : `#/${v.dataset.cat}`;
      return;
    }
    const pv = ev.target.closest('.placard[data-view]');
    if (pv) { view = pv.dataset.view; show(true); return; }
    const cb = ev.target.closest('[data-drink-soon]');
    if (cb) { soon(`${cb.dataset.name}, ${cb.dataset.cat}. Its page opens soon.`); return; }
    if (ev.target.closest('[data-soon]')) { soon(); return; }
    const mix = ev.target.closest('button.slot.mix');
    if (mix) location.hash = `#/${mix.dataset.cat}`;
  };
  root.addEventListener('click', onClick);
  const onMq = () => {
    if (plateKind() !== mode) render(); else if (items.length) setRows(items);
  };
  const onResize = () => { if (mode) { placeCounter(root, manifest.plates[mode], manifest.burger?.ratio); if (lower?.dataset.mode === 'sub') { if (mode === 'tall') show(false); else setRows(items); } else { clearBehindCounter(); avoidCounter(); } } };
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
