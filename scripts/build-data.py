#!/usr/bin/env python3
"""
Pipeline de transformation des exports Pix Orga vers les JSON statiques du site.

Usage :
    python3 scripts/build-data.py

Lit :
    - ../[Nom Groupe]/*.csv     (exports Pix Orga par groupe)
    - ../Liste des élèves par classes.xlsx  (référentiel élèves)

Génère :
    - data/classes.json              (mapping hash SHA-256 -> métadonnées groupe)
    - data/students-public.json      (podium Top 3 + stats globales)
    - data/groups/<hash>.json        (données détaillées par groupe, accès via code)
    - data/manifest.json             (date de la dernière génération)
"""

import csv
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent  # site/
SOURCE_ROOT = ROOT.parent                       # PIX/
DATA_DIR = ROOT / "data"
GROUPS_DIR = DATA_DIR / "groups"

STUDENT_LIST = SOURCE_ROOT / "Liste des élèves par classes.xlsx"

# Liste des comptes Pix qui ne sont PAS des élèves (enseignants, comptes de test).
# Ces comptes sont totalement exclus du site (podium, tableaux, stats).
# Format : "NOM PRENOM" en majuscules sans accent (clé normalisée).
EXCLUDED_ACCOUNTS = {
    "DEGUEURCE FRANCK",       # Enseignant Techno (3e)
    "HUOT LAURENT",           # Enseignant Techno + SNT/NSI (3e/2de/1e)
    "RAFALIARISON MAX",       # Enseignant Techno (5e + 3e)
    "RAKOTOARIMANANA RANJA",  # Enseignant Techno (4e + 5e)
}

# Codes d'accès "enseignant" : permettent de voir TOUTES les classes
# (vue dashboard avec accès global aux résultats).
# Distincts des codes élèves : univers "planètes" pour les distinguer
# clairement des codes Techno/SVT.
TEACHER_CODES = {
    "DEGUEURCE Franck":       "MERCURE",
    "HUOT Laurent":           "SATURNE",
    "RAFALIARISON Max":       "JUPITER",
    "RAKOTOARIMANANA Ranja":  "NEPTUNE",
}

# Quels groupes Pix Orga chaque enseignant assure (extrait des EDT 2025-2026).
# Sert d'indicateur visuel sur le dashboard prof.
TEACHER_GROUPS = {
    "DEGUEURCE Franck": ["3M1", "3M5", "3 TECHNO 2"],  # 3M1 P.1+P.2, 3M5 TECHNO, 3TECHNO1 (≈3 TECHNO 2 dans nos groupes)
    "HUOT Laurent":     ["3M2", "3M3", "3M6", "3M7"],  # 3M2 SVT, 3M3 TECHNO, 3M6 SVT, 3M7 TECHNO, 3SVT1
    "RAFALIARISON Max": [
        "5M1 SVT", "5M2 TECHNO", "5M3 SVT", "5M5 SVT", "5SVT1",
        "5 TECHNO 1", "5 TECHNO 2", "5M7 P.1", "5M7 P.2",
        "3M4 SVT", "3 TECHNO 2",
    ],
    "RAKOTOARIMANANA Ranja": [
        "4M1 SVT", "4M2 TECHNO", "4M3 SVT", "4M4 TECHNO", "4M5 SVT", "4M6 TECHNO",
        "4 TECHNO 1", "4 TECHNO 2", "4 TECHNO 3", "4M7 P.1", "4M7 P.2",
        "5M4 TECHNO", "5M6 TECHNO",
    ],
}

# Mapping groupe Pix Orga (= nom du dossier) -> code d'accès
GROUP_CODES = {
    # ─── Cycle 3 — 6ème ────────────────────────────────────────
    "6M1":          "ECRAN",
    "6M2":          "CLAVIER",
    "6M3":          "SOURIS",
    "6M4":          "DOSSIER",
    "6M5":          "FICHIER",
    "6M6":          "NAVIGATEUR",
    "6M7":          "INTERNET",
    # ─── Cycle 4 — 5ème ────────────────────────────────────────
    "5M1 SVT":      "MICROSCOPE",
    "5M2 TECHNO":   "ARDUINO",
    "5M3 SVT":      "CHLOROPHYLLE",
    "5M4 TECHNO":   "SOUDURE",
    "5M5 SVT":      "MITOCHONDRIE",
    "5M6 TECHNO":   "ENGRENAGE",
    "5SVT1":        "PHOTOSYNTHESE",
    "5 TECHNO 1":   "PROTOTYPE",
    "5 TECHNO 2":   "CIRCUIT",
    "5M7 P.1":      "BINAIRE",
    "5M7 P.2":      "ALGORITHME",
    # ─── Cycle 4 — 4ème ────────────────────────────────────────
    "4M1 SVT":      "CELLULE",
    "4M2 TECHNO":   "MOTEUR",
    "4M3 SVT":      "ATOME",
    "4M4 TECHNO":   "CAPTEUR",
    "4M5 SVT":      "MOLECULE",
    "4M6 TECHNO":   "ROBOT",
    "4 TECHNO 1":   "ROUAGE",
    "4 TECHNO 2":   "DIODE",
    "4 TECHNO 3":   "SONDE",
    "4M7 P.1":      "PIXEL",
    "4M7 P.2":      "ELECTRON",
    # ─── Cycle 4 — 3ème ────────────────────────────────────────
    "3M1":          "BLACKBERRY",
    "3M2":          "ESP32",
    "3M3":          "MICROBIT",
    "3M4 SVT":      "GENETIQUE",
    "3M5":          "SERVOMOTEUR",
    "3M6":          "MICROCHIP",
    "3M7":          "SOLENOIDE",
    "3 TECHNO 2":   "RASPBERRY",
    # ─── Lycée — 2nde ──────────────────────────────────────────
    "2DE1":         "SIRIUS",
    "2DE2":         "VEGA",
    "2DE3":         "ALTAIR",
    "2DE4":         "POLARIS",
    "2DE5":         "CANOPUS",
    "2DE6":         "DENEB",
    "2DE7":         "BETELGEUSE",
    "2DE8":         "ANTARES",
    "2DE9":         "RIGEL",
    "2PRO1":        "ORION",
    "2PRO2":        "PEGASE",
    # ─── Lycée — 1ère ──────────────────────────────────────────
    "1G1":          "DATABASE",
    "1G2":          "CRYPTAGE",
    "1G3":          "SERVEUR",
    "1G4":          "REQUETE",
    "1G5":          "SYNTAXE",
    "1G6":          "BOUCLE",
    "1G7":          "VARIABLE",
    "1G8":          "FONCTION",
    "1STMG1":       "MARKETING",
    "1PRO AGORA":   "AGORA",
    "1PRO VENTE":   "COMMERCE",
    "1PRO COMMUN":  "CONSEIL",
    # ─── Lycée — Terminale ─────────────────────────────────────
    "TG1":          "COMPILATEUR",
    "TG2":          "ASSEMBLEUR",
    "TG3":          "KERNEL",
    "TG4":          "PROTOCOLE",
    "TG5":          "BANDWIDTH",
    "TG6":          "TERMINAL",
    "TG7":          "CONSOLE",
    "TG8":          "CLOUD",
    "TSTMG1":       "BUSINESS",
    "TSTMG2":       "STRATEGIE",
    "TPRO AGORA":   "SAVOIR",
    "TPRO VENTE":   "SERVICE",
}

# Mapping groupe -> cycle pédagogique (pour les 3 podiums)
def group_cycle(group_name: str) -> str:
    if group_name.startswith("6"):
        return "cycle3"  # 6ème
    if group_name.startswith(("5", "4", "3")):
        return "cycle4"  # 5e, 4e, 3e
    return "lycee"       # 2DE, 2PRO, 1G, 1STMG, 1PRO, TG, TSTMG, TPRO

# Détection du niveau (pour l'affichage)
LEVEL_LABELS = {
    "6e":   "Niveau 6ème",
    "5e":   "Niveau 5ème",
    "4e":   "Niveau 4ème",
    "3e":   "Niveau 3ème",
    "2nde": "Niveau 2nde",
    "1e":   "Niveau 1ère",
    "tale": "Niveau Terminale",
}

def detect_level(group_name: str) -> str:
    if group_name.startswith("6"): return "6e"
    if group_name.startswith("5"): return "5e"
    if group_name.startswith("4"): return "4e"
    if group_name.startswith("3"): return "3e"
    if group_name.startswith("2DE") or group_name.startswith("2PRO"): return "2nde"
    if group_name.startswith("1G") or group_name.startswith("1STMG") or group_name.startswith("1PRO"): return "1e"
    if group_name.startswith("T"): return "tale"
    return "5e"

CYCLE_LABELS = {
    "cycle3": "Cycle 3 · 6ème",
    "cycle4": "Cycle 4 · 5e/4e/3e",
    "lycee":  "Lycée · 2nde/1e/Term.",
}

# Référentiel CRCN : 16 compétences groupées en 5 domaines
DOMAIN_MAP = {
    "Information et données": [
        "Mener une recherche et une veille d’information",
        "Gérer des données",
        "Traiter des données",
    ],
    "Communication et collaboration": [
        "Interagir",
        "Partager et publier",
        "Collaborer",
        "S’insérer dans le monde numérique",
    ],
    "Création de contenu": [
        "Développer des documents textuels",
        "Développer des documents multimedia",
        "Adapter les documents à leur finalité",
        "Programmer",
    ],
    "Protection et sécurité": [
        "Sécuriser l’environnement numérique",
        "Protéger les données personnelles et la vie privée",
        "Protéger la santé, le bien-être et l’environnement",
    ],
    "Environnement numérique": [
        "Résoudre des problèmes techniques",
        "Construire un environnement numérique",
    ],
}

DOMAIN_SLUGS = {
    "Information et données": "info",
    "Communication et collaboration": "communication",
    "Création de contenu": "creation",
    "Protection et sécurité": "protection",
    "Environnement numérique": "environnement",
}

# Niveaux Pix OFFICIELS (source : pix.fr/aide/comprendre-vos-resultats)
# 8 niveaux ; un score < 64 ne donne aucun niveau certifié.
PIX_LEVELS = [
    {"slug": "non-certifie", "label": "Non certifié", "short": "—",       "min": 0,   "max": 63,   "image": "niveau-1.svg"},
    {"slug": "novice-1",     "label": "Novice 1",     "short": "N1",      "min": 64,  "max": 127,  "image": "niveau-1.svg"},
    {"slug": "novice-2",     "label": "Novice 2",     "short": "N2",      "min": 128, "max": 255,  "image": "niveau-2.svg"},
    {"slug": "independant-1","label": "Indépendant 1","short": "I1",      "min": 256, "max": 383,  "image": "niveau-3.svg"},
    {"slug": "independant-2","label": "Indépendant 2","short": "I2",      "min": 384, "max": 511,  "image": "niveau-4.svg"},
    {"slug": "avance-1",     "label": "Avancé 1",     "short": "A1",      "min": 512, "max": 639,  "image": "niveau-5.svg"},
    {"slug": "avance-2",     "label": "Avancé 2",     "short": "A2",      "min": 640, "max": 767,  "image": "niveau-6.svg"},
    {"slug": "expert-1",     "label": "Expert 1",     "short": "E1",      "min": 768, "max": 895,  "image": "niveau-7.svg"},
    {"slug": "expert-2",     "label": "Expert 2",     "short": "E2",      "min": 896, "max": 1024, "image": "niveau-8.svg"},
]

PIX_MAX = 1024  # plafond théorique (le score effectif est plafonné à 895 actuellement)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    """Slug ASCII pour identifiants stables."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s


def normalize_name(s: str) -> str:
    """Clé de comparaison (majuscules, sans accent, espaces simples)."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s).upper()
    return s


def proper_case(s: str) -> str:
    """Capitalisation propre : premières lettres en maj, particules en min."""
    if not s:
        return s
    parts = s.split()
    out = []
    for i, p in enumerate(parts):
        lower = p.lower()
        if i > 0 and lower in {"de", "du", "des", "la", "le", "les", "et", "d", "l"}:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return " ".join(out)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_french_number(v) -> float:
    """Parse '0,67' (FR) et '0.67' (US), gère vides et NaN."""
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_int(v) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(str(v).strip().replace(",", ".")))
    except (ValueError, TypeError):
        return 0


def parse_date_fr(s: str):
    """Parse '27/04/2026 07:13' -> datetime (None si invalide)."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return None


def pix_level_for(pix: int) -> dict:
    for level in PIX_LEVELS:
        if level["min"] <= pix <= level["max"]:
            return level
    return PIX_LEVELS[-1]


def read_csv_orga(path: Path) -> list:
    """Lit un export Pix Orga (séparateur ;, BOM UTF-8, quotes)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        return [row for row in reader]


def detect_csv_type(rows: list) -> str:
    """Identifie 'collecte' (avec 'Nombre de pix total') ou 'parcours'."""
    if not rows:
        return "unknown"
    headers = rows[0].keys()
    if "Nombre de pix total" in headers:
        return "collecte"
    if "Palier obtenu (/3)" in headers or "% maitrise de l'ensemble des acquis du profil" in headers:
        return "parcours"
    return "unknown"


# ---------------------------------------------------------------------------
# Chargement référentiel élèves (XLSX)
# ---------------------------------------------------------------------------

def split_xlsx_name(full: str):
    """'POSTEL Laurène Marie Danielle' -> ('POSTEL', ['LAURENE','MARIE','DANIELLE'])
    Heuristique : tokens en MAJUSCULES = nom de famille, le reste = prénoms."""
    tokens = full.split()
    family, given = [], []
    for tok in tokens:
        clean = unicodedata.normalize("NFKD", tok).encode("ascii", "ignore").decode("ascii")
        if clean.isupper() and not given:
            family.append(clean)
        else:
            given.append(clean.upper())
    return " ".join(family), given


_STUDENT_BY_GROUP_CACHE = {}     # group_name -> [entries]
_STUDENT_BY_CLASS_CACHE = {}     # classe (admin) -> [entries]


def load_student_directory() -> dict:
    """Retourne un index avec plusieurs clés par élève pour faciliter le matching.
    Construit aussi en parallèle deux index secondaires :
      _STUDENT_BY_GROUP_CACHE  pour le collège (clé = nom de groupe Pix Orga)
      _STUDENT_BY_CLASS_CACHE  pour le lycée   (clé = classe admin)
    """
    if not STUDENT_LIST.exists():
        print(f"⚠  Liste élèves introuvable : {STUDENT_LIST}", file=sys.stderr)
        return {}

    df = pd.read_excel(STUDENT_LIST, dtype=str)
    df = df.fillna("")
    index = {}
    family_only = {}

    for _, row in df.iterrows():
        full = str(row.get("Élève", "")).strip()
        if not full:
            continue
        classe = str(row.get("Classe", "")).strip()
        groupes_raw = [g.strip() for g in str(row.get("Groupes", "")).split(",") if g.strip()]

        entry = {
            "fullName": full,
            "classe": classe,
            "groupes": groupes_raw,
        }
        full_key = normalize_name(full)
        index[full_key] = entry

        family, given = split_xlsx_name(full)
        if family and given:
            short_key = f"{family} {given[0]}"
            if short_key not in index:
                index[short_key] = entry
            family_only.setdefault(family, []).append(entry)

        # Index par classe admin (lycée → c'est le seul critère)
        if classe:
            _STUDENT_BY_CLASS_CACHE.setdefault(classe, []).append(entry)

        # Index par groupe Pix Orga (collège : élève appartient à un groupe TECHNO/SVT)
        for g in groupes_raw:
            _STUDENT_BY_GROUP_CACHE.setdefault(g, []).append(entry)

    for family, entries in family_only.items():
        if len(entries) == 1 and family not in index:
            index[family] = entries[0]

    return index


def normalize_group_for_xlsx(group_name: str) -> list:
    """Retourne la liste des clés possibles dans le XLSX correspondant au dossier groupe.
    Le XLSX a parfois des variantes (sans espace, avec/sans tiret).
    """
    g = group_name.strip()
    candidates = {g, g.replace(" ", ""), g.replace("  ", " ")}

    # Variantes spécifiques observées
    swaps = {
        "5 TECHNO 1": ["5TECHNO1", "5 TECHNO 1"],
        "5 TECHNO 2": ["5TECHNO2", "5 TECHNO 2"],
        "4 TECHNO 1": ["4TECHNO1", "4 TECHNO 1"],
        "4 TECHNO 2": ["4TECHNO2", "4 TECHNO 2"],
        "4 TECHNO 3": ["4TECHNO3", "4 TECHNO 3"],
        "3 TECHNO 2": ["3TECHNO2", "3 TECHNO 2"],
        "4M1 SVT":    ["4M1SVT", "4M1 SVT"],
        "4M4 TECHNO": ["4M4TECHNO", "4M4 TECHNO"],
        "5M5 SVT":    ["5M5SVT", "5M5 SVT"],
    }
    if g in swaps:
        return swaps[g]
    return list(candidates)


def expected_students(group_name: str, level: str) -> list:
    """Retourne la liste des élèves attendus dans ce groupe d'après le XLSX :
       - Lycée : les élèves dont la Classe admin == nom du groupe
       - Collège : les élèves dont la liste de Groupes contient le nom du groupe
    """
    expected = []
    if level in ("2nde", "1e", "tale"):
        # Lycée : match direct sur la classe administrative
        for variant in normalize_group_for_xlsx(group_name):
            expected.extend(_STUDENT_BY_CLASS_CACHE.get(variant, []))
    else:
        # Collège : match sur la colonne Groupes
        for variant in normalize_group_for_xlsx(group_name):
            expected.extend(_STUDENT_BY_GROUP_CACHE.get(variant, []))

    # Dédoublonne par nom
    seen = set()
    out = []
    for s in expected:
        k = normalize_name(s["fullName"])
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def match_student(directory: dict, csv_nom: str, csv_prenom: str):
    """Cherche un élève dans le référentiel via plusieurs stratégies."""
    n_full = normalize_name(f"{csv_nom} {csv_prenom}")
    n_family = normalize_name(csv_nom)
    n_first_given = normalize_name(csv_prenom).split(" ")[0] if csv_prenom else ""

    # 1. Match exact (nom + prénom complet)
    if n_full in directory:
        return directory[n_full]
    # 2. Match nom + premier mot du prénom
    short_key = f"{n_family} {n_first_given}".strip()
    if short_key in directory:
        return directory[short_key]
    # 3. Match nom de famille seul (si unique)
    if n_family in directory:
        return directory[n_family]
    return None


# ---------------------------------------------------------------------------
# Traitement Collecte
# ---------------------------------------------------------------------------

def process_collecte_rows(rows: list) -> dict:
    """Garde la dernière soumission par élève (tri par date d'envoi desc)."""
    by_student = {}
    for row in rows:
        nom = row.get("Nom du Participant", "").strip()
        prenom = row.get("Prénom du Participant", "").strip()
        if not nom and not prenom:
            continue
        key = normalize_name(f"{nom} {prenom}")
        if key in EXCLUDED_ACCOUNTS:
            continue
        date_str = row.get("Date et heure de l'envoi (Europe/Paris)", "")
        date = parse_date_fr(date_str)
        envoi = row.get("Envoi (O/N)", "").strip().upper() == "OUI"
        if not envoi:
            continue
        existing = by_student.get(key)
        if existing is None or (date and (existing["_date"] is None or date > existing["_date"])):
            by_student[key] = {
                "_date": date,
                "_raw": row,
                "_csvNom": nom,
                "_csvPrenom": prenom,
            }
    return by_student


def collecte_to_student_record(entry: dict, directory: dict, group_name: str) -> dict:
    """Transforme une entrée Collecte en record élève enrichi."""
    raw = entry["_raw"]

    # Croisement référentiel
    ref = match_student(directory, entry["_csvNom"], entry["_csvPrenom"])
    if ref:
        full_name = ref["fullName"]
        classe = ref["classe"]
    else:
        # Fallback : capitalisation propre depuis le CSV
        full_name = f"{proper_case(entry['_csvNom'])} {proper_case(entry['_csvPrenom'])}".strip()
        classe = ""

    pix_total = parse_int(raw.get("Nombre de pix total"))
    certifiable = raw.get("Certifiable (O/N)", "").strip().upper() == "OUI"
    nb_certif = parse_int(raw.get("Nombre de compétences certifiables"))

    # Compétences détaillées
    competences = {}
    for domain_name, comp_list in DOMAIN_MAP.items():
        for comp_label in comp_list:
            niv_col = f"Niveau pour la compétence {comp_label}"
            pix_col = f"Nombre de pix pour la compétence {comp_label}"
            niveau = parse_int(raw.get(niv_col))
            pix = parse_int(raw.get(pix_col))
            competences[comp_label] = {"niveau": niveau, "pix": pix}

    # Domaines agrégés
    domains = {}
    for domain_name, comp_list in DOMAIN_MAP.items():
        levels = [competences[c]["niveau"] for c in comp_list]
        pixs = [competences[c]["pix"] for c in comp_list]
        domains[DOMAIN_SLUGS[domain_name]] = {
            "label": domain_name,
            "level": max(levels) if levels else 0,
            "pix": sum(pixs),
        }

    last_date = entry["_date"]
    return {
        "id": slugify(full_name),
        "name": full_name,
        "classe": classe,
        "group": group_name,
        "pix": pix_total,
        "certifiable": certifiable,
        "competencesCertifiables": nb_certif,
        "domains": domains,
        "competences": competences,
        "lastUpdate": last_date.isoformat() if last_date else None,
    }


# ---------------------------------------------------------------------------
# Traitement Parcours
# ---------------------------------------------------------------------------

def process_parcours_csv(rows: list, group_name: str) -> dict:
    """Retourne { normalized_name: [parcours...] }."""
    by_student = {}
    for row in rows:
        nom = row.get("Nom du Participant", "").strip()
        prenom = row.get("Prénom du Participant", "").strip()
        if not nom and not prenom:
            continue
        key = normalize_name(f"{nom} {prenom}")
        if key in EXCLUDED_ACCOUNTS:
            continue

        date_str = row.get("Date et heure du partage (Europe/Paris)", "") or row.get(
            "Date et heure de début (Europe/Paris)", ""
        )
        date = parse_date_fr(date_str)
        partage = row.get("Partage (O/N)", "").strip().upper() == "OUI"

        parcours_label = row.get("Parcours", "").strip() or row.get("Nom de la campagne", "").strip()
        # Nettoyage : retire le préfixe "[CLG] " et la mention de groupe
        parcours_clean = re.sub(r"^\[[^\]]+\]\s*", "", parcours_label)
        parcours_clean = re.sub(r"^[^-]*--\s*", "", parcours_clean).strip()
        if not parcours_clean:
            parcours_clean = parcours_label

        progress = parse_french_number(row.get("% de progression", 0))
        maitrise = parse_french_number(row.get("% maitrise de l'ensemble des acquis du profil", 0))
        palier = parse_int(row.get("Palier obtenu (/3)", 0))

        record = {
            "name": parcours_clean,
            "code": row.get("Code", "").strip(),
            "campaignName": row.get("Nom de la campagne", "").strip(),
            "date": date.isoformat() if date else None,
            "partage": partage,
            "progress": round(progress, 2),
            "maitrise": round(maitrise, 2),
            "palier": palier,
        }
        by_student.setdefault(key, []).append(record)
    return by_student


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def build_group(group_dir: Path, directory: dict) -> Optional[dict]:
    """Traite un dossier groupe complet."""
    group_name = group_dir.name
    if group_name not in GROUP_CODES:
        return None

    csv_files = sorted(group_dir.glob("*.csv"))
    if not csv_files:
        print(f"  ⚠  Aucun CSV dans {group_name}", file=sys.stderr)
        return None

    collecte_data = {}        # normalized_name -> entry
    parcours_data = {}        # normalized_name -> [records]
    parcours_codes = {}       # parcours_name -> code (pour rattrapage)

    for csv_path in csv_files:
        try:
            rows = read_csv_orga(csv_path)
        except Exception as e:
            print(f"  ⚠  Erreur lecture {csv_path.name}: {e}", file=sys.stderr)
            continue

        csv_type = detect_csv_type(rows)
        if csv_type == "collecte":
            collecte_data = process_collecte_rows(rows)
        elif csv_type == "parcours":
            student_parcours = process_parcours_csv(rows, group_name)
            for key, recs in student_parcours.items():
                parcours_data.setdefault(key, []).extend(recs)
            for rec in (r for recs in student_parcours.values() for r in recs):
                parcours_codes.setdefault(rec["name"], rec["code"])

    # Construire les records élèves (à partir de Collecte si disponible, sinon Parcours)
    students = []
    seen_keys = set()

    for key, entry in collecte_data.items():
        rec = collecte_to_student_record(entry, directory, group_name)
        rec["parcours"] = sorted(
            parcours_data.get(key, []),
            key=lambda p: p.get("date") or "",
            reverse=True,
        )
        students.append(rec)
        seen_keys.add(key)

    # Élèves présents en parcours mais pas en collecte (pas de profil cible déclaré)
    for key, recs in parcours_data.items():
        if key in seen_keys:
            continue
        sample = recs[0]
        parts = key.split(" ", 1)
        ref = match_student(directory, parts[0], parts[1] if len(parts) > 1 else "")
        full_name = ref["fullName"] if ref else proper_case(key)
        classe = ref["classe"] if ref else ""
        students.append({
            "id": slugify(full_name),
            "name": full_name,
            "classe": classe,
            "group": group_name,
            "pix": 0,
            "certifiable": False,
            "competencesCertifiables": 0,
            "status": "partiel",  # a fait des parcours mais pas de Collecte
            "domains": {slug: {"label": label, "level": 0, "pix": 0}
                        for label, slug in [(name, DOMAIN_SLUGS[name]) for name in DOMAIN_MAP]},
            "competences": {},
            "lastUpdate": sample.get("date"),
            "parcours": sorted(recs, key=lambda p: p.get("date") or "", reverse=True),
        })
        seen_keys.add(key)

    # Marque les élèves "complets" issus de Collecte
    for s in students:
        if "status" not in s:
            s["status"] = "renseigne"

    # Élèves de la classe (XLSX) qui n'apparaissent pas du tout dans les CSV
    # → "non renseigné"
    level = detect_level(group_name)
    for entry in expected_students(group_name, level):
        key = normalize_name(entry["fullName"])
        if key in seen_keys or key in EXCLUDED_ACCOUNTS:
            continue
        students.append({
            "id": slugify(entry["fullName"]),
            "name": entry["fullName"],
            "classe": entry["classe"],
            "group": group_name,
            "pix": 0,
            "certifiable": False,
            "competencesCertifiables": 0,
            "status": "non_renseigne",
            "domains": {},
            "competences": {},
            "lastUpdate": None,
            "parcours": [],
        })
        seen_keys.add(key)

    # Tri : élèves avec score (desc), puis partiels, puis non renseignés (alpha)
    def sort_key(s):
        bucket = 0 if s.get("status") == "renseigne" else (1 if s.get("status") == "partiel" else 2)
        return (bucket, -s["pix"], s["name"])
    students.sort(key=sort_key)

    level = detect_level(group_name)
    cycle = group_cycle(group_name)

    # Calcul des moyennes UNIQUEMENT sur les élèves "renseignés" (avec score Pix)
    scored = [s for s in students if s["pix"] > 0]
    avg_pix = round(sum(s["pix"] for s in scored) / len(scored)) if scored else 0

    return {
        "name": group_name,
        "level": level,
        "cycle": cycle,
        "studentCount": len(students),
        "scoredCount": len(scored),
        "missingCount": len(students) - len(scored),
        "certifiableCount": sum(1 for s in students if s["certifiable"]),
        "averagePix": avg_pix,
        "parcoursCodes": parcours_codes,
        "students": students,
    }


def main() -> int:
    print("== Construction des données PIX LFT ==")
    GROUPS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    directory = load_student_directory()
    print(f"  → {len(directory)} élèves chargés depuis le référentiel XLSX")

    classes_index = {}
    all_students = []

    for group_name in GROUP_CODES:
        group_dir = SOURCE_ROOT / group_name
        if not group_dir.is_dir():
            print(f"  ⚠  Dossier introuvable : {group_name}", file=sys.stderr)
            continue
        result = build_group(group_dir, directory)
        if result is None:
            continue

        code = GROUP_CODES[group_name]
        code_hash = sha256_hex(code)

        # Écrit le fichier groupe (nommé par le hash)
        out_path = GROUPS_DIR / f"{code_hash}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        classes_index[code_hash] = {
            "name": group_name,
            "level": result["level"],
            "cycle": result["cycle"],
            "studentCount": result["studentCount"],
            "scoredCount": result.get("scoredCount", 0),
            "missingCount": result.get("missingCount", 0),
            "certifiableCount": result["certifiableCount"],
            "averagePix": result["averagePix"],
        }

        all_students.extend(result["students"])
        miss = result.get("missingCount", 0)
        miss_str = f" ({miss} non renseigné{'s' if miss > 1 else ''})" if miss else ""
        print(f"  ✓ {group_name:15} → {result['studentCount']:3} élèves, {result['certifiableCount']:3} certifiables, moy. {result['averagePix']:3} pix{miss_str}")

    # classes.json
    with open(DATA_DIR / "classes.json", "w", encoding="utf-8") as f:
        json.dump({"groups": classes_index}, f, ensure_ascii=False, indent=2)

    # ─── admin-classes.json : agrégation par CLASSE ADMINISTRATIVE Pronote ───
    # Pour le dashboard prof, on regroupe les élèves par classe admin (pas par groupe Pix).
    # Une classe (ex: "5M1") peut contenir des élèves répartis dans plusieurs groupes
    # Pix Orga (ex: "5M1 SVT", "5 TECHNO 1").
    admin_dir = DATA_DIR / "admin"
    admin_dir.mkdir(parents=True, exist_ok=True)

    # Collecte : { classe -> { fullName -> student_record } }
    by_classe = {}
    for s in all_students:
        cls = s.get("classe", "").strip()
        if not cls:
            continue
        bucket = by_classe.setdefault(cls, {})
        existing = bucket.get(s["name"])
        # Si plusieurs records pour le même élève (présent dans 2 groupes Pix Orga),
        # on garde celui avec le score le plus élevé / le plus de parcours
        if existing is None:
            bucket[s["name"]] = s
        else:
            ex_score = (existing["pix"], len(existing.get("parcours", [])))
            new_score = (s["pix"], len(s.get("parcours", [])))
            if new_score > ex_score:
                bucket[s["name"]] = s

    # Aussi : ajouter les élèves Pronote qui n'apparaissent dans aucun groupe Pix Orga
    # (cas du lycée par ex.)
    for cls, entries in _STUDENT_BY_CLASS_CACHE.items():
        bucket = by_classe.setdefault(cls, {})
        for entry in entries:
            if entry["fullName"] in bucket:
                continue
            if normalize_name(entry["fullName"]) in EXCLUDED_ACCOUNTS:
                continue
            bucket[entry["fullName"]] = {
                "id": slugify(entry["fullName"]),
                "name": entry["fullName"],
                "classe": cls,
                "group": "",  # aucun groupe Pix Orga
                "pix": 0,
                "certifiable": False,
                "competencesCertifiables": 0,
                "status": "non_renseigne",
                "domains": {},
                "competences": {},
                "lastUpdate": None,
                "parcours": [],
            }

    admin_index = {}
    for cls, students_dict in by_classe.items():
        students_list = list(students_dict.values())
        # Tri : score desc puis partiel puis non renseignés
        def sort_key(s):
            bucket_id = 0 if s.get("status") == "renseigne" else (1 if s.get("status") == "partiel" else 2)
            return (bucket_id, -s["pix"], s["name"])
        students_list.sort(key=sort_key)

        # Niveau via le nom de la classe
        admin_level = detect_level(cls)
        admin_cycle = group_cycle(cls)

        scored = [s for s in students_list if s["pix"] > 0]
        # Tous les groupes Pix Orga touchés (incluant les groupes hors-niveau,
        # ex. élèves redoublants ou ayant participé en collège quand ils sont
        # maintenant au lycée).
        all_groups_touched = sorted({
            s["group"] for s in students_list if s.get("group")
        })
        # Groupes "vrais" : seulement ceux du même niveau que la classe.
        # Un élève de 2DE2 ayant participé à "5 TECHNO 2" l'an dernier ne fait
        # pas de "5 TECHNO 2" un groupe à la charge du prof actuel de 2DE2.
        related_groups = [g for g in all_groups_touched if detect_level(g) == admin_level]
        # Groupes "historiques" (autres niveaux) : info pour le détail, pas
        # utilisés pour calculer "À ma charge".
        historical_groups = [g for g in all_groups_touched if detect_level(g) != admin_level]

        meta = {
            "name": cls,
            "level": admin_level,
            "cycle": admin_cycle,
            "studentCount": len(students_list),
            "scoredCount": len(scored),
            "missingCount": len(students_list) - len(scored),
            "certifiableCount": sum(1 for s in students_list if s["certifiable"]),
            "averagePix": round(sum(s["pix"] for s in scored) / len(scored)) if scored else 0,
            "relatedGroups": related_groups,
            "historicalGroups": historical_groups,
        }

        cls_hash = sha256_hex(f"adm:{cls}")
        admin_index[cls_hash] = meta

        # Fichier détail classe admin
        with open(admin_dir / f"{cls_hash}.json", "w", encoding="utf-8") as f:
            json.dump({**meta, "students": students_list}, f, ensure_ascii=False, indent=2)

    with open(DATA_DIR / "admin-classes.json", "w", encoding="utf-8") as f:
        json.dump({"classes": admin_index}, f, ensure_ascii=False, indent=2)

    print(f"   → {len(admin_index)} classes administratives agrégées (admin-classes.json + admin/*.json)")

    # teachers.json (codes profs hashés + leurs groupes assurés)
    teachers_index = {}
    for full_name, code in TEACHER_CODES.items():
        teachers_index[sha256_hex(code)] = {
            "name": full_name,
            "slug": slugify(full_name),
            "groups": TEACHER_GROUPS.get(full_name, []),
        }
    with open(DATA_DIR / "teachers.json", "w", encoding="utf-8") as f:
        json.dump({"teachers": teachers_index}, f, ensure_ascii=False, indent=2)

    # students-public.json — 3 podiums par cycle
    def make_podium(students_subset):
        top = sorted([s for s in students_subset if s["pix"] > 0], key=lambda s: -s["pix"])[:3]
        return [
            {
                "rank": i + 1,
                "name": s["name"],
                "classe": s["classe"],
                "group": s["group"],
                "pix": s["pix"],
                "level": pix_level_for(s["pix"])["label"],
            }
            for i, s in enumerate(top)
        ]

    # Map group_name -> cycle pour découper all_students
    group_cycle_map = {meta["name"]: meta["cycle"] for meta in classes_index.values()}

    by_cycle = {"cycle3": [], "cycle4": [], "lycee": []}
    for s in all_students:
        c = group_cycle_map.get(s["group"], "cycle4")
        by_cycle[c].append(s)

    podiums = {
        "cycle3": {"label": CYCLE_LABELS["cycle3"], "podium": make_podium(by_cycle["cycle3"])},
        "cycle4": {"label": CYCLE_LABELS["cycle4"], "podium": make_podium(by_cycle["cycle4"])},
        "lycee":  {"label": CYCLE_LABELS["lycee"],  "podium": make_podium(by_cycle["lycee"])},
    }

    scored_all = [s for s in all_students if s["pix"] > 0]
    stats = {
        "totalGroups": len(classes_index),
        "totalStudents": sum(c["studentCount"] for c in classes_index.values()),
        "totalScored": len(scored_all),
        "totalMissing": sum(c.get("missingCount", 0) for c in classes_index.values()),
        "totalCertifiable": sum(c["certifiableCount"] for c in classes_index.values()),
        "averagePix": round(sum(s["pix"] for s in scored_all) / max(1, len(scored_all))),
        "byCycle": {
            "cycle3": {"label": CYCLE_LABELS["cycle3"], "students": len(by_cycle["cycle3"])},
            "cycle4": {"label": CYCLE_LABELS["cycle4"], "students": len(by_cycle["cycle4"])},
            "lycee":  {"label": CYCLE_LABELS["lycee"],  "students": len(by_cycle["lycee"])},
        },
    }
    with open(DATA_DIR / "students-public.json", "w", encoding="utf-8") as f:
        json.dump({"podiums": podiums, "stats": stats}, f, ensure_ascii=False, indent=2)

    # manifest.json
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "pixLevels": PIX_LEVELS,
        "domains": [
            {"slug": DOMAIN_SLUGS[name], "label": name, "competences": comps}
            for name, comps in DOMAIN_MAP.items()
        ],
    }
    with open(DATA_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print()
    print(f"== Terminé. {stats['totalGroups']} groupes, {stats['totalStudents']} élèves, {stats['totalCertifiable']} certifiables.")
    print(f"   Sortie : {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
