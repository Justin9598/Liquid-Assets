// Scene engine (Plan 01 sections 2.3 to 2.5, Plan 07): a rendered plate scaled to cover the viewport, with live layers
// positioned in plate percentages from data/scene.json. Wide for landscape, tall for phones. A plate that is missing
// shows a plain placeholder in its place, so the layout can still be checked.
import { img } from './data.js';
import { esc } from './util.js';
import { labelArt } from './bottles.js';

const pct = (v) => `${+(v * 100).toFixed(3)}%`;

/** Query string from the page URL merged with the hash query, so both `?scene=v3` and `#/?scene=v3` work. */
export function sceneQuery(hashParams) {
  const q = new URLSearchParams(location.search);
  if (hashParams) for (const [k, v] of hashParams) q.set(k, v);
  return q;
}

export const wideQuery = window.matchMedia('(orientation: landscape) and (min-width: 768px)');
export const plateKind = () => (wideQuery.matches ? 'wide' : 'tall');

/** Absolute-position style for a shelf line: the row stands on the line and is as tall as the clear height above it. */
export function shelfStyle(s) {
  return `left:${pct(s.x0)};bottom:${pct(1 - s.y)};width:${pct(s.x1 - s.x0)};height:${pct(s.clear)}`;
}

const anchorStyle = (a) => `left:${pct(a.x)};top:${pct(a.y)}`;
export { anchorStyle };

export function plateHTML(P) {
  const f = P.files;
  if (f && (f.webp?.length || f.avif?.length)) {
    const set = (list) => list.map((x) => `${esc(img(x.url))} ${x.w}w`).join(', ');
    const largest = [...(f.webp || [])].sort((a, b) => b.w - a.w)[0] || f.avif[0];
    return `<picture class="plate">
${f.avif?.length ? `<source type="image/avif" srcset="${set(f.avif)}" sizes="max(100vw, calc(100dvh * ${P.ratio}))">` : ''}
${f.webp?.length ? `<source type="image/webp" srcset="${set(f.webp)}" sizes="max(100vw, calc(100dvh * ${P.ratio}))">` : ''}
<img src="${esc(img(largest.url))}" alt="" decoding="async" fetchpriority="high"></picture>`;
  }
  // plain placeholder plate: flat brick colour, oak shelf boards and counter at the manifest's measured positions
  const first = P.shelves[0];
  const last = P.shelves[P.shelves.length - 1];
  const bay = { x0: Math.min(...P.shelves.map((s) => s.x0)), x1: Math.max(...P.shelves.map((s) => s.x1)) };
  const shelves = P.shelves.map((s) => `<i class="ph-shelf" style="left:${pct(s.x0)};top:${pct(s.y)};width:${pct(s.x1 - s.x0)}"></i>`).join('');
  const sg = P.sign;
  return `<div class="plate placeholder" aria-hidden="true">
<i class="ph-bay" style="left:${pct(bay.x0)};width:${pct(bay.x1 - bay.x0)};top:${pct(first.y - first.clear)};height:${pct(last.y - first.y + first.clear)}"></i>
${shelves}
<i class="ph-sign" style="left:${pct(sg.x0)};top:${pct(sg.y0)};width:${pct(sg.x1 - sg.x0)};height:${pct(sg.y1 - sg.y0)}"></i>
<i class="ph-counter" style="top:${pct(P.counterTop)}"></i></div>`;
}

/** `?debug=scene`: the manifest's lines drawn over the plate, so alignment can be checked by eye. */
export function debugHTML(P) {
  const lines = P.shelves.map((s, i) => `<i class="dbg-clear" style="${shelfStyle(s)}"></i><i class="dbg-line" style="left:${pct(s.x0)};top:${pct(s.y)};width:${pct(s.x1 - s.x0)}"><b>shelf ${i}</b></i>`).join('');
  const sg = P.sign;
  const a = P.anchors;
  return `<div class="dbg" aria-hidden="true">
<i class="dbg-safe" style="left:19%;width:62%;top:8%;height:82%"><b>safe zone</b></i>
${lines}
<i class="dbg-sign" style="left:${pct(sg.x0)};top:${pct(sg.y0)};width:${pct(sg.x1 - sg.x0)};height:${pct(sg.y1 - sg.y0)}"><b>sign</b></i>
<i class="dbg-line dbg-counter" style="left:0;top:${pct(P.counterTop)};width:100%"><b>counter top</b></i>
<i class="dbg-pt" style="${anchorStyle(a.slate)}"><b>slate</b></i><i class="dbg-pt" style="${anchorStyle(a.menu)}"><b>menu</b></i></div>`;
}

/** A bottle assembled from the rendered shell. The label photo goes on the sake's paper label with `multiply` (the shell's
 * shading shows through) and on every other bottle as a normal label stuck to the glass, with a curvature overlay and a
 * soft 1px shadow (Plan 07 section 2.3). Glasses have no label rectangle, so they carry no photo. */
export function shellBottle(manifest, shape, { label, native, name, motif } = {}) {
  const sh = manifest?.shells?.[shape];
  if (!sh || !sh.files) return null;
  let lab = '';
  const blend = sh.labelBlend === 'multiply' ? 'multiply' : 'normal';
  if (sh.labelRect) {
    const [lx, ly, lw, lh] = sh.labelRect;
    let inner;
    if (label) {
      inner = `<img src="${esc(label)}" alt="">`;
    } else {
      const aspect = (lw * sh.aspect) / lh;          // label box width / height in real pixels
      const H = 100 / aspect;
      inner = `<svg viewBox="0 0 100 ${H.toFixed(2)}" preserveAspectRatio="none" aria-hidden="true" focusable="false">${labelArt({ x: 0, y: 0, w: 100, h: +H.toFixed(2) }, { native, name, motif })}</svg>`;
    }
    lab = `<span class="lab ${blend}" style="left:${pct(lx)};top:${pct(ly)};width:${pct(lw)};height:${pct(lh)}">${inner}</span>`;
  }
  const f = sh.files;
  const sd = sh.shadow || { w: 0.8, h: 0.06, opacity: 0.3 };
  const style = `--ar:${sh.aspect};--sc:${sh.scale ?? 1};--sh-w:${pct(sd.w)};--sh-h:${pct(sd.h)};--sh-o:${sd.opacity}`;
  return `<span class="b3 b3-${shape}" style="${style}"><img class="shell" src="${esc(img(f['1x']))}" srcset="${esc(img(f['1x']))} 1x, ${esc(img(f['2x']))} 2x" alt="">${lab}</span>`;
}
