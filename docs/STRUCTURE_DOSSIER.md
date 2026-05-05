# Structure du dossier local PIX

Le dossier `~/Documents/PIX/` (OneDrive) est l'**espace de travail** pour
gérer les données Pix. Cette structure est conçue pour supporter la
synchronisation automatique via l'agent local (`scripts/agent/`).

## Structure cible

```
PIX/
│
├── Liste des élèves par classes.xlsx     ⭐ Référentiel Pronote (source de vérité)
│
├── _inbox_pix/                           📥 INBOX — l'agent y dépose les CSV
│                                              build-data.py les classe automatiquement
│
├── _archive/                             📦 Originaux et fichiers historiques
│   ├── svg-plantes-pix/                  (8 SVG officiels Pix niveau 1-8)
│   └── logos-originaux/                  (Logos haute résolution non compressés)
│
├── _admin/                               🗂 Documents administratifs
│   ├── EDT/                              (4 emplois du temps profs)
│   └── liens-pix.rtf                     (URLs Pix Communauté/Support/Parents)
│
├── _ressources/                          📚 Ressources Pix officielles
│   ├── Actualités/                       (Catalogue parcours, IA, certif…)
│   ├── Ressources/                       (Guides, kit certification…)
│   └── Pour aller + loin/                (Liste référents AEFE…)
│
├── _divers/                              ⚠ Campagnes multi-classes / non triables
│   ├── resultats-cybersecurite_2pro-*    (touche plusieurs classes)
│   ├── resultats-ia-*                    (parcours IA transverse)
│   └── resultats-pix_2pro2026-*          (campagne 2PRO globale)
│
├── Police MARIANNE/                      (police officielle de l'État, conservée)
│
├── 6M1/, 6M2/, ... 6M7/                  📂 Cycle 3 — 7 classes 6ème
├── 5M1 SVT/, 5M2 TECHNO/, ...            📂 Cycle 4 — 11 groupes 5ème
├── 4M1 SVT/, 4M2 TECHNO/, ...            📂 Cycle 4 — 11 groupes 4ème
├── 3M1/, 3M2/, ... 3 TECHNO 2/           📂 Cycle 4 — 8 groupes 3ème
├── 2DE1/, ... 2PRO1/, 2PRO2/             📂 Lycée — 11 classes 2nde
├── 1G1/, ... 1STMG1/, 1PRO AGORA/, ...   📂 Lycée — 12 classes 1ère
├── TG1/, ... TSTMG1/, TPRO AGORA/, ...   📂 Lycée — 12 classes Terminale
│
└── site/                                 🌐 Le site web (dépôt git)
```

## Conventions

### Préfixe `_` pour les dossiers utilitaires

Les dossiers commençant par `_` (underscore) sont **triés en haut** alphabétiquement
dans le Finder, séparés des dossiers de classes. Ils contiennent les données
auxiliaires (archives, admin, ressources, inbox, divers).

### Référentiel Pronote à la racine

Le fichier `Liste des élèves par classes.xlsx` reste **à la racine** car il est
la source de vérité pour le mapping élève ↔ classe ↔ groupe. Le pipeline
build-data.py le lit pour identifier les "non renseignés" attendus dans chaque
classe.

### Un dossier = un groupe Pix Orga

Chaque dossier de classe contient les CSV exports Pix Orga pour ce groupe :
- `5M2 TECHNO/resultats-5m2_techno_--_collecte-...csv`
- `5M2 TECHNO/resultats-5m2_techno_--_cybersecurite-...csv`
- etc.

## Pipeline automatique

```
       Pix Orga
          │
          ▼ (Playwright)
    ┌──────────────┐
    │  Agent local │  scripts/agent/pix-sync-agent.py
    └──────┬───────┘
           │ download CSV
           ▼
    ┌──────────────┐
    │  _inbox_pix/ │  CSV bruts en attente
    └──────┬───────┘
           │ build-data.py dispatch_inbox()
           │   - lit chaque CSV
           │   - identifie groupe via "Nom de la campagne"
           │   - déplace vers le bon dossier groupe
           │   - remplace l'ancien fichier de même type
           ▼
    ┌─────────────────────────────────┐
    │  5M2 TECHNO/, 3M1/, TG6/, ...   │  Dossiers groupes mis à jour
    └─────────────┬───────────────────┘
                  │ build-data.py génère
                  ▼
    ┌─────────────────────────────────┐
    │  site/data/*.json                │  JSON pour le site
    │  site/data/groups/*.json         │
    │  site/data/admin/*.json          │
    └─────────────┬───────────────────┘
                  │ git push (auto par l'agent)
                  ▼
    ┌─────────────────────────────────┐
    │  GitHub Pages (publié en ~1 min) │
    └──────────────────────────────────┘
```

## Que fait `dispatch_inbox()` ?

Pour chaque CSV dans `_inbox_pix/` :

1. **Lit la première ligne de données** pour récupérer le champ `Nom de la campagne`
2. **Identifie le groupe** via mapping intelligent :
   - "5M2 TECHNO -- Collecte" → dossier `5M2 TECHNO/`
   - "Récup points 3M1" → dossier `3M1/`
   - "Sensibilisation Pix 6M5" → dossier `6M5/`
3. **Identifie le type de campagne** (collecte, recup, cybersecurite, parcours_rentree, emi…)
4. **Supprime l'ancien CSV de même type** dans le dossier cible (évite les doublons)
5. **Déplace le nouveau CSV** dans le bon dossier
6. Si non rattachable → `_divers/`

## Recommandations d'usage

| Situation | Action |
|---|---|
| Tu lances l'agent (bouton) | Tout est automatique, rien à faire |
| Tu télécharges un CSV manuellement depuis Pix Orga | Dépose-le dans `_inbox_pix/` puis `python3 scripts/build-data.py` |
| Tu veux modifier le référentiel élèves | Modifie `Liste des élèves par classes.xlsx` puis rebuild |
| Une campagne couvre plusieurs classes (ex: 2PRO multi-classes) | Reste dans `_divers/`, à traiter manuellement |
| Tu veux voir les ressources Pix officielles | `_ressources/` |
| Tu veux ajouter un EDT prof | `_admin/EDT/` |
