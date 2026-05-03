# Codes d'accès classes — PIX LFT

> ⚠ **Document interne — ne pas committer dans un repo public si tu changes les codes.**
> Ces mots permettent l'accès aux données détaillées de chaque groupe.

À distribuer aux **élèves de chaque groupe** ou à **leurs professeurs principaux**.
Saisie : un seul mot, sans accent (la casse est ignorée).

## 5ème (cycle 4)

| Groupe Pix Orga | Code | Hash SHA-256 |
|---|---|---|
| 5M1 SVT       | **MICROSCOPE**     | `4b1323df…07c21e6` |
| 5M2 TECHNO    | **ARDUINO**        | `42566beb…43432d4d` |
| 5M3 SVT       | **CHLOROPHYLLE**   | `9f2018da…9c886a82` |
| 5M5 SVT       | **MITOCHONDRIE**   | `b0f9dff9…d9927152` |
| 5SVT1         | **PHOTOSYNTHESE**  | `6c4f3e0c…446e89ca` |
| 5 TECHNO 1    | **PROTOTYPE**      | (voir `data/classes.json`) |
| 5 TECHNO 2    | **CIRCUIT**        | (voir `data/classes.json`) |
| 5M7 P.1       | **BINAIRE**        | (voir `data/classes.json`) |
| 5M7 P.2       | **ALGORITHME**     | (voir `data/classes.json`) |

## 3ème (cycle 4)

| Groupe Pix Orga | Code | Hash SHA-256 |
|---|---|---|
| 3M4 SVT       | **GENETIQUE**      | (voir `data/classes.json`) |
| 3 TECHNO 2    | **RASPBERRY**      | (voir `data/classes.json`) |

---

## Modifier un code

1. Édite le mapping `GROUP_CODES` dans `scripts/build-data.py`.
2. Regénère les données : `python3 scripts/build-data.py`.
3. Le hash et le nom du fichier dans `data/groups/` changent automatiquement.
4. Mets à jour ce document.
5. Commit & push.

## Vérifier un hash manuellement

```bash
echo -n "ARDUINO" | shasum -a 256
# 42566bebf7acabb1701120c4b6f4f735e873b2e7f3d289ef99fa9c7e43432d4d
```

Le code est mis en majuscules avant hashage (cf. `js/auth.js`).

---

## Conseils de distribution

- **Pédagogique** : invite chaque enseignant à présenter le mot en classe en
  rappelant la signification du terme (lien programme).
- **Affichage** : un grand poster A3 par classe avec le mot en gros + tutoriel d'accès.
- **Numérique** : message Pronote/Maillot avec le lien direct + le code.
- **Sécurité** : si un code est divulgué hors classe, change-le et regénère.
