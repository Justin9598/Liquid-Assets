// The reset clock (Plan 10 section 5): a small wall clock drawn in SVG, with a brass rim, a cream face, dark wooden hands and
// twelve ticks. It shows the visitor's local time and moves once a minute (no ticking, no looping animation). Tapping it
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

/** The clock button, placed from scene.json (`clock`: centre x and y as plate fractions, size as a fraction of the plate height). */
export function clockHTML(P) {
  const c = P.clock;
  return `<button type="button" class="clock" id="clock" aria-label="Back to the bar" style="left:${pct(c.x)};top:${pct(c.y)};--clock-h:${pct(c.size)}">
  <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
    <circle cx="50" cy="50" r="49" fill="#8c6a2e"/><circle cx="50" cy="50" r="47" fill="#d6b25a"/><circle cx="50" cy="50" r="44.5" fill="#6b4b1b"/>
    <circle cx="50" cy="50" r="43" fill="#f3ead6"/>
    ${TICKS}
    <line id="clock-h" x1="50" y1="50" x2="50" y2="27" stroke="#3a2412" stroke-width="4.6" stroke-linecap="round"/>
    <line id="clock-m" x1="50" y1="50" x2="50" y2="17" stroke="#3a2412" stroke-width="3.2" stroke-linecap="round"/>
    <circle cx="50" cy="50" r="3.6" fill="#8c6a2e"/>
  </svg>
  <span class="clock-tag chalkboard chalkboard--s" aria-hidden="true"><span class="chalk">Reset</span></span>
</button>`;
}

/** Wire the clock: set the hands now and once a minute, and call `onTap` when it is pressed. Returns { destroy() }. */
export function mountClock(root, onTap) {
  const btn = root.querySelector('#clock');
  if (!btn) return { destroy() {} };
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
