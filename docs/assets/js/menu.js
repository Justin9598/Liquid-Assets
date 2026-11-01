// The counter menu (Plan 01 section 13): a button on the bar counter (and in every page header) that opens a
// full-screen overlay with the site's pages and the About credits.
import { getBuild, getIndex, getSections } from './data.js';
import { icon } from './icons.js';
import { $, $$, esc, fmtDate, parseHash, plural } from './util.js';

/** The round iron puck with the Phosphor List icon, and the word "Menu" beside it on desktop. */
export function menuButton(cls = '') {
  return `<button type="button" class="menu-btn ${cls}" data-menu aria-expanded="false" aria-controls="site-menu" aria-label="Menu"><span class="puck">${icon('list', 24)}</span><span class="menu-label" aria-hidden="true">Menu</span></button>`;
}

let overlay = null;
let opener = null;
let closing = false;

function currentGroup(cats) {
  const { segs } = parseHash();
  if (!segs.length) return { home: true };
  if (segs[0] === 'makers' || segs[0] === 'producer') return { makers: true };
  if (cats.has(segs[0])) return { cat: segs[0] };
  return {};
}

const link = (href, label, extra = '', current = false) =>
  `<a class="menu-link" href="${esc(href)}"${current ? ' aria-current="page"' : ''}><span>${esc(label)}</span>${extra}</a>`;

const CREDITS = [
  'Map: Natural Earth (public domain)',
  'Type: Outfit, Cormorant Garamond, Kalam, Rye and Stardos Stencil (SIL Open Font Licence)',
  'Icons: Phosphor Icons (MIT)',
];

/** The About text, shared with the burger menu: the one-line description and the credits. */
export function aboutHTML(b) {
  const about = b
    ? `A personal log of ${plural(b.drinkCount, 'drink')}, updated ${esc(fmtDate((b.generated || '').slice(0, 10)))}.`
    : 'A personal log of drinks.';
  return `<p>${about}</p>
<ul class="credits">${CREDITS.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>`;
}

async function build() {
  const ix = await getIndex();
  const b = getBuild();
  const cur = currentGroup(ix.cats);
  const shelves = ix.shelf.categories.map((c) =>
    `<li>${link(`#/${c.key}`, c.name, `<span class="count" aria-label="${plural(c.drinkCount, 'drink')}">${c.drinkCount}</span>`, cur.cat === c.key)}</li>`).join('');
  const el = document.createElement('div');
  el.className = 'menu-overlay';
  el.id = 'site-menu';
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  el.setAttribute('aria-label', 'Site menu');
  el.innerHTML = `<div class="menu-backdrop" data-close></div>
<div class="menu-panel">
  <button type="button" class="menu-close" data-close aria-label="Close menu">${icon('x', 24)}</button>
  <div class="menu-cols">
    <nav class="menu-group menu-shelves" aria-labelledby="mh-shelves">
      <h2 id="mh-shelves">Shelves</h2>
      <ul>${shelves}</ul>
    </nav>
    <div class="menu-side">
      <nav class="menu-group" aria-labelledby="mh-bar">
        <h2 id="mh-bar">The Bar</h2>
        <ul><li>${link('#/', 'Home', '', cur.home)}</li></ul>
      </nav>
      <nav class="menu-group" aria-labelledby="mh-makers">
        <h2 id="mh-makers">The Makers</h2>
        ${getSections().makers
    ? `<ul><li>${link('#/makers', 'Every maker', b ? `<span class="count" aria-label="${plural(b.producerCount, 'producer')}">${b.producerCount}</span>` : '', cur.makers)}</li></ul>`
    : '<p class="menu-soon">Soon</p>'}
      </nav>
      <section class="menu-group menu-about" aria-labelledby="mh-about">
        <h2 id="mh-about">About</h2>
        ${aboutHTML(b)}
      </section>
    </div>
  </div>
</div>`;
  return el;
}

const focusables = () => $$('a[href], button:not([disabled])', overlay);

export async function openMenu(from) {
  if (overlay || closing) return;
  opener = from || document.activeElement;
  overlay = await build();
  document.body.appendChild(overlay);
  document.body.classList.add('menu-open');
  $('#main')?.setAttribute('inert', '');
  $$('[data-menu]').forEach((b) => b.setAttribute('aria-expanded', 'true'));
  requestAnimationFrame(() => overlay?.classList.add('open'));
  $('.menu-close', overlay).focus();
}

export function closeMenu({ restoreFocus = true } = {}) {
  if (!overlay || closing) return;
  closing = true;
  const el = overlay;
  el.classList.remove('open');
  $$('[data-menu]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
  $('#main')?.removeAttribute('inert');
  document.body.classList.remove('menu-open');
  const done = () => { el.remove(); if (overlay === el) overlay = null; closing = false; };
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) done(); else setTimeout(done, 260);
  if (restoreFocus) {
    const target = opener && document.contains(opener) ? opener : $('[data-menu]');
    target?.focus();
  }
}

export function wireMenu() {
  document.addEventListener('click', (ev) => {
    const btn = ev.target.closest?.('[data-menu]');
    if (btn) { ev.preventDefault(); openMenu(btn); return; }
    if (!overlay) return;
    if (ev.target.closest('[data-close]')) { closeMenu(); return; }
    if (ev.target.closest('a.menu-link')) closeMenu({ restoreFocus: false }); // navigation follows the link
  });
  document.addEventListener('keydown', (ev) => {
    if (!overlay) return;
    if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); closeMenu(); return; }
    if (ev.key === 'Tab') {
      const f = focusables();
      if (!f.length) return;
      const first = f[0]; const last = f[f.length - 1];
      if (!overlay.contains(document.activeElement)) { ev.preventDefault(); first.focus(); }
      else if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    }
  }, true);
}
