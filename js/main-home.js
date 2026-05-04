/*
 * Logique de la page d'accueil :
 *   - chargement du podium Top 3
 *   - jauge interactive (démo)
 *   - reveal au scroll
 *   - validation du code classe
 */

import { loadPublic, loadClasses, loadTeachers, levelFor } from "./data-loader.js";
import { tryUnlock } from "./auth.js";
import { renderPodium } from "./podium.js";
import { renderGauge } from "./pix-gauge.js";

// ─── Chargement public (3 podiums + stats + onglets) ───────────
async function initPodium() {
  const container = document.getElementById("podium");
  const statsEl = document.getElementById("global-stats");
  const tabs = document.querySelectorAll(".cycle-tab");

  try {
    const data = await loadPublic();
    let currentCycle = "cycle4";

    const renderForCycle = (cycle) => {
      const entry = data.podiums?.[cycle];
      if (!entry) return;
      renderPodium(container, entry.podium);
      // Si vide
      if (!entry.podium.length) {
        container.innerHTML = `
          <div class="podium-empty glass-bevel">
            <svg class="icon icon--3xl" aria-hidden="true" style="color: var(--text-muted); opacity: 0.6;"><use href="#ph-info"/></svg>
            <h3>Aucun score à afficher</h3>
            <p>Les élèves de ${entry.label} n'ont pas encore réalisé de campagne <em>Collecte</em>.<br>
               Le podium s'actualisera dès les premiers résultats.</p>
          </div>
        `;
        container.removeAttribute("aria-busy");
      }
    };

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const c = tab.dataset.cycle;
        if (c === currentCycle) return;
        currentCycle = c;
        tabs.forEach((t) => t.setAttribute("aria-selected", t === tab ? "true" : "false"));
        renderForCycle(c);
      });
    });

    renderForCycle(currentCycle);

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
    container.innerHTML = `<p style="text-align:center; padding: var(--space-7); color: var(--danger);">Erreur de chargement des données.</p>`;
    container.removeAttribute("aria-busy");
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

// ─── Vidéos embed (lecture sur place via iframe YouTube) ────────
function initVideoEmbeds() {
  document.querySelectorAll(".video-card--embed").forEach((card) => {
    const play = () => {
      if (card.classList.contains("is-playing")) return;
      const id = card.dataset.videoId;
      const title = card.dataset.title || "Vidéo Pix";
      if (!id) return;
      const iframe = document.createElement("iframe");
      iframe.className = "video-card__iframe";
      iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&modestbranding=1`;
      iframe.title = title;
      iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      iframe.allowFullscreen = true;
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      card.appendChild(iframe);
      card.classList.add("is-playing");
      card.removeAttribute("role");
      card.removeAttribute("tabindex");
    };
    card.addEventListener("click", play);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        play();
      }
    });
  });
}

// ─── Boot ──────────────────────────────────────────────────────
initPodium();
initDemoGauge();
initVideoEmbeds();
initReveal();
initCodeForm();
