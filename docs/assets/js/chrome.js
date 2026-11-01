// Shared page chrome: the small sign and breadcrumb (Plan 02 section 4), glossary popovers (Plan 03 section 9).
import { getJSON } from './data.js';
import { icon } from './icons.js';
import { menuButton } from './menu.js';
import { esc, fold } from './util.js';

/** crumbs: [{ label, href? }] after "Bar". `home` is the href of the small sign. */
export function topbar(crumbs, home = '#/') {
  const items = [{ label: 'Bar', href: '#/' }, ...crumbs];
  const lis = items.map((c, i) => {
    const last = i === items.length - 1;
    const sep = i ? `<span class="sep" aria-hidden="true">${icon('caret-right', 12)}</span>` : '';
    return `<li>${sep}${last || !c.href ? `<span${last ? ' aria-current="page"' : ''}>${esc(c.label)}</span>` : `<a href="${esc(c.href)}">${esc(c.label)}</a>`}</li>`;
  }).join('');
  return `<header class="topbar">
  <a class="mini-sign" href="${esc(home)}" aria-label="Liquid Assets, back to the bar">Liquid Assets</a>
  <nav class="crumbs" aria-label="Breadcrumb"><ol>${lis}</ol></nav>
  ${menuButton('in-header')}
</header>`;
}

// ---- glossary ------------------------------------------------------------------------------------------------

let glossary = null;
let popover = null;
let openBtn = null;

export async function loadGlossary() {
  if (!glossary) {
    try {
      const raw = await getJSON('glossary.json');
      glossary = new Map(Object.entries(raw).map(([k, v]) => [fold(k), { term: k, def: v }]));
    } catch { glossary = new Map(); }
  }
  return glossary;
}

export const glossaryEntry = (term) => glossary?.get(fold(term)) || null;

/** Wraps a term as a dotted-underline button when the glossary has a definition for it. */
export function termHTML(text, term = text) {
  const e = glossaryEntry(term);
  if (!e) return esc(text);
  return `<button type="button" class="gl" data-term="${esc(e.term)}" aria-expanded="false">${esc(text)}</button>`;
}

function closePopover() {
  if (popover) { popover.remove(); popover = null; }
  if (openBtn) { openBtn.setAttribute('aria-expanded', 'false'); openBtn.removeAttribute('aria-describedby'); openBtn = null; }
}

function openPopover(btn) {
  const e = glossaryEntry(btn.dataset.term);
  if (!e) return;
  closePopover();
  popover = document.createElement('div');
  popover.className = 'popover';
  popover.id = 'gl-pop';
  popover.setAttribute('role', 'region');
  popover.setAttribute('aria-label', e.term);
  popover.innerHTML = `<strong>${esc(e.term)}</strong> ${esc(e.def)}`;
  document.body.appendChild(popover);
  btn.setAttribute('aria-expanded', 'true');
  btn.setAttribute('aria-describedby', 'gl-pop');
  openBtn = btn;
  const r = btn.getBoundingClientRect();
  const pw = popover.offsetWidth;
  let left = Math.min(Math.max(8, r.left + r.width / 2 - pw / 2), window.innerWidth - pw - 8);
  popover.style.left = `${left + window.scrollX}px`;
  popover.style.top = `${r.bottom + window.scrollY + 8}px`;
}

let wired = false;
export function wireGlossary() {
  if (wired) return;
  wired = true;
  document.addEventListener('click', (ev) => {
    const btn = ev.target.closest?.('button.gl');
    if (btn) {
      if (btn === openBtn) closePopover(); else openPopover(btn);
      return;
    }
    if (popover && !ev.target.closest('.popover')) closePopover();
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && popover) { const b = openBtn; closePopover(); b?.focus(); }
  });
  window.addEventListener('hashchange', closePopover);
}
export { closePopover };

/** The friendly "empty shelf" scene (Plan 02 section 2). */
export function emptyScene(message = 'This shelf is empty') {
  return `<section class="empty-scene">
  <div class="empty-plank" aria-hidden="true"></div>
  <h1 tabindex="-1">${esc(message)}</h1>
  <p>Nothing is standing here. <a class="btn" href="#/">Back to the bar</a></p>
</section>`;
}
