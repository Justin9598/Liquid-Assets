// The rendered bottle shells on the inner pages (Plan 08 section 3.7): every place that used to draw a bottle shape
// (a card with no photo, a hero, a producer's row) stands the shell for the drink's category instead, with the drink's own
// label crop on it when it has one, and the illustrated fallback label when it does not.
import { getJSON, img } from './data.js';
import { motifFor, shapeFor } from './labels.js';
import { shellBottle } from './scene3.js';

let scene = null;

/** Load data/scene.json once; the shells and the plates come from it. */
export async function loadScene() {
  if (!scene) {
    try { scene = await getJSON('scene.json'); } catch { scene = { plates: {}, shells: {} }; }
  }
  return scene;
}

/** A shell for a category (`shape` is a key of the manifest's shells), with a label photo URL or the fallback label. */
export const shellHTML = (shape, opts = {}) => shellBottle(scene, shape, opts) || '';

/** The shell for a drink record from drinks.json: its own label crop when it has one, else the fallback label. */
export function drinkShell(d, ix, labelOverride) {
  const info = d.category && ix.subs.get(`${d.category}/${d.sub}`);
  const label = labelOverride !== undefined ? labelOverride : (d.label ? img(d.label) : null);
  return shellHTML(shapeFor(d.category, d.sub), { label, native: info?.sub.native || null, name: info?.sub.name || (d.category ? ix.cats.get(d.category)?.name : null) || 'Drink', motif: motifFor(d.category, d.sub) });
}
