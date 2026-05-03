# PIX LFT — Tableau de bord pédagogique

Site statique de consultation des résultats Pix Orga pour le **Lycée Français de Tananarive**
(AEFE, EGD). Hébergé sur GitHub Pages, accessible publiquement, avec accès classe par
**code SHA-256**.

> Phase 1 — niveaux 5ème et 3ème (11 groupes Pix Orga, ~180 élèves).
> Phase 2 et 3 (vidéos finalisées, audit RGAA AA, Lighthouse 95+) à venir.

---

## Démo locale

```bash
cd site
python3 -m http.server 8765
# → http://localhost:8765
```

(Aucune dépendance npm. Le site est 100% HTML/CSS/JS vanilla.)

---

## Architecture

```
site/
├── index.html              Accueil (hero, podium, comprendre Pix, saisie code)
├── classe.html             Vue classe verrouillée par code (chargée via #hash dans l'URL)
├── 404.html
│
├── assets/
│   ├── fonts/              Marianne 2022 woff2 (Light/Regular/Medium/Bold/ExtraBold)
│   ├── logos/              LFT, AEFE, Pix
│   └── icons/              SVG inline
│
├── css/
│   ├── marianne.css        @font-face Marianne
│   ├── theme.css           Variables couleurs (LFT/AEFE/Pix), reset, accessibilité
│   ├── glass.css           Système Liquid Glass (glassmorphism, dégradés animés)
│   └── components.css      Header, hero, podium, jauge, cartes, tableau, modal
│
├── js/                     Modules ES6 (type="module")
│   ├── data-loader.js      Fetch + cache JSON
│   ├── auth.js             SHA-256 + sessionStorage
│   ├── podium.js           Rendu Top 3
│   ├── pix-gauge.js        Jauge animée + niveaux Pix
│   ├── filters.js          Tri/filtres/recherche
│   ├── main-home.js        Logique page d'accueil
│   └── main-classe.js      Logique page classe + modal détail
│
├── data/                   ⚠ Généré par scripts/build-data.py — ne pas éditer à la main
│   ├── classes.json        { hash → {name, level, studentCount, ...} }
│   ├── students-public.json Top 3 + stats globales
│   ├── manifest.json       Date génération + référentiel niveaux/domaines
│   └── groups/<hash>.json  Données détaillées par groupe (chargées après auth)
│
└── scripts/
    └── build-data.py       Pipeline CSV (Pix Orga) + XLSX → JSON
```

---

## Workflow de mise à jour des données

Quand tu télécharges de nouveaux exports Pix Orga :

1. **Copier les CSV** dans les dossiers groupes du dossier parent (ex: `../5M2 TECHNO/*.csv`).
   Les noms de dossiers doivent rester identiques à ceux de `GROUP_CODES`
   dans `scripts/build-data.py`.

2. **Régénérer les JSON** :
   ```bash
   cd site
   python3 scripts/build-data.py
   ```

3. **Vérifier le résumé** affiché (nombre d'élèves par groupe, certifiables, moyenne).

4. **Commit & push** les fichiers modifiés dans `data/` :
   ```bash
   git add data/
   git commit -m "Maj données Pix $(date +%Y-%m-%d)"
   git push
   ```

   GitHub Pages redéploie automatiquement en ~1 minute.

> **Important** : seuls les fichiers `data/*.json` sont versionnés.
> Les CSV sources et le XLSX restent en local (non committés).

---

## Codes classes

Chaque groupe Pix Orga possède un code unique. Voir [`docs/CODES_CLASSES.md`](docs/CODES_CLASSES.md)
pour la liste complète (à transmettre aux enseignants concernés).

Modèle de sécurité :
- Le code est hashé en **SHA-256** côté navigateur (`crypto.subtle.digest`).
- Seul le hash est présent dans `classes.json` (le code en clair n'apparaît jamais
  dans le code source ni dans les JSON publiés).
- Le fichier `data/groups/<hash>.json` est nommé par le hash, donc une URL
  inconnue ne peut pas être devinée.
- Le hash débloqué est stocké en `sessionStorage` (s'efface à la fermeture de l'onglet).

Limite assumée : `classes.json` est public, donc les hashs sont visibles. Une
attaque par dictionnaire sur les 11 codes Techno reste possible mais nécessite
de connaître la liste des candidats. C'est suffisant pour l'objectif :
empêcher la consultation casuelle entre élèves.

---

## Niveaux Pix utilisés

| Niveau | Fourchette (pix) |
|---|---|
| Novice | 0 – 47 |
| Débutant | 48 – 143 |
| Indépendant | 144 – 287 |
| Avancé | 288 – 511 |
| Expert | 512+ |

(En miroir des fourchettes officielles Pix pour le cycle 4 collège.)

---

## Stack technique

- **HTML5 sémantique**, **CSS3 moderne** (custom properties, backdrop-filter, grid),
  **JavaScript vanilla ES6+** (pas de framework).
- Pipeline data : **Python 3** + pandas (lecture XLSX) + csv stdlib.
- Police : **Marianne 2022** (officielle de l'État, libre de droits).
- Hébergement : **GitHub Pages** (site statique, fichier `.nojekyll` pour
  servir HTML/JS direct).

---

## Accessibilité

- Contraste vérifié (RGAA AA) malgré le glassmorphism (overlays sombres si besoin).
- Navigation clavier complète, focus visible (outline jaune Pix).
- `aria-label`, `role`, `aria-busy`, `aria-modal` sur les composants interactifs.
- `prefers-reduced-motion` respecté.
- Fallback `prefers-contrast: more` (surfaces opaques).
- `lang="fr"`, structure de titres logique (h1, h2, h3).

---

## Phase 2 et 3 (à venir)

- [ ] Vraies vignettes vidéos (URLs YouTube exactes + thumbnails)
- [ ] Logo Pix officiel SVG (fourni par Pix)
- [ ] Audit RGAA AA complet
- [ ] Optimisation perf (Lighthouse 95+)
- [ ] Niveaux 6ème et 4ème quand les CSV seront disponibles
- [ ] Page imprimable (carnet de bord élève)
