// Japan prefecture map, drawn in chalk (Plan 08 sections 4.3 and 4.4). The SVG (assets/japan-prefectures.svg) is derived from
// Natural Earth, which is public domain; see assets/japan-prefectures.LICENSE.txt. The outline is chalk strokes on the
// slate, a prefecture with makers is lightly hatched, and the picked one is hatched in --glow chalk with a chalk circle
// round it.
import { withVersion } from './data.js';

const NS = 'http://www.w3.org/2000/svg';
let svgText = null;

export async function loadJapanMap() {
  if (!svgText) {
    svgText = fetch(withVersion('assets/japan-prefectures.svg')).then((r) => {
      if (!r.ok) throw new Error('map');
      return r.text();
    }).catch(() => { svgText = null; return ''; });
  }
  return svgText;
}

const HATCH = (id, colour, opacity) => `<pattern id="${id}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="${colour}" stroke-opacity="${opacity}" stroke-width="2.2"/></pattern>`;

/** Inline the map into `el` and return the <svg> element, or null when it could not be loaded. */
export async function insertMap(el, { label = 'Map of Japan' } = {}) {
  const text = await loadJapanMap();
  if (!text) return null;
  el.innerHTML = text;
  const svg = el.querySelector('svg');
  svg.setAttribute('class', 'jp-map');
  svg.setAttribute('role', 'group');
  svg.setAttribute('aria-label', label);
  svg.removeAttribute('width');
  svg.removeAttribute('height');
  svg.insertAdjacentHTML('afterbegin', `<defs>${HATCH('hatch-light', '#f2ede4', 0.4)}${HATCH('hatch-glow', '#f4c27a', 0.95)}</defs>`);
  return svg;
}

/** A hand-drawn chalk circle round a prefecture: a slightly uneven loop that overshoots where it closes. */
export function addRing(svg, path) {
  const b = path.getBBox();
  const cx = b.x + b.width / 2;
  const cy = b.y + b.height / 2;
  const rx = Math.max(b.width / 2 + 14, 22);
  const ry = Math.max(b.height / 2 + 14, 22);
  const pts = [];
  const n = 40;
  for (let i = 0; i <= n + 3; i++) {
    const a = -Math.PI * 0.55 + (i / n) * Math.PI * 2;
    const wobble = 1 + 0.035 * Math.sin(a * 3 + 0.8) + 0.02 * Math.sin(a * 5) + (i > n ? 0.05 * (i - n) : 0);
    pts.push(`${(cx + Math.cos(a) * rx * wobble).toFixed(1)} ${(cy + Math.sin(a) * ry * wobble).toFixed(1)}`);
  }
  const ring = document.createElementNS(NS, 'path');
  ring.setAttribute('class', 'ring');
  ring.setAttribute('d', `M${pts.join('L')}`);
  ring.setAttribute('aria-hidden', 'true');
  svg.appendChild(ring);
  return ring;
}
