// The chalk maps (Plan 14 sections 5 and 6), drawn from the Natural Earth files in assets/maps/ (public domain; see
// assets/maps/LICENSE.txt). One Miller projection for every level, so zooming from the world to a province is one smooth move
// of the view. The outlines are SVG paths in map units (0.005 degree, y down) inside a scaled group; the pins are real
// <button>s laid over the map in pixels, so they keep one size whatever the zoom.
import { withVersion } from './data.js';
import { esc, reducedMotion } from './util.js';

export const UNIT = 0.005;
const RAD = Math.PI / 180;

/** [x, y] in map units for a longitude and latitude (Miller cylindrical, as build/tools/makemaps.py). */
export function project(lon, lat) {
  const l = Math.max(-85, Math.min(85, lat));
  const y = 1.25 * Math.log(Math.tan(Math.PI / 4 + 0.4 * l * RAD));
  return [lon / UNIT, -(y / RAD) / UNIT];
}

export function unproject(x, y) {
  const ym = -y * UNIT * RAD;
  return [x * UNIT, (Math.atan(Math.exp(ym / 1.25)) - Math.PI / 4) / 0.4 / RAD];
}

// ---- the map files -------------------------------------------------------------------------------------------------
const files = new Map();
function fetchMap(name) {
  if (!files.has(name)) {
    const p = fetch(withVersion(`assets/maps/${name}.json`)).then((r) => {
      if (!r.ok) throw new Error(`map ${name}: ${r.status}`);
      return r.json();
    });
    p.catch(() => files.delete(name));
    files.set(name, p);
  }
  return files.get(name);
}
export const loadWorld = () => fetchMap('world');
export const loadCountry = (cid) => fetchMap(cid);

// ---- pins (Plan 14 section 5.4) ------------------------------------------------------------------------------------
/** Maker pin colours by main category, and the white of a group pin. */
export const PIN_COLORS = { sake: '#d8453d', fermented: '#e8c43c', umeshu: '#ec8fb4', liqueur: '#ef8a2c', wine: '#8f5ab8', spirits: '#4b88d3', cocktails: '#4fae6c' };
export const GROUP_COLOR = '#f2ede4';
export const pinColor = (cat) => PIN_COLORS[cat] || '#b9b2a6';

let defsDone = false;
/** The gloss shared by every pin head, once per page (gradients in a hidden <svg> do not draw, so this one is just out of sight). */
function ensurePinDefs() {
  if (defsDone && document.getElementById('pin-gloss')) return;
  defsDone = true;
  document.body.insertAdjacentHTML('beforeend', `<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
<radialGradient id="pin-gloss" cx=".36" cy=".3" r=".78"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset=".32" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".38"/></radialGradient>
<linearGradient id="pin-needle" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8d949a"/><stop offset=".5" stop-color="#e9edf0"/><stop offset="1" stop-color="#7c8389"/></linearGradient></defs></svg>`);
}

/** One pin as SVG markup with its origin at the middle of the head. `tip` is the offset from the head to the real spot: the
 * needle goes there, slanting a little because the pin is seen at an angle. A pin that was nudged far from its spot keeps a thin
 * chalk line back to it instead of a needle. */
export function pinArt({ r, color, count, tip, text }) {
  const light = ['#e8c43c', '#ec8fb4', '#f2ede4', '#ef8a2c', '#b9b2a6'].includes(color);
  text = text || (light ? '#262a28' : '#fff');
  const [dx, dy] = tip;
  const d = Math.hypot(dx, dy) || 1;
  const far = d > r + 26;
  const ux = dx / d;
  const uy = dy / d;
  const sx = ux * r * 0.78;
  const sy = uy * r * 0.78;
  const needle = far
    ? `<line x1="${sx.toFixed(1)}" y1="${sy.toFixed(1)}" x2="${dx.toFixed(1)}" y2="${dy.toFixed(1)}" stroke="#f2ede4" stroke-opacity=".6" stroke-width="1.2" stroke-dasharray="3 3"/><circle cx="${dx.toFixed(1)}" cy="${dy.toFixed(1)}" r="2" fill="#f2ede4" fill-opacity=".75"/>`
    : `<line x1="${sx.toFixed(1)}" y1="${sy.toFixed(1)}" x2="${dx.toFixed(1)}" y2="${dy.toFixed(1)}" stroke="#40464b" stroke-width="3.2" stroke-linecap="round" opacity=".55"/><line x1="${sx.toFixed(1)}" y1="${sy.toFixed(1)}" x2="${dx.toFixed(1)}" y2="${dy.toFixed(1)}" stroke="url(#pin-needle)" stroke-width="2" stroke-linecap="round"/>`;
  const shadow = `<ellipse cx="${(dx + 3).toFixed(1)}" cy="${(dy + 1).toFixed(1)}" rx="${(r * 0.8).toFixed(1)}" ry="${(r * 0.28).toFixed(1)}" fill="#000" opacity="${far ? 0 : 0.34}"/>`;
  const head = `<circle class="pin-head" r="${r}" fill="${color}"/><circle r="${r}" fill="url(#pin-gloss)"/><circle r="${r - 0.5}" fill="none" stroke="#000" stroke-opacity=".38"/><ellipse cx="${(-r * 0.36).toFixed(1)}" cy="${(-r * 0.42).toFixed(1)}" rx="${(r * 0.3).toFixed(1)}" ry="${(r * 0.18).toFixed(1)}" transform="rotate(-35 ${(-r * 0.36).toFixed(1)} ${(-r * 0.42).toFixed(1)})" fill="#fff" opacity=".6"/>`;
  const label = count != null ? `<text y="${(r * 0.36).toFixed(1)}" text-anchor="middle" font-family="Kalam, 'Segoe Print', cursive" font-weight="700" font-size="${(r * (String(count).length > 2 ? 0.92 : 1.08)).toFixed(1)}" fill="${text}">${count}</text>` : '';
  return `${shadow}${needle}${head}${label}`;
}

/** Pins that would touch are pushed apart. Each item has a centre (cx, cy) and a box around it; `fixed` items stay put. */
export function relax(items, W, H, gap = 3) {
  const box = (i) => ({ l: i.cx - i.bl, r: i.cx + i.br, t: i.cy - i.bt, b: i.cy + i.bb });
  const clamp = (i) => {
    i.cx = Math.min(Math.max(i.cx, i.bl + 2), W - i.br - 2);
    i.cy = Math.min(Math.max(i.cy, i.bt + 2), H - i.bb - 2);
  };
  items.forEach((i) => { if (!i.fixed) clamp(i); });
  for (let iter = 0; iter < 400; iter++) {
    let moved = false;
    for (let a = 0; a < items.length; a++) {
      for (let b = a + 1; b < items.length; b++) {
        const p = items[a];
        const q = items[b];
        if (p.fixed && q.fixed) continue;
        const A = box(p);
        const B = box(q);
        const ox = Math.min(A.r, B.r) - Math.max(A.l, B.l) + gap;
        const oy = Math.min(A.b, B.b) - Math.max(A.t, B.t) + gap;
        if (ox <= 0 || oy <= 0) continue;
        moved = true;
        const wp = p.fixed ? 0 : q.fixed ? 1 : 0.5;
        const wq = q.fixed ? 0 : p.fixed ? 1 : 0.5;
        if (ox < oy) {
          const s = p.cx === q.cx ? (a % 2 ? 1 : -1) : Math.sign(p.cx - q.cx);
          p.cx += s * ox * wp; q.cx -= s * ox * wq;
        } else {
          const s = p.cy === q.cy ? (a % 2 ? 1 : -1) : Math.sign(p.cy - q.cy);
          p.cy += s * oy * wp; q.cy -= s * oy * wq;
        }
        if (!p.fixed) clamp(p);
        if (!q.fixed) clamp(q);
      }
    }
    if (!moved) break;
  }
}

// ---- the stage -------------------------------------------------------------------------------------------------------
let stageIds = 0;
const HATCH = (id, colour, opacity) => `<pattern id="${id}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="${colour}" stroke-opacity="${opacity}" stroke-width="2.2"/></pattern>`;
const ease = (t) => 1 - (1 - t) ** 3;

export class MapStage {
  /** `host` becomes the stage: the outlines, and a layer for pins. */
  constructor(host) {
    this.host = host;
    this.uid = ++stageIds;
    this.W = 0;
    this.H = 0;
    this.v = { s: 1, tx: 0, ty: 0 };
    this.spec = null;
    this.raf = 0;
    this.fan = null;                                   // the stack of makers fanned out into a ring, if any
    this.onResize = null;
    host.classList.add('mm-stage');
    host.innerHTML = `<svg class="mm-svg" aria-hidden="true" focusable="false"><defs>${HATCH(`mm-hl-${this.uid}`, '#f2ede4', 0.4)}${HATCH(`mm-hg-${this.uid}`, '#f4c27a', 0.95)}</defs>
<g class="mm-geo"><g class="g-world"></g><g class="g-country"></g></g></svg><div class="mm-pins"></div>`;
    this.svg = host.querySelector('.mm-svg');
    this.geo = host.querySelector('.mm-geo');
    this.gWorld = host.querySelector('.g-world');
    this.gCountry = host.querySelector('.g-country');
    this.pinsEl = host.querySelector('.mm-pins');
    this.pats = [...host.querySelectorAll('pattern')];
    ensurePinDefs();
    this.measure();
    this.ro = new ResizeObserver(() => {
      const w = host.clientWidth;
      const h = host.clientHeight;
      if (w === this.W && h === this.H) return;
      this.measure();
      this.onResize?.();
    });
    this.ro.observe(host);
  }

  measure() {
    this.W = this.host.clientWidth;
    this.H = this.host.clientHeight;
    this.svg.setAttribute('viewBox', `0 0 ${this.W || 1} ${this.H || 1}`);
  }

  destroy() { cancelAnimationFrame(this.raf); this.ro.disconnect(); }

  // -- outlines
  setWorld(world) {
    this.gWorld.innerHTML = world.countries.map((c) => `<path data-id="${esc(c.id)}" d="${c.d}"/>`).join('');
  }

  /** Province outlines of one country (or none), drawn above the world. */
  setCountry(data) {
    // big outlines first, so a city-province (Daejeon) is drawn over the province round it
    const area = (p) => (p.bb[2] - p.bb[0]) * (p.bb[3] - p.bb[1]);
    this.gCountry.innerHTML = data ? [...data.provinces].sort((a, b) => area(b) - area(a)).map((p) => `<path data-id="${esc(p.id)}" d="${p.d}"/>`).join('') : '';
  }

  /** `has`: countries with makers, hatched lightly. `sel`: the chosen countries or provinces, hatched in glow chalk. */
  mark({ has = [], sel = [], edge = [], provSel = [], provAll = false, provHas = [], focus = false } = {}) {
    this.gCountry.classList.toggle('focus', focus);
    const provHasSet = new Set(provHas);
    const hasSet = new Set(has);
    const selSet = new Set(sel);
    const edgeSet = new Set(edge);
    const provSet = new Set(provSel);
    for (const el of this.gWorld.children) {
      const id = el.dataset.id;
      el.classList.toggle('sel', edgeSet.has(id) || selSet.has(id));
      el.classList.toggle('has', hasSet.has(id) && !selSet.has(id));
      el.style.fill = selSet.has(id) ? `url(#mm-hl-${this.uid})` : hasSet.has(id) ? `url(#mm-hl-${this.uid})` : '';
    }
    for (const el of this.gCountry.children) {
      const on = provSet.has(el.dataset.id);
      el.classList.toggle('sel', on);
      el.style.fill = on ? `url(#mm-hg-${this.uid})` : provAll || provHasSet.has(el.dataset.id) ? `url(#mm-hl-${this.uid})` : '';
    }
  }

  /** The box (map units) that holds the drawn outlines of these provinces, from the real path geometry. */
  boxOf(ids) {
    const want = new Set(ids);
    let b = null;
    for (const el of this.gCountry.children) {
      if (!want.has(el.dataset.id)) continue;
      const r = el.getBBox();
      b = b ? [Math.min(b[0], r.x), Math.min(b[1], r.y), Math.max(b[2], r.x + r.width), Math.max(b[3], r.y + r.height)] : [r.x, r.y, r.x + r.width, r.y + r.height];
    }
    return b;
  }

  // -- the view
  /** The transform that fits `spec` in the stage: { box: [x0, y0, x1, y1] in map units, minW, minH (map units), pad: { l, r, t, b } px }. */
  fitFor(spec) {
    const { W, H } = this;
    const pad = { l: 12, r: 12, t: 12, b: 12, ...(spec.pad || {}) };
    let [x0, y0, x1, y1] = spec.box;
    const grow = (lo, hi, min) => (hi - lo < min ? [(lo + hi) / 2 - min / 2, (lo + hi) / 2 + min / 2] : [lo, hi]);
    [x0, x1] = grow(x0, x1, spec.minW || 1);
    [y0, y1] = grow(y0, y1, spec.minH || 1);
    const aw = Math.max(W - pad.l - pad.r, 20);
    const ah = Math.max(H - pad.t - pad.b, 20);
    const s = Math.min(aw / (x1 - x0), ah / (y1 - y0));
    return { s, tx: pad.l + (aw - s * (x1 - x0)) / 2 - s * x0, ty: pad.t + (ah - s * (y1 - y0)) / 2 - s * y0 };
  }

  apply(v) {
    this.v = v;
    this.geo.setAttribute('transform', `translate(${v.tx.toFixed(2)} ${v.ty.toFixed(2)}) scale(${v.s})`);
    for (const p of this.pats) p.setAttribute('patternTransform', `rotate(45) scale(${(1 / v.s).toFixed(6)})`);
  }

  /** Moves the view to `spec`: eased over 450 ms, or at once with reduced motion or `animate: false`. Resolves when it has arrived. */
  go(spec, animate = true) {
    this.spec = spec;
    const to = this.fitFor(spec);
    cancelAnimationFrame(this.raf);
    if (!animate || reducedMotion() || !this.W) { this.apply(to); this.host.dataset.moving = '0'; return Promise.resolve(); }
    const from = { ...this.v };
    this.host.dataset.moving = '1';
    return new Promise((resolve) => {
      const t0 = performance.now();
      const tick = (now) => {
        const t = Math.min(1, (now - t0) / 450);
        const k = ease(t);
        // the scale moves in log steps so a long zoom feels even; the offsets follow so the point under the middle stays put
        const s = from.s * (to.s / from.s) ** k;
        const cx = (this.W / 2 - from.tx) / from.s;
        const cy = (this.H / 2 - from.ty) / from.s;
        const ex = (this.W / 2 - to.tx) / to.s;
        const ey = (this.H / 2 - to.ty) / to.s;
        const mx = cx + (ex - cx) * k;
        const my = cy + (ey - cy) * k;
        this.apply({ s, tx: this.W / 2 - mx * s, ty: this.H / 2 - my * s });
        if (t < 1) this.raf = requestAnimationFrame(tick);
        else { this.apply(to); this.host.dataset.moving = '0'; resolve(); }
      };
      this.raf = requestAnimationFrame(tick);
    });
  }

  toPx([x, y]) { return [this.v.s * x + this.v.tx, this.v.s * y + this.v.ty]; }

  // -- pins
  clearPins() { this.pinsEl.innerHTML = ''; }

  /** Lays the pins out and draws them. Items: { id, kind: 'group' | 'maker', x, y (map units), r, color, count, name, aria, tag }.
   * Makers that share a spot (more than 3 of them) become one stack pin; tapping it (`fan`) spreads them into a ring. */
  setPins(items) {
    this.lastItems = items;
    // a small stage (a phone) may not have room for full-size pins: the heads shrink a step at a time until none touch
    let laid = [];
    for (const k of [1, 0.85, 0.72]) {
      laid = this.layout(items.map((it) => ({ ...it, r: Math.round(it.r * k) })));
      const heads = laid.filter((a, i) => laid.some((b, j) => j !== i && Math.abs(a.cx - b.cx) < a.it.r + b.it.r + 1 && Math.abs(a.cy - b.cy) < a.it.r + b.it.r + 1));
      if (!heads.length) break;
    }
    this.draw(laid);
    return laid;
  }

  layout(items) {
    const { W, H } = this;
    const tipOf = (it) => this.toPx([it.x, it.y]);
    const laid = [];
    // stacks: makers whose spots are within 7 px of each other
    const makers = items.filter((i) => i.kind === 'maker');
    const parent = makers.map((_, i) => i);
    const find = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
    const px = makers.map(tipOf);
    for (let a = 0; a < makers.length; a++) for (let b = a + 1; b < makers.length; b++) if (Math.hypot(px[a][0] - px[b][0], px[a][1] - px[b][1]) < 7) parent[find(a)] = find(b);
    const clusters = new Map();
    makers.forEach((m, i) => { const k = find(i); if (!clusters.has(k)) clusters.set(k, []); clusters.get(k).push(i); });
    const stacked = new Set();
    const stacks = [];
    for (const idx of clusters.values()) {
      if (idx.length <= 3) continue;
      idx.forEach((i) => stacked.add(makers[i].id));
      const members = idx.map((i) => makers[i]);
      const tally = {};
      members.forEach((m) => { tally[m.color] = (tally[m.color] || 0) + 1; });
      const color = Object.keys(tally).sort((a, b) => tally[b] - tally[a])[0];
      const cx = px[idx[0]][0];
      const cy = px[idx[0]][1];
      stacks.push({ id: `stack:${members.map((m) => m.id).sort()[0]}:${members.length}`, kind: 'stack', members, r: 12, color, count: members.length, tip: [cx, cy], name: `${members.length} makers here`, aria: `${members.length} makers at one spot, spread out`, tag: false });
    }
    const make = (it, tip, extra = {}) => {
      const L = it.r + (it.kind === 'group' ? 14 : 10);
      const tagW = it.tag ? Math.ceil(String(it.name).length * 7.4 + 14) : 0;
      return { it, tip, cx: tip[0] + 0.3 * L, cy: tip[1] - L, bl: it.r, br: it.r, bt: it.r, bb: it.r, tagW, flip: false, ...extra };
    };
    for (const it of items) if (it.kind === 'group' || (it.kind === 'maker' && !stacked.has(it.id))) laid.push(make(it, tipOf(it)));
    this.lastStacks = stacks;
    for (const s of stacks) laid.push(make(s, s.tip));
    // a fanned stack: its members stand in a ring round the stack's own head, which is not drawn while it is open
    let ring = [];
    const open = stacks.find((s) => s.id === this.fan);
    if (open) {
      const at = laid.findIndex((l) => l.it === open);
      const base = laid.splice(at, 1)[0];
      const n = open.members.length;
      const R = Math.max(40, (n * 24) / (2 * Math.PI) + 14);
      const cx = Math.min(Math.max(base.cx, R + 24), W - R - 24);
      const cy = Math.min(Math.max(base.cy, R + 24), H - R - 24);
      ring = open.members.map((m, i) => {
        const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        return { ...make(m, base.tip), cx: cx + Math.cos(a) * R, cy: cy + Math.sin(a) * R, fixed: true, fanned: true };
      });
      laid.push(...ring);
    }
    for (const l of laid) {                              // the tag of a group pin goes on the side with room
      if (l.tagW) { l.flip = l.cx > W / 2; if (l.flip) l.bl = l.it.r + 4 + l.tagW; else l.br = l.it.r + 4 + l.tagW; }
    }
    relax(laid, W, H);
    // a crowded corner (a phone, Japan's eight areas): pins that still touch give up their always-on name tag, which shows on
    // hover and focus instead, and the layout runs again; heads never overlap
    const touching = () => laid.filter((a, i) => laid.some((b, j) => j !== i && a.cx - a.bl < b.cx + b.br && a.cx + a.br > b.cx - b.bl && a.cy - a.bt < b.cy + b.bb && a.cy + a.bb > b.cy - b.bt));
    // first try the tag on the other side of its pin; only then give the tag up
    for (const l of touching()) {
      if (!l.tagW) continue;
      const before = touching().length;
      [l.bl, l.br] = [l.br, l.bl];
      l.flip = !l.flip;
      if (touching().length >= before) { [l.bl, l.br] = [l.br, l.bl]; l.flip = !l.flip; }
    }
    for (let k = 0; k < 4 && touching().length; k++) {
      for (const l of touching()) if (l.tagW) { l.tagW = 0; l.bl = l.br = l.it.r; l.noTag = true; }
      relax(laid, W, H, 3 + k * 3);
    }
    return laid;
  }

  draw(laid) {
    const { W } = this;
    this.pinsEl.innerHTML = laid.map((l) => {
      const { it } = l;
      const art = pinArt({ r: it.r, color: it.kind === 'group' ? GROUP_COLOR : it.color, count: it.count, tip: [l.tip[0] - l.cx, l.tip[1] - l.cy] });
      const tag = it.kind === 'group' || it.kind === 'maker'
        ? `<span class="pin-tag chalkboard chalkboard--s${(l.tagW ? l.flip : l.cx > W / 2) ? ' flip' : ''}${it.tag && !l.noTag ? ' always' : ''}" aria-hidden="true"><span class="chalk">${esc(it.name)}</span></span>` : '';
      return `<button type="button" class="mm-pin ${it.kind}${l.fanned ? ' fanned' : ''}" data-id="${esc(it.id)}" aria-label="${esc(it.aria)}" style="left:${(l.cx - 22).toFixed(1)}px;top:${(l.cy - 22).toFixed(1)}px;--r:${it.r}px"><svg class="pin-art" width="1" height="1" aria-hidden="true" focusable="false">${art}</svg>${tag}</button>`;
    }).join('');
  }
}

// ---- a point inside a province (Plan 14 section 13.2) ----------------------------------------------------------------
const ringsOf = (prov) => {
  if (!prov._rings) {
    prov._rings = [...prov.d.matchAll(/M(-?\d+) (-?\d+)l([-\d ]*)z/g)].map((m) => {
      let x = +m[1];
      let y = +m[2];
      const pts = [[x, y]];
      const n = m[3].split(' ').filter(Boolean).map(Number);
      for (let i = 0; i + 1 < n.length; i += 2) { x += n[i]; y += n[i + 1]; pts.push([x, y]); }
      return pts;
    });
  }
  return prov._rings;
};
const inRing = (ring, x, y) => {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi || 1e-9) + xi) c = !c;
  }
  return c;
};
/** The visual centre of a province, in map units: the centroid of its biggest piece, or when that falls outside the shape (a
 * curved coast) the nearest point that is inside. Unlike the bounding-box centre it always stands on land. */
export function innerPoint(prov) {
  if (prov._inner) return prov._inner;
  const area = (r) => Math.abs(r.reduce((a, p, i) => a + p[0] * r[(i + 1) % r.length][1] - r[(i + 1) % r.length][0] * p[1], 0)) / 2;
  const ring = ringsOf(prov).reduce((a, r) => (area(r) > area(a) ? r : a));
  let a2 = 0;
  let cx = 0;
  let cy = 0;
  ring.forEach((p, i) => {
    const q = ring[(i + 1) % ring.length];
    const f = p[0] * q[1] - q[0] * p[1];
    a2 += f; cx += (p[0] + q[0]) * f; cy += (p[1] + q[1]) * f;
  });
  cx /= 3 * a2; cy /= 3 * a2;
  let best = [cx, cy];
  if (!inRing(ring, cx, cy)) {
    const xs = ring.map((p) => p[0]);
    const ys = ring.map((p) => p[1]);
    let bd = Infinity;
    for (let i = 0; i <= 40; i++) for (let j = 0; j <= 40; j++) {
      const x = Math.min(...xs) + ((Math.max(...xs) - Math.min(...xs)) * i) / 40;
      const y = Math.min(...ys) + ((Math.max(...ys) - Math.min(...ys)) * j) / 40;
      if (inRing(ring, x, y) && Math.hypot(x - cx, y - cy) < bd) { best = [x, y]; bd = Math.hypot(x - cx, y - cy); }
    }
  }
  prov._inner = best;
  return best;
}

/** Provinces that stay out of a whole-country frame (far outliers). */
export const FRAME_SKIP = { usa: ['alaska', 'hawaii'], japan: ['okinawa'] };

// ---- the map on a maker page (Plan 14 section 6) ---------------------------------------------------------------------
const INSET_SKIP = { usa: ['alaska', 'hawaii'] };          // so the continental states fill the inset
const textW = (s, px) => Math.ceil(String(s).length * px * 0.6) + 8;

/** The province the maker is in, drawn in chalk with its pin, its capital and up to 4 towns of 50,000 or more, a small country
 * inset in the corner, and words for screen readers. Resolves to true when drawn, false when it could not be (the caller then
 * leaves the map out). */
export async function drawProvinceMap(host, { p }) {
  if (!p.cid || p.lat == null) return false;
  let data;
  try { data = await loadCountry(p.cid); } catch { return false; }
  const prov = data.provinces.find((x) => x.id === p.prov);
  if (!prov) return false;
  const stage = new MapStage(host);
  host.classList.add('mini');
  stage.setCountry(data);
  const pin = project(p.lon, p.lat);
  const lat = p.lat;
  const km60 = 60 / (111.3 * Math.max(0.2, Math.cos(lat * RAD)) * UNIT);
  const [bx0, by0, bx1, by1] = prov.bb;
  stage.measure();
  const spec = {
    box: [Math.min(bx0, pin[0]), Math.min(by0, pin[1]), Math.max(bx1, pin[0]), Math.max(by1, pin[1])],
    minW: km60, minH: km60, pad: { l: 16, r: 16, t: 54, b: 18 },
  };
  stage.go(spec, false);
  stage.mark({ provSel: [prov.id] });
  const capital = (data.places || []).find((x) => x.p === prov.id && x.cap);
  const towns = prov.city ? [] : (data.places || []).filter((x) => x.p === prov.id && !x.cap && x.pop >= 50000).sort((a, b) => b.pop - a.pop).slice(0, 4);

  // the pin, then labels that never cover it or each other
  const [tx, ty] = stage.toPx(pin);
  const r = 10;
  const L = r + 11;
  const hx = tx + 0.3 * L;
  const hy = ty - L;
  const used = [{ l: hx - r - 2, r: hx + r + 2, t: hy - r - 2, b: hy + r + 2 }, { l: tx - 4, r: tx + 4, t: ty - 9, b: ty + 3 }];   // the head, and the needle's foot
  const hit = (a, b) => a.l < b.r + 3 && a.r > b.l - 3 && a.t < b.b + 3 && a.b > b.t - 3;
  const W = stage.W;
  const H = stage.H;
  const marks = [];
  /** Puts a capital or town on the map with its name. A place under the pin (Akabu stands in Morioka) is marked beside the pin,
   * so the reader still sees it named. The capital is always placed: when nothing clear is found it takes the first spot in range. */
  const label = (pl, kind) => {
    const [x, y] = stage.toPx([pl.x, pl.y]);
    const must = kind === 'cap';
    if (!must && (x < 6 || x > W - 6 || y < 6 || y > H - 6)) return;
    const w = textW(pl.n, must ? 15 : 14);
    const dot = must ? 6 : 3.5;
    const near = Math.hypot(x - tx, y - ty) < 16;
    const tries = [];
    for (const dy of [0, 14, -14, 26, -26]) for (const side of [1, -1]) tries.push({ side, dy, off: near ? 15 : 0 });
    for (const dy of [16, -16, 30, -30, 44, -44]) tries.push({ side: 0, dy, off: 0 });          // a long name that fits on neither side: centred under or over its mark
    const spot = (t) => {
      const dx = Math.min(Math.max(x + t.side * t.off, 8), W - 8);
      const dyy = Math.min(Math.max(y + (near ? 3 : 0) + t.dy, 10), H - 10);
      const l = t.side === 0 ? dx - w / 2 : t.side > 0 ? dx + dot + 3 : dx - dot - 3 - w;
      return { dx, dy: dyy, l, box: { l, r: l + w, t: dyy - 10, b: dyy + 10 }, dotBox: { l: dx - dot, r: dx + dot, t: dyy - dot, b: dyy + dot } };
    };
    const inside = (b) => b.l >= 2 && b.r <= W - 2 && b.t >= 2 && b.b <= H - 2;
    let pick = null;
    for (const t of tries) {
      const sp = spot(t);
      if (!inside(sp.box) || used.some((u) => hit(u, sp.box) || hit(u, sp.dotBox))) continue;
      pick = { t, sp };
      break;
    }
    if (!pick && must) {                               // nothing clear: the first spot that at least stays off the pin
      for (const t of tries) { const sp = spot(t); if (inside(sp.box) && !used.slice(0, 2).some((u) => hit(u, sp.box) || hit(u, sp.dotBox))) { pick = { t, sp }; break; } }
      if (!pick) for (const t of tries) { const sp = spot(t); if (inside(sp.box)) { pick = { t, sp }; break; } }
    }
    if (!pick) return;
    used.push(pick.sp.box, pick.sp.dotBox);
    marks.push({ pl, kind, x: pick.sp.dx, y: pick.sp.dy, side: pick.t.side, l: pick.sp.l, w });
  };
  if (capital) label(capital, 'cap');
  towns.forEach((t) => label(t, 'town'));
  const overlay = marks.map((m) => {
    const mark = m.kind === 'cap'
      ? `<text class="mm-star" x="${m.x}" y="${m.y + 5}" text-anchor="middle" font-size="15">★</text>`
      : `<circle class="mm-town" cx="${m.x}" cy="${m.y}" r="3.2"/>`;
    return `${mark}<text class="mm-name${m.kind === 'cap' ? ' cap' : ''}" x="${m.side === 0 ? m.l + m.w / 2 : m.side > 0 ? m.l : m.l + m.w}" y="${m.y + 4.5}" text-anchor="${m.side === 0 ? 'middle' : m.side > 0 ? 'start' : 'end'}">${esc(m.pl.n)}</text>`;
  }).join('');
  const color = pinColor(p.main);
  stage.pinsEl.innerHTML = `<svg class="mm-labels" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true" focusable="false">${overlay}<g transform="translate(${hx.toFixed(1)} ${hy.toFixed(1)})" class="mm-maker-pin">${pinArt({ r, color, tip: [tx - hx, ty - hy] })}</g></svg>`;

  // the whole country in the corner, with the province hatched
  const skip = INSET_SKIP[p.cid] || [];
  const set = skip.includes(prov.id) ? data.provinces : data.provinces.filter((x) => !skip.includes(x.id));
  const bb = [Math.min(...set.map((x) => x.bb[0])), Math.min(...set.map((x) => x.bb[1])), Math.max(...set.map((x) => x.bb[2])), Math.max(...set.map((x) => x.bb[3]))];
  const iw = 76;
  const ih = 76;
  // the inset takes the corner that has nothing in it: not over the pin and not over a label
  const corners = [[W - iw - 6, H - ih - 6], [6, H - ih - 6], [W - iw - 6, 6], [6, 6]];
  const [ix, iy] = corners.find(([cx, cy]) => !used.some((u) => hit(u, { l: cx, r: cx + iw, t: cy, b: cy + ih }))) || corners[0];
  const ps = Math.min((iw - 10) / (bb[2] - bb[0]), (ih - 10) / (bb[3] - bb[1]));
  const itx = (iw - ps * (bb[2] - bb[0])) / 2 - ps * bb[0];
  const ity = (ih - ps * (bb[3] - bb[1])) / 2 - ps * bb[1];
  host.insertAdjacentHTML('beforeend', `<svg class="mm-inset" style="left:${ix}px;top:${iy}px" width="${iw}" height="${ih}" viewBox="0 0 ${iw} ${ih}" aria-hidden="true" focusable="false"><defs>${HATCH(`mm-ig-${stage.uid}`, '#f4c27a', 0.95)}</defs>
<g transform="translate(${itx.toFixed(2)} ${ity.toFixed(2)}) scale(${ps})">${set.map((x) => `<path d="${x.d}"${x.id === prov.id ? ` class="sel" style="fill:url(#mm-ig-${stage.uid})"` : ''}/>`).join('')}</g></svg>`);
  const inset = host.querySelector('.mm-inset');
  inset.querySelector('pattern').setAttribute('patternTransform', `rotate(45) scale(${(1 / ps).toFixed(5)})`);

  const place = p.location || p.provName;
  host.setAttribute('role', 'img');
  host.setAttribute('aria-label', `Map of ${prov.name}, ${p.country}, showing ${p.name}${place ? ` in ${place}` : ''}${capital ? `, with ${capital.n} the capital` : ''}.`);
  return stage;
}
