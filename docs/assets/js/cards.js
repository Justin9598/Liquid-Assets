// Menu cards (Plan 02 section 7), shared by the shelf, drink and producer pages.
import { bottleSVG, motifFor, shapeFor } from './bottles.js';
import { img } from './data.js';
import { icon } from './icons.js';
import { esc, num, sizeShort, stars } from './util.js';

const NOTE_ICON = icon('note-pencil', 18, 'note-icon');

/** Art shown when a drink has no photo: the category bottle sketched on paper. */
export function fallbackArt(d, ix) {
  const shape = shapeFor(d.category);
  const info = d.category && ix.subs.get(`${d.category}/${d.sub}`);
  const native = info?.sub.native || null;
  const name = info?.sub.name || (d.category ? ix.cats.get(d.category)?.name : null) || 'Drink';
  const motif = motifFor(d.category, d.sub);
  return `<span class="sketch">${bottleSVG(shape, { native, name, motif, cls: 'sketched' })}</span>`;
}

export function photoOrFallback(d, ix, eager) {
  if (d.thumb) {
    return `<img src="${esc(img(d.thumb))}" alt="" width="480" height="640" loading="${eager ? 'eager' : 'lazy'}" decoding="async">`;
  }
  return fallbackArt(d, ix);
}

/**
 * opts.eager     load the photo straight away
 * opts.shelfLine replace the producer line with "Category > subcategory" (producer page)
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
  const shownTags = tags.slice(0, 3).map((t) => `<span class="tag">${esc(t)}</span>`).join('');
  const more = tags.length > 3 ? `<span class="tag more">+${tags.length - 3}</span>` : '';
  const had = d.occasions > 1
    ? `<span class="had" title="Had ${d.occasions} times"><span aria-hidden="true">×${d.occasions}</span><span class="sr-only">had ${d.occasions} times</span></span>` : '';
  const fav = d.favourite ? `<span class="ribbon"><span aria-hidden="true">${icon('star-fill', 14)}</span><span class="sr-only">Favourite</span></span>` : '';
  const sr = [d.favourite ? 'Favourite' : '', d.occasions > 1 ? `had ${d.occasions} times` : '', d.hasTasting ? 'has tasting notes' : ''].filter(Boolean).join(', ');
  return `<a class="card${opts.mini ? ' mini' : ''}" href="#/drink/${encodeURIComponent(d.id)}" data-id="${esc(d.id)}">
  <span class="card-photo">${fav}${photoOrFallback(d, ix, opts.eager)}${had}</span>
  <span class="card-body">
    <h2 class="card-name">${esc(d.name)}</h2>
    ${stars(d.rating)}
    ${lineProducer ? `<span class="card-line producer">${lineProducer}</span>` : ''}
    ${where ? `<span class="card-line">${where}</span>` : ''}
    ${bits.length ? `<span class="card-line">${bits.join(' · ')}</span>` : ''}
    ${facts ? `<span class="card-line facts">${facts}</span>` : ''}
    ${(shownTags || more) ? `<span class="tags">${shownTags}${more}</span>` : ''}
    ${d.hasTasting ? `<span class="note-mark" title="Has tasting notes">${NOTE_ICON}</span>` : ''}
    ${sr ? `<span class="sr-only">${esc(sr)}</span>` : ''}
  </span>
</a>`;
}
