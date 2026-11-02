// Shared page chrome for the inner pages: the frame every page sits in (breadcrumb and boards, over the fixed bar), the
// blackboard helpers and the glossary popovers (Plan 03 section 9, Plan 08 sections 3.1 to 3.9).
import { getJSON } from './data.js';
import { icon } from './icons.js';
import { esc, fold } from './util.js';

/** A content board (XL): the page hero and each section. */
export const board = (inner, cls = '', attrs = '') => `<section class="chalkboard chalkboard--xl board ${cls}"${attrs ? ' ' + attrs : ''}>${inner}</section>`;

/** An M board holding a heading, for a group of boards or cards (section headings that are not inside a board). */
export const headBoard = (inner, cls = '', tag = 'h2') => `<${tag} class="chalkboard chalkboard--m head-board ${cls}"><span class="chalk">${inner}</span></${tag}>`;

/** The breadcrumb S board. crumbs: [{ label, href? }] after "Bar". On a phone, when it does not fit on one line, only the
 * parent link shows ("< Parent"); fitCrumbs() decides. */
export function crumbsHTML(crumbs) {
  const items = [{ label: 'Bar', href: '#/' }, ...crumbs];
  const lis = items.map((c, i) => {
    const last = i === items.length - 1;
    const sep = i ? `<span class="sep" aria-hidden="true">${icon('caret-right', 12)}</span>` : '';
    return `<li>${sep}${last || !c.href ? `<span${last ? ' aria-current="page"' : ''}>${esc(c.label)}</span>` : `<a href="${esc(c.href)}">${esc(c.label)}</a>`}</li>`;
  }).join('');
  const parent = items.length > 1 ? items[items.length - 2] : null;
  const back = parent?.href ? `<a class="back" href="${esc(parent.href)}"><span aria-hidden="true">${icon('caret-left', 14)}</span>${esc(parent.label)}</a>` : '';
  return `<nav class="crumbs" aria-label="Breadcrumb"><div class="chalkboard chalkboard--s"><ol>${lis}</ol>${back}</div></nav>`;
}

/** Switch the breadcrumb to its parent-only form when the full trail does not fit on one line. */
export function fitCrumbs(root) {
  const nav = root.querySelector('.crumbs');
  if (!nav) return;
  nav.classList.remove('compact');
  const ol = nav.querySelector('ol');
  const room = nav.clientWidth - 30;
  if (ol && ol.scrollWidth > room && nav.querySelector('.back')) nav.classList.add('compact');
}

/** The frame of every inner page: the fixed bar shows through above the first board, which starts below the sign.
 * `boards` is the page's markup (boards and groups of cards); `link` is a sign link that goes back to the bar. */
export function pageHTML({ crumbs, boards, cls = '' }) {
  return `<div class="inner ${cls}">
  <a class="sign-link" href="#/" aria-label="Liquid Assets, back to the bar"></a>
  ${crumbsHTML(crumbs)}
  <div class="boards">${boards}</div>
</div>`;
}

/** The friendly "empty shelf" page (Plan 02 section 2, Plan 08 section 3.9): one board, then a way back to the bar. */
export function emptyHTML(message = 'This shelf is empty', crumbs = [{ label: 'Empty shelf' }]) {
  return pageHTML({
    crumbs, cls: 'empty',
    boards: `<div class="empty-wrap">${board(`<h1 class="t-title" tabindex="-1">${esc(message)}</h1><p class="t-body" style="margin-inline:auto">Nothing is standing here.</p>`)}
  <a class="chalkboard chalkboard--s btn-s" href="#/">Back to the bar</a></div>`,
  });
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
  popover.className = 'popover chalkboard chalkboard--s';
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
  const left = Math.min(Math.max(8, r.left + r.width / 2 - pw / 2), window.innerWidth - pw - 8);
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
