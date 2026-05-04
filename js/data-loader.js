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
export const loadAdminClasses = () => fetchJson("data/admin-classes.json");
export const loadTeachers = () => fetchJson("data/teachers.json");
export const loadManifest = () => fetchJson("data/manifest.json");
export const loadGroup = (hashHex) => fetchJson(`data/groups/${hashHex}.json`);
export const loadAdminClass = (hashHex) => fetchJson(`data/admin/${hashHex}.json`);

/* Niveaux Pix OFFICIELS (source : pix.fr/aide/comprendre-vos-resultats)
   8 niveaux. Un score < 64 ne donne aucun niveau certifié. */
export const PIX_LEVELS = [
  { slug: "non-certifie",  label: "Non certifié",  short: "—",  min: 0,   max: 63,   image: "niveau-1.svg" },
  { slug: "novice-1",      label: "Novice 1",      short: "N1", min: 64,  max: 127,  image: "niveau-1.svg" },
  { slug: "novice-2",      label: "Novice 2",      short: "N2", min: 128, max: 255,  image: "niveau-2.svg" },
  { slug: "independant-1", label: "Indépendant 1", short: "I1", min: 256, max: 383,  image: "niveau-3.svg" },
  { slug: "independant-2", label: "Indépendant 2", short: "I2", min: 384, max: 511,  image: "niveau-4.svg" },
  { slug: "avance-1",      label: "Avancé 1",      short: "A1", min: 512, max: 639,  image: "niveau-5.svg" },
  { slug: "avance-2",      label: "Avancé 2",      short: "A2", min: 640, max: 767,  image: "niveau-6.svg" },
  { slug: "expert-1",      label: "Expert 1",      short: "E1", min: 768, max: 895,  image: "niveau-7.svg" },
  { slug: "expert-2",      label: "Expert 2",      short: "E2", min: 896, max: 1024, image: "niveau-8.svg" },
];

export const PIX_MAX = 895;  // plafond effectif actuel chez Pix

export function levelFor(pix) {
  for (const lvl of PIX_LEVELS) {
    if (pix >= lvl.min && pix <= lvl.max) return lvl;
  }
  return PIX_LEVELS[PIX_LEVELS.length - 1];
}
