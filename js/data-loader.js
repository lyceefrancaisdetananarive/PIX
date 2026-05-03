/*
 * Chargement des fichiers JSON statiques générés par build-data.py.
 * Cache en mémoire pour éviter les fetch redondants.
 */

const CACHE = new Map();

async function fetchJson(path) {
  if (CACHE.has(path)) return CACHE.get(path);
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Impossible de charger ${path} (${res.status})`);
  }
  const data = await res.json();
  CACHE.set(path, data);
  return data;
}

export const loadPublic = () => fetchJson("data/students-public.json");
export const loadClasses = () => fetchJson("data/classes.json");
export const loadManifest = () => fetchJson("data/manifest.json");
export const loadGroup = (hashHex) => fetchJson(`data/groups/${hashHex}.json`);

/* Niveaux Pix officiels (en miroir du manifest, pour pouvoir les utiliser
   sans attendre un fetch) */
export const PIX_LEVELS = [
  { slug: "novice",      label: "Novice",      min: 0,    max: 47 },
  { slug: "debutant",    label: "Débutant",    min: 48,   max: 143 },
  { slug: "independant", label: "Indépendant", min: 144,  max: 287 },
  { slug: "avance",      label: "Avancé",      min: 288,  max: 511 },
  { slug: "expert",      label: "Expert",      min: 512,  max: 1024 },
];

export const PIX_MAX = 1024;

export function levelFor(pix) {
  for (const lvl of PIX_LEVELS) {
    if (pix >= lvl.min && pix <= lvl.max) return lvl;
  }
  return PIX_LEVELS[PIX_LEVELS.length - 1];
}
