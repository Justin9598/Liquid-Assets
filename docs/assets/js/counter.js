// Counter displays on the wide plate (Plan 07 section 4): the 5 newest drinks on the left, the 5 picks for the current
// Japanese season on the right. The build decides the picks (shelf.json `counter`); the page only chooses the season
// from the visitor's month. Bottles stand on the counter top and are larger than the shelf bottles.
import { getSections, img } from './data.js';
import { DEFAULT_LABEL, motifFor, shellOf } from './labels.js';
import { esc } from './util.js';

const pct = (v) => `${+(v * 100).toFixed(3)}%`;
export const SEASONS = ['spring', 'summer', 'autumn', 'winter'];
export const SEASON_NAMES = { spring: 'Spring', summer: 'Summer', autumn: 'Autumn', winter: 'Winter' };

/** Japanese season from the month: Spring Mar to May, Summer Jun to Aug, Autumn Sep to Nov, Winter Dec to Feb.
 * `?season=winter` forces one, for checking the other three. */
export function seasonNow(q, date = new Date()) {
  const forced = q?.get('season');
  if (SEASONS.includes(forced)) return forced;
  const m = date.getMonth();
  return m >= 2 && m <= 4 ? 'spring' : m >= 5 && m <= 7 ? 'summer' : m >= 8 && m <= 10 ? 'autumn' : 'winter';
}

const centre = (z) => (z.x0 + z.x1) / 2;

/** The slate in the middle of the counter: absolute box over the centre zone. */
export const slateStyle = (C) => `left:${pct(centre(C.slate))};top:${pct(C.slateY)};width:${pct(C.slate.x1 - C.slate.x0)}`;

/** The bottles of a counter group (shared by the first draw and the later swaps when a subcategory is chosen). */
export const rowHTML = (items, ix, art, own = null) => items.map((it) => bottleHTML(it, ix, art, own)).join('');

/** `own`: the open category's key. A bottle from another category then names its own category on its hover tag (Plan 14 section 3.1). */
function bottleHTML(it, ix, art, own) {
  const cat = ix.cats.get(it.category);
  const catName = cat ? cat.name : it.category;
  const def = DEFAULT_LABEL[it.category] || {};
  const shape = shellOf(it);
  const a = art(shape, { label: it.label && img(it.label), native: def.native, name: def.name, motif: motifFor(it.category, it.sub) });
  const other = own && it.category !== own ? `<span class="cb-cat">${esc(catName)}</span>` : '';
  const tag = `<span class="cb-tag chalkboard chalkboard--s" aria-hidden="true"><span class="chalk">${esc(it.name)}${other}</span></span>`;
  const body = `<span class="cb-art">${a}</span>${tag}`;
  // Phase 1: no drink pages yet, so a press says so on the slate (Plan 07 section 4.1)
  if (!getSections().drinks) {
    return `<li class="cb-cell"><button type="button" class="cbottle" data-drink-soon data-name="${esc(it.name)}" data-cat="${esc(catName)}" aria-label="${esc(it.name)}, ${esc(catName)}. Its page opens soon.">${body}</button></li>`;
  }
  return `<li class="cb-cell"><a class="cbottle" href="#/drink/${esc(it.id)}" aria-label="${esc(it.name)}, ${esc(catName)}">${body}</a></li>`;
}

function groupHTML(id, title, zone, C, items, ix, art, tabs) {
  const top = C.baseY - C.bottleH;
  const style = `left:${pct(zone.x0)};width:${pct(zone.x1 - zone.x0)};top:${pct(top)};height:${pct(C.bottleH)}`;
  const list = `<ul class="cg-row">${rowHTML(items, ix, art)}</ul>`;
  if (tabs) {                                   // phones: one group at a time behind a tab
    return `<section class="cgroup cg-${id}" id="cg-${id}" role="tabpanel" aria-labelledby="tab-${id}"${id === 'new' ? '' : ' hidden'} style="${style}">${list}</section>`;
  }
  return `<section class="cgroup cg-${id}" id="cg-${id}" aria-labelledby="cg-${id}-h" style="${style}">${list}</section>
<button type="button" class="placard chalkboard chalkboard--m" id="cg-${id}-h" data-view="${id === 'new' ? 'new' : 'season'}" style="left:${pct(centre(zone))};top:${pct(C.slateY)}"><span class="chalk">${esc(title)}</span><span class="in" hidden></span></button>`;
}

/** Both counter groups. Wide: two groups with placards. Tall: one group at a time behind two small tabs. */
export function countersHTML(P, counter, season, ix, art, tabs = false) {
  const C = P.counter;
  if (!C || !counter) return '';
  const n = (counter.newArrivals || []).slice(0, 5);                 // the counter's own set: the first 5 of each longer list
  const s = ((counter.inSeason || {})[season] || []).slice(0, 5);
  const html = groupHTML('new', 'New arrivals', C.new, C, n, ix, art, tabs)
    + groupHTML('season', `In season: ${SEASON_NAMES[season]}`, C.season, C, s, ix, art, tabs);
  if (!tabs) return html;
  return html + `<div class="ctabs" role="tablist" aria-label="Counter" style="left:${pct(C.new.x0)};top:${pct(C.tabsY)}">
  <button type="button" role="tab" id="tab-new" class="ctab chalkboard chalkboard--m" data-tab="new" aria-selected="true" aria-controls="cg-new" tabindex="0"><span class="chalk">New</span><span class="in" hidden></span></button>
  <button type="button" role="tab" id="tab-season" class="ctab chalkboard chalkboard--m" data-tab="season" aria-selected="false" aria-controls="cg-season" aria-label="In season: ${esc(SEASON_NAMES[season])}" tabindex="-1"><span class="chalk">In season</span><span class="in" hidden></span></button>
</div>`;
}

/** Wire the New / In season tabs (arrow keys, Home and End move between them). `onTab` runs on every pick. */
export function mountTabs(root, { onTab } = {}) {
  const list = root.querySelector('.ctabs');
  if (!list) return { destroy() {} };
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const pick = (t, focus) => {
    tabs.forEach((x) => {
      const on = x === t;
      x.setAttribute('aria-selected', String(on));
      x.tabIndex = on ? 0 : -1;
      root.querySelector(`#cg-${x.dataset.tab}`).hidden = !on;
    });
    if (focus) t.focus();
    onTab?.(t.dataset.tab);
  };
  const onClick = (ev) => { const t = ev.target.closest('[role="tab"]'); if (t) pick(t, false); };
  const onKey = (ev) => {
    const i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    const to = ev.key === 'ArrowRight' ? tabs[(i + 1) % tabs.length] : ev.key === 'ArrowLeft' ? tabs[(i - 1 + tabs.length) % tabs.length]
      : ev.key === 'Home' ? tabs[0] : ev.key === 'End' ? tabs[tabs.length - 1] : null;
    if (to) { ev.preventDefault(); pick(to, true); }
  };
  list.addEventListener('click', onClick);
  list.addEventListener('keydown', onKey);
  return { destroy() { list.removeEventListener('click', onClick); list.removeEventListener('keydown', onKey); } };
}

/** The wide plate is scaled to cover the viewport, so a screen narrower than the plate crops its left and right edges.
 * This keeps the counter's zones inside what is visible: groups start inside the left edge, the burger stays inside the
 * right edge, and the In season group makes room for it. Zones are plate fractions (scene.json); the result is applied as
 * inline left and width so nothing depends on the viewport at build time. */
export function placeCounter(root, P, burgerRatio) {
  const C = P.counter;
  const cover = root.querySelector('.cover');
  if (!C || !cover) return;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const coverW = Math.max(vw, vh * P.ratio);
  const m = Math.max(0, (coverW - vw) / 2 / coverW);
  const pad = 0.012;
  const tabs = C.mode === 'tabs';
  const set = (el, left, width) => {
    if (!el) return;
    el.style.left = pct(left);
    if (width != null) el.style.width = pct(width);
  };
  const nx0 = Math.min(Math.max(C.new.x0, m + pad), C.new.x1 - 0.08);
  let sx1 = tabs ? C.new.x1 : C.season.x1;
  const bz = C.burger;
  const anchor = root.querySelector('.burger-anchor');
  if (anchor && burgerRatio) {
    const half = (bz.h * burgerRatio) / P.ratio / 2;
    const cx = Math.min((bz.x0 + bz.x1) / 2, 1 - m - pad - half);
    set(anchor, cx);
    set(root.querySelector('.burger-tag'), cx);
    sx1 = Math.min(sx1, cx - half - 0.01);
  }
  if (tabs) {
    set(root.querySelector('.cg-new'), nx0, sx1 - nx0);
    set(root.querySelector('.cg-season'), nx0, sx1 - nx0);
    set(root.querySelector('.ctabs'), (nx0 + sx1) / 2);
    return;
  }
  set(root.querySelector('.cg-new'), nx0, C.new.x1 - nx0);
  set(root.querySelector('#cg-new-h'), (nx0 + C.new.x1) / 2);
  const sx0 = C.season.x0;
  set(root.querySelector('.cg-season'), sx0, Math.max(sx1 - sx0, 0.1));
  set(root.querySelector('#cg-season-h'), (sx0 + Math.max(sx1, sx0 + 0.1)) / 2);
}
