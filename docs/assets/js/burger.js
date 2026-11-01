// The burger menu on the bar counter (Plan 07 section 3). A burger on its plate rests at the right end of the counter.
// Pressed, the scene dims, the burger rises to the right third of the screen, its plate fades out and its layers split
// apart with one menu option beside each. Only transform and opacity are animated.
import { getBuild, getSections, img } from './data.js';
import { aboutHTML } from './menu.js';
import { $, $$, announce, esc, reducedMotion } from './util.js';

const pct = (v) => `${+(v * 100).toFixed(3)}%`;
const rectStyle = (l) => `left:${pct(l.x)};top:${pct(l.y)};width:${pct(l.w)};height:${pct(l.h)}`;
const SPRING = 'cubic-bezier(0.16, 1, 0.3, 1)';
const STEP = 0.24;                       // gap between layers when split, as a fraction of the cut-out's height
const OPEN_SCALE = 3;                    // about 3 times the size on the counter (Plan 07 section 3.3)

const sprite = (l, cls, dens) => {
  const one = esc(img(l.files['1x']));
  const set = dens ? ` srcset="${one} 1x, ${esc(img(l.files['2x']))} 2x"` : '';
  return `<img class="${cls}" alt="" aria-hidden="true" draggable="false" src="${one}"${set} style="${rectStyle(l)}" data-opt="${esc(l.key || 'plate')}">`;
};

/** The layers and plate as one stack (used at rest on the counter and as the stage of the open menu). */
function stackHTML(B, dens) {
  return (B.plate ? sprite(B.plate, 'bl-plate', dens) : '') + B.layers.map((l, i) => sprite(l, `bl bl-${i}`, dens).replace('<img ', `<img data-i="${i}" `)).join('');
}

/** The resting burger: a real button, with a slate tag that reads Menu. */
export function burgerHTML(P, B) {
  const z = P.counter.burger;
  const cx = (z.x0 + z.x1) / 2;
  const top = P.counter.baseY + (P.counter.mode === 'tabs' ? 0.012 : 0.022);
  const tagY = P.counter.mode === 'tabs' ? P.counter.tabsY : P.counter.slateY;
  return `<div class="burger-anchor" style="left:${pct(cx)};top:${pct(top)};height:${pct(z.h)};--bratio:${B.ratio}">
  <button type="button" class="burger" aria-label="Menu" aria-expanded="false" aria-controls="burger-menu" data-burger>
    <span class="burger-art">${stackHTML(B, false)}</span>
  </button>
</div>
<p class="placard burger-tag chalkboard chalkboard--m" style="left:${pct(cx)};top:${pct(tagY)}" aria-hidden="true"><span class="chalk">Menu</span></p>`;
}

/** Wire the burger button inside `root`. Returns { destroy() }. */
export function mountBurger(root, { B, ix }) {
  const btn = $('[data-burger]', root);
  if (!btn || !B?.layers?.length) return { destroy() {} };
  const art = $('.burger-art', btn);
  const n = B.layers.length;
  let dlg = null;
  let state = 'closed';                 // closed | opening | open | closing
  let rows = [];
  let startTransform = '';
  let offsets = [];
  let anims = [];
  let opener = btn;

  const layerEls = () => $$('.bl', dlg);
  const stageEl = () => $('.bd-stage', dlg);
  const run = (el, frames, o) => {
    const a = el.animate(frames, { fill: 'both', ...o });
    anims.push(a);
    return a.finished.catch(() => {});
  };

  const chalk = (l) => `<span class="chalk">${esc(l.label)}</span>`;
  function optionRow(l, i) {
    const k = l.key;
    if (k === 'bar') return `<a class="bw chalkboard chalkboard--l" href="#/" data-opt="bar" data-i="${i}">${chalk(l)}</a>`;
    if (k === 'shelves') return `<button type="button" class="bw chalkboard chalkboard--l" data-opt="shelves" data-i="${i}" aria-expanded="false" aria-controls="bd-shelves">${chalk(l)}</button>`;
    if (k === 'makers') {
      return getSections().makers
        ? `<a class="bw chalkboard chalkboard--l" href="#/makers" data-opt="makers" data-i="${i}">${chalk(l)}</a>`
        : `<p class="bw soon chalkboard chalkboard--l" data-opt="makers" data-i="${i}">${chalk(l)}<span class="soonmark">Soon</span></p>`;
    }
    if (k === 'about') return `<button type="button" class="bw chalkboard chalkboard--l" data-opt="about" data-i="${i}" aria-expanded="false" aria-controls="bd-about">${chalk(l)}</button>`;
    return `<a class="bw chalkboard chalkboard--l" href="#/" data-opt="${esc(k)}" data-i="${i}">${chalk(l)}</a>`;
  }
  const TILTS = [-1.5, 1, -1, 1.5, -1, 1];                    // a fixed hand-placed tilt per board, top to bottom

  function build() {
    const cats = ix.shelf.categories.map((c) =>
      `<li><a class="bd-link" href="#/${esc(c.key)}"><span>${esc(c.name)}</span><span class="count" aria-label="${c.drinkCount} drinks">${c.drinkCount}</span></a></li>`).join('');
    const el = document.createElement('div');
    el.className = 'bd';
    el.id = 'burger-menu';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', 'Menu');
    el.innerHTML = `<div class="bd-scrim" data-close></div>
<div class="bd-inner">
<div class="bd-stage">${stackHTML(B, true)}</div>
<div class="bd-words">${B.layers.map((l, i) => `<div class="bd-row" data-i="${i}" style="--row-tilt:${TILTS[i % TILTS.length]}deg">${optionRow(l, i)}</div>`).join('')}</div>
<div class="bd-panel chalkboard chalkboard--l" id="bd-shelves" data-for="shelves" role="group" aria-label="Shelves" hidden><ul>${cats}</ul></div>
<div class="bd-panel bd-about chalkboard chalkboard--l" id="bd-about" data-for="about" role="group" aria-label="About" hidden><h2 class="bd-h">About</h2>${aboutHTML(getBuild())}</div>
</div>`;
    return el;
  }

  let portrait = false;

  /** Lay the stage, words and panels out for the current viewport (final, split positions).
   * Landscape: the burger sits in the right third, words on its left. Portrait (phones): the burger sits at the left of
   * centre, filling most of the screen height, with the words on its right (Plan 07 sections 5.2 and 7.2). */
  function layout() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    portrait = vw < 0.9 * vh;
    dlg.dataset.layout = portrait ? 'portrait' : 'landscape';
    const R = art.getBoundingClientRect();
    const hbur = Math.max(...B.layers.map((l) => l.y + l.h));
    const minX = Math.min(...B.layers.map((l) => l.x));
    const maxR = Math.max(...B.layers.map((l) => l.x + l.w));
    let H;
    let step = STEP;
    let left;
    if (portrait) {
      const visW = 0.52 * vw;                                   // the burger's own width, without the plate
      H = Math.max(120, (visW / (maxR - minX)) / B.ratio);
      H = Math.min(H, 0.3 * vh);
      step = Math.min(0.9, Math.max(STEP, (0.8 * vh / H - hbur) / (n - 1)));
      left = 12 - minX * H * B.ratio;
    } else {
      const span = hbur + (n - 1) * STEP;                       // split height in cut-out heights
      H = Math.min(OPEN_SCALE * R.height, (0.9 * vh) / span, (0.36 * vw) / B.ratio);
      H = Math.max(H, 120);
      left = Math.min((5 / 6) * vw, vw - 16 - (H * B.ratio) / 2) - (H * B.ratio) / 2;
    }
    const W = H * B.ratio;
    const top = vh / 2 - (hbur * H) / 2;
    const st = stageEl();
    Object.assign(st.style, { left: `${left}px`, top: `${top}px`, width: `${W}px`, height: `${H}px` });
    const cx = left + W / 2;
    const dx = R.left + R.width / 2 - cx;
    const dy = R.top + R.height / 2 - (top + H / 2);
    startTransform = `translate(${dx}px, ${dy}px) scale(${R.width / W})`;
    const g = step * H;
    const offs = B.layers.map((_, i) => (i - (n - 1) / 2) * g);
    rows = $$('.bd-row', dlg);
    // each board stands in front of its layer, overlapping the layer's near edge by 18% of the layer's width:
    // the left edge on a wide screen (words on the left), the right edge on a phone (words on the right)
    const OVER = 0.18;
    let edge = 0;
    rows.forEach((r, i) => {
      const l = B.layers[i];
      const y = `${top + l.cy * H + offs[i]}px`;
      if (portrait) {
        Object.assign(r.style, { top: y, left: `${left + (l.x + l.w - OVER * l.w) * W}px`, right: 'auto' });
      } else {
        Object.assign(r.style, { top: y, right: `${vw - (left + (l.x + OVER * l.w) * W)}px`, left: 'auto' });
      }
    });
    edge = portrait ? 0 : Math.min(...rows.map((r) => vw - parseFloat(r.style.right) - r.offsetWidth));
    geo = { top, H, offs, vh, vw, edge };
    $$('.bd-panel', dlg).forEach((p) => {
      const i = B.layers.findIndex((l) => l.key === p.dataset.for);
      p.dataset.i = String(i);
      p.dataset.cy = String(top + B.layers[i].cy * H + offs[i]);
      if (portrait) {                                           // inline under its layer, the width of the screen
        p.style.left = '12px';
        p.style.right = '12px';
        p.style.width = 'auto';
        p.style.minWidth = '0';
      } else {
        p.style.right = `${Math.max(16, vw - (edge - 24))}px`;
        p.style.left = 'auto';
        p.style.width = '';
        p.style.minWidth = '';
      }
    });
    placePanels();
    return offs;
  }

  // Layer rows in a layout are about this far (in cut-out heights) from their centre to their top or bottom edge.
  const HALF = 0.14;
  let geo = null;
  let shiftT = 0;

  /** The open panel's place. Landscape: beside its layer. Portrait: inline, directly under its layer; the layers below it
   * slide down by `shift` to make room (Plan 07 section 8.1). Returns { top, shift }. */
  function placePanels() {
    if (!dlg || !geo) return { top: 0, shift: 0 };
    let result = { top: 0, shift: 0 };
    $$('.bd-panel', dlg).forEach((p) => {
      const h = p.offsetHeight || 0;
      const cy = Number(p.dataset.cy);
      const i = Number(p.dataset.i);
      let t;
      let shift = 0;
      if (portrait) {
        t = cy + HALF * geo.H + 6;
        if (i < n - 1) {
          const nextTop = geo.top + B.layers[i + 1].cy * geo.H + geo.offs[i + 1] - HALF * geo.H;
          shift = Math.max(0, t + h + 12 - nextTop);
        }
      } else {
        t = Math.max(12, Math.min(cy - h / 2, geo.vh - 12 - h));
      }
      p.style.top = `${t}px`;
      if (!p.hidden) result = { top: t, shift, bottom: t + h, i };
    });
    return result;
  }

  /** Slide the layers (and their words) below layer `idx` down by `d` px, with the spring ease and transforms only. */
  function setShift(idx, d) {
    dlg.classList.add('shifting');
    clearTimeout(shiftT);
    shiftT = setTimeout(() => dlg?.classList.remove('shifting'), 560);
    layerEls().forEach((el, i) => { el.style.transform = `translateY(${offsets[i] + (i > idx && d ? d : 0)}px)`; });
    rows.forEach((r, i) => { r.style.transform = i > idx && d ? `translateY(${d}px)` : ''; });
  }

  /** The open menu scrolls inside itself when the stack plus the panel is taller than the screen; the page never scrolls. */
  function fitInner(extraBottom) {
    const inner = $('.bd-inner', dlg);
    const lastBottom = geo.top + B.layers[n - 1].cy * geo.H + geo.offs[n - 1] + HALF * geo.H;
    const need = Math.max(lastBottom + (extraBottom.shift || 0), extraBottom.bottom || 0) + 16;
    inner.style.height = need > geo.vh ? `${need}px` : '';
  }

  function showPanel(key, on) {
    const p = $(`.bd-panel[data-for="${key}"]`, dlg);
    const b = $(`.bw[data-opt="${key}"]`, dlg);
    if (!p) return;
    if (on) {
      $$('.bd-panel', dlg).forEach((o) => { if (o !== p) showPanel(o.dataset.for, false); });
      p.hidden = false;
      const r = placePanels();
      if (portrait) {
        setShift(Number(p.dataset.i), r.shift);
        fitInner(r);
        dlg.scrollTo({ top: Math.max(0, r.bottom + 16 - geo.vh), behavior: 'auto' });
      }
      if (!reducedMotion()) p.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 240, easing: SPRING });
    } else {
      p.hidden = true;
      if (portrait && !$$('.bd-panel', dlg).some((o) => !o.hidden)) {
        setShift(-1, 0);
        fitInner({});
        dlg.scrollTo({ top: 0, behavior: 'auto' });
      }
    }
    b?.setAttribute('aria-expanded', String(on));
  }

  const toggle = (key) => { const p = $(`.bd-panel[data-for="${key}"]`, dlg); showPanel(key, p?.hidden !== false); };

  async function open(panel, { instant = false } = {}) {
    if (state !== 'closed') return;
    state = 'opening';
    opener = btn;
    btn.setAttribute('aria-expanded', 'true');
    dlg = build();
    document.body.appendChild(dlg);
    document.body.classList.add('menu-open');
    $('#main')?.setAttribute('inert', '');
    openSize = [window.innerWidth, window.innerHeight];
    const offs = layout();
    offsets = offs;
    const els = layerEls();
    const plate = $('.bl-plate', dlg);
    const scrim = $('.bd-scrim', dlg);
    art.style.opacity = '0';
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', onResize);
    window.addEventListener('hashchange', onHash);
    announce('Menu open');
    if (reducedMotion() || instant) {                            // opens already split, no flying
      els.forEach((el, i) => { el.style.transform = `translateY(${offs[i]}px)`; });
      plate.style.opacity = '0';
      dlg.classList.add('split');
      if (!instant) await run(dlg, [{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: 'linear' });
    } else {
      const st = stageEl();
      const jobs = [
        run(scrim, [{ opacity: 0 }, { opacity: 1 }], { duration: 320, easing: 'ease-out' }),
        run(st, [{ transform: startTransform }, { transform: 'none' }], { duration: 480, easing: SPRING }),
      ];
      if (plate) jobs.push(run(plate, [{ opacity: 1 }, { opacity: 0 }], { duration: 380, easing: 'ease-out' }));
      els.forEach((el, i) => jobs.push(run(el, [{ transform: 'translateY(0)' }, { transform: `translateY(${offs[i]}px)` }],
        { duration: 400, delay: 110 + i * 40, easing: SPRING })));
      rows.forEach((r, i) => jobs.push(run(r, [{ opacity: 0, transform: `translateX(${portrait ? 30 : -30}px)` }, { opacity: 1, transform: 'translateX(0)' }],
        { duration: 380, delay: 280 + i * 50, easing: SPRING })));
      await Promise.all(jobs);
      // keep the end state without running animations: layers apart, plate gone, words in
      anims.forEach((a) => { try { a.cancel(); } catch { /* ignore */ } });
      anims = [];
      els.forEach((el, i) => { el.style.transform = `translateY(${offs[i]}px)`; });
      if (plate) plate.style.opacity = '0';
      dlg.classList.add('split');
    }
    if (state !== 'opening') return;
    state = 'open';
    if (typeof panel === 'string' && panel) showPanel(panel, true);
    $('.bw[href], .bw[type="button"]', dlg)?.focus();
  }

  function finish(restoreFocus) {
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', onResize);
    window.removeEventListener('hashchange', onHash);
    anims.forEach((a) => { try { a.cancel(); } catch { /* already finished */ } });
    anims = [];
    dlg?.remove();
    dlg = null;
    art.style.opacity = '';
    document.body.classList.remove('menu-open');
    $('#main')?.removeAttribute('inert');
    btn.setAttribute('aria-expanded', 'false');
    state = 'closed';
    if (restoreFocus) btn.focus();
  }

  async function close({ restoreFocus = true } = {}) {
    if (state === 'closed' || state === 'closing') return;
    state = 'closing';
    const el = dlg;
    el.classList.remove('split');
    $$('.bd-panel', el).forEach((p) => { p.hidden = true; });
    if (reducedMotion()) {
      await run(el, [{ opacity: 1 }, { opacity: 0 }], { duration: 150, easing: 'linear' });
      finish(restoreFocus);
      return;
    }
    anims.forEach((a) => { try { a.cancel(); } catch { /* ignore */ } });
    anims = [];
    const offs = offsets;
    const els = layerEls();
    const st = stageEl();
    const plate = $('.bl-plate', el);
    const T = 0;
    const jobs = [];
    rows.forEach((r) => jobs.push(run(r, [{ opacity: 1, transform: 'translateX(0)' }, { opacity: 0, transform: `translateX(${portrait ? 18 : -18}px)` }], { duration: 160, easing: 'ease-in' })));
    // layers rejoin in reverse order: the bottom layer first, the top bun last
    els.forEach((e, i) => jobs.push(run(e, [{ transform: `translateY(${offs[i]}px)` }, { transform: 'translateY(0)' }],
      { duration: 340, delay: T + (n - 1 - i) * 40, easing: SPRING })));
    await Promise.all(jobs);
    const back = [
      run($('.bd-scrim', el), [{ opacity: 1 }, { opacity: 0 }], { duration: 340, easing: 'ease-in' }),
      run(st, [{ transform: 'none' }, { transform: startTransform }], { duration: 380, easing: 'cubic-bezier(0.65, 0, 0.35, 1)' }),
    ];
    if (plate) back.push(run(plate, [{ opacity: 0 }, { opacity: 1 }], { duration: 300, delay: 120, easing: 'ease-in' }));
    await Promise.all(back);
    finish(restoreFocus);
  }

  /** A word that is a button: Shelves and About open their panel. */
  function choose(opt) {
    if (opt === 'shelves' || opt === 'about') toggle(opt);
  }

  function onClick(ev) {
    if (!dlg || state === 'closing') return;
    const t = ev.target;
    if (btn.contains(t)) return;                                  // the press that opened the menu
    const link = t.closest('a.bw, a.bd-link');
    if (link) { close({ restoreFocus: true }); return; }          // the link's own navigation proceeds
    const word = t.closest('.bw');
    if (word) { choose(word.dataset.opt); return; }
    const layer = t.closest('.bl');
    if (layer && dlg.classList.contains('split')) { $(`.bw[data-opt="${layer.dataset.opt}"]`, dlg)?.click(); return; }
    if (t.closest('.bd-panel, .bd-row')) return;
    close({ restoreFocus: true });                                // click away
  }

  function onOver(ev) {
    const l = ev.target.closest?.('.bl');
    rows.forEach((r) => r.classList.toggle('hot', !!l && r.dataset.i === l.dataset.i));
  }

  const focusables = () => $$('a[href], button:not([disabled])', dlg).filter((e) => !e.closest('[hidden]'));
  function onKey(ev) {
    if (!dlg) return;
    if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); close({ restoreFocus: true }); return; }
    if (ev.key === 'Tab') {
      const f = focusables();
      if (!f.length) return;
      const first = f[0];
      const last = f[f.length - 1];
      if (!dlg.contains(document.activeElement)) { ev.preventDefault(); first.focus(); }
      else if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    }
  }
  let openSize = [0, 0];
  // a resize (rotation, a phone's toolbar) while the menu is open lays it out again where it stands
  const onResize = () => {
    if (!dlg || state !== 'open') return;
    if (window.innerWidth === openSize[0] && window.innerHeight === openSize[1]) return;
    openSize = [window.innerWidth, window.innerHeight];
    const offs = layout();
    offsets = offs;
    layerEls().forEach((el, i) => { el.style.transform = `translateY(${offs[i]}px)`; });
  };
  const onHash = () => { if (dlg && state !== 'closing') close({ restoreFocus: false }); };

  const onBtn = () => open();
  btn.addEventListener('click', onBtn);
  document.addEventListener('click', onClick);
  document.addEventListener('pointerover', onOver);
  return {
    destroy() {
      btn.removeEventListener('click', onBtn);
      document.removeEventListener('click', onClick);
      document.removeEventListener('pointerover', onOver);
      if (dlg) finish(false);
    },
    open,
    isOpen: () => state === 'open' || state === 'opening',
    opener: () => opener,
  };
}
