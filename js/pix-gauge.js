/*
 * Jauge Pix animée — calcul du niveau et mise à jour visuelle.
 */

import { levelFor, PIX_MAX } from "./data-loader.js";

export function renderGauge({ valueEl, levelEl, fillEl, pix }) {
  const level = levelFor(pix);
  const ratio = Math.min(1, Math.max(0, pix / PIX_MAX));

  if (valueEl) {
    animateNumber(valueEl, parseInt(valueEl.textContent, 10) || 0, pix, 900);
  }
  if (levelEl) {
    levelEl.textContent = level.label;
    levelEl.style.color = `var(--level-${level.slug})`;
  }
  if (fillEl) {
    requestAnimationFrame(() => {
      fillEl.style.width = `${ratio * 100}%`;
    });
  }
}

function animateNumber(el, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const t = Math.min(1, (now - start) / duration);
    // easeOutCubic
    const eased = 1 - Math.pow(1 - t, 3);
    const current = Math.round(from + (to - from) * eased);
    el.textContent = current;
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
