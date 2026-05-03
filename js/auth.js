/*
 * Authentification par code classe.
 *
 * Modèle de sécurité :
 *   - Le code saisi est hashé en SHA-256 côté navigateur (crypto.subtle.digest).
 *   - Le hash est comparé aux clés du fichier classes.json (les codes en clair
 *     ne sont jamais présents dans le code source ni dans les JSON).
 *   - Le hash retrouvé sert directement de nom de fichier pour le groupe :
 *     data/groups/<hash>.json — un attaquant qui ne connait pas le hash
 *     ne peut pas deviner l'URL.
 *   - Le hash courant est conservé en sessionStorage uniquement
 *     (efface à la fermeture de l'onglet).
 *
 * Limites assumées : la liste des hashs est publique (classes.json), donc une
 * attaque par dictionnaire sur les 11 codes Techno reste possible. C'est
 * suffisant contre la consultation casuelle entre élèves, ce qui est l'objectif.
 */

const STORAGE_KEY = "pix-lft.unlocked-hash";
const STORAGE_NAME = "pix-lft.unlocked-name";

export async function sha256Hex(text) {
  const data = new TextEncoder().encode(text.trim().toUpperCase());
  const buf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function tryUnlock(code, classesIndex) {
  const hash = await sha256Hex(code);
  const meta = classesIndex.groups[hash];
  if (!meta) return null;
  // Mémorise pour la page classe (ne survit pas à la fermeture d'onglet)
  sessionStorage.setItem(STORAGE_KEY, hash);
  sessionStorage.setItem(STORAGE_NAME, meta.name);
  return { hash, meta };
}

export function getUnlockedHash() {
  return sessionStorage.getItem(STORAGE_KEY);
}

export function getUnlockedName() {
  return sessionStorage.getItem(STORAGE_NAME);
}

export function lock() {
  sessionStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_NAME);
}
