// Entry point: hash router and page lifecycle. Hash routes work on GitHub Pages without server-side routing.
//
// Phase 1 shows the welcome page only. From Phase 2 the bar is the background of every page: one fixed plate (backdrop.js)
// stays in place while the page changes in front of it, and the same split burger menu sits at the top right of every
// inner page (Plan 08 sections 3 and 5).
import { fixedBurgerHTML, mountBurger } from './burger.js';
import { fitCrumbs, emptyHTML, loadGlossary, wireGlossary } from './chrome.js';
import { mountBackdrop } from './backdrop.js';
import { getBuild, getIndex, getSections, initData } from './data.js';
import { ensureDefs } from './labels.js';
import { loadScene } from './shells.js';
import { $, $$, debounce, esc, fmtDate, parseHash, plural, reducedMotion, setTitle } from './util.js';

const app = $('#page');
const state = { lastShelf: null, picked: {}, backdrop: false };
let current = null; // { name, handle }
let routing = 0;
let backdrop = null;

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
  app.innerHTML = emptyHTML(message);
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

// ---- moving between pages (Plan 08 section 5) -------------------------------------------------------------------------
// The plate stays put. Leaving the welcome page, the bottles and counter fade out (200ms) while the dimming comes in; the
// boards then fade and rise in (240ms, transform and opacity only). Coming back reverses it. Reduced motion: a plain
// 150ms cross-fade.

const isInner = (name) => name !== 'welcome';

function layers(name) {
  return name === 'welcome' ? $$('.scene3 .cover > :not(.plate)', app) : $$('.crumbs, .boards', app);
}

async function leave(from, to) {
  if (!state.backdrop) return;
  if (isInner(to)) document.body.dataset.dim = '1'; else delete document.body.dataset.dim;
  if (!from || isInner(from) === isInner(to)) return;                               // inner to inner: the new boards simply rise in
  const rm = reducedMotion();
  const out = rm ? { opacity: 0 } : { opacity: 0, transform: isInner(from) ? 'translateY(10px)' : 'none' };
  await Promise.all(layers(from).map((el) => el.animate([{ opacity: 1, transform: 'none' }, out],
    { duration: rm ? 75 : 200, easing: 'ease-in', fill: 'forwards' }).finished.catch(() => {})));
}

function enter(name, from) {
  if (!state.backdrop) return;
  const rm = reducedMotion();
  if (name === 'welcome') {
    if (from && isInner(from)) {
      layers('welcome').forEach((el) => el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: rm ? 75 : 200, easing: 'ease-out' }));
    }
    return;
  }
  const page = $('.inner', app);
  if (!page) return;
  if (rm) { page.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 75, easing: 'linear' }); return; }
  page.classList.add('enter');                                             // CSS: boards fade and rise in over 240ms
  setTimeout(() => page.classList.remove('enter'), 400);
}

/** `data-ready` on <body> is the "route ready" signal: set once the page is mounted, its data and map are in, the fonts are
 * loaded and the move between pages (section 5) has finished; cleared as soon as a new route starts. Tests wait on it. */
const setReady = (on) => { if (on) document.body.dataset.ready = '1'; else delete document.body.dataset.ready; };
async function settled(ticket) {
  // Only animations that are running can finish, and a tab that is in the background never draws a frame, so the wait for
  // them is capped: the flag is always set soon after the page is mounted, never left unset for good.
  const cap = new Promise((r) => setTimeout(r, 1500));
  const run = async () => {
    await document.fonts?.ready;
    await Promise.all(app.getAnimations({ subtree: true }).filter((a) => a.playState === 'running').map((a) => a.finished.catch(() => {})));
  };
  await Promise.race([run(), cap]);
  if (ticket === routing) setReady(true);
}

async function route() {
  const ticket = ++routing;
  setReady(false);
  let ix;
  try {
    ix = await getIndex();
  } catch (err) {
    app.innerHTML = `<section class="chalkboard chalkboard--xl" style="margin:40px auto;max-width:560px"><h1 class="t-title">The bar is closed</h1><p class="t-body">The site data could not be loaded (${esc(err.message)}). If you opened this page straight from a folder, serve it over http instead, for example with <code>preview.bat</code>.</p></section>`;
    return;
  }
  if (ticket !== routing) return;
  const ctx = { ...resolve(ix), ix, build: getBuild(), state };
  const from = current?.name || null;
  if (ctx.name === 'notfound') {
    await leave(from, 'notfound');
    if (ticket !== routing) return;
    current?.handle?.unmount?.();
    current = { name: 'notfound', handle: {} };
    emptyShelf();
    window.scrollTo(0, 0);
    backdrop?.relayout();
    enter('notfound', from);
    fitCrumbs(app);
    $('h1', app)?.focus({ preventScroll: true });
    settled(ticket);
    return;
  }
  // same page: let it update itself (welcome selection swaps, shelf filters from the Back button)
  if (current && current.name === ctx.name && current.handle?.update && current.handle.sameTarget?.(ctx)) {
    current.handle.update(ctx);
    settled(ticket);
    return;
  }
  const mod = await PAGES[ctx.name]();
  if (ticket !== routing) return;
  await leave(from, ctx.name);
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
    backdrop?.relayout();
    fitCrumbs(app);
    $('h1', app)?.focus({ preventScroll: true });
  }
  enter(ctx.name, from);
  settled(ticket);
}

function footer(build) {
  const el = $('#footer');
  if (!el) return;
  const bits = [];
  if (build?.generated) bits.push(`Last updated ${esc(fmtDate(build.generated.slice(0, 10)))}`);
  if (build) bits.push(plural(build.drinkCount, 'drink'));
  bits.push('Map: Natural Earth (public domain)');
  bits.push('Type: Kalam (SIL Open Font Licence)');
  bits.push('Icons: Phosphor (MIT)');
  el.innerHTML = `<span>${bits.join(' · ')}</span>`;
}

/** From Phase 2: the fixed bar behind every page and the burger menu at the top right of every inner page. */
async function setupChrome(ix) {
  const scene = await loadScene();
  if (!scene?.plates?.wide || !scene?.plates?.tall) return;
  backdrop = mountBackdrop(scene);
  state.backdrop = true;
  const chrome = $('#chrome');
  if (!chrome || !scene.burger?.layers?.length) return;
  chrome.innerHTML = fixedBurgerHTML(scene.burger);
  // the open menu is sized as if the burger stood on the counter, so it matches the one on the welcome page
  const restHeight = () => {
    const P = scene.plates[document.documentElement.dataset.plate || 'wide'];
    const cover = $('#backdrop .plate-cover')?.getBoundingClientRect();
    return (P.counter?.burger?.h || 0.1) * (cover ? cover.height : window.innerHeight);
  };
  mountBurger(chrome, { B: scene.burger, ix, restHeight });
}

async function boot() {
  ensureDefs();
  wireGlossary();
  const build = await initData();
  footer(build);
  if (getSections().drinks) loadGlossary();
  if (getSections().shelves) {
    try { await setupChrome(await getIndex()); } catch { /* the page still works on a plain dark background */ }
  }
  window.addEventListener('hashchange', route);
  const refit = debounce(() => fitCrumbs(app), 120);
  window.addEventListener('resize', refit);
  document.fonts?.ready.then(() => fitCrumbs(app));
  route();
}

boot();
