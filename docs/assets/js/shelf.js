// Shelf list page: "Up close" (Plan 02, looks from Plan 08 section 4.1). Filters, sort and search all run in the browser
// and live in the hash. A hero board with the shelf's shell, a strip of sibling shelves, a toolbar board and a grid of cards.
import { cardHTML } from './cards.js';
import { board, pageHTML } from './chrome.js';
import { getJSON, img } from './data.js';
import { icon } from './icons.js';
import { motifFor, randomPick, shapeFor } from './labels.js';
import { shellHTML } from './shells.js';
import { $, $$, announce, buildHash, debounce, esc, fold, plural, replaceHash, setTitle, slug } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');
const SORTS = {
  name: 'Name A to Z', fav: 'Favourites first', producer: 'Producer', origin: 'Origin',
  abv: 'ABV high to low', most: 'Most had', rating: 'Rating', recent: 'Recently added',
};

export async function mount(root, ctx) {
  const { ix, cat, sub } = ctx;
  const info = ix.subs.get(`${cat}/${sub}`);
  const c = info.cat;
  const s = info.sub;
  let content = {};
  try { content = await getJSON('subcategories.json'); } catch { /* copy is optional */ }
  const copy = content[`${cat}/${sub}`] || {};
  const drinks = ix.drinks.filter((d) => d.category === cat && d.sub === sub); // already Name A-Z
  const order = new Map(drinks.map((d, i) => [d.id, i]));
  const single = c.subcategories.length === 1;
  const hasToolbar = drinks.length >= 8;
  const few = drinks.length <= 3;

  setTitle(single ? c.name : s.name);

  // ---- hero: the bottle the visitor tapped on the bar is the bottle they see ---------------------------------
  const key = `${cat}/${sub}`;
  const picked = ctx.state.picked?.[key] ?? randomPick(s.labels, new Set());
  const pickedDrink = picked ? (s.drinks || []).find((x) => img(x.label) === img(picked)) : null;   // the hero wears one drink's label, so it stands in that drink's shell (Plan 15 section 4.4)
  const heroShell = shellHTML((pickedDrink && pickedDrink.shell) || shapeFor(cat, sub), { label: picked && img(picked), native: s.native, name: s.name, motif: motifFor(cat, sub) });
  const producers = new Set(drinks.map((d) => d.producerKey || d.producer).filter(Boolean));
  const origins = new Set(drinks.map((d) => d.origin).filter(Boolean));
  const allJapan = drinks.length > 0 && drinks.every((d) => d.country === 'Japan');
  const stats = [plural(drinks.length, 'drink'), plural(producers.size, 'producer'),
    `${origins.size} ${allJapan ? (origins.size === 1 ? 'prefecture' : 'prefectures') : (origins.size === 1 ? 'region' : 'regions')}`].join(' · ');
  const nativeLang = s.native ? (isHangul(s.native) ? 'ko' : 'ja') : '';

  const strip = single ? '' : `<nav class="strip" id="strip" aria-label="Other ${esc(c.name)} shelves">${
    c.subcategories.map((o) => {
      const cur = o.key === sub;
      return `<a class="sib chalkboard chalkboard--s${cur ? ' on' : ''}" href="#/${c.key}/${o.key}"${cur ? ' aria-current="page"' : ''} aria-label="${esc(o.name)}, ${plural(o.drinkCount, 'drink')}"><span class="chalk">${esc(o.name)}</span><span class="ct" aria-hidden="true">${o.drinkCount}</span></a>`;
    }).join('')}</nav>`;

  const hero = board(`<div class="hero-shelf">
  <div class="stand" aria-hidden="true">${heroShell}</div>
  <div class="hero-copy">
    <h1 class="t-title" tabindex="-1">${esc(s.name)}${s.native ? ` <span class="native" lang="${nativeLang}">${esc(s.native)}</span>` : ''}</h1>
    <p class="t-data">${esc(stats)}</p>
    ${copy.explainer ? `<p class="t-body">${esc(copy.explainer)}</p>` : ''}
    ${copy.facts?.length ? `<ul class="fact-chips">${copy.facts.map((f) => `<li class="chalkboard chalkboard--s">${esc(f)}</li>`).join('')}</ul>` : ''}
  </div>
</div><i class="tray" aria-hidden="true"></i>`, 'has-tray hero');

  const toolbar = hasToolbar ? board(`
    <div class="tb-top">
      <label class="search"><span class="sr-only">Search name or producer</span><input class="chalk-input" type="search" id="q" placeholder="Search name or producer" autocomplete="off"></label>
      <button type="button" class="chalkboard chalkboard--s btn-s sheet-btn" id="sheet-btn" aria-expanded="false" aria-controls="filters">Filter &amp; sort</button>
    </div>
    <div class="filters" id="filters" role="group" aria-label="Filter and sort">
      <div class="sheet-head"><strong class="t-label">Filter &amp; sort</strong><button type="button" class="chalkboard chalkboard--s btn-s" id="sheet-done">Done</button></div>
      <div class="chip-row" id="chips" aria-label="Styles"></div>
      <div class="row-controls">
        <label class="field"><span>Origin</span><select class="chalk-input" id="origin"></select></label>
        <button type="button" class="chalkboard chalkboard--s btn-s" id="fav" aria-pressed="false"><span class="chalk">${icon('star-fill', 16)} Favourites</span></button>
        <label class="field"><span>Sort</span><select class="chalk-input" id="sort"></select></label>
      </div>
    </div>
    <div class="sheet-backdrop" id="backdrop-sheet"></div>
    <p class="showing t-data" id="count" aria-live="polite"></p>`, 'toolbar', 'id="toolbar"') : '';

  const crumbs = single ? [{ label: c.name }] : [{ label: c.name, href: `#/${c.key}` }, { label: s.name }];
  root.innerHTML = pageHTML({
    crumbs, cls: 'shelf-page',
    boards: `${hero}${strip}${toolbar}<div class="grid${few ? ' few' : ''}" id="grid"></div>`,
  });

  const grid = $('#grid', root);
  const countEl = $('#count', root);

  // soft fades at the ends of the sibling strip when it scrolls sideways
  const stripEl = $('#strip', root);
  const fades = () => {
    if (!stripEl) return;
    const max = stripEl.scrollWidth - stripEl.clientWidth;
    stripEl.classList.toggle('fade-l', stripEl.scrollLeft > 4);
    stripEl.classList.toggle('fade-r', max - stripEl.scrollLeft > 4);
  };
  if (stripEl) {
    stripEl.addEventListener('scroll', fades, { passive: true });
    window.addEventListener('resize', fades);
    $('.sib.on', stripEl)?.scrollIntoView({ inline: 'center', block: 'nearest' });
    requestAnimationFrame(fades);
  }

  // ---- state from the URL -----------------------------------------------------------------------------------
  const st = { q: '', styles: new Set(), origin: '', fav: false, sort: 'name' };
  const styleCounts = new Map();
  for (const d of drinks) for (const t of d.styles) styleCounts.set(t, (styleCounts.get(t) || 0) + 1);
  const styleList = [...styleCounts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const styleByFold = new Map(styleList.map(([t]) => [fold(t), t]));
  const originCounts = new Map();
  for (const d of drinks) if (d.origin) originCounts.set(d.origin, (originCounts.get(d.origin) || 0) + 1);
  const countries = new Set(drinks.map((d) => d.country).filter(Boolean));
  const hasFav = drinks.some((d) => d.favourite);
  const nRating = drinks.filter((d) => d.rating != null).length;
  const nAdded = drinks.filter((d) => d.added).length;
  const sortKeys = ['name', 'fav', 'producer', 'origin', 'abv', 'most'].concat(nRating >= 5 ? ['rating'] : [], nAdded >= 5 ? ['recent'] : []);

  function readParams(params) {
    st.q = hasToolbar ? (params.get('q') || '') : '';
    st.styles = new Set();
    for (const part of (params.get('style') || '').split(',')) {
      const t = styleByFold.get(fold(part));
      if (t) st.styles.add(t);
    }
    const o = params.get('origin');
    st.origin = '';
    if (o) for (const name of originCounts.keys()) if (slug(name) === slug(o)) st.origin = name;
    st.fav = hasFav && params.get('fav') === '1';
    const so = params.get('sort');
    st.sort = sortKeys.includes(so) ? so : 'name';
    if (!hasToolbar) { st.styles = new Set(); st.origin = ''; st.fav = false; }
  }

  // ---- controls ---------------------------------------------------------------------------------------------
  if (hasToolbar) {
    const sel = $('#origin', root);
    const opt = (name) => `<option value="${esc(name)}">${esc(name)} (${originCounts.get(name)})</option>`;
    let html = `<option value="">All (${drinks.length})</option>`;
    if (countries.size > 1) {
      for (const country of [...countries].sort()) {
        const names = [...originCounts.keys()].filter((n) => drinks.some((d) => d.origin === n && d.country === country)).sort((a, b) => a.localeCompare(b));
        html += `<optgroup label="${esc(country)}">${names.map(opt).join('')}</optgroup>`;
      }
    } else html += [...originCounts.keys()].sort((a, b) => a.localeCompare(b)).map(opt).join('');
    sel.innerHTML = html;
    $('#sort', root).innerHTML = sortKeys.map((k) => `<option value="${k}">${SORTS[k]}</option>`).join('');
    if (!hasFav) $('#fav', root).hidden = true;
    if (!styleList.length) $('#chips', root).hidden = true;
  }

  const passes = (d, skip) => {
    if (skip !== 'q' && st.q) {
      const hay = fold(`${d.name} ${d.producer || ''}`);
      if (!fold(st.q).split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    if (skip !== 'styles' && st.styles.size && ![...st.styles].every((t) => d.styles.includes(t))) return false;
    if (skip !== 'origin' && st.origin && d.origin !== st.origin) return false;
    if (skip !== 'fav' && st.fav && !d.favourite) return false;
    return true;
  };

  const byName = (a, b) => order.get(a.id) - order.get(b.id);
  const cmp = {
    name: byName,
    fav: (a, b) => (b.favourite - a.favourite) || byName(a, b),
    producer: (a, b) => fold(a.producer || '￿').localeCompare(fold(b.producer || '￿')) || byName(a, b),
    origin: (a, b) => fold(a.origin || '￿').localeCompare(fold(b.origin || '￿')) || byName(a, b),
    abv: (a, b) => ((b.abv ?? -1) - (a.abv ?? -1)) || byName(a, b),
    most: (a, b) => (b.occasions - a.occasions) || byName(a, b),
    rating: (a, b) => ((b.rating ?? -1) - (a.rating ?? -1)) || byName(a, b),
    recent: (a, b) => (b.added || '').localeCompare(a.added || '') || byName(a, b),
  };

  const active = () => !!(st.q || st.styles.size || st.origin || st.fav);

  function writeUrl() {
    const h = buildHash([cat, sub], {
      style: [...st.styles].map((t) => fold(t)).join(','), origin: st.origin ? slug(st.origin) : '',
      fav: st.fav ? '1' : '', sort: st.sort !== 'name' ? st.sort : '', q: st.q.trim(),
    });
    replaceHash(h);
    ctx.state.lastShelf = location.hash;
  }

  function renderChips() {
    if (!hasToolbar || !styleList.length) return;
    $('#chips', root).innerHTML = styleList.map(([t, n]) => {
      const on = st.styles.has(t);
      const next = new Set(st.styles).add(t);
      const wouldBe = drinks.filter((d) => passes(d, 'styles') && [...next].every((x) => d.styles.includes(x))).length;
      return `<button type="button" class="chip chalkboard chalkboard--s" data-style="${esc(t)}" aria-pressed="${on}"${!on && wouldBe === 0 ? ' disabled' : ''}><span class="chalk">${esc(t)} <span class="n">${n}</span></span></button>`;
    }).join('');
  }

  function apply(announceIt = true) {
    const list = drinks.filter((d) => passes(d)).sort(cmp[st.sort]);
    if (!list.length) {
      grid.innerHTML = `<div class="nothing chalkboard chalkboard--xl"><h2 class="t-head">Nothing on this shelf matches.</h2><div><button type="button" class="chalkboard chalkboard--s btn-s" id="clear2">Clear filters</button></div></div>`;
    } else {
      grid.innerHTML = list.map((d, i) => cardHTML(d, ix, { eager: i < 8 })).join('');
    }
    if (countEl) {
      countEl.innerHTML = `Showing ${list.length} of ${drinks.length}${active() ? ' · <button type="button" class="linkish" id="clear1">Clear filters</button>' : ''}`;
    }
    if (hasToolbar) {
      const qEl = $('#q', root);
      if (qEl.value !== st.q) qEl.value = st.q;
      $('#origin', root).value = st.origin;
      $('#sort', root).value = st.sort;
      $('#fav', root).setAttribute('aria-pressed', String(st.fav));
      renderChips();
    }
    if (announceIt && hasToolbar) announce(`Showing ${list.length} of ${drinks.length}`);
  }

  readParams(ctx.params);
  apply(false);
  ctx.state.lastShelf = location.hash;

  // ---- events -----------------------------------------------------------------------------------------------
  const clear = () => { st.q = ''; st.styles = new Set(); st.origin = ''; st.fav = false; apply(); writeUrl(); };
  const onClick = (ev) => {
    const chip = ev.target.closest('.chip');
    if (chip && !chip.disabled) {
      const t = chip.dataset.style;
      if (st.styles.has(t)) st.styles.delete(t); else st.styles.add(t);
      apply(); writeUrl();
      $(`.chip[data-style="${CSS.escape(t)}"]`, root)?.focus();
      return;
    }
    if (ev.target.closest('#fav')) { st.fav = !st.fav; apply(); writeUrl(); return; }
    if (ev.target.closest('#clear1, #clear2')) { clear(); return; }
    if (ev.target.closest('#sheet-btn')) { setSheet(true); return; }
    if (ev.target.closest('#sheet-done, #backdrop-sheet')) { setSheet(false); }
  };
  function setSheet(open) {
    const tb = $('#toolbar', root);
    if (!tb) return;
    tb.classList.toggle('sheet-open', open);
    $('#sheet-btn', root).setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('no-scroll', open && window.matchMedia('(max-width: 767px)').matches);
  }
  root.addEventListener('click', onClick);
  const onChange = (ev) => {
    if (ev.target.id === 'origin') { st.origin = ev.target.value; apply(); writeUrl(); }
    else if (ev.target.id === 'sort') { st.sort = ev.target.value; apply(); writeUrl(); }
  };
  root.addEventListener('change', onChange);
  const onInput = debounce((ev) => {
    if (ev.target.id !== 'q') return;
    st.q = ev.target.value;
    apply(); writeUrl();
  }, 150);
  root.addEventListener('input', onInput);
  const onKey = (ev) => { if (ev.key === 'Escape') setSheet(false); };
  document.addEventListener('keydown', onKey);

  return {
    sameTarget: (n) => n.cat === cat && n.sub === sub,
    update(n) { readParams(n.params); apply(false); ctx.state.lastShelf = location.hash; },
    unmount() {
      root.removeEventListener('click', onClick);
      root.removeEventListener('change', onChange);
      root.removeEventListener('input', onInput);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', fades);
      document.body.classList.remove('no-scroll');
    },
  };
}
