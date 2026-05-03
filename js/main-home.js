/*
 * Logique de la page d'accueil :
 *   - chargement du podium Top 3
 *   - jauge interactive (démo)
 *   - reveal au scroll
 *   - validation du code classe
 */

import { loadPublic, loadClasses, levelFor } from "./data-loader.js";
import { tryUnlock } from "./auth.js";
import { renderPodium } from "./podium.js";
import { renderGauge } from "./pix-gauge.js";

// ─── Chargement public (podium + stats) ────────────────────────
async function initPodium() {
  const container = document.getElementById("podium");
  const statsEl = document.getElementById("global-stats");
  try {
    const data = await loadPublic();
    renderPodium(container, data.podium);

    if (statsEl && data.stats) {
      statsEl.innerHTML = `
        <strong>${data.stats.totalStudents}</strong> élèves suivis ·
        <strong>${data.stats.totalCertifiable}</strong> certifiables ·
        moyenne de <strong>${data.stats.averagePix}</strong> pix ·
        <strong>${data.stats.totalGroups}</strong> groupes
      `;
    }
  } catch (err) {
    console.error(err);
    container.innerHTML = `<p style="text-align:center; padding: var(--space-7); color: var(--danger);">Erreur de chargement des données.</p>`;
    container.removeAttribute("aria-busy");
  }
}

// ─── Jauge démo (slider) ───────────────────────────────────────
function initDemoGauge() {
  const slider = document.getElementById("demo-gauge-slider");
  const valueEl = document.getElementById("demo-gauge-value");
  const levelEl = document.getElementById("demo-gauge-level");
  const fillEl = document.getElementById("demo-gauge-fill");
  if (!slider) return;

  const update = (pix) => {
    const lvl = levelFor(pix);
    valueEl.textContent = pix;
    levelEl.textContent = lvl.label;
    levelEl.style.color = `var(--level-${lvl.slug})`;
    fillEl.style.width = `${(pix / 1024) * 100}%`;
  };

  slider.addEventListener("input", (e) => update(parseInt(e.target.value, 10)));
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
      const result = await tryUnlock(code, classesIndex);
      if (result) {
        // Animation de succès
        input.style.borderColor = "var(--success)";
        input.style.background = "rgba(24, 117, 60, 0.06)";
        setTimeout(() => {
          window.location.href = `classe.html#${result.hash}`;
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

// ─── Boot ──────────────────────────────────────────────────────
initPodium();
initDemoGauge();
initReveal();
initCodeForm();
