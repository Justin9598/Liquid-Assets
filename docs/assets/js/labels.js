// The illustrated paper label that goes on a bottle shell when the drink has no label photo (Plan 01 section 6), plus the
// shape and label defaults shared by the welcome shelves, the counter and the inner pages. The bottles themselves are the
// rendered shells (Plan 07 section 2); nothing here draws a bottle.
import { esc, rand } from './util.js';

/** Fallback-label motif: vine for wine, a plum blossom for the Umeshu subcategory (Plan 01 sections 3 and 4.3). */
export const motifFor = (catKey) => (catKey === 'wine' ? 'vine' : catKey === 'umeshu' ? 'blossom' : null);

const SHAPES = new Set(['sake', 'makgeolli', 'liqueur', 'beer', 'wine', 'spirits', 'cocktail', 'highball']);
/** The shell for a category, and for a subcategory where it differs (Plan 10 section 2): makgeolli has its own bottle, the beer
 * styles share the beer bottle, umeshu and liqueur use the liquor bottle, cocktails the highball glass. */
export const shapeFor = (catKey, subKey) => {
  if (catKey === 'fermented') return subKey === 'makgeolli' ? 'makgeolli' : 'beer';
  if (catKey === 'umeshu') return 'liqueur';
  if (catKey === 'cocktails') return 'highball';
  return SHAPES.has(catKey) ? catKey : 'sake';
};

// Default labels for the mixed view when a category has no photo (Plan 01 section 3, last column)
export const DEFAULT_LABEL = {
  sake: { native: '酒', name: 'Sake' },
  makgeolli: { native: '막걸리', name: 'Makgeolli' },
  liqueur: { name: 'LIQUEUR' },
  fermented: { name: 'BEER' },
  umeshu: { native: '梅酒', name: 'Umeshu', motif: 'blossom' },
  beer: { name: 'BEER' },
  wine: { name: 'Wine', motif: 'vine' },
  spirits: { name: 'Spirits' },
  cocktails: { name: 'Cocktail' },
  cocktail: { name: 'Cocktail' },
};

let defsDone = false;
/** The paper gradient the illustrated labels use, in one hidden <defs> block. */
export function ensureDefs() {
  if (defsDone) return;
  defsDone = true;
  const host = document.createElement('div');
  host.innerHTML = '<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs><linearGradient id="washi" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#f1e9d6"/><stop offset="1" stop-color="#e2d5b8"/></linearGradient></defs></svg>';
  document.body.prepend(host.firstChild);
}

// ---- label art ---------------------------------------------------------------------------------------------

const CJK_FONT = '"Noto Serif JP","Yu Mincho","Hiragino Mincho ProN","Noto Serif KR","Malgun Gothic",serif';
const LABEL_FONT = 'Kalam,cursive';

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
        out += `<text x="${cx}" y="${(y + h - 7 - (arr.length - 1 - i) * (fsn + 1.2)).toFixed(1)}" text-anchor="middle" font-size="${fsn.toFixed(1)}" fill="#6b5a4a" font-family='${LABEL_FONT}' letter-spacing=".4">${esc(line)}</text>`;
      });
    }
  } else if (name) {
    const lines = wrap(name, 12, 3);
    const longest = Math.max(...lines.map((l) => l.length));
    const fs = Math.max(6, Math.min(13, (w - 10) / (longest * 0.6)));
    const total = lines.length * fs * 1.15;
    let ty = y + (h - total) / 2 + fs * 0.9 + (hasMotif ? 6 : 0);
    for (const line of lines) {
      out += `<text x="${cx}" y="${ty.toFixed(1)}" text-anchor="middle" font-size="${fs.toFixed(1)}" font-weight="700" fill="#2a1d14" font-family='${LABEL_FONT}'>${esc(line)}</text>`;
      ty += fs * 1.15;
    }
  }
  return out;
}

export function randomPick(list, used) {
  const pool = list.filter((l) => !used.has(l));
  if (!pool.length) return null;
  const pick = rand(pool);
  used.add(pick);
  return pick;
}
