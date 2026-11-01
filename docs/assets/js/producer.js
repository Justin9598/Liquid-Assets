// Producer page: "The Makers" crate (Plan 04).
import { bottleSVG, motifFor, shapeFor } from './bottles.js';
import { cardHTML } from './cards.js';
import { emptyScene, topbar } from './chrome.js';
import { getJSON, img } from './data.js';
import { icon } from './icons.js';
import { insertMap } from './map.js';
import { $, $$, esc, plural, regionKey, setTitle } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');

const SUGIDAMA = `<svg class="sugidama" viewBox="0 0 60 120" aria-hidden="true" focusable="false">
<path d="M30 0V44" stroke="#6b4a2a" stroke-width="3"/>
<circle cx="30" cy="78" r="32" fill="#5b7a3a"/>
<g stroke="#3f5a26" stroke-width="2" stroke-linecap="round">${Array.from({ length: 28 }, (_, i) => {
    const a = (i / 28) * Math.PI * 2;
    return `<path d="M${(30 + Math.cos(a) * 20).toFixed(1)} ${(78 + Math.sin(a) * 20).toFixed(1)}L${(30 + Math.cos(a) * 33).toFixed(1)} ${(78 + Math.sin(a) * 33).toFixed(1)}"/>`;
  }).join('')}</g>
<circle cx="22" cy="68" r="7" fill="rgba(255,255,255,.14)"/>
</svg>`;

export const crateTile = (p, relation) => `<a class="crate-tile" href="#/producer/${encodeURIComponent(p.key)}">
  <span class="nm">${esc(p.name)}</span>
  <span class="loc">${esc(relation || [p.region, p.country].filter(Boolean).join(', '))}</span>
  ${p.drinkCount != null ? `<span class="n" aria-label="${plural(p.drinkCount, 'drink')}">${p.drinkCount}</span>` : ''}
  ${p.favourites ? `<span class="star" aria-hidden="true">${icon('star-fill', 12)}</span>` : ''}
</a>`;

export async function mount(root, ctx) {
  const { ix, key } = ctx;
  let p;
  try {
    p = await getJSON(`producers/${encodeURIComponent(key)}.json`);
  } catch {
    setTitle('Empty shelf');
    root.innerHTML = topbar([{ label: 'Makers', href: '#/makers' }, { label: 'Empty shelf' }]) + emptyScene('This shelf is empty');
    return {};
  }
  const producers = await getJSON('producers.json');
  const pByKey = new Map(producers.map((x) => [x.key, x]));
  setTitle(p.name);

  const drinks = p.drinks.map((r) => ix.byId.get(r.id)).filter(Boolean);
  const nativeLang = p.native ? (isHangul(p.native) ? 'ko' : 'ja') : '';

  // ---- crate hero -------------------------------------------------------------------------------------------
  const bottleOf = (d) => {
    const info = d.category && ix.subs.get(`${d.category}/${d.sub}`);
    const label = d.label ? img(d.label) : null;
    return `<a class="cb" href="#/drink/${encodeURIComponent(d.id)}" aria-label="${esc(d.name)}" title="${esc(d.name)}">${bottleSVG(shapeFor(d.category), {
      label, native: info?.sub.native, name: info?.sub.name, motif: motifFor(d.category, d.sub) })}</a>`;
  };
  const shown = drinks.slice(0, 12);
  const bottles = shown.map(bottleOf).join('')
    + (drinks.length > 12 ? `<span class="cb-more desk">+${drinks.length - 12}</span>` : '')
    + (drinks.length > 5 ? `<span class="cb-more phone">+${drinks.length - 5}</span>` : '');
  const sugi = p.country === 'Japan' && drinks.some((d) => d.category === 'sake');
  const locLine = [p.location || p.region, p.country, p.founded ? `Est. ${p.founded}` : ''].filter(Boolean).map(esc).join(' · ');

  // ---- tally ------------------------------------------------------------------------------------------------
  const t = p.tally;
  const tally = [plural(t.drinks, 'drink'), plural(t.categories, 'category', 'categories')];
  if (t.favourites > 0) tally.push(plural(t.favourites, 'favourite'));
  if (t.timesHad > t.drinks) tally.push(`had ${t.timesHad} times`);

  // ---- story and facts --------------------------------------------------------------------------------------
  const story = p.about.length ? `<section class="panel story" aria-labelledby="h-story"><h2 id="h-story">The Story</h2>
  <div class="prose dropcap">${p.about.map((x) => `<p>${esc(x)}</p>`).join('')}</div>
  ${p.sources.length ? `<p class="sources">Sources: ${p.sources.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(hostOf(u) || `source ${i + 1}`)} ${icon('arrow-up-right', 12)}</a>`).join(' · ')}</p>` : ''}</section>` : '';
  const facts = [];
  const add = (k, v) => { if (v) facts.push(`<div class="spec-row"><dt>${k}</dt><dd><span class="val">${v}</span></dd></div>`); };
  add('Location', esc(p.location || p.region || ''));
  add('Country', esc(p.country || ''));
  add('Founded', p.founded ? esc(p.founded) : '');
  add('Brands', p.brands.length ? esc(p.brands.join(', ')) : '');
  add('Master brewer', esc(p.master || ''));
  add('Website', p.website ? `<a href="${esc(p.website)}" target="_blank" rel="noopener noreferrer">${esc(hostOf(p.website) || p.website)} ${icon('arrow-up-right', 14)}</a>` : '');
  const mapBox = p.country === 'Japan' && p.region ? '<div class="locator" id="locator"></div>' : '';
  const factsPanel = `<section class="panel facts" aria-labelledby="h-facts"><h2 id="h-facts">The Facts</h2><dl class="spec">${facts.join('')}</dl>${mapBox}</section>`;

  // ---- their bottles on my shelf ----------------------------------------------------------------------------
  const catOrder = ix.shelf.categories.map((c) => c.key);
  const groups = new Map();
  for (const d of drinks) {
    const k = d.category || '_';
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(d);
  }
  const sortedKeys = [...groups.keys()].sort((a, b) => (catOrder.indexOf(a) + 100) % 100 - (catOrder.indexOf(b) + 100) % 100);
  const multi = sortedKeys.length > 1;
  let n = 0;
  const cards = sortedKeys.map((k) => {
    const cs = groups.get(k).map((d) => cardHTML(d, ix, { shelfLine: true, eager: n++ < 8 })).join('');
    const head = multi ? `<h3 class="group-h">${esc(ix.cats.get(k)?.name || 'Other')}</h3>` : '';
    return `${head}<div class="grid${groups.get(k).length <= 3 ? ' few' : ''}">${cs}</div>`;
  }).join('');

  const related = p.related.map((r) => {
    const rec = pByKey.get(r.key);
    return rec ? crateTile(rec, r.relationship || '') : '';
  }).join('');
  const region = p.moreFromRegion.map((k) => pByKey.get(k)).filter(Boolean).map((x) => crateTile(x)).join('');

  root.innerHTML = `<div class="producer-page">
<div class="wall"><div class="wall-in">
${topbar([{ label: 'Makers', href: '#/makers' }, { label: p.name }], '#/')}
<section class="crate-scene">
  <div class="crate-bottles">${bottles}</div>
  <div class="crate">
    <div class="crate-face">
      ${sugi ? `<span class="sugi-wrap">${SUGIDAMA}</span>` : ''}
      <h1 class="stencil" tabindex="-1">${esc(p.name)}</h1>
      ${p.native ? `<span class="seal" lang="${nativeLang}">${esc(p.native)}</span>` : ''}
      <p class="crate-loc">${locLine}</p>
    </div>
  </div>
</section>
</div><div class="counter-lip"></div></div>
<div class="page">
<p class="tally">${tally.map(esc).join(' · ')}</p>
<div class="panels producer-panels${story ? '' : ' wide'}">${p.about.length ? `${factsPanel}${story}` : factsPanel}</div>
<section class="stack" aria-labelledby="h-shelf"><h2 class="band-h" id="h-shelf">Their bottles on my shelf</h2>${cards}</section>
${related ? `<section class="stack" aria-labelledby="h-rel"><h2 class="band-h" id="h-rel">Related makers</h2><div class="tile-row">${related}</div></section>` : ''}
${region ? `<section class="stack" aria-labelledby="h-reg"><h2 class="band-h" id="h-reg">More from ${esc(p.region || p.location)}</h2><div class="tile-row">${region}</div></section>` : ''}
</div>
</div>`;

  if (mapBox) {
    const svg = await insertMap($('#locator', root), { label: `Map of Japan with ${p.region} highlighted` });
    if (svg) {
      const path = svg.querySelector(`[data-key="${CSS.escape(regionKey(p.region))}"]`);
      if (path) path.classList.add('hl');
      else $('#locator', root).remove();
    }
  }
  return {};
}

function hostOf(u) {
  try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; }
}
