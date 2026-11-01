// Japan prefecture map. The SVG (assets/japan-prefectures.svg) is derived from Natural Earth, which is public
// domain; see assets/japan-prefectures.LICENSE.txt.
import { withVersion } from './data.js';

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
  return svg;
}
