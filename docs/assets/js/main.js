// Entry point: hash router and page lifecycle. Hash routes work on GitHub Pages without server-side routing.
import { ensureDefs } from './bottles.js';
import { getBuild, getIndex, getSections, initData } from './data.js';
import { emptyScene, wireGlossary, loadGlossary, topbar } from './chrome.js';
import { wireMenu } from './menu.js';
import { $, esc, fmtDate, parseHash, plural, setTitle } from './util.js';

const app = $('#page');
const state = { lastShelf: null };
let current = null; // { name, handle }
let routing = 0;

const PAGES = {
  welcome: () => import('./welcome.js'),
  shelf: () => import('./shelf.js'),
  drink: () => import('./drink.js'),
  producer: () => import('./producer.js'),
  makers: () => import('./makers.js'),
};

function emptyShelf(message = 'This shelf is empty') {
  setTitle('Empty shelf');
  document.body.dataset.page = 'empty';
  app.innerHTML = topbar([{ label: 'Empty shelf' }]) + emptyScene(message);
}

/** Links from before the rename: #/umeshu goes to #/liqueur, and #/umeshu/<kind> to the Umeshu bottle. */
function redirectOld() {
  const { segs } = parseHash();
  if (segs[0] !== 'umeshu') return;
  const target = segs.length > 1 ? '#/liqueur/umeshu' : '#/liqueur';
  history.replaceState(null, '', target + (location.hash.includes('?') ? location.hash.slice(location.hash.indexOf('?')) : ''));
}

/** Phase 1 (welcome page only): every other route goes to the bar, with the category selected when there is one. */
function redirectGated(ix) {
  const sec = getSections();
  const { segs } = parseHash();
  if (sec.shelves || !segs.length) return;
  const target = segs.length === 1 && ix.cats.has(segs[0]) ? `#/${segs[0]}`
    : segs.length === 2 && ix.cats.has(segs[0]) && segs[0] !== 'drink' && segs[0] !== 'producer' ? `#/${segs[0]}` : '#/';
  if (location.hash.replace(/\?.*$/, '') !== target) history.replaceState(null, '', target);
}

function resolve(ix) {
  redirectOld();
  redirectGated(ix);
  const { segs, params } = parseHash();
  if (!segs.length) return { name: 'welcome', cat: null, segs, params };
  const [a, b] = segs;
  if (a === 'makers' && segs.length === 1) return { name: 'makers', segs, params };
  if (a === 'producer' && b && segs.length === 2) return { name: 'producer', key: b, segs, params };
  if (a === 'drink' && b && segs.length === 2) return { name: 'drink', id: b, segs, params };
  if (segs.length === 1 && ix.cats.has(a)) return { name: 'welcome', cat: a, segs, params };
  if (segs.length === 2 && ix.subs.has(`${a}/${b}`)) return { name: 'shelf', cat: a, sub: b, segs, params };
  return { name: 'notfound', segs, params };
}

async function route() {
  const ticket = ++routing;
  let ix;
  try {
    ix = await getIndex();
  } catch (err) {
    app.innerHTML = `<section class="empty-scene"><h1>The bar is closed</h1><p>The site data could not be loaded (${esc(err.message)}). If you opened this page straight from a folder, serve it over http instead, for example with <code>preview.bat</code>.</p></section>`;
    return;
  }
  if (ticket !== routing) return;
  const ctx = { ...resolve(ix), ix, build: getBuild(), state };
  if (ctx.name === 'notfound') {
    current?.handle?.unmount?.();
    current = null;
    emptyShelf();
    window.scrollTo(0, 0);
    return;
  }
  // same page: let it update itself (welcome selection swaps, shelf filters from the Back button)
  if (current && current.name === ctx.name && current.handle?.update && current.handle.sameTarget?.(ctx)) {
    current.handle.update(ctx);
    return;
  }
  const mod = await PAGES[ctx.name]();
  if (ticket !== routing) return;
  current?.handle?.unmount?.();
  app.innerHTML = '';
  app.removeAttribute('aria-busy');
  document.body.dataset.page = ctx.name;
  const handle = (await mod.mount(app, ctx)) || {};
  if (ticket !== routing) { handle.unmount?.(); return; }
  current = { name: ctx.name, handle };
  if (ctx.name !== 'welcome') {
    window.scrollTo(0, 0);
    $('h1', app)?.focus({ preventScroll: true });
  }
}

function footer(build) {
  const el = $('#footer');
  if (!el) return;
  const bits = [];
  if (build?.generated) bits.push(`Last updated ${esc(fmtDate(build.generated.slice(0, 10)))}`);
  if (build) bits.push(plural(build.drinkCount, 'drink'));
  bits.push('Map: Natural Earth (public domain)');
  bits.push('Type: Outfit, Cormorant Garamond, Kalam, Rye, Stardos Stencil (SIL Open Font Licence)');
  bits.push('Icons: Phosphor (MIT)');
  el.innerHTML = bits.join(' · ');
}

async function boot() {
  ensureDefs();
  wireGlossary();
  wireMenu();
  const build = await initData();
  footer(build);
  if (getSections().drinks) loadGlossary();
  window.addEventListener('hashchange', route);
  route();
}

boot();
