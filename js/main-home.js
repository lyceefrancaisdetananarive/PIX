/*
 * Logique de la page d'accueil :
 *   - chargement du podium Top 3
 *   - jauge interactive (démo)
 *   - reveal au scroll
 *   - validation du code classe
 */

import { loadPublic, loadClasses, loadTeachers, levelFor } from "./data-loader.js";
import { tryUnlock } from "./auth.js";
import { renderPodium, renderPodiumMini } from "./podium.js";
import { renderGauge } from "./pix-gauge.js";

// ─── Chargement public (3 mini-podiums simultanés + stats) ─────
async function initPodium() {
  const grid = document.getElementById("podiums-grid");
  const statsEl = document.getElementById("global-stats");

  try {
    const data = await loadPublic();

    // Render simultané des 3 podiums
    const cycles = [
      { id: "cycle3", el: document.getElementById("podium-cycle3"), label: "Cycle 3" },
      { id: "cycle4", el: document.getElementById("podium-cycle4"), label: "Cycle 4" },
      { id: "lycee",  el: document.getElementById("podium-lycee"),  label: "Lycée" },
    ];

    cycles.forEach(({ id, el }) => {
      const entry = data.podiums?.[id];
      const podium = entry?.podium || [];
      if (podium.length === 0) {
        el.innerHTML = `
          <div class="podium-mini-empty">
            <svg class="icon icon--xl" aria-hidden="true" style="color: var(--text-muted); opacity: 0.6;"><use href="#ph-info"/></svg>
            <p>Aucun score<br>à afficher</p>
          </div>
        `;
      } else {
        renderPodiumMini(el, podium);
      }
    });

    grid.removeAttribute("aria-busy");

    if (statsEl && data.stats) {
      const renseignesPct = data.stats.totalStudents > 0
        ? Math.round((data.stats.totalScored / data.stats.totalStudents) * 100)
        : 0;
      statsEl.innerHTML = `
        <strong>${data.stats.totalStudents}</strong> élèves au total ·
        <strong>${data.stats.totalScored}</strong> avec score Pix (${renseignesPct}%) ·
        <strong>${data.stats.totalCertifiable}</strong> certifiables ·
        <strong>${data.stats.totalGroups}</strong> groupes répartis sur 3 cycles
      `;
    }
  } catch (err) {
    console.error(err);
    grid.innerHTML = `<p style="text-align:center; padding: var(--space-7); color: var(--danger);">Erreur de chargement des données.</p>`;
    grid.removeAttribute("aria-busy");
  }
}

// ─── Explorateur de niveaux Pix (slider + plante + description) ──
const LEVEL_DESCRIPTIONS = {
  "non-certifie":  "Score non certifié. Un score inférieur à 64 pix ne donne aucun niveau Pix officiel. Continuez à pratiquer pour atteindre Novice 1.",
  "novice-1":      "Pratiques numériques simples avec besoin d'aide. Vous savez vous repérer dans les interfaces que vous avez déjà utilisées (tablette, téléphone, ordinateur).",
  "novice-2":      "Pratiques numériques simples, avec aide quand la situation se complique. Recherches sur le Web, e-mails, mots de passe sécurisés.",
  "independant-1": "Autonomie sur situations courantes. Recherche approfondie, activités collaboratives, fonctionnalités courantes des logiciels usuels.",
  "independant-2": "À l'aise dans toutes les situations courantes. Vérification de la fiabilité des informations, création multi-formats, sécurité, vie privée.",
  "avance-1":      "Pratiques avancées, vous pouvez aider d'autres personnes. Outils spécialisés, analyse de données, paramétrage d'environnements.",
  "avance-2":      "Pratiques approfondies, créatives et sécurisées. Vous pouvez accompagner la montée en compétences d'autres personnes (programmation, automatisation).",
  "expert-1":      "Pratiques optimisées face à des situations complexes et nouvelles. Analyse de besoins, évaluation de solutions, esprit critique sur les enjeux.",
  "expert-2":      "Capacité à documenter et partager vos solutions à des problèmes nouveaux et spécifiques.",
};

function initDemoGauge() {
  const slider = document.getElementById("demo-gauge-slider");
  const valueEl = document.getElementById("demo-gauge-value");
  const levelEl = document.getElementById("demo-gauge-level");
  const fillEl = document.getElementById("demo-gauge-fill");
  const plantEl = document.getElementById("demo-plant");
  const descEl = document.getElementById("demo-gauge-desc");
  if (!slider) return;

  const update = (pix) => {
    const lvl = levelFor(pix);
    valueEl.textContent = pix;
    levelEl.textContent = lvl.label;
    if (fillEl) fillEl.style.width = `${(pix / 1024) * 100}%`;
    if (plantEl) {
      const newSrc = `assets/levels/${lvl.image}`;
      if (!plantEl.src.endsWith(lvl.image)) {
        plantEl.style.transform = "scale(0.92)";
        plantEl.style.opacity = "0.6";
        setTimeout(() => {
          plantEl.src = newSrc;
          plantEl.style.transform = "scale(1)";
          plantEl.style.opacity = "1";
        }, 160);
      }
    }
    if (descEl) descEl.textContent = LEVEL_DESCRIPTIONS[lvl.slug] || "";

    // Surligne la carte niveau correspondante
    document.querySelectorAll(".level-card").forEach((c) => {
      const min = parseInt(c.dataset.min, 10);
      const max = parseInt(c.dataset.max, 10);
      c.classList.toggle("is-active", pix >= min && pix <= max);
    });
  };

  slider.addEventListener("input", (e) => update(parseInt(e.target.value, 10)));

  // Permet aussi de cliquer sur une carte de niveau pour positionner le slider
  document.querySelectorAll(".level-card").forEach((card) => {
    card.style.cursor = "pointer";
    card.addEventListener("click", () => {
      const target = parseInt(card.dataset.min, 10) + 30;
      slider.value = target;
      update(target);
    });
  });

  update(parseInt(slider.value, 10));
}

// ─── Reveal au scroll ──────────────────────────────────────────
function initReveal() {
  const els = document.querySelectorAll(".reveal");

  // Filet de sécurité : tout visible après 1.5s même si l'observer ne tire pas
  setTimeout(() => els.forEach((el) => el.classList.add("is-visible")), 1500);

  if (!("IntersectionObserver" in window)) {
    els.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.05, rootMargin: "0px 0px 80px 0px" }
  );

  els.forEach((el) => {
    // Marque immédiatement les éléments déjà dans le viewport
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      el.classList.add("is-visible");
    } else {
      obs.observe(el);
    }
  });
}

// ─── Formulaire code classe ────────────────────────────────────
async function initCodeForm() {
  const form = document.getElementById("code-form");
  const input = document.getElementById("code-input");
  const error = document.getElementById("code-error");
  if (!form) return;

  let classesIndex = null;
  let teachersIndex = null;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.classList.remove("is-visible");

    const code = input.value.trim();
    if (!code) {
      input.focus();
      return;
    }

    try {
      if (!classesIndex) classesIndex = await loadClasses();
      if (!teachersIndex) teachersIndex = await loadTeachers().catch(() => ({ teachers: {} }));

      const result = await tryUnlock(code, classesIndex, teachersIndex);
      if (result) {
        // Animation de succès
        input.style.borderColor = "var(--success)";
        input.style.background = "rgba(24, 117, 60, 0.06)";
        setTimeout(() => {
          if (result.type === "teacher") {
            window.location.href = `teacher.html#${result.hash}`;
          } else {
            window.location.href = `classe.html#${result.hash}`;
          }
        }, 320);
      } else {
        showError("Code inconnu. Vérifiez auprès de votre professeur.");
        input.select();
      }
    } catch (err) {
      console.error(err);
      showError("Erreur de chargement. Réessayez dans un instant.");
    }

    function showError(msg) {
      error.textContent = msg;
      error.classList.add("is-visible");
    }
  });

  // Reset visuel à la frappe
  input.addEventListener("input", () => {
    input.style.borderColor = "";
    input.style.background = "";
    error.classList.remove("is-visible");
  });
}

// ─── Vidéos : click → ouvre YouTube dans un nouvel onglet ────────
// On évite l'iframe embed parce que YouTube affiche fréquemment le challenge
// « Connectez-vous pour confirmer que vous n'êtes pas un robot » dans les
// embeds quand l'utilisateur n'a pas de session YouTube active. Ouvrir
// directement la vidéo sur youtube.com utilise la session du navigateur
// et contourne le challenge.
function initVideoEmbeds() {
  document.querySelectorAll(".video-card--embed").forEach((card) => {
    const id = card.dataset.videoId;
    if (!id) return;
    const url = `https://www.youtube.com/watch?v=${id}`;

    // Rend la carte sémantiquement un lien (mieux pour Cmd/Ctrl+click → onglet)
    card.setAttribute("role", "link");
    card.setAttribute("tabindex", "0");
    card.dataset.youtubeUrl = url;

    const open = () => window.open(url, "_blank", "noopener,noreferrer");

    card.addEventListener("click", open);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });
}

// ─── Toggle œil sur le champ code ──────────────────────────────
function initCodeToggle() {
  const input = document.getElementById("code-input");
  const btn = document.getElementById("code-input-toggle");
  if (!input || !btn) return;

  const eyeOpen  = `<svg class="icon" aria-hidden="true"><use href="#ph-eye"/></svg>`;
  const eyeShut  = `<svg class="icon" aria-hidden="true"><use href="#ph-eye-slash"/></svg>`;

  btn.addEventListener("click", () => {
    const isPwd = input.type === "password";
    input.type = isPwd ? "text" : "password";
    btn.innerHTML = isPwd ? eyeShut : eyeOpen;
    btn.setAttribute("aria-pressed", String(isPwd));
    btn.setAttribute("aria-label", isPwd ? "Masquer le code" : "Afficher le code en clair");
    input.focus();
  });
}

// ─── Boot ──────────────────────────────────────────────────────
initPodium();
initDemoGauge();
initVideoEmbeds();
initReveal();
initCodeForm();
initCodeToggle();
