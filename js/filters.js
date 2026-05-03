/*
 * Filtres et tris pour la liste d'élèves.
 */

const collator = new Intl.Collator("fr", { sensitivity: "base" });

export function applyFilters(students, { search = "", sort = "pix-desc", cert = "all" } = {}) {
  const q = search.trim().toLowerCase();

  let out = students.filter((s) => {
    if (q && !normalize(s.name).includes(normalize(q))) return false;
    if (cert === "certifiable" && !s.certifiable) return false;
    if (cert === "not-certifiable" && (s.certifiable || s.pix === 0)) return false;
    if (cert === "no-data" && s.pix > 0) return false;
    return true;
  });

  switch (sort) {
    case "pix-desc":
      out.sort((a, b) => (b.pix - a.pix) || collator.compare(a.name, b.name));
      break;
    case "pix-asc":
      out.sort((a, b) => (a.pix - b.pix) || collator.compare(a.name, b.name));
      break;
    case "name-asc":
      out.sort((a, b) => collator.compare(a.name, b.name));
      break;
    case "name-desc":
      out.sort((a, b) => collator.compare(b.name, a.name));
      break;
    case "cert-first":
      out.sort((a, b) => {
        if (a.certifiable !== b.certifiable) return a.certifiable ? -1 : 1;
        return b.pix - a.pix;
      });
      break;
  }

  return out;
}

function normalize(s) {
  return String(s ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}
