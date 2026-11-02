// Menu cards (Plan 02 section 7, Plan 08 section 4.1): each card is a small blackboard in the grid. A pinned photo print at
// the top, or the category's shell standing on a ledge when the drink has no photo, then the details in chalk. Shared by
// the shelf, drink and producer pages.
import { img } from './data.js';
import { icon } from './icons.js';
import { drinkShell } from './shells.js';
import { esc, num, sizeShort, stars } from './util.js';

const NOTE_ICON = icon('note-pencil', 18, 'note-icon');

/** The top of a card: a photo print, or the shell for the drink's category on a ledge. */
export function cardPhoto(d, ix, eager) {
  if (d.thumb) {
    return `<span class="print"><img src="${esc(img(d.thumb))}" alt="" width="480" height="640" loading="${eager ? 'eager' : 'lazy'}" decoding="async"></span>`;
  }
  return `<span class="stand stand--card" aria-hidden="true">${drinkShell(d, ix)}</span>`;
}

/**
 * opts.eager     load the photo straight away
 * opts.shelfLine replace the producer line with "Category, subcategory" (producer page)
 * opts.mini      compact version for rows that scroll sideways
 */
export function cardHTML(d, ix, opts = {}) {
  const info = d.category && ix.subs.get(`${d.category}/${d.sub}`);
  const lineProducer = opts.shelfLine
    ? (info ? `${esc(ix.cats.get(d.category).name)}, ${esc(info.sub.name)}` : '')
    : esc(d.producer || '');
  const where = [d.origin, d.country].filter(Boolean).map(esc).join(' · ');
  const bits = [];
  if (d.abv != null) bits.push(`${num(d.abv)}%`);
  if (d.sizes?.length) bits.push(d.sizes.map(sizeShort).map(esc).join(' · '));
  const facts = (d.facts || []).map(esc).join(' · ');
  const tags = d.styles || [];
  const shownTags = tags.slice(0, 3).map((t) => `<span class="tag chalkboard chalkboard--s">${esc(t)}</span>`).join('');
  const more = tags.length > 3 ? `<span class="tag chalkboard chalkboard--s">+${tags.length - 3}</span>` : '';
  const had = d.occasions > 1
    ? `<span class="had chalkboard chalkboard--s" title="Had ${d.occasions} times"><span aria-hidden="true">×${d.occasions}</span><span class="sr-only">had ${d.occasions} times</span></span>` : '';
  const fav = d.favourite ? `<span class="fav"><span aria-hidden="true">${icon('star-fill', 18)}</span><span class="sr-only">Favourite</span></span>` : '';
  const sr = [d.favourite ? 'Favourite' : '', d.occasions > 1 ? `had ${d.occasions} times` : '', d.hasTasting ? 'has tasting notes' : ''].filter(Boolean).join(', ');
  return `<a class="card chalkboard chalkboard--l${opts.mini ? ' mini' : ''}" href="#/drink/${encodeURIComponent(d.id)}" data-id="${esc(d.id)}">
  <span class="card-top">${fav}${cardPhoto(d, ix, opts.eager)}${had}</span>
  <span class="card-body">
    <h2 class="card-name">${esc(d.name)}</h2>
    ${stars(d.rating)}
    ${lineProducer ? `<span class="card-line producer">${lineProducer}</span>` : ''}
    ${where ? `<span class="card-line">${where}</span>` : ''}
    ${bits.length ? `<span class="card-line">${bits.join(' · ')}</span>` : ''}
    ${facts ? `<span class="card-line">${facts}</span>` : ''}
    ${(shownTags || more) ? `<span class="tags">${shownTags}${more}</span>` : ''}
    ${d.hasTasting ? `<span class="note-mark" title="Has tasting notes">${NOTE_ICON}</span>` : ''}
    ${sr ? `<span class="sr-only">${esc(sr)}</span>` : ''}
  </span>
</a>`;
}
