// Data loading. Everything is a relative path so the site works from a sub-path such as /Liquid-Assets/.

let version = '';
let build = null;
const cache = new Map();

export async function initData() {
  try {
    const r = await fetch('data/build.json', { cache: 'no-cache' });
    build = await r.json();
    version = build.version || '';
  } catch {
    build = null;
  }
  return build;
}

export const getBuild = () => build;
/** Which sections of the site are published (Plan 06 section 12). Missing means everything, as in a full local build. */
export const getSections = () => build?.sections || { welcome: true, shelves: true, drinks: true, makers: true };
export const withVersion = (url) => (version ? `${url}?v=${version}` : url);
export const img = (path) => (path ? withVersion(path) : null);

export function getJSON(path) {
  if (!cache.has(path)) {
    const p = fetch(withVersion('data/' + path)).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    });
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return cache.get(path);
}

let idx = null;
/** Loads shelf.json and drinks.json once and builds lookup tables. */
export async function getIndex() {
  if (idx) return idx;
  idx = (async () => {
    const s = getSections();
    const [shelf, drinks] = await Promise.all([getJSON('shelf.json'), s.shelves || s.drinks ? getJSON('drinks.json') : Promise.resolve([])]);
    const cats = new Map(shelf.categories.map((c) => [c.key, c]));
    const subs = new Map();
    for (const c of shelf.categories) for (const s of c.subcategories) subs.set(`${c.key}/${s.key}`, { cat: c, sub: s });
    const byId = new Map(drinks.map((d) => [d.id, d]));
    return { shelf, drinks, cats, subs, byId };
  })();
  idx.catch(() => { idx = null; });
  return idx;
}
