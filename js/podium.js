/*
 * Rendu du podium Top 3 — version premium :
 * - 1ère place : grande, centrale, couronne, halo doré, animation
 * - 2e et 3e   : encadrant la 1ère, plus petites mais distinctes (argent/bronze)
 */

const MEDAL_DATA = [
  { icon: "ph-crown-simple", color: "gold",   label: "1ère place" },
  { icon: "ph-medal",        color: "silver", label: "2ème place" },
  { icon: "ph-medal",        color: "bronze", label: "3ème place" },
];

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

  const first = podium[0];
  const second = podium[1];
  const third = podium[2];

  container.innerHTML = `
    <div class="podium-premium">
      ${second ? renderSide(second, "second") : '<div></div>'}
      ${first ? renderFirst(first) : ''}
      ${third ? renderSide(third, "third") : '<div></div>'}
    </div>
  `;

  container.removeAttribute("aria-busy");
}

function renderFirst(entry) {
  const meta = entry.classe || entry.group || "";
  return `
    <article class="podium-first glass-bevel" aria-label="1ère place">
      <div class="podium-first__halo" aria-hidden="true"></div>
      <div class="podium-first__crown" aria-hidden="true">
        <svg class="icon icon--3xl"><use href="#ph-crown-simple"/></svg>
      </div>
      <div class="podium-first__rank">1ère place</div>
      <h3 class="podium-first__name">${escapeHtml(entry.name)}</h3>
      <div class="podium-first__meta">${escapeHtml(meta)}</div>
      <div class="podium-first__score">
        <span class="podium-first__score-value">${entry.pix}</span>
        <span class="podium-first__score-unit">pix</span>
      </div>
      <div class="podium-first__level">${escapeHtml(entry.level)}</div>
      <div class="podium-first__sparkles" aria-hidden="true">
        <span></span><span></span><span></span><span></span><span></span><span></span>
      </div>
    </article>
  `;
}

function renderSide(entry, position) {
  const data = MEDAL_DATA[entry.rank - 1] ?? MEDAL_DATA[entry.rank > 3 ? 2 : 0];
  const meta = entry.classe || entry.group || "";
  return `
    <article class="podium-side podium-side--${position} podium-side--${data.color} glass-bevel"
             aria-label="${data.label}">
      <div class="podium-side__medal" aria-hidden="true">
        <svg class="icon icon--2xl"><use href="#${data.icon}"/></svg>
      </div>
      <div class="podium-side__rank">${data.label}</div>
      <h3 class="podium-side__name">${escapeHtml(entry.name)}</h3>
      <div class="podium-side__meta">${escapeHtml(meta)}</div>
      <div class="podium-side__score">
        <span>${entry.pix}</span>
        <span class="podium-side__score-unit">pix</span>
      </div>
    </article>
  `;
}

// ─── Mini-podium (3 colonnes côte à côte) ──────────────────────
export function renderPodiumMini(container, podium) {
  if (!podium || podium.length === 0) return;

  const items = [];
  if (podium[1]) items.push(renderMiniRank(podium[1], 2));
  if (podium[0]) items.push(renderMiniFirst(podium[0]));
  if (podium[2]) items.push(renderMiniRank(podium[2], 3));

  container.innerHTML = items.join("");
}

function renderMiniFirst(entry) {
  const meta = entry.classe || entry.group || "";
  return `
    <div class="podium-mini__first" aria-label="1ère place">
      <div class="podium-mini__crown" aria-hidden="true">
        <svg class="icon icon--xl"><use href="#ph-crown-simple"/></svg>
      </div>
      <div class="podium-mini__name">${escapeHtml(entry.name)}</div>
      <div class="podium-mini__meta">${escapeHtml(meta)}</div>
      <div class="podium-mini__score">
        <span class="podium-mini__score-value">${entry.pix}</span>
        <span class="podium-mini__score-unit">pix</span>
      </div>
      ${entry.level ? `<div class="podium-mini__level">${escapeHtml(entry.level)}</div>` : ""}
    </div>
  `;
}

function renderMiniRank(entry, rank) {
  const meta = entry.classe || entry.group || "";
  const data = MEDAL_DATA[rank - 1];
  return `
    <div class="podium-mini__side podium-mini__side--${data.color}" aria-label="${data.label}">
      <div class="podium-mini__medal" aria-hidden="true">
        <svg class="icon icon--lg"><use href="#${data.icon}"/></svg>
      </div>
      <div class="podium-mini__name podium-mini__name--side">${escapeHtml(entry.name)}</div>
      <div class="podium-mini__meta">${escapeHtml(meta)}</div>
      <div class="podium-mini__score podium-mini__score--side">
        <span class="podium-mini__score-value">${entry.pix}</span>
        <span class="podium-mini__score-unit">pix</span>
      </div>
    </div>
  `;
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
