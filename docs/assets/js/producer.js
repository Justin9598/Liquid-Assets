// Producer page (Plan 04, looks from Plan 08 section 4.3): a title board with their bottles standing on its ledge, a Facts board
// with the map drawn in chalk, and their bottles on my shelf as cards.
import { cardHTML } from './cards.js';
import { board, emptyHTML, headBoard, pageHTML } from './chrome.js';
import { getJSON } from './data.js';
import { icon } from './icons.js';
import { addRing, insertMap } from './map.js';
import { drinkShell } from './shells.js';
import { $, esc, plural, regionKey, setTitle } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');

/** A small blackboard for a maker: name, place and the number of drinks in a chalk circle. Used on the Makers index and in
 * the Related and More from rows. */
export const makerTile = (p, relation) => `<a class="tile chalkboard chalkboard--l" href="#/producer/${encodeURIComponent(p.key)}">
  <span class="nm">${esc(p.name)}</span>
  <span class="loc">${esc(relation || [p.region, p.country].filter(Boolean).join(', '))}</span>
  ${p.drinkCount != null ? `<span class="n" aria-label="${plural(p.drinkCount, 'drink')}">${p.drinkCount}</span>` : ''}
  ${p.favourites ? `<span class="star" aria-hidden="true">${icon('star-fill', 14)}</span><span class="sr-only">Has a favourite</span>` : ''}
</a>`;

export async function mount(root, ctx) {
  const { ix, key } = ctx;
  let p;
  try {
    p = await getJSON(`producers/${encodeURIComponent(key)}.json`);
  } catch {
    setTitle('Empty shelf');
    root.innerHTML = emptyHTML('This shelf is empty', [{ label: 'Makers', href: '#/makers' }, { label: 'Empty shelf' }]);
    return {};
  }
  const producers = await getJSON('producers.json');
  const pByKey = new Map(producers.map((x) => [x.key, x]));
  setTitle(p.name);

  const drinks = p.drinks.map((r) => ix.byId.get(r.id)).filter(Boolean);
  const nativeLang = p.native ? (isHangul(p.native) ? 'ko' : 'ja') : '';

  // ---- title board: the name, where, a tally, and their bottles on the ledge -------------------------------------
  const bottleOf = (d) => `<a class="ledge-item" href="#/drink/${encodeURIComponent(d.id)}" aria-label="${esc(d.name)}" title="${esc(d.name)}">${drinkShell(d, ix)}</a>`;
  const shown = drinks.slice(0, 12);
  const bottles = shown.map(bottleOf).join('')
    + (drinks.length > 12 ? `<span class="ledge-more desk chalk">+${drinks.length - 12} more</span>` : '')
    + (drinks.length > 6 ? `<span class="ledge-more phone chalk">+${drinks.length - 6} more</span>` : '');
  const locLine = [p.location || p.region, p.country, p.founded ? `Est. ${p.founded}` : ''].filter(Boolean).map(esc).join(' · ');
  const t = p.tally;
  const tally = [plural(t.drinks, 'drink'), plural(t.categories, 'category', 'categories')];
  if (t.favourites > 0) tally.push(plural(t.favourites, 'favourite'));
  if (t.timesHad > t.drinks) tally.push(`had ${t.timesHad} times`);

  const title = board(`<h1 class="t-title" tabindex="-1">${esc(p.name)}${p.native ? ` <span class="native" lang="${nativeLang}">${esc(p.native)}</span>` : ''}</h1>
  ${locLine ? `<p class="t-data">${locLine}</p>` : ''}
  <p class="t-data">${tally.map(esc).join(' · ')}</p>
  <div class="ledge-row">${bottles}</div><i class="tray" aria-hidden="true"></i>`, 'title-board has-tray');

  // ---- the facts, with the map -------------------------------------------------------------------------------
  const facts = [];
  const add = (k, v) => { if (v) facts.push(`<div class="spec-row"><dt>${k}</dt><dd><span class="val">${v}</span></dd></div>`); };
  add('Location', esc(p.location || p.region || ''));
  add('Country', esc(p.country || ''));
  add('Founded', p.founded ? esc(p.founded) : '');
  add('Brands', p.brands.length ? esc(p.brands.join(', ')) : '');
  add('Master brewer', esc(p.master || ''));
  add('Website', p.website ? `<a class="chalk-link site" href="${esc(p.website)}" title="${esc(p.website)}" target="_blank" rel="noopener noreferrer"><span class="host">${esc(hostOf(p.website) || p.website)}</span>${icon('arrow-up-right', 14)}</a>` : '');
  const wantsMap = p.country === 'Japan' && !!p.region;
  const factsBoard = board(`<div class="facts-grid${wantsMap ? '' : ' nomap'}" id="facts-grid">
  <div><h2 class="t-head" id="h-facts">The Facts</h2><dl class="spec">${facts.join('')}</dl></div>
  ${wantsMap ? '<div class="map-chalk" id="locator"></div>' : ''}
</div>`, 'facts', 'aria-labelledby="h-facts"');
  const storyBoard = p.about.length ? board(`<h2 class="t-head" id="h-story">The Story</h2>
  ${p.about.map((x) => `<p class="t-body">${esc(x)}</p>`).join('')}
  ${p.sources.length ? `<p class="t-small sources">Sources: ${sourceLinks(p.sources)}</p>` : ''}`, 'story', 'aria-labelledby="h-story"') : '';

  // ---- their bottles on my shelf -----------------------------------------------------------------------------
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
    const head = multi ? headBoard(esc(ix.cats.get(k)?.name || 'Other'), 'group-head', 'h3') : '';
    return `${head}<div class="grid${groups.get(k).length <= 3 ? ' few' : ''}">${cs}</div>`;
  }).join('');
  const shelf = `${headBoard('Their bottles on my shelf')}${cards}`;

  const rowOf = (heading, tiles) => (tiles ? `${headBoard(heading)}<div class="tile-row">${tiles}</div>` : '');
  const related = p.related.map((r) => {
    const rec = pByKey.get(r.key);
    return rec ? makerTile(rec, r.relationship || '') : '';
  }).join('');
  const region = p.moreFromRegion.map((k) => pByKey.get(k)).filter(Boolean).map((x) => makerTile(x)).join('');

  const pair = storyBoard ? `<div class="pair">${factsBoard}${storyBoard}</div>` : factsBoard;
  root.innerHTML = pageHTML({
    crumbs: [{ label: 'Makers', href: '#/makers' }, { label: p.name }], cls: 'producer-page',
    boards: `${title}${pair}${shelf}${rowOf('Related makers', related)}${rowOf(`More from ${esc(p.region || p.location || '')}`, region)}`,
  });

  if (wantsMap) {
    const loc = $('#locator', root);
    const svg = await insertMap(loc, { label: `Map of Japan with ${p.region} highlighted` });
    const path = svg && svg.querySelector(`path[data-key="${CSS.escape(regionKey(p.region))}"]`);
    if (path) {
      path.classList.add('hl');
      addRing(svg, path);
    } else {
      loc.remove();                                   // a map that cannot place the prefecture is left out, never shown unmarked
      $('#facts-grid', root)?.classList.add('nomap');
    }
  }
  return {};
}

/** Each host once, in source order (the official site first), linking to its first URL (Plan 09 section 11.4). */
function sourceLinks(urls) {
  const seen = new Map();
  urls.forEach((u, i) => { const h = hostOf(u) || `source ${i + 1}`; if (!seen.has(h)) seen.set(h, u); });
  return [...seen].map(([h, u]) => `<a class="chalk-link" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(h)} ${icon('arrow-up-right', 12)}</a>`).join(' · ');
}

function hostOf(u) {
  try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; }
}
