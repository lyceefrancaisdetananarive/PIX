#!/usr/bin/env python3
"""
Génère un PDF récapitulatif (1 page A4 recto) avec :
  - 4 codes enseignants (avec accès global)
  - Tous les codes élèves par classe (6e → Terminale)

Style cohérent avec le site (palette LFT/Pix, police Marianne, glassmorphism léger).

Sortie :
  - site/docs/codes-classes.html  (toujours généré, imprimable directement)
  - site/docs/codes-classes.pdf   (si WeasyPrint installé)

Usage :
  python3 scripts/generate-codes-pdf.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Import des codes depuis build-data.py
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
build = import_module("build-data")
GROUP_CODES = build.GROUP_CODES
TEACHER_CODES = build.TEACHER_CODES

ROOT = Path(__file__).resolve().parent.parent  # site/
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)
HTML_OUT = DOCS_DIR / "codes-classes.html"
PDF_OUT = DOCS_DIR / "codes-classes.pdf"

# ─── Regroupement par niveau ─────────────────────────────────────
def level_of(name: str) -> str:
    if name.startswith("6"): return "6ème"
    if name.startswith("5"): return "5ème"
    if name.startswith("4"): return "4ème"
    if name.startswith("3"): return "3ème"
    if name.startswith("2DE") or name.startswith("2PRO"): return "2nde"
    if name.startswith(("1G", "1STMG", "1PRO")): return "1ère"
    if name.startswith("T"): return "Terminale"
    return "?"

LEVEL_ORDER = ["6ème", "5ème", "4ème", "3ème", "2nde", "1ère", "Terminale"]

by_level = {lvl: [] for lvl in LEVEL_ORDER}
for group, code in GROUP_CODES.items():
    by_level[level_of(group)].append((group, code))
for lvl in by_level:
    by_level[lvl].sort(key=lambda x: x[0])

# Profs : pour l'affichage on inverse "NOM Prénom" → "Prénom NOM" plus naturel
def display_teacher(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2 and parts[0].isupper():
        return f"{' '.join(parts[1:])} {parts[0].title()}"
    return name



# ─── HTML print-friendly ─────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8">
<title>PIX LFT — Codes d'accès classes 2025-2026</title>
<style>
@font-face {
  font-family: "Marianne";
  src: url("../assets/fonts/Marianne-Regular.woff2") format("woff2");
  font-weight: 400;
}
@font-face {
  font-family: "Marianne";
  src: url("../assets/fonts/Marianne-Bold.woff2") format("woff2");
  font-weight: 700;
}
@font-face {
  font-family: "Marianne";
  src: url("../assets/fonts/Marianne-ExtraBold.woff2") format("woff2");
  font-weight: 800;
}

@page {
  size: A4 portrait;
  margin: 7mm 9mm;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  font-family: "Marianne", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  color: #1a1a1a;
  background: #fff;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

body {
  width: 192mm;          /* 210mm - 18mm marges */
  margin: 0 auto;
  padding: 0;
  font-size: 9pt;
  line-height: 1.25;
}

/* ── Header LFT (compact) ────────────────────────────── */
.doc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 3mm;
  border-bottom: 1.2px solid rgba(0, 59, 115, 0.15);
  margin-bottom: 3mm;
}
.doc-head__brand {
  display: flex;
  align-items: center;
  gap: 3mm;
}
.doc-head__logo {
  width: 11mm;
  height: 11mm;
  border-radius: 50%;
  object-fit: cover;
  background: #fff;
}
.doc-head__title-block { line-height: 1.1; }
.doc-head__brand-name {
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #003b73;
}
.doc-head__title {
  font-size: 16pt;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
  background: linear-gradient(135deg, #003b73 0%, #e10075 100%);
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-top: 0.5mm;
}
.doc-head__year {
  font-size: 7.5pt;
  font-weight: 700;
  color: #6b7280;
  text-align: right;
  letter-spacing: 0.05em;
  line-height: 1.2;
}
.doc-head__year strong { color: #003b73; font-size: 10pt; display: block; }

/* ── Bandeau ENSEIGNANTS (4 colonnes, ultra compact) ── */
.teachers {
  margin-bottom: 3mm;
  padding: 2.5mm 3mm;
  background: linear-gradient(135deg, rgba(61, 104, 255, 0.06), rgba(225, 0, 117, 0.04));
  border: 1px solid rgba(61, 104, 255, 0.2);
  border-radius: 3mm;
}
.teachers__title {
  font-size: 7.5pt;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #2952d6;
  margin-bottom: 1.5mm;
}
.teachers__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0 4mm;
}
.teachers__row {
  display: flex;
  flex-direction: column;
  gap: 0.8mm;
  padding: 0.5mm 0;
}
.teachers__name {
  font-size: 7.5pt;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.1;
}
.teachers__code {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 9.5pt;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #003b73;
  background: linear-gradient(135deg, #ffe070 0%, #ffc400 100%);
  padding: 0.6mm 2mm;
  border-radius: 1.2mm;
  box-shadow: inset 0 0.4px 0 rgba(255, 255, 255, 0.5);
  align-self: flex-start;
}

/* ── Sections COLLÈGE / LYCÉE ─────────────────────────── */
.section-pill {
  display: inline-block;
  font-size: 7pt;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  padding: 0.8mm 3mm;
  border-radius: 999px;
  margin: 2.5mm 0 1.5mm;
}
.section-pill--college { background: rgba(61, 104, 255, 0.1); color: #2952d6; }
.section-pill--lycee   { background: rgba(225, 0, 117, 0.1); color: #b8005e; }

/* ── Grille de niveaux ─────────────────────────────────── */
.levels {
  display: grid;
  gap: 2mm;
}
.levels--college { grid-template-columns: 0.85fr 1.55fr 1.55fr 1.25fr; }
.levels--lycee   { grid-template-columns: 1.3fr 1.5fr 1.5fr; }

.level-block {
  background: rgba(0, 59, 115, 0.025);
  border: 0.5px solid rgba(0, 59, 115, 0.12);
  border-radius: 2.5mm;
  padding: 2mm 2.2mm;
  break-inside: avoid;
}
.level-block__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1.2mm;
  padding-bottom: 1mm;
  border-bottom: 0.5px solid rgba(0, 59, 115, 0.1);
}
.level-block__name {
  font-size: 10pt;
  font-weight: 800;
  letter-spacing: -0.01em;
  background: linear-gradient(135deg, #003b73, #e10075);
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
}
.level-block__count {
  font-size: 6.5pt;
  font-weight: 600;
  color: #6b7280;
}

.code-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.7mm 0;
  border-bottom: 0.5px dotted rgba(0, 59, 115, 0.1);
}
.code-row:last-child { border-bottom: none; }
.code-row__group {
  font-size: 7.5pt;
  font-weight: 600;
  color: #1a1a1a;
  letter-spacing: -0.005em;
}
.code-row__value {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 7.5pt;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #003b73;
  white-space: nowrap;
}


/* ── Footer ───────────────────────────────────────────── */
.doc-foot {
  margin-top: 2.5mm;
  padding-top: 2mm;
  border-top: 0.5px solid rgba(0, 59, 115, 0.12);
  display: flex;
  justify-content: space-between;
  font-size: 6.5pt;
  color: #6b7280;
}
.doc-foot__legal { font-style: italic; }
.doc-foot__url   { font-weight: 700; color: #2952d6; }
</style>
</head>
<body>

<header class="doc-head">
  <div class="doc-head__brand">
    <img class="doc-head__logo" src="../assets/logos/lft.png" alt="">
    <div class="doc-head__title-block">
      <div class="doc-head__brand-name">Lycée Français de Tananarive · Pix</div>
      <h1 class="doc-head__title">Codes d'accès classes</h1>
    </div>
  </div>
  <div class="doc-head__year">Année scolaire<strong>2025 — 2026</strong></div>
</header>

<!-- ENSEIGNANTS -->
<section class="teachers">
  <div class="teachers__title">⛟ Enseignants — accès aux 72 classes</div>
  <div class="teachers__grid">
    __TEACHER_ROWS__
  </div>
</section>

<!-- COLLÈGE -->
<span class="section-pill section-pill--college">Collège · Cycle 3 + Cycle 4</span>
<div class="levels levels--college">
  __COLLEGE_BLOCKS__
</div>

<!-- LYCÉE -->
<span class="section-pill section-pill--lycee">Lycée · 2nde, 1ère, Terminale</span>
<div class="levels levels--lycee">
  __LYCEE_BLOCKS__
</div>

<footer class="doc-foot">
  <div class="doc-foot__legal">
    Document interne — codes à transmettre aux élèves de chaque classe ou via leur PP.
  </div>
  <div class="doc-foot__url">lyceefrancaisdetananarive.github.io/PIX</div>
</footer>

</body></html>
"""

def render():
    # Profs
    teacher_rows = []
    for full_name, code in TEACHER_CODES.items():
        display = display_teacher(full_name)
        teacher_rows.append(
            f'<div class="teachers__row">'
            f'<span class="teachers__name">{display}</span>'
            f'<span class="teachers__code">{code}</span></div>'
        )

    def make_block(level_name):
        rows = by_level[level_name]
        lines = "\n".join(
            f'<div class="code-row">'
            f'<span class="code-row__group">{group}</span>'
            f'<span class="code-row__value">{code}</span></div>'
            for group, code in rows
        )

        return (
            f'<div class="level-block">'
            f'<div class="level-block__head">'
            f'<span class="level-block__name">{level_name}</span>'
            f'<span class="level-block__count">{len(rows)} code{"s" if len(rows) > 1 else ""}</span>'
            f'</div>{lines}</div>'
        )

    college_blocks = "\n".join(make_block(lvl) for lvl in ["6ème", "5ème", "4ème", "3ème"])
    lycee_blocks   = "\n".join(make_block(lvl) for lvl in ["2nde", "1ère", "Terminale"])

    html = (HTML
        .replace("__TEACHER_ROWS__", "\n".join(teacher_rows))
        .replace("__COLLEGE_BLOCKS__", college_blocks)
        .replace("__LYCEE_BLOCKS__", lycee_blocks)
    )
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML : {HTML_OUT}")

    # PDF via Chrome headless (déjà installé sur tous les macOS modernes)
    import subprocess
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    chrome = next((p for p in chrome_paths if Path(p).exists()), None)

    if chrome:
        try:
            subprocess.run(
                [chrome,
                 "--headless=new",
                 "--disable-gpu",
                 "--no-pdf-header-footer",
                 f"--print-to-pdf={PDF_OUT}",
                 f"file://{HTML_OUT}"],
                check=True, capture_output=True, timeout=30,
            )
            print(f"  ✓ PDF  : {PDF_OUT}")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠  Chrome a échoué : {e.stderr.decode()[:200] if e.stderr else e}")
            print_manual_fallback()
        except subprocess.TimeoutExpired:
            print(f"  ⚠  Chrome timeout. Imprime manuellement.")
            print_manual_fallback()
    else:
        # Tente Playwright en fallback
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f"file://{HTML_OUT}", wait_until="networkidle")
                page.pdf(path=str(PDF_OUT), format="A4", print_background=True,
                         margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
                browser.close()
            print(f"  ✓ PDF  : {PDF_OUT}  (via Playwright)")
        except ImportError:
            print(f"  ℹ  Aucun navigateur trouvé → ouvre le HTML manuellement.")
            print_manual_fallback()


def print_manual_fallback():
    print(f"\n     Pour générer le PDF manuellement :")
    print(f"        1. Ouvre {HTML_OUT.name} dans Chrome/Safari/Firefox")
    print(f"        2. Cmd+P → Destination 'Enregistrer au format PDF'")
    print(f"        3. Mise en page : A4, marges par défaut")
    print(f"        4. Activez 'Graphiques d'arrière-plan' (cocher)\n")


if __name__ == "__main__":
    print("== Génération du récapitulatif des codes ==")
    render()
    print(f"\n  Total : {len(TEACHER_CODES)} profs + {sum(len(v) for v in by_level.values())} codes classes")
