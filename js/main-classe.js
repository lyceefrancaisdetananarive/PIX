/*
 * Logique de la page classe :
 *   - lit le hash du groupe depuis l'URL (#xxx)
 *   - vérifie qu'il correspond au hash débloqué en sessionStorage
 *   - charge data/groups/<hash>.json
 *   - rend le tableau, gère filtres/tri/recherche
 *   - ouvre la modal détail élève au clic
 */

import { loadGroup, loadClasses, levelFor, PIX_LEVELS } from "./data-loader.js";
import { getUnlockedHash, isTeacher, getTeacherName } from "./auth.js";
import { applyFilters } from "./filters.js";
import { renderGauge } from "./pix-gauge.js";
import { escapeHtml } from "./podium.js";

const HEX_RE = /^[a-f0-9]{64}$/i;

let allStudents = [];
let groupName = "";

async function init() {
  const hashFromUrl = window.location.hash.replace("#", "").trim();
  const hashFromSession = getUnlockedHash();
  const teacherMode = isTeacher();

  // Accès autorisé si :
  //  - on est en mode prof (vue toutes classes), OU
  //  - le hash URL correspond au hash débloqué en session (mode élève normal)
  const allowed =
    HEX_RE.test(hashFromUrl) &&
    (teacherMode || hashFromUrl === hashFromSession);

  if (!hashFromUrl || !allowed) {
    redirectHome();
    return;
  }

  try {
    const [classesIndex, groupData] = await Promise.all([
      loadClasses(),
      loadGroup(hashFromUrl),
    ]);

    const meta = classesIndex.groups[hashFromUrl];
    if (!meta) {
      redirectHome();
      return;
    }

    groupName = meta.name;
    allStudents = groupData.students || [];

    renderBanner(meta, teacherMode);
    renderTable();
    bindToolbar();
    bindModal();
  } catch (err) {
    console.error(err);
    document.getElementById("students-container").innerHTML = `
      <p style="text-align: center; padding: var(--space-7); color: var(--danger);">
        Erreur de chargement. <a href="index.html">Retour à l'accueil</a>
      </p>
    `;
  }
}

function redirectHome() {
  window.location.replace("index.html");
}

// ─── Bandeau classe + stats ────────────────────────────────────
function renderBanner(meta, teacherMode) {
  document.title = `${meta.name} — PIX LFT`;
  document.getElementById("classe-name").textContent = meta.name;

  const levelLabels = {
    "6e": "Niveau 6ème · Cycle 3",
    "5e": "Niveau 5ème · Cycle 4",
    "4e": "Niveau 4ème · Cycle 4",
    "3e": "Niveau 3ème · Cycle 4",
    "2nde": "Classe de 2nde · Lycée",
    "1e": "Classe de 1ère · Lycée",
    "tale": "Classe de Terminale · Lycée",
  };
  const levelText = levelLabels[meta.level] || "Cycle 4";
  document.getElementById("classe-level").textContent = levelText;

  // Bouton retour : vers le dashboard prof ou vers l'accueil
  const backBtn = document.querySelector(".classe-banner__back");
  if (backBtn && teacherMode) {
    backBtn.setAttribute("href", `teacher.html#${sessionStorage.getItem("pix-lft.teacher-hash")}`);
    backBtn.setAttribute("aria-label", "Retour au dashboard enseignant");
    backBtn.title = "← Retour au dashboard enseignant";
  }

  const certifPct = meta.studentCount > 0
    ? Math.round((meta.certifiableCount / meta.studentCount) * 100)
    : 0;

  document.getElementById("classe-stats").innerHTML = `
    <div class="stat">
      <span class="stat__value">${meta.studentCount}</span>
      <span class="stat__label">Élèves</span>
    </div>
    <div class="stat">
      <span class="stat__value">${meta.certifiableCount}</span>
      <span class="stat__label">Certifiables</span>
    </div>
    <div class="stat">
      <span class="stat__value">${certifPct}%</span>
      <span class="stat__label">Taux certif.</span>
    </div>
    <div class="stat">
      <span class="stat__value">${meta.averagePix}</span>
      <span class="stat__label">Moy. pix</span>
    </div>
  `;
}

// ─── Tableau élèves ────────────────────────────────────────────
function renderTable() {
  const search = document.getElementById("search-input")?.value || "";
  const sort = document.getElementById("sort-select")?.value || "pix-desc";
  const cert = document.getElementById("filter-cert")?.value || "all";

  const filtered = applyFilters(allStudents, { search, sort, cert });
  const container = document.getElementById("students-container");

  if (filtered.length === 0) {
    container.innerHTML = `
      <p style="text-align: center; padding: var(--space-7); color: var(--text-secondary);">
        Aucun élève ne correspond à ces critères.
      </p>
    `;
    container.removeAttribute("aria-busy");
    return;
  }

  const rows = filtered
    .map((s, i) => {
      const status = s.status || (s.pix > 0 ? "renseigne" : "partiel");
      const isMissing = status === "non_renseigne";
      const isPartial = status === "partiel";
      const cls = isMissing ? "is-empty" : (isPartial ? "is-partial" : "");

      let badge;
      if (isMissing) {
        badge = '<span class="badge badge--muted">Non renseigné</span>';
      } else if (isPartial) {
        badge = '<span class="badge badge--warning">Parcours en cours</span>';
      } else if (s.certifiable) {
        badge = '<span class="badge badge--success"><svg class="icon"><use href="#ph-check-circle"/></svg> Certifiable</span>';
      } else {
        badge = '<span class="badge badge--warning">En cours</span>';
      }

      const lvl = (status === "renseigne") ? levelFor(s.pix) : null;
      const lvlBadge = lvl && lvl.slug !== "non-certifie"
        ? `<span class="pix-level-pill pix-level-pill--${lvl.slug}">${escapeHtml(lvl.short)}</span>`
        : "";
      const pix = (status === "renseigne")
        ? `<span class="pix-pill"><span>${s.pix}</span><span class="pix-pill__unit">pix</span></span>${lvlBadge}`
        : '<span class="pix-pill pix-pill--muted">—</span>';

      const interactive = !isMissing;

      return `
        <tr class="${cls}" data-id="${escapeHtml(s.id)}" tabindex="${interactive ? 0 : -1}"
            role="${interactive ? "button" : ""}" aria-label="${interactive ? "Voir le détail de " + escapeHtml(s.name) : "Élève non renseigné"}">
          <td><span class="student-rank">${i + 1}</span></td>
          <td><span class="student-name">${escapeHtml(s.name)}</span></td>
          <td>${escapeHtml(s.classe || "—")}</td>
          <td>${pix}</td>
          <td>${badge}</td>
          <td>${s.parcours?.length || 0}</td>
        </tr>
      `;
    })
    .join("");

  container.innerHTML = `
    <table class="students-table" role="table" aria-label="Élèves de ${escapeHtml(groupName)}">
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">Élève</th>
          <th scope="col">Classe</th>
          <th scope="col">Score</th>
          <th scope="col">Statut</th>
          <th scope="col">Parcours</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
  container.removeAttribute("aria-busy");

  // Click + clavier sur les lignes non "non renseignées"
  container.querySelectorAll('tr[data-id]:not(.is-empty)').forEach((tr) => {
    tr.addEventListener("click", () => openModal(tr.dataset.id));
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openModal(tr.dataset.id);
      }
    });
  });
}

// ─── Toolbar (filtres/tri/recherche) ───────────────────────────
function bindToolbar() {
  const search = document.getElementById("search-input");
  const sort = document.getElementById("sort-select");
  const cert = document.getElementById("filter-cert");

  let debounce;
  search?.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(renderTable, 120);
  });
  sort?.addEventListener("change", renderTable);
  cert?.addEventListener("change", renderTable);
}

// ─── Modal détail élève ────────────────────────────────────────
function bindModal() {
  const backdrop = document.getElementById("student-modal");
  const closeBtn = document.getElementById("modal-close");

  const close = () => {
    backdrop.classList.remove("is-open");
    backdrop.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  closeBtn?.addEventListener("click", close);
  backdrop?.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && backdrop.classList.contains("is-open")) close();
  });
}

function openModal(id) {
  const student = allStudents.find((s) => s.id === id);
  if (!student) return;

  const backdrop = document.getElementById("student-modal");
  document.getElementById("modal-name").textContent = student.name;

  const meta = [student.classe, groupName].filter(Boolean).join(" · ");
  const lastUpdate = student.lastUpdate
    ? `Dernière mise à jour : ${formatDate(student.lastUpdate)}`
    : "";
  document.getElementById("modal-meta").innerHTML =
    `${escapeHtml(meta)}${lastUpdate ? ` · ${escapeHtml(lastUpdate)}` : ""}`;

  // Jauge
  const valueEl = document.getElementById("modal-gauge-value");
  valueEl.textContent = "0";
  renderGauge({
    valueEl,
    levelEl: document.getElementById("modal-gauge-level"),
    fillEl: document.getElementById("modal-gauge-fill"),
    pix: student.pix,
  });

  // Badge certifiable
  const certBadge = document.getElementById("modal-cert-badge");
  if (student.certifiable) {
    certBadge.innerHTML = `
      <span class="badge badge--success"><svg class="icon"><use href="#ph-check-circle"/></svg> Certifiable — ${student.competencesCertifiables} compétences niveau 1+</span>
    `;
  } else if (student.pix > 0) {
    certBadge.innerHTML = `
      <span class="badge badge--warning"><svg class="icon"><use href="#ph-warning"/></svg> En cours — ${student.competencesCertifiables} compétences validées sur 5 minimum</span>
    `;
  } else {
    certBadge.innerHTML = `<span class="badge badge--muted">Aucune Collecte effectuée</span>`;
  }

  // Domaines
  const domains = document.getElementById("modal-domains");
  if (student.domains && Object.keys(student.domains).length > 0) {
    domains.innerHTML = Object.values(student.domains)
      .map((d) => `
        <article class="domain-card">
          <div class="domain-card__label">${escapeHtml(d.label)}</div>
          <div class="domain-card__level">N${d.level}</div>
          <div class="domain-card__pix">${d.pix} pix</div>
        </article>
      `)
      .join("");
  } else {
    domains.innerHTML = `<p style="color: var(--text-muted);">Pas de données par domaine.</p>`;
  }

  // Parcours
  const parcours = document.getElementById("modal-parcours");
  if (student.parcours && student.parcours.length > 0) {
    parcours.innerHTML = student.parcours
      .map((p) => {
        const date = p.date ? formatDate(p.date) : "—";
        const pct = Math.round((p.maitrise || 0) * 100);
        const palier = p.palier ? `Palier ${p.palier}/3` : "";
        return `
          <div class="parcours-item">
            <div>
              <div class="parcours-item__name">${escapeHtml(p.name)}</div>
              <div class="parcours-item__date">${escapeHtml(date)} ${palier ? `· ${palier}` : ""}</div>
            </div>
            <span class="parcours-item__progress">${pct}%</span>
          </div>
        `;
      })
      .join("");
  } else {
    parcours.innerHTML = `<p style="color: var(--text-muted);">Aucun parcours réalisé.</p>`;
  }

  // Codes rattrapage : récupère depuis les parcours uniques par nom
  const codes = document.getElementById("modal-codes");
  const uniqueCodes = uniqueParcoursCodes(student.parcours || []);
  if (uniqueCodes.length > 0) {
    codes.innerHTML = uniqueCodes
      .map((c, i) => `
        <div class="code-rattrapage">
          <span class="code-rattrapage__label">${escapeHtml(c.name)}</span>
          <span class="code-rattrapage__code">${escapeHtml(c.code)}</span>
          <button type="button" class="code-rattrapage__copy" data-code="${escapeHtml(c.code)}" data-idx="${i}">
            <svg class="icon"><use href="#ph-copy"/></svg> Copier
          </button>
        </div>
      `)
      .join("");

    codes.querySelectorAll(".code-rattrapage__copy").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.code);
          btn.innerHTML = '<svg class="icon"><use href="#ph-check-circle"/></svg> Copié';
          btn.classList.add("is-copied");
          setTimeout(() => {
            btn.innerHTML = '<svg class="icon"><use href="#ph-copy"/></svg> Copier';
            btn.classList.remove("is-copied");
          }, 1600);
        } catch {
          /* ignore */
        }
      });
    });
  } else {
    codes.innerHTML = `<p style="color: var(--text-muted);">Aucun code de rattrapage disponible.</p>`;
  }

  backdrop.classList.add("is-open");
  backdrop.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  document.getElementById("modal-close").focus();
}

// ─── Helpers ───────────────────────────────────────────────────
function uniqueParcoursCodes(parcours) {
  const seen = new Map();
  for (const p of parcours) {
    if (p.code && !seen.has(p.code)) seen.set(p.code, { name: p.name, code: p.code });
  }
  return [...seen.values()];
}

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
  } catch {
    return iso;
  }
}

init();
