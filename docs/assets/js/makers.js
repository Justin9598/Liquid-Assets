// Makers index (Plan 04 section 5, looks from Plan 08 section 4.4): a title board, a map board with the controls, and a grid of
// small blackboards, one per maker, grouped by country.
import { board, headBoard, pageHTML } from './chrome.js';
import { getJSON } from './data.js';
import { icon } from './icons.js';
import { insertMap } from './map.js';
import { makerTile } from './producer.js';
import { $, $$, buildHash, debounce, esc, fold, plural, reducedMotion, regionKey, replaceHash, setTitle, slug } from './util.js';

const SORTS = { az: 'A to Z', most: 'Most drinks', region: 'Region' };

export async function mount(root, ctx) {
  setTitle('The Makers');
  const producers = await getJSON('producers.json');
  const byName = (a, b) => fold(a.name).localeCompare(fold(b.name)) || a.key.localeCompare(b.key);

  const countryCounts = new Map();
  for (const p of producers) if (p.country) countryCounts.set(p.country, (countryCounts.get(p.country) || 0) + 1);
  const countries = [...countryCounts.keys()].sort((a, b) => (a === 'Japan' ? -1 : b === 'Japan' ? 1 : countryCounts.get(b) - countryCounts.get(a) || a.localeCompare(b)));
  const regionStats = new Map(); // regionKey -> { name, makers, drinks }
  for (const p of producers) {
    if (p.country !== 'Japan' || !p.region) continue;
    const k = regionKey(p.region);
    const r = regionStats.get(k) || { name: p.region, makers: 0, drinks: 0 };
    r.makers += 1; r.drinks += p.drinkCount;
    regionStats.set(k, r);
  }

  const elsewhere = countries.filter((c) => c !== 'Japan');
  const title = board(`<h1 class="t-title" tabindex="-1">The Makers</h1>
  <p class="t-data" style="margin-top:10px">${esc(plural(producers.length, 'producer'))} · ${esc(plural(countries.length, 'country', 'countries'))}</p>`, 'title-board');
  const mapBoard = `<div class="m-top">${board(`<div class="map-chalk" id="mapbox-wrap"><div id="mapbox"></div></div>
    <p class="t-body" id="map-tip" role="status" aria-live="polite">Pick a prefecture to filter the list.</p>`, 'map-board', 'aria-label="Map of Japan"')}
${board(`    <div class="m-controls">
      <label class="search"><span class="sr-only">Search makers</span><input class="chalk-input" type="search" id="mq" placeholder="Search makers, native names, brands" autocomplete="off"></label>
      <label class="field"><span>Country</span><select class="chalk-input" id="mcountry"><option value="">All</option>${countries.map((c) => `<option value="${esc(slug(c))}">${esc(c)} (${countryCounts.get(c)})</option>`).join('')}</select></label>
      <label class="field"><span>Sort</span><select class="chalk-input" id="msort">${Object.entries(SORTS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></label>
    </div>
    ${elsewhere.length ? `<div class="elsewhere"><span class="t-data lead">Elsewhere:</span>${elsewhere.map((c) => `<a class="chalkboard chalkboard--s btn-s" href="${esc(buildHash(['makers'], { country: slug(c) }))}" data-country="${esc(slug(c))}"><span class="chalk">${esc(c)} <span class="ct">${countryCounts.get(c)}</span></span></a>`).join('')}</div>` : ''}
    <p class="region-chip" id="region-chip"></p>
    <p class="t-data" id="mcount" aria-live="polite"></p>`, 'controls-board m-side', 'aria-label="Filters"')}
</div>`;
  root.innerHTML = pageHTML({ crumbs: [{ label: 'Makers' }], cls: 'makers-page', boards: `${title}${mapBoard}<div class="boards-list" id="mlist"></div>` });

  const st = { q: '', country: '', region: '', sort: 'az' };
  const countrySlugs = new Map(countries.map((c) => [slug(c), c]));
  function read(params) {
    st.q = params.get('q') || '';
    const c = params.get('country') || '';
    st.country = countrySlugs.has(c) ? c : '';
    const r = params.get('region') || '';
    st.region = regionStats.has(r) ? r : '';
    if (st.region) st.country = 'japan';
    const so = params.get('sort');
    st.sort = SORTS[so] ? so : 'az';
  }

  function matches(p) {
    if (st.country && slug(p.country || '') !== st.country) return false;
    if (st.region && regionKey(p.region || '') !== st.region) return false;
    if (st.q) {
      const hay = fold([p.name, p.native, ...(p.brands || [])].filter(Boolean).join(' '));
      if (!fold(st.q).split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  }
  const sorters = {
    az: byName,
    most: (a, b) => b.drinkCount - a.drinkCount || byName(a, b),
    region: (a, b) => fold(a.region || '￿').localeCompare(fold(b.region || '￿')) || byName(a, b),
  };

  function writeUrl() {
    replaceHash(buildHash(['makers'], { country: st.country, region: st.region, sort: st.sort !== 'az' ? st.sort : '', q: st.q.trim() }));
  }

  function paintMap() {
    $$('.jp-map [data-key]', root).forEach((el) => el.classList.toggle('sel', el.dataset.key === st.region));
  }

  function render(announceIt = true) {
    const list = producers.filter(matches);
    const groupsMap = new Map();
    for (const p of list) {
      const k = p.country || 'Elsewhere';
      if (!groupsMap.has(k)) groupsMap.set(k, []);
      groupsMap.get(k).push(p);
    }
    const order = [...groupsMap.keys()].sort((a, b) => (a === 'Japan' ? -1 : b === 'Japan' ? 1 : groupsMap.get(b).length - groupsMap.get(a).length || a.localeCompare(b)));
    const el = $('#mlist', root);
    el.innerHTML = order.map((k) => {
      const items = groupsMap.get(k).sort(sorters[st.sort]);
      return `<section class="country-group">${headBoard(`${esc(k)} <span class="n">${items.length}</span>`)}<div class="tile-grid">${items.map((p) => makerTile(p)).join('')}</div></section>`;
    }).join('') || `<div class="chalkboard chalkboard--xl nothing"><h2 class="t-head">No makers match.</h2></div>`;
    $('#mcount', root).textContent = `Showing ${list.length} of ${producers.length}`;
    const mq = $('#mq', root);
    if (mq.value !== st.q) mq.value = st.q;
    $('#mcountry', root).value = st.country;
    $('#msort', root).value = st.sort;
    const chip = $('#region-chip', root);
    chip.innerHTML = st.region ? `<button type="button" class="chalkboard chalkboard--s btn-s" id="clear-region" aria-label="Remove filter ${esc(regionStats.get(st.region).name)}"><span class="chalk">${esc(regionStats.get(st.region).name)} ${icon('x', 14)}</span></button>` : '';
    paintMap();
  }

  read(ctx.params);
  render(false);

  // ---- map ---------------------------------------------------------------------------------------------------
  const tip = $('#map-tip', root);
  const svg = await insertMap($('#mapbox', root), { label: 'Map of Japan. The list beside it does the same job.' });
  if (svg) {
    const dotsG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    dotsG.setAttribute('class', 'dots');
    svg.appendChild(dotsG);
    for (const el of $$('[data-key]', svg)) {
      const r = regionStats.get(el.dataset.key);
      if (!r) continue;
      el.classList.add('has');
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', `${r.name}, ${plural(r.drinks, 'drink')}, ${plural(r.makers, 'maker')}`);
      const b = el.getBBox();
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', (b.x + b.width / 2).toFixed(1));
      c.setAttribute('cy', (b.y + b.height / 2).toFixed(1));
      c.setAttribute('r', (3 + Math.sqrt(r.drinks) * 1.5).toFixed(1));
      dotsG.appendChild(c);
    }
    paintMap();
  } else {
    $('#mapbox-wrap', root).remove();
    $('.m-top', root).style.gridTemplateColumns = 'minmax(0, 1fr)';
    $('.map-board', root)?.remove();
    tip.remove();
  }
  const showTip = (el) => {
    const r = regionStats.get(el.dataset.key);
    if (r && tip.isConnected) tip.textContent = `${r.name} · ${plural(r.drinks, 'drink')} · ${plural(r.makers, 'maker')}`;
  };
  const toggleRegion = (el) => {
    const k = el.dataset.key;
    st.region = st.region === k ? '' : k;
    st.country = st.region ? 'japan' : st.country;
    render(); writeUrl();
    if (window.innerWidth < 768) $('#mcount', root)?.scrollIntoView({ block: 'center', behavior: reducedMotion() ? 'auto' : 'smooth' });   // the list's count comes into view
  };

  // ---- events ------------------------------------------------------------------------------------------------
  const onClick = (ev) => {
    const area = ev.target.closest('.jp-map .has');
    if (area) { toggleRegion(area); return; }
    if (ev.target.closest('#clear-region')) { st.region = ''; render(); writeUrl(); return; }
    const link = ev.target.closest('a[data-country]');
    if (link) { ev.preventDefault(); st.country = link.dataset.country; st.region = ''; render(); writeUrl(); }
  };
  root.addEventListener('click', onClick);
  const onKey = (ev) => {
    const area = ev.target.closest?.('.jp-map .has');
    if (area && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); toggleRegion(area); }
  };
  root.addEventListener('keydown', onKey);
  const onOver = (ev) => { const a = ev.target.closest?.('.jp-map .has'); if (a) showTip(a); };
  root.addEventListener('mouseover', onOver);
  root.addEventListener('focusin', onOver);
  const onChange = (ev) => {
    if (ev.target.id === 'mcountry') { st.country = ev.target.value; if (st.country !== 'japan') st.region = ''; render(); writeUrl(); }
    else if (ev.target.id === 'msort') { st.sort = ev.target.value; render(); writeUrl(); }
  };
  root.addEventListener('change', onChange);
  const onInput = debounce((ev) => { if (ev.target.id === 'mq') { st.q = ev.target.value; render(); writeUrl(); } }, 150);
  root.addEventListener('input', onInput);

  return {
    sameTarget: () => true,
    update(n) { read(n.params); render(false); },
    unmount() {
      root.removeEventListener('click', onClick);
      root.removeEventListener('keydown', onKey);
      root.removeEventListener('mouseover', onOver);
      root.removeEventListener('focusin', onOver);
      root.removeEventListener('change', onChange);
      root.removeEventListener('input', onInput);
    },
  };
}
