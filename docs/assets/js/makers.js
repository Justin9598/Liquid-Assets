// Makers index (Plan 04 section 5, looks from Plan 08 section 4.4, the map from Plan 14 section 5): a title board, a map board with
// pins and a chalk breadcrumb, the filters, and a grid of small blackboards, one per maker, grouped by country.
// The map and the list move together: the place chosen on the map filters the list, and the list's filters move the map.
import { board, headBoard, pageHTML } from './chrome.js';
import { getJSON } from './data.js';
import { icon } from './icons.js';
import { MapStage, loadCountry, loadWorld, pinColor, project } from './map.js';
import { buildTree, chainOf, countryNode, crumbs, findNode, provinceNode, smallestHolding, tally, upFrom, viewOf } from './maptree.js';
import { makerTile } from './producer.js';
import { $, buildHash, debounce, esc, fold, plural, regionKey, replaceHash, setTitle, slug } from './util.js';

const SORTS = { az: 'A to Z', most: 'Most drinks', region: 'Region' };
const WORLD_BOX = (() => { const a = project(-168, 76); const b = project(180, -57); return [a[0], a[1], b[0], b[1]]; })();

export async function mount(root, ctx) {
  const { ix } = ctx;
  setTitle('The Makers');
  const producers = await getJSON('producers.json');
  const byName = (a, b) => fold(a.name).localeCompare(fold(b.name)) || a.key.localeCompare(b.key);

  const countryCounts = new Map();
  const countryName = new Map();
  for (const p of producers) if (p.country) { const id = p.cid || slug(p.country); countryCounts.set(id, (countryCounts.get(id) || 0) + 1); countryName.set(id, p.country); }
  const countries = [...countryCounts.keys()].sort((a, b) => (a === 'japan' ? -1 : b === 'japan' ? 1 : countryCounts.get(b) - countryCounts.get(a) || countryName.get(a).localeCompare(countryName.get(b))));
  const tree = buildTree(producers);
  for (const p of producers) p._path = p.lat != null ? chainOf(p).map((c) => c.id).join('/') : '';
  const catName = (k) => ix.cats.get(k)?.name || k;

  const title = board(`<h1 class="t-title" tabindex="-1">The Makers</h1>
  <p class="t-data" style="margin-top:10px">${esc(plural(producers.length, 'producer'))} · ${esc(plural(countries.length, 'country', 'countries'))}</p>`, 'title-board');
  const mapBoard = `<div class="m-top">${board(`<div class="mm-bar"><button type="button" class="chalkboard chalkboard--s btn-s mm-back" id="mm-back"><span class="chalk">Back</span></button><nav class="mm-crumbs" aria-label="Place on the map"><ol id="mm-crumbs"></ol></nav></div>
    <div id="mapbox" class="mm-host"></div>
    <div class="mm-legend" id="mm-legend" aria-label="Pin colours"></div>
    <p class="t-body mm-info" id="map-info" aria-live="polite"></p>`, 'map-board', 'aria-label="Map of the makers. The list below does the same job."')}
${board(`    <div class="m-controls">
      <label class="search"><span class="sr-only">Search makers</span><input class="chalk-input" type="search" id="mq" placeholder="Search makers, native names, brands" autocomplete="off"></label>
      <label class="field"><span>Country</span><select class="chalk-input" id="mcountry"><option value="">All</option>${countries.map((c) => `<option value="${esc(c)}">${esc(countryName.get(c))} (${countryCounts.get(c)})</option>`).join('')}</select></label>
      <label class="field"><span>Sort</span><select class="chalk-input" id="msort">${Object.entries(SORTS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></label>
    </div>
    <p class="region-chip" id="region-chip"></p>
    <p class="t-data" id="mcount" aria-live="polite"></p>`, 'controls-board m-side', 'aria-label="Filters"')}
</div>`;
  root.innerHTML = pageHTML({ crumbs: [{ label: 'Makers' }], cls: 'makers-page', boards: `${title}${mapBoard}<div class="boards-list" id="mlist"></div>` });

  const st = { q: '', at: '', sort: 'az' };
  function read(params) {
    st.q = params.get('q') || '';
    let at = params.get('at') || '';
    if (at && !findNode(tree, at)) at = '';
    const country = params.get('country') || '';
    const region = params.get('region') || '';
    if (!at && region) at = provinceNode(tree, 'japan', regionKey(region))?.path || (countryNode(tree, 'japan')?.path ?? '');       // the old ?region= and ?country= links
    else if (!at && country) at = countryNode(tree, country)?.path || '';
    st.at = at;
    const so = params.get('sort');
    st.sort = SORTS[so] ? so : 'az';
  }

  const inPlace = (p, at) => !at || p._path === at || p._path.startsWith(`${at}/`);
  function matchesText(p) {
    if (!st.q) return true;
    const hay = fold([p.name, p.native, ...(p.brands || [])].filter(Boolean).join(' '));
    return fold(st.q).split(/\s+/).every((w) => hay.includes(w));
  }
  const filtered = () => producers.filter((p) => inPlace(p, st.at) && matchesText(p));
  const sorters = {
    az: byName,
    most: (a, b) => b.drinkCount - a.drinkCount || byName(a, b),
    region: (a, b) => fold(a.region || '￿').localeCompare(fold(b.region || '￿')) || byName(a, b),
  };
  function writeUrl() {
    replaceHash(buildHash(['makers'], { at: st.at, sort: st.sort !== 'az' ? st.sort : '', q: st.q.trim() }));
  }
  const atNode = () => findNode(tree, st.at) || tree;
  /** The place the map shows: the place chosen, or while searching the smallest place holding every match. */
  const shownNode = (list) => (st.q.trim() ? smallestHolding(tree, list.filter((p) => p.lat != null)) : atNode());

  // ---- the list, the count, the chip, the breadcrumb, the legend, the info line -------------------------------------------
  function renderText(list, node) {
    const groupsMap = new Map();
    for (const p of list) {
      const k = p.country || 'Elsewhere';
      if (!groupsMap.has(k)) groupsMap.set(k, []);
      groupsMap.get(k).push(p);
    }
    const order = [...groupsMap.keys()].sort((a, b) => (a === 'Japan' ? -1 : b === 'Japan' ? 1 : groupsMap.get(b).length - groupsMap.get(a).length || a.localeCompare(b)));
    $('#mlist', root).innerHTML = order.map((k) => {
      const items = groupsMap.get(k).sort(sorters[st.sort]);
      return `<section class="country-group">${headBoard(`${esc(k)} <span class="n">${items.length}</span>`)}<div class="tile-grid">${items.map((p) => makerTile(p)).join('')}</div></section>`;
    }).join('') || `<div class="chalkboard chalkboard--xl nothing"><h2 class="t-head">No makers match.</h2></div>`;
    $('#mcount', root).textContent = plural(list.length, 'maker');
    const mq = $('#mq', root);
    if (mq.value !== st.q) mq.value = st.q;
    const at = atNode();
    const cNode = (() => { for (let n = at; n; n = n.parent) if (n.level === 'country') return n; return null; })();
    $('#mcountry', root).value = cNode ? cNode.id : '';
    $('#msort', root).value = st.sort;
    $('#region-chip', root).innerHTML = st.at ? `<button type="button" class="chalkboard chalkboard--s btn-s" id="clear-place" aria-label="Remove filter ${esc(at.name)}"><span class="chalk">${esc(at.name)} ${icon('x', 14)}</span></button>` : '';
    const trail = crumbs(node);
    $('#mm-crumbs', root).innerHTML = trail.map((n, i) => (i === trail.length - 1
      ? `<li aria-current="location"><span class="chalk">${esc(n.label)}</span></li>`
      : `<li><button type="button" class="mm-crumb" data-at="${esc(n.path)}"><span class="chalk">${esc(n.label)}</span></button></li>`)).join('');
    $('#mm-back', root).disabled = !node.parent;
    const t = tally(list);
    $('#map-info', root).innerHTML = `<b>${esc(node.parent ? node.name : 'Everywhere')}</b> · ${plural(t.makers, 'maker')} · ${plural(t.drinks, 'drink')} · ${plural(t.favourites, 'favourite')}`;
    const cats = [...ix.cats.keys()].filter((k) => list.some((p) => p.main === k));
    $('#mm-legend', root).innerHTML = cats.map((k) => `<span class="mm-key"><svg width="16" height="16" viewBox="-8 -8 16 16" aria-hidden="true" focusable="false"><circle r="6" fill="${pinColor(k)}"/><circle r="6" fill="url(#pin-gloss)"/><circle r="5.6" fill="none" stroke="#000" stroke-opacity=".38"/></svg>${esc(catName(k))}</span>`).join('');
  }

  // ---- the map -------------------------------------------------------------------------------------------------------
  const host = $('#mapbox', root);
  let stage = null;
  let world = null;
  let token = 0;
  let cardFor = null;
  try {
    world = await loadWorld();
    stage = new MapStage(host);
    stage.setWorld(world);
    host.insertAdjacentHTML('beforeend', '<div class="mm-card chalkboard" id="mm-card" hidden role="dialog" aria-label="Maker"></div>');
  } catch {
    $('.map-board', root)?.remove();
    $('.m-top', root).style.gridTemplateColumns = 'minmax(0, 1fr)';
  }

  const radiusFor = (n) => (n < 20 ? 13 : n < 60 ? 16 : 19);
  const centreOf = (list) => {
    const pts = list.filter((p) => p.lat != null).map((p) => project(p.lon, p.lat));
    return [pts.reduce((a, q) => a + q[0], 0) / pts.length, pts.reduce((a, q) => a + q[1], 0) / pts.length];
  };
  const makerItem = (p) => {
    const [x, y] = project(p.lon, p.lat);
    return { id: `m:${p.key}`, kind: 'maker', x, y, r: 9, color: pinColor(p.main), name: p.name, tag: false, key: p.key,
      aria: `${p.name}, ${p.location || p.region || p.country || ''}, open card` };
  };
  const groupItem = (g) => {
    const [x, y] = centreOf(g.producers);
    return { id: `g:${g.path}`, kind: 'group', x, y, r: radiusFor(g.producers.length), count: g.producers.length, name: g.name, tag: true, path: g.path,
      aria: `${g.name}, ${plural(g.producers.length, 'maker')}, zoom in` };
  };

  const closeCard = () => { const c = $('#mm-card', root); if (c) c.hidden = true; cardFor = null; };

  function openCard(btn, p) {
    const c = $('#mm-card', root);
    cardFor = p.key;
    const nativeLang = /[ᄀ-ᇿ㄰-㆏가-힯]/.test(p.native || '') ? 'ko' : 'ja';
    c.innerHTML = `<p class="nm">${esc(p.name)}</p>${p.native ? `<p class="nat" lang="${nativeLang}">${esc(p.native)}</p>` : ''}<p class="loc">${esc(p.location || [p.region, p.country].filter(Boolean).join(', '))}</p>
<p class="n">${esc(plural(p.drinkCount, 'drink'))}</p><a class="chalk-link" href="#/producer/${encodeURIComponent(p.key)}">Open maker ${icon('arrow-up-right', 14)}</a>`;
    c.hidden = false;
    const hr = host.getBoundingClientRect();
    const br = btn.getBoundingClientRect();
    const cw = c.offsetWidth;
    const ch = c.offsetHeight;
    let left = br.left - hr.left + br.width / 2 - cw / 2;
    left = Math.min(Math.max(left, 6), hr.width - cw - 6);
    let top = br.top - hr.top - ch - 6;
    if (top < 6) top = Math.min(br.bottom - hr.top + 6, hr.height - ch - 6);
    c.style.left = `${left}px`;
    c.style.top = `${Math.max(6, top)}px`;
    $('a', c).focus({ preventScroll: true });
  }

  /** Pixel padding that leaves room for the pins' heads above their spots and the name tags beside them. */
  const padding = () => (host.clientWidth < 520 ? { l: 36, r: 60, t: 60, b: 26 } : { l: 70, r: 100, t: 70, b: 30 });

  async function drawMap(list, node, animate) {
    const my = ++token;
    const view = st.q.trim() ? { kind: 'makers', node, makers: list.filter((p) => p.lat != null), groups: [] } : viewOf(node);
    host.dataset.at = st.at;
    host.dataset.level = node.level;
    host.dataset.kind = view.kind;
    host.dataset.ready = '0';
    closeCard();
    stage.fan = null;
    // which outlines: the countries with makers, then the chosen place
    const countryLevel = ['country', 'area', 'province'].includes(view.node.level);
    let data = null;
    if (countryLevel) {
      const cid = view.node.level === 'country' ? view.node.id : (() => { for (let n = view.node; n; n = n.parent) if (n.level === 'country') return n.id; return null; })();
      try { data = await loadCountry(cid); } catch { data = null; }
      if (my !== token) return;
    }
    stage.setCountry(data);
    const cids = [...new Set(view.node.producers.map((p) => p.cid))];
    const allCids = [...new Set(producers.map((p) => p.cid).filter(Boolean))];
    let provSel = [];
    if (data && view.node.level === 'province') provSel = [view.node.id];
    else if (data && view.node.level === 'area') provSel = [...new Set(view.node.producers.map((p) => p.prov))];
    // the countries with makers are hatched lightly above the country level; a country opened whole is hatched, and below it only the chosen provinces are
    const hatch = view.node.level === 'country' ? cids : [];
    stage.mark({ has: view.node.level === 'world' || !countryLevel ? allCids : [], sel: hatch, edge: view.node.level === 'world' ? [] : cids, provSel });
    stage.clearPins();
    // where to look
    const pad = padding();
    let spec;
    if (view.node.level === 'world' && view.kind === 'groups') spec = { box: WORLD_BOX, pad: { l: 10, r: 10, t: 24, b: 10 } };
    else {
      const pts = (view.kind === 'groups' ? view.node.producers : view.makers).filter((p) => p.lat != null).map((p) => project(p.lon, p.lat));
      if (view.node.level === 'province' && data) {                     // a province fills the view, outline and all
        const pv = data.provinces.find((x) => x.id === view.node.id);
        if (pv) pts.push([pv.bb[0], pv.bb[1]], [pv.bb[2], pv.bb[3]]);
      }
      if (!pts.length) pts.push(...(WORLD_BOX ? [[WORLD_BOX[0], WORLD_BOX[1]], [WORLD_BOX[2], WORLD_BOX[3]]] : []));
      const xs = pts.map((q) => q[0]);
      const ys = pts.map((q) => q[1]);
      spec = { box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], minW: 700, minH: 500, pad };
    }
    await stage.go(spec, animate);
    if (my !== token) return;
    const items = view.kind === 'groups' ? [...view.groups.map(groupItem), ...view.makers.map(makerItem)] : view.makers.map(makerItem);
    stage.setPins(items);
    host.dataset.pins = String(items.length);
    host.dataset.ready = '1';                       // the pins are drawn: tests wait on this
  }

  let busy = Promise.resolve();
  function render(animate = false) {
    const list = filtered();
    const node = shownNode(list);
    renderText(list, node);
    if (stage) busy = drawMap(list, node, animate);
    return busy;
  }

  function goTo(path) {
    st.at = path || '';
    if (st.at && !findNode(tree, st.at)) st.at = '';
    render(true);
    writeUrl();
  }

  read(ctx.params);
  render(false);
  if (stage) stage.onResize = () => render(false);

  // ---- events --------------------------------------------------------------------------------------------------------
  const pinById = (id) => {
    if (id.startsWith('g:')) return { group: findNode(tree, id.slice(2)) };
    if (id.startsWith('m:')) return { maker: producers.find((p) => p.key === id.slice(2)) };
    return { stack: id };
  };
  /** One level up. While searching it steps up from the place chosen, not from the place the search zoomed to. */
  const goUp = () => {
    const up = upFrom(st.q.trim() ? atNode() : shownNode(filtered()));
    if (up && (st.at || !st.q.trim())) goTo(up.path);
  };
  const onClick = (ev) => {
    const pin = ev.target.closest('.mm-pin');
    if (pin) {
      const hit = pinById(pin.dataset.id);
      if (hit.group) { goTo(hit.group.path); return; }
      if (hit.maker) { if (cardFor === hit.maker.key) closeCard(); else openCard(pin, hit.maker); return; }
      closeCard();
      stage.fan = stage.fan === hit.stack ? null : hit.stack;
      stage.setPins(stage.lastItems || []);
      return;
    }
    if (ev.target.closest('#mm-card')) return;
    if (ev.target.closest('.mm-stage') && (cardFor || stage?.fan)) { closeCard(); if (stage.fan) { stage.fan = null; stage.setPins(stage.lastItems || []); } return; }
    const crumb = ev.target.closest('.mm-crumb');
    if (crumb) { goTo(crumb.dataset.at); return; }
    if (ev.target.closest('#mm-back')) { goUp(); return; }
    if (ev.target.closest('#clear-place')) { goTo(''); }
  };
  root.addEventListener('click', onClick);
  const onKey = (ev) => {
    if (ev.key !== 'Escape' || ev.defaultPrevented || document.body.classList.contains('menu-open')) return;
    if (cardFor) { const k = cardFor; closeCard(); $(`.mm-pin[data-id="m:${CSS.escape(k)}"]`, root)?.focus(); ev.preventDefault(); return; }
    if (stage?.fan) { stage.fan = null; stage.setPins(stage.lastItems || []); ev.preventDefault(); return; }
    if (st.at && !st.q.trim()) { goUp(); ev.preventDefault(); }
  };
  document.addEventListener('keydown', onKey);
  const onChange = (ev) => {
    if (ev.target.id === 'mcountry') { const n = ev.target.value ? countryNode(tree, ev.target.value) : null; goTo(n ? n.path : ''); }
    else if (ev.target.id === 'msort') { st.sort = ev.target.value; render(); writeUrl(); }
  };
  root.addEventListener('change', onChange);
  const onInput = debounce((ev) => { if (ev.target.id === 'mq') { st.q = ev.target.value; render(true); writeUrl(); } }, 150);
  root.addEventListener('input', onInput);

  return {
    sameTarget: () => true,
    update(n) { read(n.params); render(false); },
    unmount() {
      token++;
      stage?.destroy();
      root.removeEventListener('click', onClick);
      document.removeEventListener('keydown', onKey);
      root.removeEventListener('change', onChange);
      root.removeEventListener('input', onInput);
    },
  };
}
