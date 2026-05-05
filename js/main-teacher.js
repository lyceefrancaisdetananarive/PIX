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
    bindSync(teacher);   // bouton "Synchroniser Pix Orga"
    initReveal();

    // Compteur dynamique dans le titre de section
    const countEl = document.getElementById("all-classes-count");
    if (countEl) countEl.textContent = allClasses.length;
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

// ─── Mes classes (regroupées par niveau, comme la section globale) ──
function renderMyClasses() {
  const container = document.getElementById("my-groups-grid");
  const section = document.getElementById("my-groups-section");
  const countEl = document.getElementById("my-classes-count");

  const mine = allClasses.filter(isMine);
  if (countEl) countEl.textContent = mine.length;

  if (mine.length === 0) {
    section.style.display = "none";
    return;
  }

  container.innerHTML = renderGroupedByLevel(mine);
  bindCardClicks(container);
}

// ─── Helper commun : génère le HTML regroupé par niveau ───────
function renderGroupedByLevel(classes) {
  const byLevel = {};
  for (const cls of classes) {
    (byLevel[cls.level] = byLevel[cls.level] || []).push(cls);
  }
  Object.values(byLevel).forEach((arr) =>
    arr.sort((a, b) => collator.compare(a.name, b.name))
  );

  return LEVEL_ORDER
    .filter((lvl) => byLevel[lvl] && byLevel[lvl].length > 0)
    .map((lvl) => {
      const arr = byLevel[lvl];
      return `
        <section class="level-section">
          <header class="level-section__head">
            <h3 class="level-section__title">${LEVEL_FULL_LABELS[lvl]}</h3>
            <span class="level-section__cycle">${LEVEL_CYCLE_LABELS[lvl]}</span>
            <span class="level-section__count">${arr.length} classe${arr.length > 1 ? "s" : ""}</span>
          </header>
          <div class="level-section__grid">
            ${arr.map(renderClassCard).join("")}
          </div>
        </section>
      `;
    })
    .join("");
}

// ─── Toutes les classes ───────────────────────────────────────
const LEVEL_ORDER = ["6e", "5e", "4e", "3e", "2nde", "1e", "tale"];
const LEVEL_FULL_LABELS = {
  "6e":   "6ème",
  "5e":   "5ème",
  "4e":   "4ème",
  "3e":   "3ème",
  "2nde": "2nde",
  "1e":   "1ère",
  "tale": "Terminale",
};
const LEVEL_CYCLE_LABELS = {
  "6e":   "Cycle 3",
  "5e":   "Cycle 4",
  "4e":   "Cycle 4",
  "3e":   "Cycle 4",
  "2nde": "Lycée",
  "1e":   "Lycée",
  "tale": "Lycée",
};

function renderAllClasses() {
  const level = document.getElementById("level-filter")?.value || "all";
  const sort = document.getElementById("sort-classes")?.value || "name";

  let filtered = allClasses.filter((c) => level === "all" || c.level === level);
  const container = document.getElementById("all-groups-grid");

  if (filtered.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">Aucune classe ne correspond.</p>`;
    return;
  }

  // Si tri par nom : on regroupe par niveau dans l'ordre éducatif
  if (sort === "name") {
    container.innerHTML = renderGroupedByLevel(filtered);
  } else {
    // Tris alternatifs : flat sans regroupement
    switch (sort) {
      case "students-desc": filtered.sort((a, b) => b.studentCount - a.studentCount); break;
      case "cert-desc":     filtered.sort((a, b) => b.certifiableCount - a.certifiableCount); break;
      case "avg-desc":      filtered.sort((a, b) => b.averagePix - a.averagePix); break;
    }
    container.innerHTML = `<div class="cards-grid">${filtered.map(renderClassCard).join("")}</div>`;
  }
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
      ${cls.historicalGroups && cls.historicalGroups.length > 0 ? `
      <div style="margin-top: var(--space-2); font-size: 10px; color: var(--text-muted); line-height: 1.4; opacity: 0.7;" title="Groupes Pix d'autres niveaux où des élèves de cette classe ont participé (ex. années précédentes)">
        Hist. : ${cls.historicalGroups.map(g => `<span style="display:inline-block; padding: 1px 6px; margin: 2px 2px 0 0; background: rgba(107,114,128,0.08); border-radius: 6px; font-style: italic;">${escapeHtml(g)}</span>`).join("")}
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

// ─── Bouton de synchronisation Pix Orga ────────────────────────
//   Visible uniquement pour l'admin (BUGATTI / RAFALIARISON Max).
//   Contacte l'agent local sur http://127.0.0.1:7777 et streame
//   la progression via Server-Sent Events.
const AGENT_URL = "http://127.0.0.1:7777";
const ADMIN_TEACHER_SLUG = "rafaliarison_max";  // = slug de Max dans teachers.json

async function checkAgentAlive() {
  try {
    const r = await fetch(`${AGENT_URL}/health`, {
      mode: "cors",
      signal: AbortSignal.timeout(2000),
    });
    return r.ok;
  } catch {
    return false;
  }
}

async function bindSync(teacher) {
  const btn = document.getElementById("sync-btn");
  if (!btn) return;

  // Le bouton n'apparaît que pour l'admin
  if (teacher?.slug !== ADMIN_TEACHER_SLUG) {
    btn.remove();
    return;
  }
  btn.hidden = false;

  // Sonde initiale (informationnelle — l'agent peut être lancé après le clic)
  if (!(await checkAgentAlive())) {
    btn.title = "Agent local non lancé — démarre start.command";
    btn.dataset.state = "agent-off";
  } else {
    btn.dataset.state = "agent-on";
  }

  // À chaque clic on re-vérifie l'agent (cas : démarrage tardif, redémarrage,
  // changement Private Network Access, etc.). Ne dépend plus d'une closure
  // capturée au chargement.
  btn.addEventListener("click", async () => {
    const alive = await checkAgentAlive();
    btn.dataset.state = alive ? "agent-on" : "agent-off";
    openSyncModal(alive);
  });
}

function openSyncModal(agentAlive) {
  const backdrop = document.getElementById("sync-modal");
  const status = document.getElementById("sync-status");
  const bar = document.getElementById("sync-bar");
  const pct = document.getElementById("sync-percent");
  const log = document.getElementById("sync-log");
  const closeBtn = document.getElementById("sync-close");

  // Reset visuel
  bar.style.width = "0%";
  pct.textContent = "0 %";
  log.innerHTML = "";
  status.textContent = "Connexion à l'agent local…";

  const close = () => {
    backdrop.classList.remove("is-open");
    backdrop.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };
  closeBtn.onclick = close;
  backdrop.onclick = (e) => { if (e.target === backdrop) close(); };

  backdrop.classList.add("is-open");
  backdrop.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";

  if (!agentAlive) {
    status.textContent = "⚠ L'agent local n'est pas lancé.";
    log.innerHTML = `
      <div class="sync-log__line sync-log__line--warn">
        Pour démarrer l'agent :
        <ol style="margin: 8px 0 0 16px; padding: 0;">
          <li>Ouvre le dossier <code>site/scripts/agent/</code></li>
          <li>Double-clique sur <code>start.command</code></li>
          <li>Garde la fenêtre Terminal ouverte</li>
          <li>Reviens ici et clique à nouveau sur « Synchroniser Pix Orga »</li>
        </ol>
      </div>`;
    return;
  }

  startSync(status, bar, pct, log);
}

async function startSync(statusEl, bar, pct, log) {
  try {
    // Démarre le job
    statusEl.textContent = "Synchronisation en cours…";
    const res = await fetch(`${AGENT_URL}/sync`, { method: "POST", mode: "cors" });
    const { job_id } = await res.json();

    // Stream SSE
    const ev = new EventSource(`${AGENT_URL}/sync/${job_id}/events`);
    ev.onmessage = (m) => {
      const e = JSON.parse(m.data);
      if (e.stage === "_end_") {
        ev.close();
        return;
      }
      if (typeof e.progress === "number" && e.progress > 0) {
        const p = Math.round(e.progress * 100);
        bar.style.width = `${p}%`;
        pct.textContent = `${p} %`;
      }
      const cls = e.stage === "error" ? "sync-log__line--error"
                : e.stage === "done"  ? "sync-log__line--done"
                : "";
      const line = document.createElement("div");
      line.className = `sync-log__line ${cls}`;
      line.innerHTML = `<span class="sync-log__time">${e.time}</span> <span class="sync-log__stage">[${e.stage}]</span> ${escapeHtmlSafe(e.message)}`;
      log.appendChild(line);
      log.scrollTop = log.scrollHeight;

      if (e.stage === "done") {
        statusEl.textContent = "✓ Synchronisation terminée";
        bar.style.background = "linear-gradient(90deg, #10b981, #059669)";
      } else if (e.stage === "error") {
        statusEl.textContent = "✗ Erreur — voir les logs";
        bar.style.background = "linear-gradient(90deg, #ef4444, #b91c1c)";
      }
    };
    ev.onerror = () => {
      ev.close();
      statusEl.textContent = "Connexion à l'agent perdue.";
    };
  } catch (err) {
    statusEl.textContent = `Erreur : ${err.message}`;
  }
}

function escapeHtmlSafe(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ─── Reveal ─────────────────────────────────────────────────────
function initReveal() {
  document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-visible"));
}

init();
