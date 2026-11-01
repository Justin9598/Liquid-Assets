// Bottle and glass artwork (Plan 01 sections 3 and 7). Every shape is drawn in SVG in a 100 x 300 box,
// with three parts: glass, liquid and a label area with a clip path. The clip paths and gradients live once
// in a hidden <defs> block (ensureDefs); each bottle then references them.
import { esc, rand } from './util.js';

// Vessel specs. `body` is the glass outline; `label` is the label area in the same coordinates.
export const SPECS = {
  sake: {
    body: 'M41 38 L41 108 C41 134 13 142 13 176 L13 278 Q13 290 25 290 L75 290 Q87 290 87 278 L87 176 C87 142 59 134 59 108 L59 38 Z',
    glass: ['#241d12', '#4b3e24'], liquid: ['#b99a4a', 120], opacity: 0.9,
    label: { x: 17, y: 186, w: 66, h: 78, shape: 'rect' },
    cap: '<rect x="37" y="17" width="26" height="23" rx="3" fill="#c9a24a"/><path d="M40 22v14M45 22v14M50 22v14M55 22v14M60 22v14" stroke="#8a6b25" stroke-width="1"/>',
  },
  makgeolli: {
    body: 'M38 56 L38 82 C38 98 14 100 14 124 L14 270 Q14 290 32 290 L68 290 Q86 290 86 270 L86 124 C86 100 62 98 62 82 L62 56 Z',
    glass: ['#9fb9c3', '#d6e6ec'], liquid: ['#f3ecd9', 100], opacity: 0.95,
    label: { x: 16, y: 134, w: 68, h: 112, shape: 'rect' },
    cap: '<rect x="34" y="36" width="32" height="22" rx="4" fill="#2e8b7a"/><path d="M38 40v14M43 40v14M48 40v14M53 40v14M58 40v14" stroke="#1f6356" stroke-width="1"/>',
    extra: '<path d="M14 106H86M14 112H86M14 262H86M14 268H86" stroke="rgba(255,255,255,.45)" stroke-width="1.2"/>',
  },
  liqueur: {
    body: 'M42 108 L42 130 C42 146 6 150 6 192 L6 274 Q6 290 22 290 L78 290 Q94 290 94 274 L94 192 C94 150 58 146 58 130 L58 108 Z',
    glass: ['#c9d8dc', '#eef4f5'], liquid: ['#c98a2b', 152], opacity: 0.85,
    label: { x: 20, y: 192, w: 60, h: 62, shape: 'ellipse' },
    cap: '<rect x="39" y="92" width="22" height="18" rx="3" fill="#b8905a"/>',
  },
  beer: {
    body: 'M42 28 L42 128 C42 148 24 158 24 184 L24 280 Q24 290 34 290 L66 290 Q76 290 76 280 L76 184 C76 158 58 148 58 128 L58 28 Z',
    glass: ['#3a1f0c', '#7a4a1e'], liquid: ['#b9741f', 100], opacity: 0.9,
    label: { x: 25, y: 192, w: 50, h: 68, shape: 'ellipse' },
    cap: '<path d="M38 19h24l-2 11H40z" fill="#c9a24a"/><path d="M41 19v11M46 19v11M50 19v11M54 19v11M59 19v11" stroke="#8a6b25" stroke-width="1"/>',
  },
  wine: {
    body: 'M43 36 L43 112 C43 122 17 124 17 144 L17 278 Q17 290 29 290 L71 290 Q83 290 83 278 L83 144 C83 124 57 122 57 112 L57 36 Z',
    glass: ['#13281a', '#2d5238'], liquid: ['#3a1220', 140], opacity: 0.9,
    label: { x: 19, y: 164, w: 62, h: 92, shape: 'rect' },
    cap: '<rect x="40" y="19" width="20" height="40" rx="2" fill="#6b1f2a"/><path d="M40 55h20" stroke="#4a1019" stroke-width="2"/>',
    extra: '<path d="M26 290 Q50 268 74 290" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="2"/>',
  },
  spirits: {
    body: 'M38 64 L38 94 Q38 100 30 102 L22 104 Q14 106 14 114 L14 274 Q14 290 30 290 L70 290 Q86 290 86 274 L86 114 Q86 106 78 104 L70 102 Q62 100 62 94 L62 64 Z',
    glass: ['#b9a67f', '#e8dcc0'], liquid: ['#b8741a', 122], opacity: 0.85,
    label: { x: 22, y: 150, w: 56, h: 84, shape: 'rect' },
    cap: '<rect x="35" y="43" width="30" height="23" rx="6" fill="#a98a62"/><path d="M40 50h20" stroke="#7d6340" stroke-width="1"/>',
    extra: '<rect x="14" y="264" width="72" height="26" fill="rgba(255,255,255,.2)"/>',
  },
  // top-shelf glass: coupe with a garnish (no label)
  cocktail: {
    body: 'M10 62 C10 112 36 136 50 136 C64 136 90 112 90 62 Z',
    glass: ['#c8dbe3', '#eef6f9'], liquid: ['#e9c991', 86], opacity: 0.9,
    label: null,
    cap: '',
    extra: '<rect x="47" y="134" width="6" height="114" rx="2" fill="rgba(220,235,242,.55)"/><ellipse cx="50" cy="252" rx="28" ry="6" fill="rgba(220,235,242,.55)"/><path d="M64 34 L38 98" stroke="#b8905a" stroke-width="1.6"/><circle cx="43" cy="88" r="7" fill="#7a8f3a"/><circle cx="43" cy="88" r="2.4" fill="#b8362e"/>',
    noBody: true,
  },
  // lower-shelf cocktail shape: highball glass with a paper tag tied round it
  highball: {
    body: 'M26 80 L74 80 L70 282 Q70 290 62 290 L38 290 Q30 290 30 282 Z',
    glass: ['#c8dbe3', '#eef6f9'], liquid: ['#d9a24a', 110], opacity: 0.85,
    label: { x: 32, y: 152, w: 36, h: 48, shape: 'rect', rotate: -6 },
    cap: '',
    extra: '<rect x="37" y="214" width="12" height="12" rx="2" fill="rgba(255,255,255,.28)"/><rect x="51" y="236" width="12" height="12" rx="2" fill="rgba(255,255,255,.22)"/><rect x="38" y="258" width="11" height="11" rx="2" fill="rgba(255,255,255,.25)"/>',
    tag: true,
  },
};

// Category key -> shape used on the lower shelves
/** Fallback-label motif: vine for wine, a plum blossom for the Umeshu subcategory (Plan 01 sections 3 and 4.3). */
export const motifFor = (catKey, subKey) => (catKey === 'wine' ? 'vine' : catKey === 'liqueur' && subKey === 'umeshu' ? 'blossom' : null);

export const shapeFor = (catKey) => (catKey === 'cocktails' ? 'highball' : (SPECS[catKey] ? catKey : 'sake'));

// Default labels for the mixed view when a category has no photo (Plan 01 section 3, last column)
export const DEFAULT_LABEL = {
  sake: { native: '酒', name: 'Sake' },
  makgeolli: { native: '막걸리', name: 'Makgeolli' },
  liqueur: { name: 'LIQUEUR' },
  beer: { name: 'BEER' },
  wine: { name: 'Wine', motif: 'vine' },
  spirits: { name: 'Spirits' },
  cocktails: { name: 'Cocktail' },
  cocktail: { name: 'Cocktail' },
};

let defsDone = false;
export function ensureDefs() {
  if (defsDone) return;
  defsDone = true;
  let defs = '';
  for (const [key, s] of Object.entries(SPECS)) {
    defs += `<linearGradient id="gl-${key}" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="${s.glass[0]}"/><stop offset=".22" stop-color="${s.glass[1]}"/><stop offset=".5" stop-color="${s.glass[0]}"/><stop offset="1" stop-color="${s.glass[0]}"/></linearGradient>`;
    defs += `<clipPath id="cb-${key}"><path d="${s.body}"/></clipPath>`;
    if (s.label) {
      const L = s.label;
      const tr = L.rotate ? ` transform="rotate(${L.rotate} ${L.x + L.w / 2} ${L.y + L.h / 2})"` : '';
      const shape = L.shape === 'ellipse'
        ? `<ellipse cx="${L.x + L.w / 2}" cy="${L.y + L.h / 2}" rx="${L.w / 2}" ry="${L.h / 2}"/>`
        : `<rect x="${L.x}" y="${L.y}" width="${L.w}" height="${L.h}" rx="2"${tr}/>`;
      defs += `<clipPath id="cl-${key}">${shape}</clipPath>`;
    }
  }
  defs += '<linearGradient id="shade" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".5"/><stop offset=".3" stop-color="#000" stop-opacity="0"/><stop offset=".62" stop-color="#fff" stop-opacity=".12"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>';
  defs += '<linearGradient id="washi" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#f1e9d6"/><stop offset="1" stop-color="#e2d5b8"/></linearGradient>';
  const host = document.createElement('div');
  host.innerHTML = `<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>${defs}</defs></svg>`;
  document.body.prepend(host.firstChild);
}

// ---- label art ---------------------------------------------------------------------------------------------

const CJK_FONT = '"Noto Serif JP","Yu Mincho","Hiragino Mincho ProN","Noto Serif KR","Malgun Gothic",serif';
const SANS_FONT = 'Outfit,system-ui,sans-serif';

function wrap(text, maxChars, maxLines) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > maxChars && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines);
    kept[maxLines - 1] = kept[maxLines - 1].replace(/\s+\S*$/, '') + '…';
    return kept;
  }
  return lines;
}

/** Illustrated paper label: native name large, English name small (or English large when no native name). */
export function labelArt(L, { native, name, motif } = {}) {
  const { x, y, w, h } = L;
  const cx = x + w / 2;
  let out = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#washi)"/>`;
  out += `<rect x="${x + 2.5}" y="${y + 2.5}" width="${w - 5}" height="${h - 5}" fill="none" stroke="#8a5a33" stroke-opacity=".4" stroke-width=".7"/>`;
  if (motif === 'blossom') {
    const px = cx, py = y + 11;
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2 - Math.PI / 2;
      out += `<circle cx="${(px + Math.cos(a) * 3.4).toFixed(1)}" cy="${(py + Math.sin(a) * 3.4).toFixed(1)}" r="2.6" fill="#d98aa0" opacity=".9"/>`;
    }
    out += `<circle cx="${px}" cy="${py}" r="1.4" fill="#c9a24a"/>`;
  } else if (motif === 'vine') {
    out += `<path d="M${x + 8} ${y + 14} q10 -9 20 0 t20 0" fill="none" stroke="#4d6b3a" stroke-width="1"/>`;
    out += `<circle cx="${x + 18}" cy="${y + 12}" r="2" fill="#4d6b3a"/><circle cx="${x + 30}" cy="${y + 15}" r="2" fill="#4d6b3a"/><circle cx="${x + 42}" cy="${y + 12}" r="2" fill="#4d6b3a"/>`;
  }
  const hasMotif = !!motif;
  if (native) {
    const n = [...native].length;
    const fs = Math.max(8, Math.min(h > 80 ? 26 : 20, (w - 10) / n));
    const ny = y + h * (name ? (hasMotif ? 0.58 : 0.5) : 0.55) + fs * 0.1;
    out += `<text x="${cx}" y="${ny.toFixed(1)}" text-anchor="middle" font-size="${fs.toFixed(1)}" font-weight="700" fill="#2a1d14" font-family='${CJK_FONT}'>${esc(native)}</text>`;
    if (name) {
      const fsn = Math.min(6.4, (w - 10) / (Math.max(...wrap(name, 14, 2).map((l) => l.length)) * 0.6));
      wrap(name, Math.max(8, Math.floor((w - 8) / (fsn * 0.58))), 2).forEach((line, i, arr) => {
        out += `<text x="${cx}" y="${(y + h - 7 - (arr.length - 1 - i) * (fsn + 1.2)).toFixed(1)}" text-anchor="middle" font-size="${fsn.toFixed(1)}" fill="#6b5a4a" font-family='${SANS_FONT}' letter-spacing=".4">${esc(line)}</text>`;
      });
    }
  } else if (name) {
    const lines = wrap(name, 12, 3);
    const longest = Math.max(...lines.map((l) => l.length));
    const fs = Math.max(6, Math.min(13, (w - 10) / (longest * 0.62)));
    const total = lines.length * fs * 1.15;
    let ty = y + (h - total) / 2 + fs * 0.9 + (hasMotif ? 6 : 0);
    for (const line of lines) {
      out += `<text x="${cx}" y="${ty.toFixed(1)}" text-anchor="middle" font-size="${fs.toFixed(1)}" font-weight="700" fill="#2a1d14" font-family='"Cormorant Garamond",Georgia,serif'>${esc(line)}</text>`;
      ty += fs * 1.15;
    }
  }
  return out;
}

function photoLabel(L, url) {
  return `<image href="${esc(url)}" x="${L.x}" y="${L.y}" width="${L.w}" height="${L.h}" preserveAspectRatio="xMidYMid slice"/>`;
}

let uid = 0;

/**
 * Returns an <svg> string for a bottle.
 *  shape:  key of SPECS
 *  label:  URL of a photo label, or null for the illustrated paper label
 *  native / name / motif: used by the paper label
 */
export function bottleSVG(shape, { label = null, native = null, name = null, motif = null, cls = '' } = {}) {
  const s = SPECS[shape] || SPECS.sake;
  const key = SPECS[shape] ? shape : 'sake';
  const id = `b${++uid}`;
  let g = '';
  const GLASS_OP = { sake: 0.92, makgeolli: 0.3, liqueur: 0.2, beer: 0.9, wine: 0.95, spirits: 0.28, cocktail: 0.35, highball: 0.3 };
  // liquid first (clipped to the glass), then the glass over it
  g += `<g clip-path="url(#cb-${key})"><rect x="0" y="${s.liquid[1]}" width="100" height="300" fill="${s.liquid[0]}" opacity="${s.opacity}"/>${s.extra && !s.noBody ? s.extra : ''}</g>`;
  g += `<path d="${s.body}" fill="url(#gl-${key})" opacity="${GLASS_OP[key]}"/>`;
  if (s.noBody) g += s.extra;
  g += s.cap || '';
  if (s.label) {
    const L = s.label;
    const art = label ? photoLabel(L, label) : labelArt(L, { native, name, motif });
    const tr = L.rotate ? ` transform="rotate(${L.rotate} ${L.x + L.w / 2} ${L.y + L.h / 2})"` : '';
    if (s.tag) {
      // string and tag tied round the glass
      g += `<path d="M${L.x + L.w / 2} ${L.y + 2} C ${L.x - 8} ${L.y - 18}, ${L.x + L.w + 8} ${L.y - 18}, ${L.x + L.w / 2} ${L.y + 2}" fill="none" stroke="#b8905a" stroke-width="1.2"/>`;
    }
    g += `<g clip-path="url(#cl-${key})">${art}<rect x="${L.x}" y="${L.y}" width="${L.w}" height="${L.h}" fill="url(#shade)"${tr}/></g>`;
    if (L.shape === 'ellipse') {
      g += `<ellipse cx="${L.x + L.w / 2}" cy="${L.y + L.h / 2}" rx="${L.w / 2}" ry="${L.h / 2}" fill="none" stroke="rgba(0,0,0,.35)" stroke-width="1"/>`;
    } else {
      g += `<rect x="${L.x}" y="${L.y}" width="${L.w}" height="${L.h}" rx="2" fill="none" stroke="rgba(0,0,0,.3)" stroke-width="1"${tr}/>`;
    }
  }
  // highlight edge (nothing loops: no idle shine, Plan 01 section 3)
  g += `<path d="${s.body}" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1.2"/>`;
  return `<svg class="bottle bottle-${key} ${cls}" id="${id}" viewBox="0 0 100 300" aria-hidden="true" focusable="false">${g}</svg>`;
}

/** Fallback art for a drink with no photo: the category bottle on a soft paper background (Plan 02 section 7.1). */
export function sketchSVG(shape, info) {
  return `<span class="sketch">${bottleSVG(shape, { ...info, cls: 'sketched' })}</span>`;
}

export function randomPick(list, used) {
  const pool = list.filter((l) => !used.has(l));
  if (!pool.length) return null;
  const pick = rand(pool);
  used.add(pick);
  return pick;
}
