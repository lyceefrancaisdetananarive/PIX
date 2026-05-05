# Codes d'accès — PIX LFT

> Document interne — à distribuer aux élèves de chaque classe ou aux profs Techno.

Saisie : un seul mot, sans accent (la casse est ignorée).

---

## 👨‍🏫 Codes ENSEIGNANTS (accès TOTAL aux 72 classes)

| Enseignant | Code | Niveau enseigné |
|---|---|---|
| **DEGUEURCE Franck**       | **FERRARI**     | 3ème |
| **HUOT Laurent**           | **LAMBORGHINI** | 3ème + SNT/NSI |
| **RAFALIARISON Max**       | **BUGATTI**     | 5ème + 3M4 SVT + 3 TECHNO 2 |
| **RAKOTOARIMANANA Ranja**  | **BENTLEY**     | 4ème + 5M4/5M6 TECHNO |

> Les 4 codes profs ouvrent le dashboard enseignant (`teacher.html`) avec accès à
> toutes les classes du collège ET du lycée.

---

## 🎓 Cycle 3 — 6ème (7 classes)

| Classe | Code |
|---|---|
| 6M1 | **ECRAN** |
| 6M2 | **CLAVIER** |
| 6M3 | **SOURIS** |
| 6M4 | **DOSSIER** |
| 6M5 | **FICHIER** |
| 6M6 | **NAVIGATEUR** |
| 6M7 | **INTERNET** |

## 🎓 Cycle 4 — 5ème (11 groupes)

| Groupe | Code |
|---|---|
| 5M1 SVT | **MICROSCOPE** |
| 5M2 TECHNO | **ARDUINO** |
| 5M3 SVT | **CHLOROPHYLLE** |
| 5M4 TECHNO | **SOUDURE** |
| 5M5 SVT | **MITOCHONDRIE** |
| 5M6 TECHNO | **ENGRENAGE** |
| 5SVT1 | **PHOTOSYNTHESE** |
| 5 TECHNO 1 | **PROTOTYPE** |
| 5 TECHNO 2 | **CIRCUIT** |
| 5M7 P.1 | **BINAIRE** |
| 5M7 P.2 | **ALGORITHME** |

## 🎓 Cycle 4 — 4ème (11 groupes)

| Groupe | Code |
|---|---|
| 4M1 SVT | **CELLULE** |
| 4M2 TECHNO | **MOTEUR** |
| 4M3 SVT | **ATOME** |
| 4M4 TECHNO | **CAPTEUR** |
| 4M5 SVT | **MOLECULE** |
| 4M6 TECHNO | **ROBOT** |
| 4 TECHNO 1 | **ROUAGE** |
| 4 TECHNO 2 | **DIODE** |
| 4 TECHNO 3 | **SONDE** |
| 4M7 P.1 | **PIXEL** |
| 4M7 P.2 | **ELECTRON** |

## 🎓 Cycle 4 — 3ème (8 groupes)

| Groupe | Code |
|---|---|
| 3M1 | **BLACKBERRY** |
| 3M2 | **ESP32** |
| 3M3 | **MICROBIT** |
| 3M4 SVT | **GENETIQUE** |
| 3M5 | **SERVOMOTEUR** |
| 3M6 | **MICROCHIP** |
| 3M7 | **SOLENOIDE** |
| 3 TECHNO 2 | **RASPBERRY** |

---

## 🏫 Lycée — 2nde (11 classes)

| Classe | Code |
|---|---|
| 2DE1 | **SIRIUS** |
| 2DE2 | **VEGA** |
| 2DE3 | **ALTAIR** |
| 2DE4 | **POLARIS** |
| 2DE5 | **CANOPUS** |
| 2DE6 | **DENEB** |
| 2DE7 | **BETELGEUSE** |
| 2DE8 | **ANTARES** |
| 2DE9 | **RIGEL** |
| 2PRO1 | **ORION** |
| 2PRO2 | **PEGASE** |

## 🏫 Lycée — 1ère (12 classes)

| Classe | Code |
|---|---|
| 1G1 | **DATABASE** |
| 1G2 | **CRYPTAGE** |
| 1G3 | **SERVEUR** |
| 1G4 | **REQUETE** |
| 1G5 | **SYNTAXE** |
| 1G6 | **BOUCLE** |
| 1G7 | **VARIABLE** |
| 1G8 | **FONCTION** |
| 1STMG1 | **MARKETING** |
| 1PRO AGORA | **AGORA** |
| 1PRO VENTE | **COMMERCE** |
| 1PRO COMMUN | **CONSEIL** |

## 🏫 Lycée — Terminale (12 classes)

| Classe | Code |
|---|---|
| TG1 | **COMPILATEUR** |
| TG2 | **ASSEMBLEUR** |
| TG3 | **KERNEL** |
| TG4 | **PROTOCOLE** |
| TG5 | **BANDWIDTH** |
| TG6 | **TERMINAL** |
| TG7 | **CONSOLE** |
| TG8 | **CLOUD** |
| TSTMG1 | **BUSINESS** |
| TSTMG2 | **STRATEGIE** |
| TPRO AGORA | **SAVOIR** |
| TPRO VENTE | **SERVICE** |

---

## Modifier un code

1. Édite le mapping `GROUP_CODES` dans [`scripts/build-data.py`](../scripts/build-data.py).
2. Régénère : `python3 scripts/build-data.py`.
3. Mets à jour ce document.
4. Commit & push.

## Total : **72 codes classes + 4 codes profs**

| Cycle | Classes / groupes | Élèves attendus |
|---|---|---|
| Cycle 3 (6ème) | 7 | ~ 162 |
| Cycle 4 (5e/4e/3e) | 30 | ~ 742 |
| Lycée (2nde/1e/Term.) | 35 | ~ 1257 |
| **Total** | **72** | **~ 2161** |
