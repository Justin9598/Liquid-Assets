// Self-check for the welcome page, run only when the page is opened with ?check=1 (build/tools/smoke.py does this at four
// screen sizes). It checks what Plan 07 sections 8 to 10 promise and writes the result as JSON into <pre id="check-result">.
// Nothing here runs for visitors.
import { $, $$ } from './util.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const finishAll = () => document.getAnimations().forEach((a) => { try { a.finish(); } catch { /* ignore */ } });
async function until(cond, tries = 60) {
  for (let i = 0; i < tries && !cond(); i++) { finishAll(); await sleep(30); }
  return cond();
}
const rect = (el) => el.getBoundingClientRect();
const hit = (a, b, pad = 0) => a.left < b.right - pad && a.right > b.left + pad && a.top < b.bottom - pad && a.bottom > b.top + pad;

export async function run(ctx) {
  const { manifest, ix } = ctx;
  const problems = [];
  const stats = {};
  const bad = (m) => problems.push(m);
  await document.fonts.ready;
  const kind = $('.scene3').dataset.plate;
  const P = manifest.plates[kind];
  const cover = rect($('.cover'));
  const W = cover.width;
  const H = cover.height;
  stats.size = [innerWidth, innerHeight];
  stats.plate = kind;
  stats.kalam = document.fonts.check("700 14px Kalam");
  if (!stats.kalam) bad('Kalam did not load');

  // the shelf area: the shelf unit's clear width, from the top shelf's clear space down to the counter top
  const s0 = P.shelves[0];
  const area = {
    left: cover.left + s0.x0 * W - 1, right: cover.left + s0.x1 * W + 1,
    top: cover.top + (s0.y - s0.clear) * H - 1, bottom: cover.top + P.counterTop * H + 1,
  };

  // ---- 1. category captions are always visible and never overlap ------------------------------------------------
  const caps = $$('.vessel-cap').map((c) => ({ c, r: rect(c) }));
  stats.captions = caps.length;
  for (const { c, r } of caps) {
    const cs = getComputedStyle(c);
    if (cs.opacity !== '1' || cs.visibility !== 'visible') bad(`caption "${c.textContent.trim()}" is not visible`);
    if (parseFloat(cs.fontSize) < 14) bad(`caption "${c.textContent.trim()}" is under 14px`);
    if (r.left < area.left || r.right > area.right) bad(`caption "${c.textContent.trim()}" leaves the shelf area`);
  }
  for (let i = 0; i < caps.length; i++) for (let j = i + 1; j < caps.length; j++) if (hit(caps[i].r, caps[j].r)) bad(`captions overlap: ${caps[i].c.textContent.trim()} / ${caps[j].c.textContent.trim()}`);

  // ---- 2. resting state: no lower-shelf bottle is drawn behind a counter bottle -----------------------------------
  const front = $$('.cgroup:not([hidden]) .cb-art > *').map(rect).filter((r) => r.width > 0);
  stats.counterBottles = front.length;
  if (kind === 'wide') {
    const behind = $$('#lower .slot.mix:not(.blocked) .art > *').map(rect).filter((r) => front.some((f) => hit(r, f)));
    if (behind.length) bad(`${behind.length} lower-shelf bottle(s) drawn behind a counter bottle at rest`);
  } else {
    // phones: shelf 3 shows its full row of 3, and no bottle is more than 35% covered by a counter bottle
    const rr = rect($('.lowrow .row-items'));
    const inView = $$('#lower .slot.mix').filter((s) => { const r = rect(s); return r.left >= rr.left - 1 && r.right <= rr.right + 1; });
    stats.shelf3AtRest = inView.length;
    if (inView.length !== 3) bad(`shelf 3 shows ${inView.length} bottles at rest, not 3`);
    if (inView.some((s) => s.classList.contains('blocked') || getComputedStyle(s).visibility === 'hidden')) bad('a shelf-3 bottle is hidden at rest');
    const shares = inView.map((s) => {
      const a = rect($('.art > *', s));
      let sum = 0;
      for (const f of front) { const w = Math.min(a.right, f.right) - Math.max(a.left, f.left); const h = Math.min(a.bottom, f.bottom) - Math.max(a.top, f.top); if (w > 0 && h > 0) sum += w * h; }
      return sum / (a.width * a.height);
    });
    stats.shelf3Covered = shares.map((x) => +x.toFixed(2));
    if (shares.some((x) => x > 0.35)) bad(`a shelf-3 bottle is ${(Math.max(...shares) * 100).toFixed(0)}% covered by a counter bottle`);
  }
  const boards = [...$$('.placard, .slate.s3, .ctab, .burger-tag')].filter((e) => e.offsetParent !== null).map((e) => ({ e, r: rect(e) }));
  for (let i = 0; i < boards.length; i++) for (let j = i + 1; j < boards.length; j++) if (hit(boards[i].r, boards[j].r)) bad(`labels overlap: ${boards[i].e.textContent.trim()} / ${boards[j].e.textContent.trim()}`);
  for (const { e } of boards) if (parseFloat(getComputedStyle(e).fontSize) < 14) bad(`label "${e.textContent.trim()}" is under 14px`);

  // ---- 3. every category: tags fit, are 14px or more, do not overlap and stay inside the shelf area -------------------
  stats.categories = {};
  for (const c of ix.shelf.categories) {
    location.hash = `#/${c.key}`;
    await until(() => $('#lower')?.dataset.mode === 'sub' && $$('#lower .slot.sub').length === c.subcategories.length);
    finishAll();
    await sleep(60);
    const row = $('.lowrow .row-items');
    const rr = row ? rect(row) : null;
    const tags = [];
    for (const slot of $$('#lower .slot.sub')) {
      const sr = rect(slot);
      if (kind === 'tall' && rr && (sr.left < rr.left - 1 || sr.right > rr.right + 1)) continue;   // scrolled out of view
      const h = $('.hang', slot);
      tags.push({ h, r: rect(h), name: $('.nm', h).textContent.trim() });
    }
    stats.categories[c.key] = { tags: tags.length, per: $('.lowrow')?.style.getPropertyValue('--per'), fitFail: $('#lower').dataset.fitFail };
    if (tags.length === 0) bad(`${c.key}: no visible tags`);
    for (const t of tags) {
      const cs = getComputedStyle(t.h);
      if (parseFloat(cs.fontSize) < 14) bad(`${c.key}/${t.name}: tag under 14px`);
      if (t.h.scrollWidth > t.h.clientWidth + 1) bad(`${c.key}/${t.name}: tag text is clipped`);
      const lh = parseFloat(getComputedStyle($('.nm', t.h)).lineHeight);
      if ($('.nm', t.h).getBoundingClientRect().height > lh * 2 + 1) bad(`${c.key}/${t.name}: name needs more than 2 lines`);
      if (t.r.left < area.left || t.r.right > area.right || t.r.top < area.top || t.r.bottom > area.bottom + (kind === 'tall' ? 3 : 0)) bad(`${c.key}/${t.name}: tag leaves the shelf area`);
    }
    for (let i = 0; i < tags.length; i++) for (let j = i + 1; j < tags.length; j++) if (hit(tags[i].r, tags[j].r)) bad(`${c.key}: tags overlap: ${tags[i].name} / ${tags[j].name}`);
    for (const { c: cap, r } of caps) for (const t of tags) if (hit(rect(cap), t.r)) bad(`${c.key}: caption ${cap.textContent.trim()} overlaps tag ${t.name}`);
    const groups = $$('.cgroup:not([hidden])');
    if (groups.some((g) => getComputedStyle(g).opacity !== '0')) bad(`${c.key}: counter bottles did not fade out`);
    const placards = $$('.placard, .ctab').filter((e) => e.offsetParent !== null);
    for (const t of tags) for (const p of placards) if (hit(t.r, rect(p))) bad(`${c.key}: tag ${t.name} overlaps counter label ${p.textContent.trim()}`);
    const slate = rect($('#plaque'));
    for (const t of tags) if (hit(t.r, slate)) bad(`${c.key}: tag ${t.name} overlaps the slate`);
    const burger = $('.burger-anchor') ? rect($('.burger-anchor')) : null;
    if (burger) for (const t of tags) if (hit(t.r, burger)) bad(`${c.key}: tag ${t.name} overlaps the burger`);
  }
  location.hash = '#/';
  await until(() => $('#lower')?.dataset.mode === 'mix');
  finishAll();
  await sleep(60);
  const back = $$('.cgroup:not([hidden])');
  if (!back.length || back.some((g) => getComputedStyle(g).opacity !== '1')) bad('counter bottles did not return at #/');

  // ---- 4. the burger menu: real open, boards stay at opacity 1 --------------------------------------------------
  const rowsOk = (when) => {
    const rows = $$('.bd-row');
    if (rows.length !== manifest.burger.layers.length) bad(`${when}: expected ${manifest.burger.layers.length} boards, found ${rows.length}`);
    for (const r of rows) {
      const cs = getComputedStyle(r);
      const bw = $('.bw', r);
      if (cs.opacity !== '1' || r.style.opacity) bad(`${when}: board "${r.textContent.trim().slice(0, 12)}" has opacity ${cs.opacity}`);
      if (getComputedStyle(bw).visibility !== 'visible') bad(`${when}: board is hidden`);
      const rb = rect(bw);
      if (rb.left < 0 || rb.right > innerWidth + 1 || rb.top < -1) bad(`${when}: board "${bw.textContent.trim().slice(0, 12)}" is off the screen`);
    }
  };
  const btn = $('.scene3 [data-burger]');
  btn.click();
  const opened = await until(() => $('.bd.split'));
  if (!opened) bad('the menu never reached its split state');
  await sleep(1000);
  rowsOk('after opening');
  const layers = $$('.bd .bl');
  const rowEls = $$('.bd-row');
  stats.boards = rowEls.length;
  stats.fontOnBoard = getComputedStyle($('.bw')).fontFamily.split(',')[0].trim();
  // each board stands in front of its layer: overlaps its near edge by about 18% and covers at most 25% of it
  rowEls.forEach((r, i) => {
    const b = rect($('.bw', r));
    const l = rect(layers[i]);
    const over = Math.max(0, Math.min(b.right, l.right) - Math.max(b.left, l.left)) * Math.max(0, Math.min(b.bottom, l.bottom) - Math.max(b.top, l.top));
    const share = over / (l.width * l.height);
    stats[`board${i}`] = { overlapShare: +share.toFixed(3), overlapWidth: +(Math.max(0, Math.min(b.right, l.right) - Math.max(b.left, l.left)) / l.width).toFixed(3) };
    if (share > 0.25) bad(`board ${i} covers ${(share * 100).toFixed(0)}% of its layer`);
    const near = kind === 'tall' || innerWidth < 0.9 * innerHeight ? b.right > l.right - 0.5 * l.width && b.left < l.right : b.left < l.left + 0.5 * l.width && b.right > l.left;
    if (!near) bad(`board ${i} does not overlap its layer's near edge`);
  });
  for (const l of layers) {
    l.dispatchEvent(new PointerEvent('pointerover', { bubbles: true }));
    await sleep(40);
    rowsOk(`hovering layer ${l.dataset.opt}`);
  }
  const shelvesBtn = $('.bw[data-opt=shelves]');
  shelvesBtn.click();
  await sleep(700);
  finishAll();
  rowsOk('with Shelves open');
  const panel = $('#bd-shelves');
  const pr = rect(panel);
  if (panel.hidden) bad('Shelves panel did not open');
  const pbg = getComputedStyle(panel).backgroundColor;
  if (/rgba\(.*,\s*0?\.\d+\)$/.test(pbg)) bad(`Shelves panel is not opaque (${pbg})`);
  // the panel covers no other board or layer
  for (const r of rowEls) {
    if (r.dataset.i === shelvesBtn.dataset.i) continue;
    if (hit(rect($('.bw', r)), pr, 2)) bad(`Shelves panel covers the "${r.textContent.trim().slice(0, 12)}" board`);
  }
  for (const l of layers) if (l.dataset.opt !== 'shelves' && hit(rect(l), pr, 4)) bad(`Shelves panel covers the ${l.dataset.opt} layer`);
  const dlg = $('.bd');
  stats.shelvesPanel = { scrolls: dlg.scrollHeight > dlg.clientHeight + 1, pageScrolls: document.documentElement.scrollHeight > innerHeight + 1 };
  if (stats.shelvesPanel.pageScrolls) bad('the page scrolls while the menu is open');
  shelvesBtn.click();
  await sleep(700);
  finishAll();
  rowsOk('after closing Shelves');
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
  const closed = await until(() => !$('.bd'));
  if (!closed) bad('Esc did not close the menu');
  if (document.activeElement !== btn) bad('focus did not return to the burger');

  const out = { ok: problems.length === 0, problems, stats };
  let pre = $('#check-result');
  if (!pre) { pre = document.createElement('pre'); pre.id = 'check-result'; document.body.appendChild(pre); }
  pre.textContent = JSON.stringify(out);
}
