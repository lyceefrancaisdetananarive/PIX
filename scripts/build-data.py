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

# Mapping groupe Pix Orga (= nom du dossier) -> code d'accès
GROUP_CODES = {
    # ── 5ème ───────────────────────────────────────────────────
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
    # ── 4ème ───────────────────────────────────────────────────
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
    # ── 3ème ───────────────────────────────────────────────────
    "3M1":          "BLACKBERRY",
    "3M2":          "ESP32",
    "3M3":          "MICROBIT",
    "3M4 SVT":      "GENETIQUE",
    "3M5":          "SERVOMOTEUR",
    "3M6":          "MICROCHIP",
    "3M7":          "SOLENOIDE",
    "3 TECHNO 2":   "RASPBERRY",
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

# Niveaux Pix officiels (fourchettes en pix)
PIX_LEVELS = [
    {"slug": "novice",      "label": "Novice",      "min": 0,    "max": 47},
    {"slug": "debutant",    "label": "Débutant",    "min": 48,   "max": 143},
    {"slug": "independant", "label": "Indépendant", "min": 144,  "max": 287},
    {"slug": "avance",      "label": "Avancé",      "min": 288,  "max": 511},
    {"slug": "expert",      "label": "Expert",      "min": 512,  "max": 1024},
]

PIX_MAX = 1024  # plafond théorique cycle 4

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


def load_student_directory() -> dict:
    """Retourne un index avec plusieurs clés par élève pour faciliter le matching :
    - clé "FULL NORMALIZED NAME" (nom + tous les prénoms)
    - clé "FAMILY FIRSTGIVEN" (nom + premier prénom seulement)
    - clé "FAMILYNAME" seule (fallback si prénom ambigu)
    """
    if not STUDENT_LIST.exists():
        print(f"⚠  Liste élèves introuvable : {STUDENT_LIST}", file=sys.stderr)
        return {}

    df = pd.read_excel(STUDENT_LIST, dtype=str)
    df = df.fillna("")
    index = {}
    family_only = {}  # famille seule -> [entries] pour fallback

    for _, row in df.iterrows():
        full = str(row.get("Élève", "")).strip()
        if not full:
            continue
        entry = {
            "fullName": full,
            "classe": str(row.get("Classe", "")).strip(),
            "groupes": [g.strip() for g in str(row.get("Groupes", "")).split(",") if g.strip()],
        }
        full_key = normalize_name(full)
        index[full_key] = entry

        family, given = split_xlsx_name(full)
        if family and given:
            short_key = f"{family} {given[0]}"
            # Si déjà occupé par un autre élève (homonymie), ne pas écraser
            if short_key not in index:
                index[short_key] = entry
            family_only.setdefault(family, []).append(entry)

    # Famille seule = fallback uniquement si UN SEUL élève porte ce nom
    for family, entries in family_only.items():
        if len(entries) == 1 and family not in index:
            index[family] = entries[0]

    return index


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
        # Le key est "NOM PRENOM" normalisé : tente la résolution via le référentiel
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
            "domains": {slug: {"label": label, "level": 0, "pix": 0}
                        for label, slug in [(name, DOMAIN_SLUGS[name]) for name in DOMAIN_MAP]},
            "competences": {},
            "lastUpdate": sample.get("date"),
            "parcours": sorted(recs, key=lambda p: p.get("date") or "", reverse=True),
        })

    # Tri par score décroissant
    students.sort(key=lambda s: (-s["pix"], s["name"]))

    # Détection du niveau d'après le préfixe du nom de dossier
    if group_name.startswith("3"):
        level = "3e"
    elif group_name.startswith("4"):
        level = "4e"
    elif group_name.startswith("6"):
        level = "6e"
    else:
        level = "5e"

    return {
        "name": group_name,
        "level": level,
        "studentCount": len(students),
        "certifiableCount": sum(1 for s in students if s["certifiable"]),
        "averagePix": round(sum(s["pix"] for s in students) / len(students)) if students else 0,
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
            "studentCount": result["studentCount"],
            "certifiableCount": result["certifiableCount"],
            "averagePix": result["averagePix"],
        }

        all_students.extend(result["students"])
        print(f"  ✓ {group_name:15} → {result['studentCount']:3} élèves, {result['certifiableCount']:3} certifiables, moy. {result['averagePix']:3} pix")

    # classes.json
    with open(DATA_DIR / "classes.json", "w", encoding="utf-8") as f:
        json.dump({"groups": classes_index}, f, ensure_ascii=False, indent=2)

    # students-public.json (Top 3 + stats globales)
    podium = sorted(
        [s for s in all_students if s["pix"] > 0],
        key=lambda s: -s["pix"],
    )[:3]
    podium_public = [
        {
            "rank": i + 1,
            "name": s["name"],
            "classe": s["classe"],
            "group": s["group"],
            "pix": s["pix"],
            "level": pix_level_for(s["pix"])["label"],
        }
        for i, s in enumerate(podium)
    ]
    stats = {
        "totalGroups": len(classes_index),
        "totalStudents": sum(c["studentCount"] for c in classes_index.values()),
        "totalCertifiable": sum(c["certifiableCount"] for c in classes_index.values()),
        "averagePix": round(sum(s["pix"] for s in all_students) / max(1, len([s for s in all_students if s["pix"] > 0]))),
    }
    with open(DATA_DIR / "students-public.json", "w", encoding="utf-8") as f:
        json.dump({"podium": podium_public, "stats": stats}, f, ensure_ascii=False, indent=2)

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
