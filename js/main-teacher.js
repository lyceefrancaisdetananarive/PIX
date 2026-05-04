/*
 * Dashboard enseignant — vue par CLASSE ADMINISTRATIVE Pronote.
 *
 * Affiche les classes (5M1, 5M2, ..., TG6, etc.) avec stats agrégées
 * de tous les élèves de la classe (peu importe leur groupe Pix Orga).
 * Clic sur une classe → vue détail élèves de la classe.
 */

import { loadAdminClasses, loadTeachers } from "./data-loader.js";
import { getTeacherHash, lock } from "./auth.js";
import { escapeHtml } from "./podium.js";

const HEX_RE = /^[a-f0-9]{64}$/i;
const collator = new Intl.Collator("fr", { sensitivity: "base" });

let allClasses = [];      // classes admin avec leurs métadonnées
let teacherGroupSet = new Set();

async function init() {
  const hashFromUrl = window.location.hash.replace("#", "").trim();
  const hashFromSession = getTeacherHash();

  if (!hashFromUrl || !HEX_RE.test(hashFromUrl) || hashFromUrl !== hashFromSession) {
    window.location.replace("index.html");
    return;
  }

  try {
    const [adminClasses, teachersIndex] = await Promise.all([
      loadAdminClasses(),
      loadTeachers(),
    ]);

    const teacher = teachersIndex.teachers[hashFromUrl];
    if (!teacher) {
      window.location.replace("index.html");
      return;
    }

    allClasses = Object.entries(adminClasses.classes).map(([hash, meta]) => ({
      hash,
      ...meta,
    }));

    teacherGroupSet = new Set(teacher.groups || []);

    renderHeader(teacher);
    renderGlobalStats();
    renderMyClasses();
    renderAllClasses();
    bindFilters();
    bindLogout();
    initReveal();
  } catch (err) {
    console.error(err);
    document.getElementById("all-groups-grid").innerHTML = `
      <p style="text-align: center; padding: var(--space-7); color: var(--danger);">
        Erreur de chargement. <a href="index.html">Retour à l'accueil</a>
      </p>
    `;
  }
}

// ─── Une classe est-elle "à la charge" du prof ?
//   Oui si au moins un de ses groupes Pix Orga est dans teacher.groups
function isMine(cls) {
  return (cls.relatedGroups || []).some((g) => teacherGroupSet.has(g));
}

// ─── Header ────────────────────────────────────────────────────
function renderHeader(teacher) {
  document.title = `${teacher.name} — Dashboard PIX LFT`;
  const firstName = teacher.name.split(" ").slice(1).join(" ") || teacher.name;
  document.getElementById("teacher-name").textContent = `Bonjour ${firstName}`;
  const myCount = allClasses.filter(isMine).length;
  document.getElementById("teacher-meta").textContent =
    `Accès enseignant · ${myCount} classe${myCount > 1 ? "s" : ""} à votre charge sur ${allClasses.length}`;
}

function renderGlobalStats() {
  const totalStudents = allClasses.reduce((s, c) => s + c.studentCount, 0);
  const totalScored = allClasses.reduce((s, c) => s + c.scoredCount, 0);
  const totalCertif = allClasses.reduce((s, c) => s + c.certifiableCount, 0);
  const scored = allClasses.reduce(
    (acc, c) => ({
      sum: acc.sum + c.averagePix * c.scoredCount,
      n: acc.n + c.scoredCount,
    }),
    { sum: 0, n: 0 }
  );
  const avgPix = scored.n > 0 ? Math.round(scored.sum / scored.n) : 0;

  document.getElementById("global-stats").innerHTML = `
    <div class="stat">
      <span class="stat__value">${allClasses.length}</span>
      <span class="stat__label">Classes</span>
    </div>
    <div class="stat">
      <span class="stat__value">${totalStudents}</span>
      <span class="stat__label">Élèves</span>
    </div>
    <div class="stat">
      <span class="stat__value">${totalScored}</span>
      <span class="stat__label">Avec score</span>
    </div>
    <div class="stat">
      <span class="stat__value">${totalCertif}</span>
      <span class="stat__label">Certifiables</span>
    </div>
    <div class="stat">
      <span class="stat__value">${avgPix}</span>
      <span class="stat__label">Moy. pix</span>
    </div>
  `;
}

// ─── Mes classes ──────────────────────────────────────────────
function renderMyClasses() {
  const container = document.getElementById("my-groups-grid");
  const section = document.getElementById("my-groups-section");

  const mine = allClasses.filter(isMine);
  if (mine.length === 0) {
    section.style.display = "none";
    return;
  }

  const sorted = [...mine].sort((a, b) => {
    if (a.level !== b.level) return collator.compare(a.level, b.level);
    return collator.compare(a.name, b.name);
  });

  container.innerHTML = sorted.map(renderClassCard).join("");
  bindCardClicks(container);
}

// ─── Toutes les classes ───────────────────────────────────────
function renderAllClasses() {
  const level = document.getElementById("level-filter")?.value || "all";
  const sort = document.getElementById("sort-classes")?.value || "name";

  let filtered = allClasses.filter((c) => level === "all" || c.level === level);

  switch (sort) {
    case "students-desc": filtered.sort((a, b) => b.studentCount - a.studentCount); break;
    case "cert-desc":     filtered.sort((a, b) => b.certifiableCount - a.certifiableCount); break;
    case "avg-desc":      filtered.sort((a, b) => b.averagePix - a.averagePix); break;
    default:              filtered.sort((a, b) => collator.compare(a.name, b.name));
  }

  const container = document.getElementById("all-groups-grid");
  if (filtered.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">Aucune classe ne correspond.</p>`;
    return;
  }
  container.innerHTML = filtered.map(renderClassCard).join("");
  bindCardClicks(container);
}

function renderClassCard(cls) {
  const certifPct = cls.scoredCount > 0
    ? Math.round((cls.certifiableCount / cls.studentCount) * 100)
    : 0;

  const levelLabel = {
    "6e": "6e", "5e": "5e", "4e": "4e", "3e": "3e",
    "2nde": "2nde", "1e": "1ère", "tale": "Term"
  }[cls.level] || "";

  const mine = isMine(cls);

  return `
    <button type="button"
            class="info-card glass glass-bevel glass-hoverable group-card${mine ? ' group-card--mine' : ''}"
            data-hash="${escapeHtml(cls.hash)}"
            aria-label="Voir le détail de la classe ${escapeHtml(cls.name)}">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);">
        <div class="info-card__icon" aria-hidden="true" style="margin: 0; width: 44px; height: 44px; font-size: 14px; font-weight: 800;">
          ${escapeHtml(levelLabel)}
        </div>
        ${mine ? '<span class="badge badge--success"><svg class="icon"><use href="#ph-check-circle"/></svg> À ma charge</span>' : ''}
      </div>
      <h3 class="info-card__title" style="margin-top: var(--space-2);">${escapeHtml(cls.name)}</h3>
      <div style="display: flex; gap: var(--space-4); margin-top: var(--space-2);">
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--lft-blue); line-height: 1;">${cls.studentCount}</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">élèves</div>
        </div>
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--success); line-height: 1;">${certifPct}%</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">certifiables</div>
        </div>
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--lft-magenta); line-height: 1;">${cls.averagePix}</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">moy. pix</div>
        </div>
      </div>
      ${cls.relatedGroups && cls.relatedGroups.length > 0 ? `
      <div style="margin-top: var(--space-3); font-size: 11px; color: var(--text-muted); line-height: 1.4;">
        Groupes Pix : ${cls.relatedGroups.map(g => `<span style="display:inline-block; padding: 1px 6px; margin: 2px 2px 0 0; background: rgba(0,59,115,0.06); border-radius: 6px;">${escapeHtml(g)}</span>`).join("")}
      </div>
      ` : ''}
    </button>
  `;
}

function bindCardClicks(container) {
  container.querySelectorAll(".group-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      // Préfixe "adm-" pour distinguer classe admin / groupe Pix Orga
      window.location.href = `classe.html#adm-${btn.dataset.hash}`;
    });
  });
}

// ─── Filtres ───────────────────────────────────────────────────
function bindFilters() {
  document.getElementById("level-filter")?.addEventListener("change", renderAllClasses);
  document.getElementById("sort-classes")?.addEventListener("change", renderAllClasses);
}

// ─── Logout ────────────────────────────────────────────────────
function bindLogout() {
  document.getElementById("logout-btn")?.addEventListener("click", () => {
    lock();
    window.location.href = "index.html";
  });
}

// ─── Reveal ─────────────────────────────────────────────────────
function initReveal() {
  document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-visible"));
}

init();
