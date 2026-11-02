// The bar behind every page (Plan 08 section 3.1): the rendered plate, fixed in place, dimmed a little, with the boards
// scrolling over it. A `position: fixed` layer holds the plate (not `background-attachment: fixed`, which fails on iPhone).
// Wide plate on desktop and tablet, tall plate on phones, cropped with the same cover rule as the welcome page.
//
// It also measures, in pixels, where the sign ends so the first board can start just below it (`content_top` in
// scene.json), and where the sign is, for the link over it. While the visitor is scrolled down those numbers stay put, so a
// phone's collapsing toolbar cannot make the page jump; they catch up when the page is back at the top.
import { plateHTML, plateKind, wideQuery } from './scene3.js';
import { $ } from './util.js';

export function mountBackdrop(manifest) {
  const el = document.createElement('div');
  el.id = 'backdrop';
  el.setAttribute('aria-hidden', 'true');
  document.body.prepend(el);
  const root = document.documentElement;
  let kind = null;
  let lastW = 0;
  let stale = false;

  function measure() {
    const P = manifest.plates[kind];
    const cover = $('.plate-cover', el).getBoundingClientRect();
    const px = (v) => `${Math.round(v * 10) / 10}px`;
    root.style.setProperty('--content-top', px(Math.max(0, cover.top + P.content_top * cover.height)));
    root.style.setProperty('--sign-l', px(cover.left + P.sign.x0 * cover.width));
    root.style.setProperty('--sign-t', px(cover.top + P.sign.y0 * cover.height));
    root.style.setProperty('--sign-w', px((P.sign.x1 - P.sign.x0) * cover.width));
    root.style.setProperty('--sign-h', px((P.sign.y1 - P.sign.y0) * cover.height));
  }

  /** Re-measure now, or later (when the page is back at the top) if the visitor is scrolled down and only the height moved. */
  function layout(force = false) {
    const w = window.innerWidth;
    if (!force && window.scrollY > 8 && w === lastW) { stale = true; return; }
    lastW = w;
    stale = false;
    measure();
  }

  function render() {
    kind = plateKind();
    const P = manifest.plates[kind];
    el.innerHTML = `<div class="plate-cover" style="--ratio:${P.ratio}">${plateHTML(P)}</div><div class="dim"></div>`;
    el.dataset.plate = kind;
    root.dataset.plate = kind;
    layout(true);
  }

  const onResize = () => layout(false);
  const onScroll = () => { if (stale && window.scrollY <= 8) layout(true); };
  const onMq = () => { if (plateKind() !== kind) render(); };
  window.addEventListener('resize', onResize);
  window.addEventListener('scroll', onScroll, { passive: true });
  wideQuery.addEventListener('change', onMq);
  render();

  return {
    el,
    /** Pages call this after they change the document's top (a new route starts at scroll 0). */
    relayout: () => layout(true),
    destroy() {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('scroll', onScroll);
      wideQuery.removeEventListener('change', onMq);
      el.remove();
    },
  };
}
