// The reset clock (Plan 10 section 5): a rendered clock face (Plan 16) with dark wooden hands drawn on top in SVG (the old drawn face is the fallback). It shows the visitor's local time and moves once a minute (no ticking, no looping animation). Tapping it
// returns the bar to its first look.
const pct = (v) => `${+(v * 100).toFixed(3)}%`;

function hands(d) {
  const m = d.getMinutes();
  const h = (d.getHours() % 12) + m / 60;
  return { hour: h * 30, minute: m * 6 };
}

const TICKS = Array.from({ length: 12 }, (_, i) => {
  const a = (i * Math.PI) / 6;
  const long = i % 3 === 0;
  const r1 = long ? 36 : 39;
  return `<line x1="${(50 + Math.sin(a) * r1).toFixed(1)}" y1="${(50 - Math.cos(a) * r1).toFixed(1)}" x2="${(50 + Math.sin(a) * 43).toFixed(1)}" y2="${(50 - Math.cos(a) * 43).toFixed(1)}" stroke="#4a3220" stroke-width="${long ? 3 : 1.8}" stroke-linecap="round"/>`;
}).join('');

/** The old drawn face, kept as the fallback when the picture does not load (Plan 16 section 4). */
const FALLBACK_FACE = `<g class="clock-fallback">
    <circle cx="50" cy="50" r="49" fill="#8c6a2e"/><circle cx="50" cy="50" r="47" fill="#d6b25a"/><circle cx="50" cy="50" r="44.5" fill="#6b4b1b"/>
    <circle cx="50" cy="50" r="43" fill="#f3ead6"/>
    ${TICKS}
  </g>`;

/** The clock button, placed from scene.json (`clock`: centre x and y as plate fractions, size as a fraction of the plate height).
 *  `files` is the rendered face ({ "1x", "2x" }, Plan 16); the SVG on top holds only the hands and the cap. */
export function clockHTML(P, files) {
  const c = P.clock;
  const img = files ? `<img class="clock-face" src="${files['1x']}" srcset="${files['1x']} 1x, ${files['2x']} 2x" alt="" draggable="false">` : '';
  return `<button type="button" class="clock${files ? '' : ' clock--drawn'}" id="clock" aria-label="Back to the bar" style="left:${pct(c.x)};top:${pct(c.y)};--clock-h:${pct(c.size)}">
  ${img}
  <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
    ${FALLBACK_FACE}
    <g class="clock-hands">
      <line id="clock-h" x1="50" y1="50" x2="50" y2="29" stroke="#2a1a0e" stroke-width="4.2" stroke-linecap="round"/>
      <line id="clock-m" x1="50" y1="50" x2="50" y2="17" stroke="#2a1a0e" stroke-width="2.8" stroke-linecap="round"/>
      <circle cx="50" cy="50" r="3.2" fill="#a07a35" stroke="#6b4b1b" stroke-width="0.6"/>
    </g>
  </svg>
  <span class="clock-tag chalkboard chalkboard--s" aria-hidden="true"><span class="chalk">Reset</span></span>
</button>`;
}

/** Wire the clock: set the hands now and once a minute, and call `onTap` when it is pressed. Returns { destroy() }. */
export function mountClock(root, onTap) {
  const btn = root.querySelector('#clock');
  if (!btn) return { destroy() {} };
  const showFallback = () => { btn.classList.add('clock--drawn'); btn.querySelector('.clock-face')?.remove(); };
  const face = btn.querySelector('.clock-face');
  if (face) { face.addEventListener('error', showFallback, { once: true }); if (face.complete && face.currentSrc && face.naturalWidth === 0) showFallback(); }
  else showFallback();
  const set = () => {
    const { hour, minute } = hands(new Date());
    btn.querySelector('#clock-h')?.setAttribute('transform', `rotate(${hour} 50 50)`);
    btn.querySelector('#clock-m')?.setAttribute('transform', `rotate(${minute} 50 50)`);
    btn.title = '';
  };
  set();
  let timer = setTimeout(function tick() { set(); timer = setTimeout(tick, 60000); }, 60000 - (Date.now() % 60000));
  const click = () => onTap(btn);
  btn.addEventListener('click', click);
  return { destroy() { clearTimeout(timer); btn.removeEventListener('click', click); }, set };
}
