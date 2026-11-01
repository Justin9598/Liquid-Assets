// Welcome page: the bar (Plan 01). Top shelf = categories, lower shelves = subcategory bottles.
// Two scenes share the same live layers: v2 (illustrated, used until the rendered plates exist) and v3 (the plate engine).
import { bottleSVG, DEFAULT_LABEL, motifFor, randomPick, shapeFor } from './bottles.js';
import { getJSON, getSections, img } from './data.js';
import { menuButton } from './menu.js';
import { BARREL, BAY_ROWS, GLASSES, PRINT, SIGN, STOOL } from './scene.js';
import { anchorStyle, debugHTML, plateHTML, plateKind, sceneQuery, shelfStyle, shellBottle, wideQuery } from './scene3.js';
import { $, $$, announce, esc, plural, reducedMotion, setTitle } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');
const langOf = (s) => (isHangul(s) ? 'ko' : 'ja');

const mqDesktop = window.matchMedia('(min-width: 1024px)');
const mqTablet = window.matchMedia('(min-width: 768px)');
const perRow = () => (mqDesktop.matches ? 6 : mqTablet.matches ? 4 : 3);

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
  const forced = q.get('scene');                      // ?scene=v3 or ?scene=v2 overrides the automatic choice
  const debug = q.get('debug') === 'scene';

  let sel = ctx.cat || null;
  let items = [];
  let token = 0;
  let mode = null;                                   // 'v2' | 'wide' | 'tall'
  let lower = null;
  let plaque = null;

  // Automatic choice (Plan 01 section 15.2): a screen shape uses the rendered scene when its plate exists, otherwise the
  // v2 illustration. Landscape has the wide plate today; phones keep v2 until the tall plate arrives.
  const hasPlate = (kind) => !!manifest?.plates?.[kind]?.files;
  const currentMode = () => {
    if (!manifest || forced === 'v2') return 'v2';
    const kind = plateKind();
    return forced === 'v3' || hasPlate(kind) ? kind : 'v2';
  };

  // ---- bottle art: rendered shell when one exists, otherwise the SVG bottle -------------------------------------
  const art = (shape, o) => (mode && mode !== 'v2' && shellBottle(manifest, shape, o)) || bottleSVG(shape, o);

  const vesselHTML = (c) => {
    const def = DEFAULT_LABEL[c.vessel] || {};
    return `<button type="button" class="vessel" data-cat="${esc(c.key)}" aria-pressed="false">
  <span class="vessel-art">${art(c.vessel, { native: def.native, name: def.name, motif: def.motif })}</span>
  <span class="vessel-cap">${esc(c.name)}</span>
</button>`;
  };

  // ---- skeletons ------------------------------------------------------------------------------------------------
  function skeletonV2() {
    const spots = Array.from({ length: 6 }, () => '<i></i>').join('');
    return `<div class="bar">
  <div class="room" aria-hidden="true">
    <div class="beam beam-back"></div><div class="beam beam-front"><span class="spots">${spots}</span></div>
  </div>
  <h1 class="sr-only" tabindex="-1">Liquid Assets</h1>
  <div class="sign" aria-hidden="true">${SIGN}</div>
  <div class="stage">
    <div class="side left" aria-hidden="true"><div class="print">${PRINT}</div></div>
    <div class="shelving">
      <div class="soffit" aria-hidden="true">${spots}</div>
      <section class="topshelf" aria-label="Categories. Pick one to see its shelves.">
        <div class="tier t1">${cats.slice(0, 4).map(vesselHTML).join('')}</div>
        <div class="tier t2">${cats.slice(4).map(vesselHTML).join('')}</div>
      </section>
      <section class="lower" id="lower" aria-label="Shelves"></section>
    </div>
    <div class="side right" aria-hidden="true"><div class="side-bay">${BAY_ROWS.map((r) => `<div class="bay-row">${r}</div>`).join('')}</div></div>
  </div>
  <div class="counter">
    <div class="counter-top">
      <p class="slate" id="plaque">${IDLE}</p>
      <span class="glasses" aria-hidden="true">${GLASSES}</span>
      ${menuButton('on-counter')}
    </div>
    <div class="counter-front" aria-hidden="true"><span class="plinth"></span></div>
  </div>
  <div class="floor" aria-hidden="true">
    <span class="barrel">${BARREL}</span>
    <div class="stools">${STOOL}${STOOL}${STOOL}${STOOL}</div>
  </div>
</div>`;
  }

  function skeletonV3(kind) {
    const P = manifest.plates[kind];
    const vesselRows = kind === 'wide' ? [cats] : [cats.slice(0, 4), cats.slice(4)];
    const rows = vesselRows.map((row, i) => `<div class="shelf-row s3 vrow" style="${shelfStyle(P.shelves[i])}"><div class="row-items" style="--n:${row.length}">${row.map(vesselHTML).join('')}</div></div>`).join('');
    return `<div class="bar scene3" data-plate="${kind}">
  <h1 class="sr-only" tabindex="-1">Liquid Assets</h1>
  <div class="cover" style="--ratio:${P.ratio}">
    ${plateHTML(P)}
    <section class="topshelf3" aria-label="Categories. Pick one to see its shelves.">${rows}</section>
    <section class="lower" id="lower" aria-label="Shelves"></section>
    <p class="slate s3" id="plaque" style="${anchorStyle(P.anchors.slate)}">${IDLE}</p>
    <div class="menu-anchor" style="${anchorStyle(P.anchors.menu)}">${menuButton('on-counter')}</div>
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
  <span class="hang" aria-hidden="true">${tagHTML}</span>`;
    // Phase 1: the shelf pages aren't published, so the bottles are buttons that say so on the slate (Plan 06 section 12.1)
    if (!getSections().shelves) {
      return `<button type="button" class="slot sub soon" data-soon aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}. This shelf opens soon." data-shape="${it.shape}">${inner}</button>`;
    }
    return `<a class="slot sub" href="${esc(it.href)}" aria-label="${esc(it.name)}, ${plural(it.count, 'drink')}" data-shape="${it.shape}">${inner}</a>`;
  }

  // ---- placing rows ----------------------------------------------------------------------------------------------
  function rowsV2(list) {
    const sizes = distribute(list.length, perRow());
    const shelves = Math.max(2, sizes.length);
    let k = 0;
    let html = '';
    for (let r = 0; r < shelves; r++) {
      const n = sizes[r] || 0;
      const cells = [];
      for (let j = 0; j < n; j++, k++) cells.push(slotHTML(list[k]));
      html += `<div class="shelf-row${n === 1 ? ' single' : ''}"><div class="row-items">${cells.join('')}</div><div class="plank"></div></div>`;
    }
    return html;
  }

  function rowsV3(list) {
    const kind = mode;
    const P = manifest.plates[kind];
    const nTop = kind === 'wide' ? 1 : 2;
    const shelves = P.shelves.slice(nTop);
    let groups;
    if (kind === 'wide') {
      const sizes = distribute(list.length, 6);
      let k = 0;
      groups = sizes.map((n) => { const g = list.slice(k, k + n); k += n; return g; });
    } else {
      groups = list.length <= 3 ? [list] : [list.slice(0, Math.ceil(list.length / 2)), list.slice(Math.ceil(list.length / 2))];
    }
    return shelves.map((s, i) => {
      const g = groups[i] || [];
      const per = kind === 'wide' ? 6 : 3;
      return `<div class="shelf-row s3 lowrow${g.length === 1 ? ' single' : ''}" style="${shelfStyle(s)};--per:${per}"><div class="row-items">${g.map(slotHTML).join('')}</div></div>`;
    }).join('');
  }

  function setRows(list) {
    items = list;
    lower.innerHTML = mode === 'v2' ? rowsV2(list) : rowsV3(list);
    lower.dataset.mode = list.length && list[0].mix ? 'mix' : 'sub';
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
  function soon() {
    clearTimeout(soonTimer);
    plaque.textContent = 'This shelf opens soon.';
    announce('This shelf opens soon.');
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
    if (c) announce(c.subcategories.length === 1 ? `Showing ${c.name}: ${plural(c.drinkCount, 'drink')}` : `Showing ${c.name}: ${c.subcategories.length} kinds`);
    else announce('Showing a mixed selection');
  }

  // ---- render ----------------------------------------------------------------------------------------------------
  function render() {
    mode = currentMode();
    root.innerHTML = mode === 'v2' ? skeletonV2() : skeletonV3(mode);
    document.body.dataset.scene = mode === 'v2' ? 'v2' : 'v3';
    lower = $('#lower', root);
    plaque = $('#plaque', root);
    select(sel, false);
  }

  const onClick = (ev) => {
    const v = ev.target.closest('.vessel');
    if (v) {
      location.hash = sel === v.dataset.cat ? '#/' : `#/${v.dataset.cat}`;
      return;
    }
    if (ev.target.closest('[data-soon]')) { soon(); return; }
    const mix = ev.target.closest('.slot.mix');
    if (mix) location.hash = `#/${mix.dataset.cat}`;
  };
  root.addEventListener('click', onClick);
  const onMq = () => {
    if (currentMode() !== mode) render(); else if (items.length) setRows(items);
  };
  mqDesktop.addEventListener('change', onMq);
  mqTablet.addEventListener('change', onMq);
  wideQuery.addEventListener('change', onMq);

  render();

  return {
    sameTarget: () => true,
    update(c) { select(c.cat, true); },
    unmount() {
      token++;
      clearTimeout(soonTimer);
      root.removeEventListener('click', onClick);
      mqDesktop.removeEventListener('change', onMq);
      mqTablet.removeEventListener('change', onMq);
      wideQuery.removeEventListener('change', onMq);
      delete document.body.dataset.scene;
    },
  };
}
