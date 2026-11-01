// Illustrated props for the rustic bar (Plan 01 section 7): the carved sign, stools, barrel, framed print and glasses.
// Everything here is decorative (aria-hidden), drawn in SVG so it scales and rearranges for phones.

export const SIGN = `<svg class="sign-svg" viewBox="0 0 900 200" aria-hidden="true" focusable="false">
<defs>
  <filter id="sg-oak" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.006 0.22" numOctaves="3" seed="9" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.40  0 0 0 0 0.26  0 0 0 0 0.12  0 0 0 0.95 -0.32" result="grain"/>
    <feComposite in="grain" in2="SourceGraphic" operator="in" result="g2"/>
    <feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="g2"/></feMerge>
  </filter>
  <filter id="sg-carve" x="-5%" y="-25%" width="110%" height="150%">
    <feComponentTransfer in="SourceAlpha" result="inv"><feFuncA type="table" tableValues="1 0"/></feComponentTransfer>
    <feGaussianBlur in="inv" stdDeviation="2.2" result="blur"/>
    <feOffset in="blur" dx="3" dy="3" result="off"/>
    <feFlood flood-color="#2a1608" flood-opacity=".9" result="col"/>
    <feComposite in="col" in2="off" operator="in" result="sh"/>
    <feComposite in="sh" in2="SourceAlpha" operator="in" result="inner"/>
    <feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="inner"/></feMerge>
  </filter>
  <radialGradient id="sg-knot"><stop offset="0" stop-color="#5a3a1c"/><stop offset=".55" stop-color="#7a5430"/><stop offset="1" stop-color="#c49a68" stop-opacity="0"/></radialGradient>
</defs>
<g fill="#1f1c1a" stroke="#1f1c1a">
  <path d="M128 0V52M772 0V52" stroke-width="6" fill="none"/>
  <rect x="116" y="0" width="24" height="9" rx="2" stroke="none"/><rect x="760" y="0" width="24" height="9" rx="2" stroke="none"/>
  <path d="M116 44h24v10h-24zM760 44h24v10h-24z" stroke="none"/>
  <circle cx="122" cy="49" r="2" fill="#6f655c" stroke="none"/><circle cx="134" cy="49" r="2" fill="#6f655c" stroke="none"/>
  <circle cx="766" cy="49" r="2" fill="#6f655c" stroke="none"/><circle cx="778" cy="49" r="2" fill="#6f655c" stroke="none"/>
</g>
<ellipse cx="450" cy="184" rx="420" ry="9" fill="#000" opacity=".28"/>
<g filter="url(#sg-oak)">
  <path d="M22 54H878L880 95H20Z" fill="#c9a06c"/>
  <path d="M17 95H883L881 137H19Z" fill="#c29765"/>
  <path d="M25 137H875L877 176H23Z" fill="#cba473"/>
</g>
<g fill="none" stroke="#4a2e18" stroke-opacity=".55" stroke-width="2.2"><path d="M20 95H880M19 137H881"/></g>
<g fill="none" stroke="#fff3d6" stroke-opacity=".35" stroke-width="1.4"><path d="M21 97H879M20 139H880"/><path d="M22 55H878"/></g>
<ellipse cx="238" cy="76" rx="11" ry="7" fill="url(#sg-knot)"/><ellipse cx="640" cy="118" rx="12" ry="8" fill="url(#sg-knot)"/><ellipse cx="760" cy="158" rx="10" ry="6" fill="url(#sg-knot)"/>
<g fill="#3d2716"><circle cx="36" cy="63" r="3"/><circle cx="864" cy="63" r="3"/><circle cx="34" cy="105" r="3"/><circle cx="866" cy="105" r="3"/><circle cx="38" cy="146" r="3"/><circle cx="862" cy="146" r="3"/></g>
<g font-family="Rye, 'Stardos Stencil', serif" font-size="92" text-anchor="middle">
  <text x="453" y="143" fill="#fff0d0" opacity=".8" textLength="760" lengthAdjust="spacingAndGlyphs">LIQUID ASSETS</text>
  <text x="450" y="140" fill="#8b6439" filter="url(#sg-carve)" textLength="760" lengthAdjust="spacingAndGlyphs">LIQUID ASSETS</text>
</g>
</svg>`;

export const STOOL = `<svg class="stool" viewBox="0 0 120 170" aria-hidden="true" focusable="false">
<defs><radialGradient id="st-sea" cx=".5" cy=".42" r=".7"><stop offset="0" stop-color="#dcc28f"/><stop offset="1" stop-color="#b9995f"/></radialGradient></defs>
<g stroke="#1f1c1a" stroke-linecap="round" fill="none">
  <path d="M26 52L14 170M94 52L106 170" stroke-width="5.5"/>
  <path d="M46 56L41 170M74 56L79 170" stroke-width="4" opacity=".8"/>
  <ellipse cx="60" cy="122" rx="46" ry="10" stroke-width="4"/>
</g>
<path d="M7 32v14a53 15 0 0 0 106 0V32z" fill="#1f1c1a"/>
<ellipse cx="60" cy="32" rx="53" ry="15" fill="#2c2926"/>
<ellipse cx="60" cy="31" rx="47" ry="12" fill="url(#st-sea)"/>
<g fill="none" stroke="#8d6f3e" stroke-opacity=".55" stroke-width="1.2"><ellipse cx="60" cy="31" rx="38" ry="9.5"/><ellipse cx="60" cy="31" rx="28" ry="7"/><ellipse cx="60" cy="31" rx="18" ry="4.5"/><ellipse cx="60" cy="31" rx="8" ry="2.2"/><path d="M60 19.5V42.5M14 31H106M27 22L93 40M93 22L27 40" stroke-opacity=".3"/></g>
<path d="M18 26Q60 16 100 25" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="2"/>
</svg>`;

export const BARREL = `<svg class="barrel-svg" viewBox="0 0 120 160" aria-hidden="true" focusable="false">
<defs><linearGradient id="br-g" x1="0" x2="1"><stop offset="0" stop-color="#6e4524"/><stop offset=".3" stop-color="#b58850"/><stop offset=".6" stop-color="#9a6b3a"/><stop offset="1" stop-color="#5e3a1e"/></linearGradient></defs>
<path d="M14 24Q-4 82 14 148H106Q124 82 106 24Z" fill="url(#br-g)"/>
<g fill="none" stroke="#3d2716" stroke-opacity=".5" stroke-width="1.4"><path d="M30 26Q20 86 30 148M45 26Q40 86 45 148M60 26V148M75 26Q80 86 75 148M90 26Q100 86 90 148"/></g>
<g fill="none" stroke="#1f1c1a" stroke-width="7"><path d="M8 52Q60 66 112 52M3 100Q60 114 117 100"/></g>
<ellipse cx="60" cy="24" rx="46" ry="11" fill="#a8794a" stroke="#4a2e18" stroke-width="2"/>
<ellipse cx="60" cy="24" rx="36" ry="7.5" fill="none" stroke="#6b4423" stroke-opacity=".6"/>
<ellipse cx="60" cy="21" rx="20" ry="5" fill="#8f9091"/><ellipse cx="60" cy="20" rx="14" ry="3.2" fill="#b3b4b5"/>
</svg>`;

// a deterministic little random so the print looks the same on every load
const rng = (() => { let s = 7; return () => { s = (s * 16807) % 2147483647; return s / 2147483647; }; })();

export const PRINT = (() => {
  let specks = '';
  for (let i = 0; i < 70; i++) specks += `<circle cx="${(10 + rng() * 130).toFixed(1)}" cy="${(10 + rng() * 180).toFixed(1)}" r="${(0.4 + rng() * 1.6).toFixed(1)}" fill="#e9ddc2"/>`;
  return `<svg class="print-svg" viewBox="0 0 150 200" aria-hidden="true" focusable="false">
<defs>
  <radialGradient id="pr-s1"><stop offset="0" stop-color="#b79868" stop-opacity=".55"/><stop offset="1" stop-color="#b79868" stop-opacity="0"/></radialGradient>
  <linearGradient id="pr-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eee2c6"/><stop offset="1" stop-color="#dccaa4"/></linearGradient>
</defs>
<rect width="150" height="200" fill="#1a1715"/>
<rect x="7" y="7" width="136" height="186" fill="url(#pr-bg)"/>
<ellipse cx="30" cy="40" rx="42" ry="30" fill="url(#pr-s1)"/><ellipse cx="118" cy="150" rx="46" ry="40" fill="url(#pr-s1)"/><ellipse cx="110" cy="30" rx="26" ry="18" fill="url(#pr-s1)"/>
<g font-family="Cormorant Garamond, Georgia, serif" text-anchor="middle" fill="#4e3b26" opacity=".62">
  <text x="75" y="36" font-size="8" letter-spacing="2.4">THE BAR</text>
  <text x="75" y="84" font-size="31" font-weight="700">LIQUID</text>
  <text x="75" y="118" font-size="31" font-weight="700">ASSETS</text>
  <text x="75" y="142" font-size="9" letter-spacing="2">· EST. 2026 ·</text>
  <text x="75" y="172" font-size="6.5" letter-spacing="1.2">SAKE · BEER · WINE · SPIRITS</text>
</g>
<path d="M22 150h106" stroke="#4e3b26" stroke-opacity=".4"/>
${specks}
</svg>`;
})();

const glass = (cx, y = 0, s = 1) => `<g transform="translate(${cx} ${y}) scale(${s})">
<path d="M-15 8C-19 38-8 54 0 54C8 54 19 38 15 8Z" fill="#e8f1f4" fill-opacity=".28" stroke="#fff" stroke-opacity=".75" stroke-width="1.2"/>
<path d="M-11 12C-12 30-7 42-3 48" stroke="#fff" stroke-opacity=".7" stroke-width="1.6" fill="none"/>
<rect x="-1.3" y="54" width="2.6" height="32" fill="#e8f1f4" fill-opacity=".55"/>
<ellipse cx="0" cy="88" rx="13" ry="3.2" fill="#e8f1f4" fill-opacity=".5" stroke="#fff" stroke-opacity=".6"/>
</g>`;

/** Two stemmed glasses on a small round wooden tray (counter top). */
export const GLASSES = `<svg class="glasses-svg" viewBox="0 0 150 124" aria-hidden="true" focusable="false">
<ellipse cx="75" cy="106" rx="68" ry="13" fill="#6b4b2b"/><ellipse cx="75" cy="103" rx="68" ry="12" fill="#c7a06c"/><ellipse cx="75" cy="103" rx="56" ry="9" fill="#d6b27d"/>
<ellipse cx="75" cy="106" rx="68" ry="13" fill="none" stroke="#8d6b48" stroke-width="1.5"/>
${glass(52, 0, 0.98)}${glass(98, 4, 0.98)}
</svg>`;

/** Props for the narrow side bay: stacked glasses, a tray and dim bottles. One row per shelf. */
export const BAY_ROWS = [
  `<svg viewBox="0 0 150 70" aria-hidden="true" focusable="false">${[22, 50, 78, 106, 134].map((x) => glass(x, -2, 0.62)).join('')}</svg>`,
  `<svg viewBox="0 0 150 70" aria-hidden="true" focusable="false">
<g fill="#e8f1f4" fill-opacity=".34" stroke="#fff" stroke-opacity=".6">${[0, 1, 2, 3].map((i) => `<path d="M${30 - i * 0.5} ${64 - i * 14}h30l-3 ${-12}h-24z" transform="translate(0 0)"/>`).join('')}</g>
<ellipse cx="108" cy="62" rx="34" ry="6" fill="#c7a06c"/><ellipse cx="108" cy="60" rx="34" ry="5.5" fill="#d6b27d"/>
<path d="M92 56c0-14 6-22 16-22s16 8 16 22z" fill="#8d6b48" opacity=".9"/><rect x="104" y="28" width="8" height="8" rx="2" fill="#6b4b2b"/>
</svg>`,
  `<svg viewBox="0 0 150 70" aria-hidden="true" focusable="false"><g opacity=".8">
<path d="M26 66V32l4-8h8l4 8v34z" fill="#3a2a14"/><path d="M62 66V28l4-10h8l4 10v38z" fill="#1f3a26"/><path d="M98 66V34l4-8h8l4 8v32z" fill="#6b3a14"/><path d="M122 66V30l3-8h6l3 8v36z" fill="#2e2418"/>
<rect x="28" y="40" width="12" height="14" fill="#efe6d2" opacity=".85"/><rect x="64" y="38" width="12" height="16" fill="#efe6d2" opacity=".85"/><rect x="100" y="42" width="12" height="12" fill="#efe6d2" opacity=".85"/></g></svg>`,
];
