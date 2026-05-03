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
const STORAGE_TEACHER = "pix-lft.teacher-hash";
const STORAGE_TEACHER_NAME = "pix-lft.teacher-name";

export async function sha256Hex(text) {
  const data = new TextEncoder().encode(text.trim().toUpperCase());
  const buf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Tente de déverrouiller : essaie d'abord les codes PROFS puis les codes ÉLÈVES.
 * Retourne :
 *   { type: "teacher", hash, meta }   pour un code prof
 *   { type: "student", hash, meta }   pour un code élève
 *   null                              si aucun match
 */
export async function tryUnlock(code, classesIndex, teachersIndex) {
  const hash = await sha256Hex(code);

  // 1. Code PROF (priorité — vue globale)
  const teacher = teachersIndex?.teachers?.[hash];
  if (teacher) {
    sessionStorage.setItem(STORAGE_TEACHER, hash);
    sessionStorage.setItem(STORAGE_TEACHER_NAME, teacher.name);
    return { type: "teacher", hash, meta: teacher };
  }

  // 2. Code ÉLÈVE
  const group = classesIndex?.groups?.[hash];
  if (group) {
    sessionStorage.setItem(STORAGE_KEY, hash);
    sessionStorage.setItem(STORAGE_NAME, group.name);
    return { type: "student", hash, meta: group };
  }

  return null;
}

export function getUnlockedHash() {
  return sessionStorage.getItem(STORAGE_KEY);
}

export function getUnlockedName() {
  return sessionStorage.getItem(STORAGE_NAME);
}

export function getTeacherHash() {
  return sessionStorage.getItem(STORAGE_TEACHER);
}

export function getTeacherName() {
  return sessionStorage.getItem(STORAGE_TEACHER_NAME);
}

export function isTeacher() {
  return !!sessionStorage.getItem(STORAGE_TEACHER);
}

export function lock() {
  sessionStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_NAME);
  sessionStorage.removeItem(STORAGE_TEACHER);
  sessionStorage.removeItem(STORAGE_TEACHER_NAME);
}
