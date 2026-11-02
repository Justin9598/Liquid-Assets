// Drink detail page: "On the counter" (Plan 03, looks from Plan 08 section 4.2). A hero board with the photo print and the
// facts, then one board each for The Label, The Glass, The Story, The Maker and The Tab. Everything is chalk on slate.
import { cardHTML } from './cards.js';
import { board, emptyHTML, glossaryEntry, loadGlossary, pageHTML, termHTML } from './chrome.js';
import { getJSON, img } from './data.js';
import { icon } from './icons.js';
import { drinkShell } from './shells.js';
import { $, $$, esc, fmtDate, money, num, setTitle, short, sizeShort, stars } from './util.js';

const isHangul = (s) => /[ᄀ-ᇿ㄰-㆏가-힯]/.test(s || '');
const COLOUR = { colourless: '#f4f1e4', 'lemon-green': '#e1ea9a', lemon: '#efe27a', gold: '#dfb73d', amber: '#c4842a', brown: '#774a22' };
const MINUS = '−';

function dots(label, value, steps) {
  if (!steps?.length) return `<span class="word">${esc(value)}</span>`;
  const i = steps.indexOf(value);
  const on = i < 0 ? 0 : i + 1;
  const d = steps.map((_, k) => `<i class="${k < on ? 'on' : ''}"></i>`).join('');
  const txt = i < 0 ? `${label}: ${value}` : `${label}: ${value}, ${on} of ${steps.length}`;
  return `<span class="dots" role="img" aria-label="${esc(txt)}">${d}</span><span class="word" aria-hidden="true">${esc(value)}</span>`;
}

function specValue(item) {
  const { value, unit, viz } = item;
  if (viz === 'polish' && typeof value === 'number') {
    return `<span class="val">${num(value)}%</span><span class="polish" role="img" aria-label="${num(value)}% of each grain remains after polishing"><span class="grain"><span class="kept" style="width:${Math.max(0, Math.min(100, value))}%"></span></span></span>`;
  }
  if (viz === 'smv' && typeof value === 'number') {
    const clamped = Math.max(-15, Math.min(15, value));
    const pos = ((clamped + 15) / 30) * 100;
    const pin = value < -15 ? ' pin-left' : value > 15 ? ' pin-right' : '';
    const arrow = value < -15 ? '◀' : value > 15 ? '▶' : '';
    const text = `${value > 0 ? '+' : value < 0 ? MINUS : ''}${num(Math.abs(value))}`;
    return `<span class="val">${text}</span><span class="smv${pin}" role="img" aria-label="SMV ${text}, scale from sweet at ${MINUS}15 to dry at +15"><span class="smv-track"><i class="smv-mark" style="left:${pos}%">${arrow}</i></span><span class="smv-ends"><em>Sweet</em><em>Dry</em></span></span>`;
  }
  const v = typeof value === 'number' ? num(value) : String(value);
  return `<span class="val">${esc(v)}${unit ? esc(unit) : ''}</span>`;
}

function tastingHTML(t) {
  const sc = t.scales || {};
  const block = (title, body) => (body ? `<section class="t-block"><h3>${title}</h3>${body}</section>` : '');
  const row = (k, v) => `<div class="t-row"><span class="k">${k}</span><span class="v">${v}</span></div>`;
  const tags = (arr) => arr?.length ? `<span class="aroma">${arr.map((a) => `<em>${esc(a)}</em>`).join('')}</span>` : '';
  let body = '';
  const a = t.appearance;
  if (a) {
    const words = [a.clarity, a.intensity, a.colour].filter(Boolean).join(' · ');
    const sw = a.colour ? `<span class="swatch" style="--sw:${COLOUR[a.colour] || '#eee'}" aria-hidden="true"></span>` : '';
    body = row('Look', `${sw}<span class="word">${esc(words)}</span>${a.other ? `<span class="word">${esc(a.other)}</span>` : ''}`);
  }
  const look = block('Appearance', body);
  const n = t.nose;
  body = '';
  if (n) {
    if (n.condition) body += row('Condition', `<span class="word${n.condition.includes('unclean') ? ' warn' : ''}">${esc(n.condition)}</span>`);
    if (n.intensity) body += row('Intensity', dots('Nose intensity', n.intensity, sc.noseIntensity));
    if (n.aroma?.length) body += row('Aroma', tags(n.aroma));
  }
  const nose = block('Nose', body);
  const p = t.palate;
  body = '';
  if (p) {
    const scales = [['Sweetness', 'sweetness', 'sweetness'], ['Acidity', 'acidity', 'acidity'], ['Umami', 'umami', 'umami'], ['Alcohol', 'alcohol', 'alcohol'],
      ['Body', 'body', 'body'], ['Flavour intensity', 'flavourIntensity', 'flavourIntensity'], ['Finish', 'finish', 'finish']];
    for (const [label, key, sKey] of scales) if (p[key]) body += row(label, dots(label, p[key], sc[sKey]));
    if (p.mousse) body += row('Mousse', `<span class="word">${esc(p.mousse)}</span>`);
    if (p.flavour?.length) body += row('Flavour', tags(p.flavour));
    if (p.other) body += row('Other', `<span class="word">${esc(p.other)}</span>`);
  }
  const palate = block('Palate', body);
  const c = t.conclusion;
  body = '';
  if (c) {
    if (c.quality) body += `<div class="stamp" role="img" aria-label="Quality: ${esc(c.quality)}"><span aria-hidden="true">${esc(c.quality)}</span></div>`;
    const chips = [c.category, c.ginjo, c.production, c.special].filter(Boolean).map((x) => `<span class="pill chalkboard chalkboard--s">${esc(x)}</span>`).join('');
    if (chips) body += `<div class="pills">${chips}</div>`;
  }
  return [look, nose, palate, block('Conclusion', body)].join('');
}

function paragraphs(text) {
  return String(text).split(/\n\s*\n|\n/).map((p) => p.trim()).filter(Boolean).map((p) => `<p class="t-body">${esc(p)}</p>`).join('');
}

/** One visit as a chalked line on the tab: date, size, where, then the price at the right. */
function visitLine(v) {
  const bits = [v.date && `<span class="v-date">${esc(fmtDate(v.date))}</span>`, v.size && `<span>${esc(sizeShort(v.size))}</span>`, v.where && `<span>${esc(v.where)}</span>`].filter(Boolean);
  if (v.price != null) bits.push(`<span class="v-price">${esc(money(v.price))}</span>`);
  return bits.join('');
}
const visitText = (v) => [v.date && fmtDate(v.date), v.size && sizeShort(v.size), v.where, v.price != null && money(v.price)].filter(Boolean).join(' · ');

export async function mount(root, ctx) {
  const { ix, id, state } = ctx;
  await loadGlossary();
  let d;
  try {
    d = await getJSON(`drinks/${encodeURIComponent(id)}.json`);
  } catch {
    setTitle('Empty shelf');
    root.innerHTML = emptyHTML('This shelf is empty');
    return {};
  }
  const idxRec = ix.byId.get(d.id);
  const info = d.category && ix.subs.get(`${d.category}/${d.sub}`);
  const cat = d.category && ix.cats.get(d.category);
  const single = cat && cat.subcategories.length === 1;
  setTitle(d.name);

  const crumbs = [];
  if (cat) {
    crumbs.push({ label: cat.name, href: `#/${cat.key}` });
    if (!single) crumbs.push({ label: info.sub.name, href: `#/${cat.key}/${info.sub.key}` });
  }
  crumbs.push({ label: short(d.name) });

  // back to shelf: restore the previous shelf hash (filters intact) when it was this drink's shelf
  const shelfHref = info ? `#/${cat.key}/${info.sub.key}` : '#/';
  const back = state.lastShelf && info && state.lastShelf.startsWith(shelfHref) ? state.lastShelf : shelfHref;

  // ---- hero -------------------------------------------------------------------------------------------------
  const photos = d.photos || [];
  const noPhoto = !photos.length;
  const heroPhoto = noPhoto
    ? `<div class="stand" aria-hidden="true">${drinkShell(idxRec || { category: d.category, sub: d.sub }, ix)}</div><p class="t-small none-note">No photo yet</p>`
    : `<figure class="print print--tilt"><button type="button" class="photo-main" id="photo-main" aria-label="Open the photo larger"><img id="main-img" src="${esc(img(photos[0].web))}" alt="${esc(photos[0].caption)} of ${esc(d.name)}" width="${photos[0].w}" height="${photos[0].h}" fetchpriority="high"></button></figure>`;
  const thumbs = photos.length > 1
    ? `<ul class="thumbs" aria-label="Photos">${photos.map((p, i) => `<li><button type="button" class="thumb${i === 0 ? ' on' : ''}" data-i="${i}" aria-label="Show ${esc(p.caption.toLowerCase())}" aria-pressed="${i === 0}"><span class="print"><img src="${esc(img(p.web))}" alt="" loading="lazy"></span></button></li>`).join('')}</ul>` : '';

  const pr = d.producer;
  const nativeLang = pr.native ? (isHangul(pr.native) ? 'ko' : 'ja') : '';
  const makerLine = pr.key
    ? `<a class="chalk-link" href="#maker" data-jump="maker">${esc(pr.name)}</a>${pr.location ? ` · ${esc(pr.location)}` : ''}`
    : (pr.location ? esc(pr.location) : '');
  const quick = [];
  if (d.abv != null) quick.push(`${num(d.abv)}%`);
  const sizes = [...new Set(d.visits.map((v) => v.size).filter(Boolean))];
  if (sizes.length) quick.push(sizes.map(sizeShort).join(' · '));
  if (d.visits.length > 1) quick.push(`had ${d.visits.length} times`);
  const oneVisit = d.visits.length === 1 ? visitText({ ...d.visits[0], size: null }) : '';
  const styleTags = d.styles.length ? `<ul class="style-tags" aria-label="Styles">${d.styles.map((t) => `<li>${glossaryEntry(t)
    ? `<button type="button" class="gl chalkboard chalkboard--s" data-term="${esc(glossaryEntry(t).term)}" aria-expanded="false"><span class="chalk">${esc(t)}</span></button>`
    : `<span class="tag chalkboard chalkboard--s">${esc(t)}</span>`}</li>`).join('')}</ul>` : '';
  const prevRec = d.prev && ix.byId.get(d.prev);
  const nextRec = d.next && ix.byId.get(d.next);
  const hasNav = d.prev && d.next && d.prev !== d.id;

  const hero = board(`<div class="hero-drink">
  <div class="hd-photo">${heroPhoto}${thumbs}</div>
  <div class="hd-copy">
    ${d.favourite ? `<span class="fav-line"><span aria-hidden="true">${icon('star-fill', 20)}</span> Favourite</span>` : ''}
    <h1 class="t-title" tabindex="-1">${esc(d.name)}</h1>
    ${makerLine ? `<p class="t-data maker-line">${makerLine}</p>` : ''}
    <div class="hd-chips">${info ? `<a class="chalkboard chalkboard--s btn-s" href="${esc(shelfHref)}"><span class="chalk">${esc(cat.name)}${single ? '' : `, ${esc(info.sub.name)}`}</span></a>` : ''}${quick.length ? `<span class="t-data quick">${esc(quick.join(' · '))}</span>` : ''}</div>
    ${oneVisit ? `<p class="t-data">${esc(oneVisit)}${d.visits[0].note ? `<span class="vnote">${esc(d.visits[0].note)}</span>` : ''}</p>` : ''}
    ${styleTags}
    ${d.rating != null ? `<p class="rating">${stars(d.rating)}</p>` : ''}
    <div class="hd-nav">
      <a class="chalkboard chalkboard--s btn-s" href="${esc(back)}"><span aria-hidden="true">${icon('caret-left', 14)}</span> Back to ${info ? esc(single ? cat.name : info.sub.name) : 'the bar'}</a>
      ${hasNav ? `<a class="chalkboard chalkboard--s btn-s" href="#/drink/${encodeURIComponent(d.prev)}" rel="prev" aria-label="Previous: ${esc(prevRec?.name || '')}"><span aria-hidden="true">${icon('caret-left', 16)}</span> Prev</a>
      <a class="chalkboard chalkboard--s btn-s" href="#/drink/${encodeURIComponent(d.next)}" rel="next" aria-label="Next: ${esc(nextRec?.name || '')}">Next <span aria-hidden="true">${icon('caret-right', 16)}</span></a>` : ''}
    </div>
  </div>
</div>${noPhoto ? '<i class="tray" aria-hidden="true"></i>' : ''}`, `hero${noPhoto ? ' has-tray' : ''}`);

  // ---- section boards ---------------------------------------------------------------------------------------
  const spec = d.spec.map((it) => `<div class="spec-row"><dt>${termHTML(it.label)}</dt><dd>${specValue(it)}</dd></div>`).join('');
  const labelBoard = spec ? board(`<h2 class="t-head" id="h-label">The Label</h2><dl class="spec">${spec}</dl>`, 'label-board', 'aria-labelledby="h-label"') : '';
  const wsetNote = glossaryEntry('WSET-style tasting')?.def || '';
  const glassBoard = d.tasting ? board(`<h2 class="t-head" id="h-glass">The Glass</h2>
  ${wsetNote ? `<p class="t-small wset"><button type="button" class="info-btn" id="wset-btn" aria-expanded="false" aria-controls="wset-note">WSET-style tasting <span aria-hidden="true">${icon('info', 16)}</span></button></p>
  <p class="t-body wset-note" id="wset-note" hidden>${esc(wsetNote)}</p>` : ''}
  ${tastingHTML(d.tasting)}`, 'glass-board', 'aria-labelledby="h-glass"') : '';
  const pair = labelBoard && glassBoard ? `<div class="pair">${labelBoard}${glassBoard}</div>` : (labelBoard || glassBoard);
  const storyBoard = d.story ? board(`<h2 class="t-head" id="h-story">The Story</h2>${paragraphs(d.story)}`, 'story', 'aria-labelledby="h-story"') : '';

  let inner;
  if (pr.key) {
    const more = d.moreFromProducer.map((mid) => ix.byId.get(mid)).filter(Boolean);
    inner = `<div class="maker-head"><h2 class="t-head" id="h-maker">The Maker</h2>
  <h3 class="t-title maker-name">${esc(pr.name)}${pr.native ? ` <span class="native" lang="${nativeLang}">${esc(pr.native)}</span>` : ''}</h3>
  <p class="t-data meta">${[pr.location, pr.founded ? `est. ${pr.founded}` : ''].filter(Boolean).map(esc).join(' · ')}</p></div>
  ${pr.about ? `<p class="t-body">${esc(pr.about)}</p>` : ''}
  <p class="maker-links"><a class="chalkboard chalkboard--s btn-s" href="#/producer/${encodeURIComponent(pr.key)}">Visit producer ${icon('arrow-right', 16)}</a>${pr.url ? ` <a class="chalk-link" href="${esc(pr.url)}" target="_blank" rel="noopener noreferrer">Website ${icon('arrow-up-right', 14)}</a>` : ''}</p>
  ${more.length ? `<h3 class="more-h">More from ${esc(pr.name)} (${more.length})</h3><div class="mini-row">${more.map((m) => cardHTML(m, ix, { mini: true })).join('')}</div>` : ''}`;
  } else {
    inner = `<h2 class="t-head" id="h-maker">The Maker</h2><p class="t-data">Producer not recorded${pr.location ? ` · ${esc(pr.location)}` : ''}</p>`;
  }
  const makerBoard = board(inner, 'maker', 'id="maker" aria-labelledby="h-maker"');

  const tabBoard = d.visits.length > 1 ? board(`<h2 class="t-head" id="h-tab">The Tab: had ${d.visits.length} times</h2>
  <ul class="visits">${d.visits.map((v) => `<li>${visitLine(v) || '<span>A visit</span>'}${v.note ? `<span class="vnote">${esc(v.note)}</span>` : ''}</li>`).join('')}</ul>`, 'tab', 'aria-labelledby="h-tab"') : '';

  root.innerHTML = pageHTML({ crumbs, cls: 'drink-page', boards: `${hero}${pair}${storyBoard}${makerBoard}${tabBoard}` });

  // ---- photo switching and lightbox -------------------------------------------------------------------------
  let cur = 0;
  const mainBtn = $('#photo-main', root);
  const mainImg = $('#main-img', root);
  function show(i) {
    cur = i;
    const p = photos[i];
    mainImg.src = img(p.web);
    mainImg.width = p.w; mainImg.height = p.h;
    mainImg.alt = `${p.caption} of ${d.name}`;
    $$('.thumb', root).forEach((b, k) => { b.classList.toggle('on', k === i); b.setAttribute('aria-pressed', String(k === i)); });
  }
  let lb = null;
  let lbFrom = null;
  function openLightbox() {
    if (lb || !photos.length) return;
    lbFrom = document.activeElement;
    lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', `Photos of ${d.name}`);
    lb.innerHTML = `<button type="button" class="chalkboard chalkboard--s lb-close" aria-label="Close">${icon('x', 22)}</button>
<button type="button" class="chalkboard chalkboard--s lb-nav lb-prev" aria-label="Previous photo"${photos.length < 2 ? ' hidden' : ''}>${icon('caret-left', 22)}</button>
<figure><span class="print"><img alt=""></span><figcaption class="chalkboard chalkboard--s"></figcaption></figure>
<button type="button" class="chalkboard chalkboard--s lb-nav lb-next" aria-label="Next photo"${photos.length < 2 ? ' hidden' : ''}>${icon('caret-right', 22)}</button>`;
    document.body.appendChild(lb);
    document.body.classList.add('no-scroll');
    const paint = () => {
      const p = photos[cur];
      $('img', lb).src = img(p.web);
      $('img', lb).alt = `${p.caption} of ${d.name}`;
      $('figcaption', lb).textContent = `${p.caption}${photos.length > 1 ? ` · ${cur + 1} of ${photos.length}` : ''}`;
    };
    paint();
    const step = (n) => { cur = (cur + n + photos.length) % photos.length; show(cur); paint(); };
    lb.addEventListener('click', (ev) => {
      if (ev.target.closest('.lb-close') || ev.target === lb) closeLightbox();
      else if (ev.target.closest('.lb-prev')) step(-1);
      else if (ev.target.closest('.lb-next')) step(1);
    });
    let x0 = null;
    lb.addEventListener('touchstart', (ev) => { x0 = ev.touches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend', (ev) => {
      if (x0 == null || photos.length < 2) return;
      const dx = ev.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
      x0 = null;
    });
    lb._step = step;
    $('.lb-close', lb).focus();
  }
  function closeLightbox() {
    if (!lb) return;
    lb.remove(); lb = null;
    document.body.classList.remove('no-scroll');
    (lbFrom || mainBtn)?.focus?.();
  }
  const onKey = (ev) => {
    if (lb) {
      if (ev.key === 'Escape') { ev.preventDefault(); closeLightbox(); }
      else if (ev.key === 'ArrowLeft') lb._step(-1);
      else if (ev.key === 'ArrowRight') lb._step(1);
      else if (ev.key === 'Tab') {
        const f = $$('button:not([hidden])', lb);
        const first = f[0]; const last = f[f.length - 1];
        if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
        else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
      }
      return;
    }
    if (document.body.classList.contains('menu-open') || ev.target.closest?.('input, textarea, select') || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    if (ev.key === 'ArrowLeft' && d.prev && d.prev !== d.id) location.hash = `#/drink/${encodeURIComponent(d.prev)}`;
    else if (ev.key === 'ArrowRight' && d.next && d.next !== d.id) location.hash = `#/drink/${encodeURIComponent(d.next)}`;
  };
  document.addEventListener('keydown', onKey);

  const onClick = (ev) => {
    if (ev.target.closest('#photo-main')) { openLightbox(); return; }
    const t = ev.target.closest('.thumb');
    if (t) { show(Number(t.dataset.i)); return; }
    const jump = ev.target.closest('[data-jump="maker"]');
    if (jump) { ev.preventDefault(); const m = $('#maker', root); m?.scrollIntoView({ behavior: 'smooth', block: 'start' }); m?.setAttribute('tabindex', '-1'); m?.focus({ preventScroll: true }); return; }
    const b = ev.target.closest('#wset-btn');
    if (b) {
      const note = $('#wset-note', root);
      if (!note) return;
      note.hidden = !note.hidden;
      b.setAttribute('aria-expanded', String(!note.hidden));
    }
  };
  root.addEventListener('click', onClick);

  return {
    unmount() {
      closeLightbox();
      document.removeEventListener('keydown', onKey);
      root.removeEventListener('click', onClick);
    },
  };
}
