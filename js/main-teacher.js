/*
 * Dashboard enseignant — accès global à toutes les classes.
 *
 * Vérifie la session prof, charge classes.json et teachers.json,
 * affiche les groupes "à charge" du prof + tous les groupes du collège.
 * Clic sur une carte → ouverture de la vue classe correspondante.
 */

import { loadClasses, loadTeachers } from "./data-loader.js";
import { getTeacherHash, getTeacherName, lock } from "./auth.js";
import { escapeHtml } from "./podium.js";

const HEX_RE = /^[a-f0-9]{64}$/i;
const collator = new Intl.Collator("fr", { sensitivity: "base" });

let allGroups = [];      // [{ hash, ...meta }]
let teacherGroups = [];  // sous-ensemble assuré par ce prof

async function init() {
  const hashFromUrl = window.location.hash.replace("#", "").trim();
  const hashFromSession = getTeacherHash();

  if (!hashFromUrl || !HEX_RE.test(hashFromUrl) || hashFromUrl !== hashFromSession) {
    window.location.replace("index.html");
    return;
  }

  try {
    const [classesIndex, teachersIndex] = await Promise.all([
      loadClasses(),
      loadTeachers(),
    ]);

    const teacher = teachersIndex.teachers[hashFromUrl];
    if (!teacher) {
      window.location.replace("index.html");
      return;
    }

    // Tous les groupes
    allGroups = Object.entries(classesIndex.groups).map(([hash, meta]) => ({
      hash,
      ...meta,
    }));

    // Groupes à charge du prof (intersection avec teacher.groups)
    const teacherGroupSet = new Set(teacher.groups || []);
    teacherGroups = allGroups.filter((g) => teacherGroupSet.has(g.name));

    renderHeader(teacher);
    renderGlobalStats();
    renderMyGroups();
    renderAllGroups();
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

// ─── Header ────────────────────────────────────────────────────
function renderHeader(teacher) {
  document.title = `${teacher.name} — Dashboard PIX LFT`;
  document.getElementById("teacher-name").textContent = `Bonjour ${teacher.name.split(" ").slice(1).join(" ")}`;
  const groupCount = teacherGroups.length;
  document.getElementById("teacher-meta").textContent =
    `Accès enseignant · ${groupCount} groupe${groupCount > 1 ? "s" : ""} à votre charge`;
}

function renderGlobalStats() {
  const totalStudents = allGroups.reduce((s, g) => s + g.studentCount, 0);
  const totalCertif = allGroups.reduce((s, g) => s + g.certifiableCount, 0);
  const avgPix = Math.round(
    allGroups.reduce((s, g) => s + g.averagePix * g.studentCount, 0) / Math.max(1, totalStudents)
  );

  document.getElementById("global-stats").innerHTML = `
    <div class="stat">
      <span class="stat__value">${allGroups.length}</span>
      <span class="stat__label">Groupes</span>
    </div>
    <div class="stat">
      <span class="stat__value">${totalStudents}</span>
      <span class="stat__label">Élèves</span>
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

// ─── Mes groupes (à charge) ────────────────────────────────────
function renderMyGroups() {
  const container = document.getElementById("my-groups-grid");
  const section = document.getElementById("my-groups-section");

  if (teacherGroups.length === 0) {
    section.style.display = "none";
    return;
  }

  // Tri par niveau puis nom
  const sorted = [...teacherGroups].sort((a, b) => {
    if (a.level !== b.level) return collator.compare(a.level, b.level);
    return collator.compare(a.name, b.name);
  });

  container.innerHTML = sorted.map(renderGroupCard).join("");
  bindCardClicks(container);
}

// ─── Tous les groupes ──────────────────────────────────────────
function renderAllGroups() {
  const level = document.getElementById("level-filter")?.value || "all";
  const sort = document.getElementById("sort-classes")?.value || "name";

  let filtered = allGroups.filter((g) => level === "all" || g.level === level);

  switch (sort) {
    case "students-desc": filtered.sort((a, b) => b.studentCount - a.studentCount); break;
    case "cert-desc":     filtered.sort((a, b) => b.certifiableCount - a.certifiableCount); break;
    case "avg-desc":      filtered.sort((a, b) => b.averagePix - a.averagePix); break;
    default:              filtered.sort((a, b) => collator.compare(a.name, b.name));
  }

  const container = document.getElementById("all-groups-grid");
  if (filtered.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">Aucun groupe ne correspond.</p>`;
    return;
  }
  container.innerHTML = filtered.map(renderGroupCard).join("");
  bindCardClicks(container);
}

function renderGroupCard(group) {
  const certifPct = group.studentCount > 0
    ? Math.round((group.certifiableCount / group.studentCount) * 100)
    : 0;

  const levelLabel = { "3e": "3ème", "4e": "4ème", "5e": "5ème", "6e": "6ème" }[group.level] || "";
  const isMine = teacherGroups.some((g) => g.hash === group.hash);

  return `
    <button type="button"
            class="info-card glass glass-bevel glass-hoverable group-card${isMine ? ' group-card--mine' : ''}"
            data-hash="${escapeHtml(group.hash)}"
            aria-label="Voir le détail de ${escapeHtml(group.name)}">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);">
        <div class="info-card__icon" aria-hidden="true" style="margin: 0; width: 44px; height: 44px; font-size: 18px;">
          ${escapeHtml(levelLabel)}
        </div>
        ${isMine ? '<span class="badge badge--success"><svg class="icon"><use href="#ph-check-circle"/></svg> À ma charge</span>' : ''}
      </div>
      <h3 class="info-card__title" style="margin-top: var(--space-2);">${escapeHtml(group.name)}</h3>
      <div style="display: flex; gap: var(--space-4); margin-top: var(--space-2);">
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--lft-blue); line-height: 1;">${group.studentCount}</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">élèves</div>
        </div>
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--success); line-height: 1;">${certifPct}%</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">certifiables</div>
        </div>
        <div>
          <div style="font-size: var(--text-2xl); font-weight: 800; color: var(--lft-magenta); line-height: 1;">${group.averagePix}</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;">moy. pix</div>
        </div>
      </div>
    </button>
  `;
}

function bindCardClicks(container) {
  container.querySelectorAll(".group-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      window.location.href = `classe.html#${btn.dataset.hash}`;
    });
  });
}

// ─── Filtres ───────────────────────────────────────────────────
function bindFilters() {
  document.getElementById("level-filter")?.addEventListener("change", renderAllGroups);
  document.getElementById("sort-classes")?.addEventListener("change", renderAllGroups);
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
