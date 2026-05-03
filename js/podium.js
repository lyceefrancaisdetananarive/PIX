/*
 * Rendu du podium Top 3.
 */

const MEDALS = ["🥇", "🥈", "🥉"];

export function renderPodium(container, podium) {
  if (!podium || podium.length === 0) {
    container.innerHTML = `
      <p style="text-align:center; padding: var(--space-7); color: var(--text-secondary);">
        Aucun résultat disponible pour le moment.
      </p>
    `;
    container.removeAttribute("aria-busy");
    return;
  }

  // Ordre visuel : 2e, 1er, 3e (le 1er au centre, en hauteur)
  const layoutOrder = [];
  if (podium[1]) layoutOrder.push(podium[1]);
  if (podium[0]) layoutOrder.push(podium[0]);
  if (podium[2]) layoutOrder.push(podium[2]);

  container.innerHTML = layoutOrder
    .map((entry) => {
      const medal = MEDALS[entry.rank - 1] ?? "🎖";
      const meta = [entry.classe, entry.group].filter(Boolean).join(" · ");
      return `
        <article class="podium__step podium__step--rank-${entry.rank} glass-bevel">
          <div class="podium__medal" aria-hidden="true">${medal}</div>
          <div class="podium__rank">${ordinal(entry.rank)} place</div>
          <div class="podium__name">${escapeHtml(entry.name)}</div>
          <div class="podium__meta">${escapeHtml(meta)}</div>
          <div class="podium__score">
            <span>${entry.pix}</span>
            <span class="podium__score-unit">pix</span>
          </div>
        </article>
      `;
    })
    .join("");

  container.removeAttribute("aria-busy");
}

function ordinal(n) {
  return n === 1 ? "1ère" : `${n}ème`;
}

export function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
