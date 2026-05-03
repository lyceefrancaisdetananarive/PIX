# Codes d'accès classes — PIX LFT

> ⚠ **Document interne — à distribuer aux élèves de chaque groupe ou à leurs professeurs principaux.**

Saisie : un seul mot, sans accent (la casse est ignorée).

---

## 5ème (cycle 4) — 11 groupes

| Groupe Pix Orga | Code |
|---|---|
| 5M1 SVT       | **MICROSCOPE**     |
| 5M2 TECHNO    | **ARDUINO**        |
| 5M3 SVT       | **CHLOROPHYLLE**   |
| 5M4 TECHNO    | **SOUDURE**        |
| 5M5 SVT       | **MITOCHONDRIE**   |
| 5M6 TECHNO    | **ENGRENAGE**      |
| 5SVT1         | **PHOTOSYNTHESE**  |
| 5 TECHNO 1    | **PROTOTYPE**      |
| 5 TECHNO 2    | **CIRCUIT**        |
| 5M7 P.1       | **BINAIRE**        |
| 5M7 P.2       | **ALGORITHME**     |

## 4ème (cycle 4) — 11 groupes

| Groupe Pix Orga | Code |
|---|---|
| 4M1 SVT       | **CELLULE**        |
| 4M2 TECHNO    | **MOTEUR**         |
| 4M3 SVT       | **ATOME**          |
| 4M4 TECHNO    | **CAPTEUR**        |
| 4M5 SVT       | **MOLECULE**       |
| 4M6 TECHNO    | **ROBOT**          |
| 4 TECHNO 1    | **ROUAGE**         |
| 4 TECHNO 2    | **DIODE**          |
| 4 TECHNO 3    | **SONDE**          |
| 4M7 P.1       | **PIXEL**          |
| 4M7 P.2       | **ELECTRON**       |

## 3ème (cycle 4) — 8 groupes

| Groupe Pix Orga | Code |
|---|---|
| 3M1           | **BLACKBERRY**     |
| 3M2           | **ESP32**          |
| 3M3           | **MICROBIT**       |
| 3M4 SVT       | **GENETIQUE**      |
| 3M5           | **SERVOMOTEUR**    |
| 3M6           | **MICROCHIP**      |
| 3M7           | **SOLENOIDE**      |
| 3 TECHNO 2    | **RASPBERRY**      |

---

## Modifier un code

1. Édite le mapping `GROUP_CODES` dans [`scripts/build-data.py`](../scripts/build-data.py).
2. Régénère les données : `python3 scripts/build-data.py`.
3. Le hash et le nom du fichier dans `data/groups/` changent automatiquement.
4. Mets à jour ce document.
5. Commit & push.

## Vérifier un hash manuellement

```bash
echo -n "ARDUINO" | shasum -a 256
# 42566bebf7acabb1701120c4b6f4f735e873b2e7f3d289ef99fa9c7e43432d4d
```

Le code est mis en majuscules avant hashage (cf. `js/auth.js`).

## Conseils de distribution

- **Pédagogique** : invite chaque enseignant à présenter le mot en classe en
  rappelant la signification du terme (lien programme).
- **Affichage** : un grand poster A3 par classe avec le mot en gros + tutoriel d'accès.
- **Numérique** : message Pronote/Maillot avec le lien direct + le code.
- **Sécurité** : si un code est divulgué hors classe, change-le et regénère.
