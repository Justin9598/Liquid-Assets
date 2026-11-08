import { icon } from './icons.js';
// Small shared helpers. No dependencies.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ESC[c]);

/** Case- and accent-insensitive comparison key. */
export const fold = (s) => String(s ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
/** Key used for regions and map ids ("Hyōgo" -> "hyogo"). */
export const regionKey = (s) => fold(s).replace(/[^a-z0-9]/g, '');
export const slug = (s) => fold(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

export const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;

/** Parse location.hash into { segs, params }. "#/sake/junmai-ginjo?style=nama,genshu" */
export function parseHash(hash = location.hash) {
  const raw = hash.replace(/^#\/?/, '');
  const [path, query = ''] = raw.split('?');
  const segs = path.split('/').filter(Boolean).map((s) => { try { return decodeURIComponent(s); } catch { return s; } });
  const params = new URLSearchParams(query);
  return { segs, params };
}

export function buildHash(segs, params) {
  let h = '#/' + segs.map(encodeURIComponent).join('/');
  const q = [];
  if (params) for (const [k, v] of Object.entries(params)) if (v !== '' && v != null && v !== false) q.push(`${k}=${encodeURIComponent(v).replace(/%2C/gi, ',')}`);
  if (q.length) h += '?' + q.join('&');
  return h;
}

/** Replace the hash without triggering the router. */
export function replaceHash(hash) {
  if (location.hash !== hash) history.replaceState(null, '', hash);
}

const SIZE_SHORT = { '60ml Tasting': 'Tasting', '90ml Pour': 'Pour', '180ml Carafe': 'Carafe' };
export const sizeShort = (s) => SIZE_SHORT[s] || s;


export function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'T00:00:00Z');
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(d);
}

export const num = (n) => (n == null ? '' : (Number.isInteger(n) ? String(n) : String(+Number(n).toFixed(2))));

export function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function announce(msg) {
  const el = document.getElementById('live');
  if (!el) return;
  el.textContent = '';
  setTimeout(() => { el.textContent = msg; }, 30);
}

export function setTitle(t) {
  document.title = t ? `${t} · Liquid Assets` : 'Liquid Assets';
}

export const rand = (arr) => arr[Math.floor(Math.random() * arr.length)];

/** Truncate for breadcrumbs only. */
export const short = (s, n = 32) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);

export function stars(rating) {
  if (rating == null) return '';
  const out = [];
  for (let i = 1; i <= 5; i++) {
    const cls = rating >= i ? 'full' : rating >= i - 0.5 ? 'half' : 'empty';
    out.push(`<span class="star ${cls}" aria-hidden="true">${icon('star-fill', 14)}</span>`);
  }
  return `<span class="stars" role="img" aria-label="Rated ${rating} out of 5">${out.join('')}</span>`;
}
