// The places the Makers map moves through (Plan 14 section 5.3): World > Continent > Region > Country > Japan's area > Province or
// state > Maker. Pure data, no drawing, so it can be tested on its own.
//
// Two rules decide what shows (section 5.3):
//   - fewer than MIN_GROUP makers: a place does not break down any further; opening it shows its makers' own pins;
//   - one child: a level with only one group below it is skipped.
// The groups come from each maker's own fields in producers.json (cont, reg, cid, area, prov), so the tree never waits for a
// map file to load.
import { slug } from './util.js';

export const MIN_GROUP = 10;

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** The maker's places, from the top: [{ level, id, name }]. A maker with no area or province just stops early. */
export function chainOf(p) {
  const out = [];
  if (p.cont) out.push({ level: 'continent', id: slug(p.cont), name: p.cont });
  if (p.reg) out.push({ level: 'region', id: slug(p.reg), name: p.reg });
  if (p.cid) out.push({ level: 'country', id: p.cid, name: p.country || cap(p.cid) });
  if (p.area) out.push({ level: 'area', id: p.area, name: cap(p.area) });
  if (p.prov) out.push({ level: 'province', id: p.prov, name: p.provName || cap(p.prov) });
  return out;
}

/** Makers with a pin go in the tree. Returns the root: { level: 'world', id: '', name: 'Everywhere', path: '', producers, children, own }. */
export function buildTree(producers) {
  const root = { level: 'world', id: '', name: 'Everywhere', label: 'World', path: '', producers: [], children: [], own: [], parent: null };
  for (const p of producers) {
    if (p.lat == null || p.lon == null) continue;
    let node = root;
    root.producers.push(p);
    for (const c of chainOf(p)) {
      let child = node.children.find((x) => x.level === c.level && x.id === c.id);
      if (!child) {
        child = { level: c.level, id: c.id, name: c.name, label: c.name, path: node.path ? `${node.path}/${c.id}` : c.id, producers: [], children: [], own: [], parent: node };
        node.children.push(child);
      }
      child.producers.push(p);
      node = child;
    }
    node.own.push(p);                                   // a maker belongs to the deepest place its fields reach
  }
  const order = (a, b) => b.producers.length - a.producers.length || a.name.localeCompare(b.name);
  (function sort(n) { n.children.sort(order); n.children.forEach(sort); })(root);
  return root;
}

/** The place with this address ("asia/east-asia/japan/tohoku"), or null. */
export function findNode(root, path) {
  let node = root;
  for (const seg of String(path || '').split('/').filter(Boolean)) {
    node = node.children.find((c) => c.id === seg);
    if (!node) return null;
  }
  return node;
}

/** What opening a place shows (section 5.3): its makers' pins, or one pin per group below it.
 * `node` in the result is the place the groups belong to: a chain of single-child places is skipped to reach it. */
export function viewOf(node) {
  if (node.producers.length < MIN_GROUP) return { kind: 'makers', node, makers: node.producers, groups: [] };
  let eff = node;
  while (eff.children.length === 1 && eff.own.length === 0) eff = eff.children[0];
  if (!eff.children.length) return { kind: 'makers', node: eff, makers: eff.producers, groups: [] };
  return { kind: 'groups', node: eff, makers: eff.own, groups: eff.children };
}

/** The chalk breadcrumb: World, then each place on the way down. A place with the same name as the one before it is dropped
 * (South America, then the South America region, then Chile reads "South America > Chile"). */
export function crumbs(node) {
  const chain = [];
  for (let n = node; n; n = n.parent) chain.unshift(n);
  const out = [];
  chain.forEach((n, i) => {
    const next = chain[i + 1];
    if (next && next.name === n.name && next.producers.length === n.producers.length) return;
    out.push(n);
  });
  return out;
}

/** One step up: the nearest place above this one that shows something different. */
export function upFrom(node) {
  let n = node.parent;
  while (n && n.parent && n.producers.length === node.producers.length) n = n.parent;
  return n || null;
}

/** The smallest place that holds all of these makers. */
export function smallestHolding(root, makers) {
  if (!makers.length) return root;
  const chains = makers.map((p) => chainOf(p).map((c) => c.id));
  let node = root;
  for (let d = 0; ; d++) {
    const id = chains[0][d];
    if (!id || chains.some((c) => c[d] !== id)) break;
    const child = node.children.find((c) => c.id === id);
    if (!child) break;
    node = child;
  }
  return node;
}

/** The place for a country (the dropdown, and the old ?country= address), or null. */
export function countryNode(root, cid) {
  let found = null;
  (function walk(n) { if (n.level === 'country' && n.id === cid) found = n; else n.children.forEach(walk); })(root);
  return found;
}

/** The place for a province (the old ?region= address) within a country, or null. */
export function provinceNode(root, cid, prov) {
  const c = countryNode(root, cid);
  let found = null;
  (function walk(n) { if (n.level === 'province' && n.id === prov) found = n; else n.children.forEach(walk); })(c || { children: [] });
  return found;
}

export function tally(list) {
  return { makers: list.length, drinks: list.reduce((a, p) => a + (p.drinkCount || 0), 0), favourites: list.reduce((a, p) => a + (p.favourites || 0), 0) };
}

/** Every place reachable by opening pins from the World, for tests: [{ node, view }]. */
export function walk(root) {
  const out = [];
  (function go(node) {
    const view = viewOf(node);
    out.push({ node, view });
    if (view.kind === 'groups') view.groups.forEach(go);
  })(root);
  return out;
}
