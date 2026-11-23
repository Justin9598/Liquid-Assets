// The real map in chalk (Plan 17): MapLibre GL JS draws OpenStreetMap vector tiles from OpenFreeMap in our own style (assets/maps/
// chalk-style.json, made by build/tools/makestyle.py), and our overlays go on top: the hatched countries and provinces as map layers,
// and the pins, name tags and capital as the same HTML and SVG the SVG map uses. This file is loaded only by the Makers page and the
// maker pages; MapLibre itself is loaded on first use, as a dynamic import, from assets/vendor/maplibre-gl/ (self-hosted).
//
// GLStage has the same methods as MapStage in map.js (setWorld, setCountry, mark, boxOf, go, toPx, setPins ...), so makers.js and
// drawProvinceMap work with either. When the real map cannot run (no WebGL, the tiles or the style fail, no load within 8 s, or
// ?map=svg in the address) createGLStage resolves to null and the caller draws the SVG map, which is unchanged (Plan 17 section 8).
import { withVersion } from './data.js';
import { MapStage, drawProvinceMap, ensurePinDefs, unproject } from './map.js';
import { esc, reducedMotion } from './util.js';

export const MAPLIBRE_VERSION = '6.17.0';
const VENDOR = new URL('../vendor/maplibre-gl/', import.meta.url);
const LOAD_TIMEOUT = 8000;
const CHALK = '#f2ede4';
const GLOW = '#f4c27a';
const SLATE = '#262a28';
const IRON = '#1f1c1a';
const MAX_ZOOM = 14;                                       // OpenFreeMap's top zoom (Plan 17 section 6)
const WORLD = [[-170, -58], [180, 77]];                    // south-west, north-east: the world as the Makers map frames it
const EMPTY = { type: 'FeatureCollection', features: [] };
// The sea's polygons end at 180 degrees, and the coastline layer draws that edge as a line. When the copies of the world are on (Fiji
// lies across 180) the line would run through the middle of the view, so it is covered in the colour of the sea. Taveuni stands on
// 180 degrees (about 16.7 S), so the cover has a gap there, and its coast is not painted over.
const SEAM = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'MultiLineString', coordinates:
  [180, -180].flatMap((x) => [[[x, -85], [x, -17.4]], [[x, -16.0], [x, 85]]]) } }] };
const none = (ids) => (ids && ids.length ? ids : ['\u0000']);           // an empty list in a filter

const log = (why) => console.info(`Map: using the SVG map (${why})`);

// ---- can the real map run? ---------------------------------------------------------------------------------------------
function flag(name, params) {
  return new URLSearchParams(location.search).get(name) || (params && params.get && params.get(name)) || '';
}

let webgl = null;
export function hasWebGL() {
  if (webgl === null) {
    try {
      const c = document.createElement('canvas');
      const g = c.getContext('webgl2');
      webgl = !!g;
      g?.getExtension('WEBGL_lose_context')?.loseContext();
    } catch { webgl = false; }
  }
  return webgl;
}

/** { real: true } when the real map should be tried, else { real: false, why }. `?map=svg` (in the address or after the # route)
 * asks for the SVG map, for testing and for comparing. */
export function mapMode(params) {
  if (flag('map', params) === 'svg') return { real: false, why: 'the address asks for it: ?map=svg' };
  if (!hasWebGL()) return { real: false, why: 'this browser has no WebGL' };
  return { real: true };
}

// ---- loading MapLibre and the style ------------------------------------------------------------------------------------
let lib = null;
function loadLib() {
  if (!lib) {
    lib = (async () => {
      if (!document.querySelector('link[data-maplibre]')) {
        const sheets = [new URL(`maplibre-gl.css?v=${MAPLIBRE_VERSION}`, VENDOR).href, new URL(withVersion('../css/mapgl.css'), import.meta.url).href];
        await Promise.all(sheets.map((href, i) => new Promise((res) => {
          const l = document.createElement('link');
          l.rel = 'stylesheet';
          l.href = href;
          if (i === 0) l.dataset.maplibre = '';
          l.onload = res;
          l.onerror = res;
          document.head.append(l);
        })));
      }
      return import(new URL(`maplibre-gl.mjs?v=${MAPLIBRE_VERSION}`, VENDOR).href);
    })();
    lib.catch(() => { lib = null; });
  }
  return lib;
}

async function loadStyle(params) {
  const r = await fetch(withVersion('assets/maps/chalk-style.json'));
  if (!r.ok) throw new Error(`style ${r.status}`);
  const style = await r.json();
  if (!style.sources?.openmaptiles?.url) throw new Error('the style has no tile source');
  if (flag('maptest', params) === 'tiles-down') style.sources.openmaptiles.url = 'http://127.0.0.1:9/planet';      // test only: tiles that cannot be reached
  return style;
}

const geoFiles = new Map();
function loadGeo(name) {
  if (!geoFiles.has(name)) {
    const p = fetch(withVersion(`assets/maps/geo/${name}.geojson`)).then((r) => {
      if (!r.ok) throw new Error(`geo ${name}: ${r.status}`);
      return r.json();
    });
    p.catch(() => geoFiles.delete(name));
    geoFiles.set(name, p);
  }
  return geoFiles.get(name);
}

/** The 6 px diagonal chalk line our hatched places use (Plan 17 section 5): a tile whose diagonal runs corner to corner, drawn at
 * twice the density so it stays sharp. The lines are 6 css px apart. */
function hatchImage(color) {
  const S = 17;                                            // device px: 8.5 css px across, so the lines stand 6 css px apart
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d');
  g.strokeStyle = color;
  g.lineWidth = 3.4;
  g.lineCap = 'butt';
  for (const k of [0, S, 2 * S]) { g.beginPath(); g.moveTo(-S, k + S); g.lineTo(k + S, -S); g.stroke(); }
  return g.getImageData(0, 0, S, S);
}

const ease = (t) => 1 - (1 - t) ** 3;
let ids = 0;

// ---- the stage ---------------------------------------------------------------------------------------------------------
export class GLStage {
  constructor(host, ML, style, { mini = false } = {}) {
    this.gl = true;
    this.host = host;
    host._stage = this;                                    // the tests read the map's state through this
    this.ML = ML;
    this.mini = mini;
    this.uid = ++ids;
    this.W = 0;
    this.H = 0;
    this.spec = null;
    this.fan = null;                                       // the stack of makers fanned out into a ring, if any
    this.onResize = null;
    this.onMoved = null;                                   // after the visitor has moved the map and the pins are laid out again
    this.onMoveStart = null;                               // as the visitor starts to move it (the open card closes)
    this.auto = false;                                     // true while we move the map ourselves
    this.goToken = 0;
    this.countryData = null;
    this.cTok = 0;
    this.marks = { has: [], edge: [], provSel: [], provAll: false, provHas: [], focus: false };
    host.classList.add('mm-stage', 'mm-gl');
    host.innerHTML = `<div class="mm-gl-map"></div><div class="mm-grain" aria-hidden="true"></div><div class="mm-pins"></div>${mini ? '' : '<button type="button" class="mm-reset chalkboard chalkboard--s btn-s" hidden aria-label="Reset the map to the place chosen"><span class="chalk">Reset view</span></button>'}<p class="mm-attrib"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a> · <a href="https://openfreemap.org" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> · <a href="https://openmaptiles.org" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · <a href="https://maplibre.org" target="_blank" rel="noopener noreferrer">MapLibre</a></p>`;
    this.pinsEl = host.querySelector('.mm-pins');
    this.resetBtn = host.querySelector('.mm-reset');
    this.attrib = host.querySelector('.mm-attrib');
    ensurePinDefs();
    this.measure();
    this.map = new ML.Map({
      container: host.querySelector('.mm-gl-map'), style, center: [10, 25], zoom: 1, minZoom: -1, maxZoom: MAX_ZOOM,
      renderWorldCopies: false, attributionControl: false, trackResize: false, dragRotate: false, pitchWithRotate: false,
      touchPitch: false, keyboard: false, interactive: !mini, cooperativeGestures: !mini, fadeDuration: 120,
    });
    if (!mini) this.map.touchZoomRotate.disableRotation();
    const canvas = this.map.getCanvas();
    canvas.tabIndex = -1;                                  // the list under the map is the way in for the keyboard
    canvas.setAttribute('aria-hidden', 'true');
    this.map.getCanvasContainer().removeAttribute('tabindex');
    this.map.on('movestart', () => { if (!this.auto) this.onMoveStart?.(); });
    this.map.on('move', () => { if (!this.auto) this.track(); });
    this.map.on('moveend', () => { if (!this.auto) this.moved(); });
    this.resetBtn?.addEventListener('click', () => this.reset());
    this.ro = new ResizeObserver(() => {
      if (host.clientWidth === this.W && host.clientHeight === this.H) return;
      this.measure();
      this.map.resize();
      this.onResize?.();
    });
    this.ro.observe(host);
  }

  measure() {
    this.W = this.host.clientWidth;
    this.H = this.host.clientHeight;
  }

  /** Resolves once the style and the first tiles are in, with our layers added. Rejects on a source error or after `ms`. */
  ready(ms = LOAD_TIMEOUT) {
    return new Promise((resolve, reject) => {
      let done = false;
      const fail = (e) => { if (!done) { done = true; clearTimeout(timer); reject(e); } };
      const timer = setTimeout(() => fail(new Error(`no load within ${ms / 1000} s`)), ms);
      this.map.on('error', (e) => {
        const m = String(e?.error?.message || e?.message || '');
        if (!done && (e?.sourceId === 'openmaptiles' || /Failed to fetch|NetworkError|AJAXError|Load failed|style/i.test(m))) fail(new Error(m || 'a source error'));
      });
      this.map.once('load', () => {
        if (done) return;
        try { this.addLayers(); } catch (e) { fail(e); return; }
        // the whole world fits the map at the smallest zoom a visitor can reach, whatever its size (a phone needs less than zoom 1)
        const cam = this.map.cameraForBounds(WORLD, { padding: 10 });
        this.map.setMinZoom(Math.min(1, cam ? cam.zoom : 1));
        done = true;
        clearTimeout(timer);
        resolve();
      });
    });
  }

  addLayers() {
    const m = this.map;
    m.addImage('hatch-glow', hatchImage(GLOW), { pixelRatio: 2 });
    m.addSource('seam', { type: 'geojson', data: SEAM });
    m.addLayer({ id: 'seam', type: 'line', source: 'seam', layout: { visibility: 'none' }, paint: { 'line-color': IRON, 'line-width': 3.5 } }, 'park');
    m.addSource('ours-world', { type: 'geojson', data: EMPTY });
    m.addSource('ours-prov', { type: 'geojson', data: EMPTY });
    const before = 'place-country';
    const hatch = (id, source, opacity, filter) => ({ id, type: 'fill', source, filter, paint: { 'fill-pattern': 'hatch-glow', 'fill-opacity': opacity } });
    m.addLayer(hatch('ours-world-hatch', 'ours-world', 0.35, ['in', ['get', 'id'], ['literal', none()]]), before);
    m.addLayer({ id: 'ours-world-edge', type: 'line', source: 'ours-world', filter: ['in', ['get', 'id'], ['literal', none()]],
      layout: { 'line-join': 'round' }, paint: { 'line-color': CHALK, 'line-opacity': 0.9, 'line-width': 1.6 } }, before);
    m.addLayer(hatch('ours-prov-hatch', 'ours-prov', 0.35, ['in', ['get', 'id'], ['literal', none()]]), before);
    m.addLayer({ id: 'ours-prov-wash', type: 'fill', source: 'ours-prov', layout: { visibility: 'none' }, filter: ['in', ['get', 'id'], ['literal', none()]],
      paint: { 'fill-color': SLATE, 'fill-opacity': 0.5 } }, before);
    m.addLayer(hatch('ours-prov-sel-hatch', 'ours-prov', 0.85, ['in', ['get', 'id'], ['literal', none()]]), before);
    m.addLayer({ id: 'ours-prov-line', type: 'line', source: 'ours-prov', layout: { 'line-join': 'round' },
      paint: { 'line-color': CHALK, 'line-opacity': 0.78, 'line-width': 1.4 } }, before);
    m.addLayer({ id: 'ours-prov-sel-line', type: 'line', source: 'ours-prov', layout: { 'line-join': 'round' }, filter: ['in', ['get', 'id'], ['literal', none()]],
      paint: { 'line-color': GLOW, 'line-width': 2 } }, before);
    this.applyMarks();
  }

  destroy() {
    this.dead = true;
    this.goToken++;
    this.ro.disconnect();
    try { this.map.remove(); } catch { /* already gone */ }
  }

  // -- outlines (the same calls as MapStage; the outlines themselves are our GeoJSON)
  setWorld() {
    loadGeo('world').then((d) => { if (!this.dead) this.map.getSource('ours-world')?.setData(d); }).catch(() => {});
  }

  /** `data` is the country's SVG-map file (it has the boxes, the areas and the places); its GeoJSON outlines are fetched here. */
  setCountry(data) {
    this.countryData = data;
    const tok = ++this.cTok;
    const src = this.map.getSource('ours-prov');
    if (!data) { src?.setData(EMPTY); this.applyMarks(); return; }
    loadGeo(data.id).then((d) => { if (tok === this.cTok && !this.dead) { this.map.getSource('ours-prov')?.setData(d); this.applyMarks(); } }).catch(() => {});
  }

  /** The same state MapStage.mark takes. A country's own outline is left to the basemap and to its provinces, so `sel` is not drawn. */
  mark({ has = [], edge = [], provSel = [], provAll = false, provHas = [], focus = false } = {}) {
    this.marks = { has, edge, provSel, provAll, provHas, focus };
    this.applyMarks();
  }

  applyMarks() {
    const m = this.map;
    if (!m.getLayer('ours-prov-line')) return;
    const inIds = (list) => ['in', ['get', 'id'], ['literal', none(list)]];
    const { has, edge, provSel, provAll, provHas, focus } = this.marks;
    const provinces = !!this.countryData;
    m.setFilter('ours-world-hatch', inIds(provinces ? [] : has));
    m.setFilter('ours-world-edge', inIds(provinces ? [] : edge));
    const hatched = provAll ? ['!', inIds(provSel)] : ['all', inIds(provHas), ['!', inIds(provSel)]];
    m.setFilter('ours-prov-hatch', hatched);
    m.setFilter('ours-prov-sel-hatch', inIds(provSel));
    m.setFilter('ours-prov-sel-line', inIds(provSel));
    m.setFilter('ours-prov-wash', ['!', inIds(provSel)]);
    m.setLayoutProperty('ours-prov-wash', 'visibility', focus && provSel.length ? 'visible' : 'none');
    this.lineAlpha = this.mini ? 0.5 : focus ? 0.4 : 0.78;
    m.setPaintProperty('ours-prov-line', 'line-opacity', ['case', inIds(provSel), 0, this.lineAlpha]);
    m.setPaintProperty('ours-prov-sel-line', 'line-width', focus ? 2.4 : 2);
  }

  /** The box (map units) that holds the outlines of these provinces: the boxes the build wrote. */
  boxOf(idsWanted) {
    const want = new Set(idsWanted);
    let b = null;
    for (const p of this.countryData?.provinces || []) {
      if (!want.has(p.id) || !p.bb) continue;
      b = b ? [Math.min(b[0], p.bb[0]), Math.min(b[1], p.bb[1]), Math.max(b[2], p.bb[2]), Math.max(b[3], p.bb[3])] : [...p.bb];
    }
    return b;
  }

  // -- the view
  /** The camera that frames `spec` (the same spec MapStage takes: box in map units, minW/minH, pad in px). */
  camFor(spec) {
    const pad = { l: 12, r: 12, t: 12, b: 12, ...(spec.pad || {}) };
    let [x0, y0, x1, y1] = spec.box;
    const grow = (lo, hi, min) => (hi - lo < min ? [(lo + hi) / 2 - min / 2, (lo + hi) / 2 + min / 2] : [lo, hi]);
    [x0, x1] = grow(x0, x1, spec.minW || 1);
    [y0, y1] = grow(y0, y1, spec.minH || 1);
    const [west, north] = unproject(x0, y0);
    const [east, south] = unproject(x1, y1);
    // never so much padding that nothing is left to draw in
    const px = Math.min(pad.l + pad.r, this.W - 20) / (pad.l + pad.r || 1);
    const py = Math.min(pad.t + pad.b, this.H - 20) / (pad.t + pad.b || 1);
    const padding = { left: pad.l * px, right: pad.r * px, top: pad.t * py, bottom: pad.b * py };
    const cam = this.map.cameraForBounds([[west, south], [east, north]], { padding, maxZoom: MAX_ZOOM });
    return { cam, wraps: east > 180 || west < -180 };
  }

  /** Moves to `spec`: eased over about 700 ms, or at once with reduced motion or `animate: false`. Resolves when it has arrived. */
  go(spec, animate = true) {
    this.spec = spec;
    const { cam, wraps } = this.camFor(spec);
    const m = this.map;
    const my = ++this.goToken;
    this.pinsEl.style.transform = '';
    this.pinsEl.style.visibility = '';
    this.resetBtn && (this.resetBtn.hidden = true);
    m.setRenderWorldCopies(wraps);
    if (m.getLayer('seam')) m.setLayoutProperty('seam', 'visibility', wraps ? 'visible' : 'none');                         // Fiji lies across 180 degrees, and only then do the copies of the world show
    if (!cam) return Promise.resolve();
    const to = { center: cam.center, zoom: cam.zoom };
    if (!animate || reducedMotion() || !this.W) {
      this.auto = true;
      m.jumpTo(to);
      this.auto = false;
      this.host.dataset.moving = '0';
      return Promise.resolve();
    }
    this.auto = true;
    this.host.dataset.moving = '1';
    return new Promise((resolve) => {
      let ended = false;
      const end = () => {
        if (ended) return;
        ended = true;
        if (my === this.goToken) { this.auto = false; this.host.dataset.moving = '0'; }
        resolve();
      };
      m.once('moveend', end);
      m.easeTo({ ...to, duration: 700, easing: ease });
      setTimeout(end, 1100);                               // an ease that has nowhere to go may not report an end
    });
  }

  /** Leaves one town's name off the basemap (the maker page draws its own starred label for the capital in the same place). */
  hideName(name) {
    const same = ['coalesce', ['get', 'name:en'], ['get', 'name_en'], ['get', 'name']];
    for (const id of ['place-city-large', 'place-city', 'place-town', 'place-village']) {
      this.baseFilters ||= {};
      this.baseFilters[id] ||= this.map.getFilter(id);
      this.map.setFilter(id, ['all', this.baseFilters[id], ['!=', same, name]]);
    }
  }

  /** The pixel position inside the stage of a point in map units. A longitude beyond 180 (Fiji) is read in the copy of the world
   * nearest the middle of the view. */
  toPx([x, y]) {
    let [lon, lat] = unproject(x, y);
    lon += 360 * Math.round((this.map.getCenter().lng - lon) / 360);
    const p = this.map.project([lon, lat]);
    return [p.x, p.y];
  }

  // -- the visitor moves the map: the pins ride along, then are laid out again when it stops
  track() {
    const ref = this.ref;
    if (!ref) return;
    if (Math.abs(this.map.getZoom() - ref.zoom) > 1e-4) { this.pinsEl.style.visibility = 'hidden'; return; }
    this.pinsEl.style.visibility = '';
    const p = this.map.project(ref.ll);
    this.pinsEl.style.transform = `translate(${(p.x - ref.x).toFixed(1)}px, ${(p.y - ref.y).toFixed(1)}px)`;
  }

  moved() {
    this.pinsEl.style.transform = '';
    this.pinsEl.style.visibility = '';
    this.setPins(this.lastItems || []);
    if (this.resetBtn) this.resetBtn.hidden = false;
    this.onMoved?.();
  }

  reset() {
    if (!this.spec) return;
    this.pinsEl.style.visibility = 'hidden';
    this.go(this.spec, true).then(() => {
      if (this.dead) return;
      this.pinsEl.style.visibility = '';
      this.setPins(this.lastItems || []);
      this.onMoved?.();
    });
  }

  clearPins() { this.pinsEl.innerHTML = ''; this.pinsEl.style.transform = ''; }

  setPins(items) {
    const laid = MapStage.prototype.setPins.call(this, items);
    const ll = this.map.getCenter();
    const p = this.map.project(ll);
    this.ref = { ll, x: p.x, y: p.y, zoom: this.map.getZoom() };
    return laid;
  }

  /** Resolves when the map has finished drawing its tiles (for screenshots and the tests). */
  idle() {
    return new Promise((resolve) => {
      const done = () => { if (this.map.loaded() && !this.map.isMoving()) resolve(); else this.map.once('idle', done); };
      done();
    });
  }

  /** The attribution's box in the stage, so the maker page's inset keeps clear of it. */
  attribBox() {
    const h = this.host.getBoundingClientRect();
    const a = this.attrib.getBoundingClientRect();
    return { l: a.left - h.left, r: a.right - h.left, t: a.top - h.top, b: a.bottom - h.top };
  }

  /** For the tests: where the chosen outlines stand in the stage, and what is drawn. Same fields as the SVG map's checks read. */
  shapeInfo() {
    const d = this.countryData;
    if (!d) return null;
    const { provSel, provAll, provHas } = this.marks;
    const use = provSel.length ? d.provinces.filter((p) => provSel.includes(p.id)) : d.provinces.filter((p) => !['okinawa', 'alaska', 'hawaii'].includes(p.id));
    let l = 1e9;
    let t = 1e9;
    let r = -1e9;
    let b = -1e9;
    for (const p of use) {
      const [ax, ay] = this.toPx([p.bb[0], p.bb[1]]);
      const [bx, by] = this.toPx([p.bb[2], p.bb[3]]);
      l = Math.min(l, ax, bx); r = Math.max(r, ax, bx); t = Math.min(t, ay, by); b = Math.max(b, ay, by);
    }
    return { paths: d.provinces.length, selN: provSel.length, padL: l / this.W, padR: (this.W - r) / this.W, padT: t / this.H, padB: (this.H - b) / this.H,
      minStroke: 1.4, minAlpha: this.lineAlpha, hatched: provAll ? d.provinces.length : new Set([...provHas, ...provSel]).size };
  }
}

for (const k of ['layout', 'draw']) GLStage.prototype[k] = MapStage.prototype[k];          // the pins are laid out and drawn exactly as on the SVG map

// ---- the entry points --------------------------------------------------------------------------------------------------
/** The real map in `host`, or null (after one line in the console) when it cannot run. `host` is left clean for the SVG map then. */
export async function createGLStage(host, { mini = false, params } = {}) {
  const mode = mapMode(params);
  if (!mode.real) { log(mode.why); return null; }
  let stage = null;
  try {
    const [ML, style] = await Promise.all([loadLib(), loadStyle(params)]);
    if (!host.isConnected) return null;
    stage = new GLStage(host, ML, style, { mini });
    await stage.ready();
    if (!host.isConnected) { stage.destroy(); return null; }
    return stage;
  } catch (e) {
    log(`${e?.message || e}`);
    stage?.destroy();
    host.classList.remove('mm-gl', 'mm-stage');
    host.innerHTML = '';
    return null;
  }
}

/** The map on a maker page: the real map when it can run, else the SVG one. Resolves to { drawn, stage }. */
export async function drawMakerMap(host, { p }) {
  if (!p.cid || p.lat == null) return { drawn: false };
  const stage = await createGLStage(host, { mini: true });
  const drawn = await drawProvinceMap(host, { p }, stage ? { stage, towns: false } : undefined);
  if (!drawn && stage) stage.destroy();
  return { drawn, stage };
}
