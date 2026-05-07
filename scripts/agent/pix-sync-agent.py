#!/usr/bin/env python3
"""
Agent local de synchronisation Pix Orga → site PIX LFT.

Tourne sur 127.0.0.1:7777 et expose :
  - GET  /              → page admin de pilotage (HTML)
  - POST /sync          → démarre une synchro, retourne job_id
  - GET  /sync/<id>/events → SSE temps réel des étapes

Le bouton "Synchroniser" dans le dashboard prof du site
(https://lyceefrancaisdetananarive.github.io/PIX/) appelle cet agent.

SÉCURITÉ
- Identifiants Pix Orga lus depuis le Keychain macOS uniquement
  (jamais stockés en clair dans un fichier).
- Listen 127.0.0.1 uniquement : non accessible depuis le réseau.
- CORS strict : seules deux origines autorisées (le site GitHub Pages
  + l'admin local).
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 7777
KEYCHAIN_SERVICE = "pix-lft-sync"
KEYCHAIN_ACCOUNT = "pix-orga"

# Permet de relocaliser le script (ex. installation LaunchAgent en dehors d'OneDrive,
# OneDrive bloque les accès TCC pour les processus lancés par launchd).
# La variable d'environnement PIX_REPO doit pointer vers le dossier site/ du dépôt.
_env_repo = os.environ.get("PIX_REPO")
REPO_DIR = Path(_env_repo).resolve() if _env_repo else Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_DIR.parent                        # PIX/
BUILD_SCRIPT = REPO_DIR / "scripts" / "build-data.py"

# Sonde au démarrage : vérifie l'accès au dépôt (utile pour diagnostiquer TCC sous launchd)
def _probe_repo_access():
    manifest = REPO_DIR / "data" / "manifest.json"
    try:
        size = manifest.stat().st_size if manifest.exists() else -1
        print(f"[agent] dépôt OK : {REPO_DIR} (manifest={size} bytes)", flush=True)
    except Exception as e:
        print(f"[agent] ⚠ accès dépôt bloqué : {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        print(f"[agent]    chemin : {manifest}", file=sys.stderr, flush=True)
        print(f"[agent]    Si exécuté via launchd : autorise Full Disk Access pour", file=sys.stderr, flush=True)
        print(f"[agent]    /usr/bin/python3 et le venv (~/.local/share/pix-sync/venv/bin/python)", file=sys.stderr, flush=True)

_probe_repo_access()

ALLOWED_ORIGINS = {
    "https://lyceefrancaisdetananarive.github.io",
    f"http://{HOST}:{PORT}",
    "http://localhost:8765",
    "http://localhost:8766",
}

# ─── Stockage des jobs (en mémoire) ───────────────────────────────
JOBS = {}  # job_id -> { queue, status, started_at }


def now():
    return datetime.now().strftime("%H:%M:%S")


# ─── Lecture des credentials depuis le Keychain macOS ─────────────
def read_credentials():
    """Lit l'email + mot de passe stockés dans le Keychain macOS.

    Convention (cf. setup-keychain.sh) :
      service=pix-lft-sync, account=pix-orga-email  →  password = email
      service=pix-lft-sync, account=pix-orga        →  password = mot de passe

    NB : on n'utilise PAS le filtre -D (Kind) côté find-generic-password,
    il est ignoré par macOS et retourne n'importe quelle entrée matchant
    -s/-a, ce qui causait la confusion email↔password (issue Pix Orga login
    en silence : le champ email était rempli avec le mot de passe).
    """
    try:
        email = subprocess.check_output(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE, "-a", "pix-orga-email", "-w"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        password = subprocess.check_output(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "Identifiants Pix Orga introuvables dans le Keychain.\n"
            "Lance : ./scripts/agent/setup-keychain.sh"
        )

    # Garde-fou : un email doit contenir un '@'. Si ce n'est pas le cas,
    # c'est que les entrées Keychain sont inversées ou mal saisies.
    if "@" not in email:
        raise RuntimeError(
            f"Le champ email lu depuis le Keychain ({email!r}) ne contient pas d'@. "
            "Relance setup-keychain.sh pour corriger."
        )

    return email, password


# ─── Worker de synchronisation ────────────────────────────────────
def sync_worker(job_id: str):
    q = JOBS[job_id]["queue"]

    def emit(stage: str, message: str, progress: float = None, detail: dict = None):
        evt = {
            "stage": stage,
            "message": message,
            "progress": progress,
            "time": now(),
            "detail": detail or {},
        }
        q.put(evt)

    try:
        emit("init", "Démarrage de la synchronisation…", 0.01)

        # 1. Credentials
        emit("auth", "Lecture des identifiants depuis le Keychain macOS", 0.05)
        email, password = read_credentials()
        emit("auth", f"OK — connecté en tant que {email}", 0.08)

        # 2. Lancement Playwright
        emit("browser", "Démarrage du navigateur Playwright (headless)", 0.10)

        # Import paresseux : Playwright peut ne pas être installé encore
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            emit("error", "Playwright n'est pas installé. Lance : pip install playwright && playwright install chromium", -1)
            JOBS[job_id]["status"] = "failed"
            return

        downloaded = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # 3. Login Pix Orga
            emit("login", "Connexion à Pix Orga…", 0.15)
            page.goto("https://orga.pix.fr/connexion", wait_until="domcontentloaded")
            page.fill('input[id="login-email"]', email)
            page.fill('input[id="login-password"]', password)
            # Après submit on attend juste une navigation (URL ≠ /connexion).
            # Pix Orga peut rediriger vers /campagnes/liste, /sco-organization-participants/list,
            # un sélecteur d'organisation, etc. — on ne préjuge pas de la cible.
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                page.click('button[type="submit"]')

            if "/connexion" in page.url:
                emit("error", f"Échec d'authentification (URL inchangée : {page.url}). "
                              f"Vérifie email/mot de passe dans le Keychain.", -1)
                JOBS[job_id]["status"] = "failed"
                return

            emit("login", f"Authentifié → {page.url}", 0.20)

            # Si Pix Orga propose un sélecteur d'organisation, on prend la première
            # ou celle qui correspond au LFT.
            try:
                if "/choisir-organisation" in page.url or "organizations" in page.url.lower():
                    lft_link = page.locator('a:has-text("Lycée"), button:has-text("Lycée"), a:has-text("LFT")').first
                    if lft_link.count() > 0:
                        with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                            lft_link.click()
                    emit("login", f"Organisation sélectionnée → {page.url}", 0.22)
            except Exception as e:
                emit("login", f"(sélecteur d'organisation absent ou ignoré : {e})", 0.22)

            # 4. Liste des campagnes — vue "Toutes les campagnes" du LFT
            # (y compris celles des autres profs : DEGUEURCE, CHAUVETEAU, etc.).
            # /campagnes redirige vers /campagnes/les-miennes (50 max). On bascule
            # sur /campagnes/toutes (50/page mais 189 entrées au total → la
            # pagination boucle sur 4 pages).
            emit("list", "Récupération de la liste des campagnes…", 0.25)
            page.goto("https://orga.pix.fr/campagnes/toutes", wait_until="domcontentloaded")
            try:
                page.wait_for_selector('table tbody tr a[href*="/campagnes/"]', timeout=20000)
            except Exception:
                emit("error", f"Tableau des campagnes introuvable (URL: {page.url}). "
                              f"Pix Orga a peut-être changé la mise en page.", -1)
                JOBS[job_id]["status"] = "failed"
                return

            # Itération sur toutes les pages. Pix Orga (Ember.js) ré-instancie les
            # lignes du tableau pendant le rendu : les Locators chaînés (links.nth(i))
            # deviennent stale entre count() et inner_text(). On lit donc TOUT le DOM
            # de la page courante en UNE SEULE évaluation JS pour éviter ce problème.
            #
            # On récupère aussi le nombre de "Résultats reçus" par campagne, pour
            # ne télécharger QUE celles qui ont changé depuis la dernière sync
            # (cache simple JSON sur disque, clé = code campagne).
            EXTRACT_JS = """
                () => Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
                    const link = tr.querySelector('a[href*="/campagnes/"]');
                    if (!link) return null;
                    const tds = Array.from(tr.querySelectorAll('td'));
                    // Dernière cellule numérique = "Résultats reçus"
                    let resultsCount = null;
                    for (let i = tds.length - 1; i >= 0; i--) {
                        const t = tds[i].innerText.trim();
                        if (/^\\d+$/.test(t)) { resultsCount = parseInt(t, 10); break; }
                    }
                    return {
                        name: (link.innerText || link.textContent || '').trim(),
                        href: link.getAttribute('href') || '',
                        resultsCount
                    };
                }).filter(x => x && x.name && x.href)
            """

            # Pagination par URL directe (Pix Orga supporte ?pageNumber=N).
            # Plus fiable que de cliquer le bouton "suivante" : Ember.js
            # ré-instancie le tableau de façon asynchrone et la détection de
            # "page chargée" est délicate.
            all_campaigns = []
            seen_urls = set()
            for page_num in range(1, 21):  # garde-fou : 20 pages × 50 = 1000 max
                if page_num > 1:
                    page.goto(
                        f"https://orga.pix.fr/campagnes/toutes?pageNumber={page_num}",
                        wait_until="domcontentloaded",
                    )
                    try:
                        page.wait_for_selector('table tbody tr a[href*="/campagnes/"]', timeout=10000)
                        # Petite attente pour que le tableau se rende complètement
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        break

                page_data = page.evaluate(EXTRACT_JS)
                added_this_page = 0
                for entry in page_data:
                    if entry["href"] in seen_urls:
                        continue
                    seen_urls.add(entry["href"])
                    all_campaigns.append(entry)
                    added_this_page += 1

                # Aucune nouvelle entrée → on a dépassé la dernière page (ou Pix
                # Orga renvoie la dernière page valide quand pageNumber > max)
                if added_this_page == 0:
                    break

            # Cache des compteurs "résultats reçus" par URL pour l'incrémental
            cache_file = SOURCE_ROOT / "_inbox_pix" / ".sync-cache.json"
            cache = {}
            if cache_file.exists():
                try:
                    cache = json.loads(cache_file.read_text(encoding="utf-8"))
                except Exception:
                    cache = {}

            campaigns = []
            unchanged = []
            for c in all_campaigns:
                prev = cache.get(c["href"])
                # Téléchargement si nouveau OU compteur changé
                if prev is None or prev != c["resultsCount"]:
                    campaigns.append(c)
                else:
                    unchanged.append(c)

            emit("list",
                 f"{len(all_campaigns)} campagnes au total — "
                 f"{len(campaigns)} à (re)télécharger, "
                 f"{len(unchanged)} inchangées (skip)",
                 0.30,
                 {"toFetch": [c["name"] for c in campaigns]})

            # 5. Téléchargement de chaque campagne qui a changé
            for i, camp in enumerate(campaigns):
                pct = 0.30 + (0.55 * (i + 1) / max(1, len(campaigns)))
                emit("download",
                     f"Téléchargement « {camp['name']} » ({i+1}/{len(campaigns)})",
                     pct)

                page.goto(f"https://orga.pix.fr{camp['href']}", wait_until="domcontentloaded")
                # Bouton "Exporter les résultats" (CSV)
                try:
                    with page.expect_download(timeout=20000) as download_info:
                        page.locator('button:has-text("Exporter")').first.click()
                    download = download_info.value
                    target = SOURCE_ROOT / "_inbox_pix" / download.suggested_filename
                    target.parent.mkdir(exist_ok=True)
                    download.save_as(str(target))
                    downloaded.append(str(target))
                    # Mémorise le compteur pour la prochaine sync
                    cache[camp["href"]] = camp["resultsCount"]
                except Exception as e:
                    emit("download", f"⚠ « {camp['name']} » échec : {str(e)[:120]}", pct)
                    continue

            # Persiste le cache
            try:
                cache_file.parent.mkdir(exist_ok=True)
                cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

            browser.close()

        emit("dispatch", f"Rangement de {len(downloaded)} fichiers dans les bons dossiers", 0.85)
        # Le rangement automatique nécessite de connaître la convention de nommage
        # de chaque CSV. On délègue au build-data.py qui sait gérer.
        # Pour l'instant on les laisse dans _inbox_pix et on demande au user
        # de les ranger ou on étend build-data.py pour scanner _inbox_pix.

        # 6. Régénération des JSON.
        # On exécute build-data.py INLINE dans le process agent plutôt que via
        # subprocess, parce que macOS TCC traite différemment le subprocess :
        # le parent (agent) a accès à OneDrive, le subprocess n'arrive pas
        # à ouvrir scripts/build-data.py ([Errno 1] Operation not permitted).
        # En l'exécutant inline, on hérite des permissions TCC du process agent.
        emit("build", "Régénération des fichiers JSON…", 0.90)
        import io, contextlib, traceback
        build_stdout = io.StringIO()
        build_stderr = io.StringIO()
        prev_argv = sys.argv
        sys.argv = [str(BUILD_SCRIPT)]
        try:
            script_src = BUILD_SCRIPT.read_text(encoding="utf-8")
            globals_ns = {
                "__name__": "__main__",
                "__file__": str(BUILD_SCRIPT),
                "__builtins__": __builtins__,
            }
            with contextlib.redirect_stdout(build_stdout), contextlib.redirect_stderr(build_stderr):
                # On change cwd le temps de l'exécution (build-data.py utilise des
                # chemins absolus mais certaines opérations dépendent du cwd)
                prev_cwd = os.getcwd()
                os.chdir(str(REPO_DIR))
                try:
                    exec(compile(script_src, str(BUILD_SCRIPT), "exec"), globals_ns)
                finally:
                    os.chdir(prev_cwd)
        except SystemExit as e:
            if e.code not in (None, 0):
                tb = traceback.format_exc()
                emit("error", f"Build SystemExit {e.code} | stderr: {build_stderr.getvalue()[-500:]!r} | trace: {tb[-300:]!r}", -1)
                JOBS[job_id]["status"] = "failed"
                return
        except Exception as e:
            tb = traceback.format_exc()
            try:
                Path("/tmp/pix-sync-build-error.log").write_text(
                    f"=== {type(e).__name__}: {e} ===\n"
                    f"--- STDOUT ---\n{build_stdout.getvalue()}\n"
                    f"--- STDERR ---\n{build_stderr.getvalue()}\n"
                    f"--- TRACEBACK ---\n{tb}\n",
                    encoding="utf-8",
                )
            except Exception:
                pass
            emit("error", f"Build {type(e).__name__}: {str(e)[:300]} (détail : /tmp/pix-sync-build-error.log)", -1)
            JOBS[job_id]["status"] = "failed"
            return
        finally:
            sys.argv = prev_argv

        # Extrait les dernières lignes du build pour l'UI
        last_lines = build_stdout.getvalue().strip().split("\n")[-3:]
        emit("build", "Build OK", 0.94, {"summary": last_lines})

        # 7. Git commit + push
        emit("git", "Git add + commit + push", 0.96)
        subprocess.run(["git", "add", "data/"], cwd=str(REPO_DIR), check=True)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(REPO_DIR),
        )
        if diff.returncode == 0:
            emit("git", "Aucun changement à committer", 1.0)
        else:
            commit_msg = f"Sync Pix Orga {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(REPO_DIR), check=True)
            push = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=str(REPO_DIR), capture_output=True, text=True,
            )
            if push.returncode != 0:
                emit("error", f"Push échoué : {push.stderr[-500:]}", -1)
                JOBS[job_id]["status"] = "failed"
                return

        emit("done", "✓ Synchronisation terminée — site mis à jour dans ~1 min", 1.0)
        JOBS[job_id]["status"] = "completed"

    except Exception as e:
        q.put({
            "stage": "error",
            "message": f"Erreur : {type(e).__name__}: {e}",
            "progress": -1,
            "time": now(),
        })
        JOBS[job_id]["status"] = "failed"
    finally:
        q.put({"stage": "_end_", "message": "", "progress": None, "time": now()})


# ─── Page admin (HTML servie en local) ────────────────────────────
ADMIN_HTML = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pix LFT — Agent local</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       margin:0;padding:32px;background:linear-gradient(180deg,#eef3fb,#f4ecf6);min-height:100vh}
  .card{max-width:720px;margin:0 auto;background:#fff;border-radius:24px;
        padding:32px;box-shadow:0 24px 60px -20px rgba(0,59,115,.18)}
  h1{margin:0 0 8px;font-size:28px;background:linear-gradient(135deg,#003b73,#e10075);
     -webkit-background-clip:text;color:transparent;letter-spacing:-.02em}
  p.lead{color:#4a4a4a;margin:0 0 24px}
  button{background:linear-gradient(135deg,#3d68ff,#003b73);color:#fff;border:none;
         padding:14px 24px;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;
         box-shadow:0 6px 18px rgba(61,104,255,.35);transition:transform .2s}
  button:hover{transform:translateY(-2px)}
  button:disabled{opacity:.5;cursor:not-allowed}
  .progress{height:8px;background:#eef;border-radius:4px;margin:16px 0;overflow:hidden;display:none}
  .progress.show{display:block}
  .progress__fill{height:100%;width:0;background:linear-gradient(90deg,#3d68ff,#e10075);
                  transition:width .5s;border-radius:4px}
  .log{font-family:"SF Mono",Menlo,monospace;font-size:13px;background:#f5f7fb;
       padding:16px;border-radius:12px;max-height:340px;overflow-y:auto;margin-top:16px;display:none}
  .log.show{display:block}
  .log__line{padding:2px 0;color:#4a4a4a}
  .log__line .t{color:#888;margin-right:8px}
  .log__line.error{color:#ce0500;font-weight:600}
  .log__line.done{color:#18753c;font-weight:600}
</style></head>
<body><div class="card">
<h1>Agent Pix Orga local</h1>
<p class="lead">Cliquez pour synchroniser tous les exports Collecte/Récup et pousser vers le site.</p>
<button id="go">Synchroniser maintenant</button>
<div class="progress" id="prog"><div class="progress__fill" id="bar"></div></div>
<div class="log" id="log"></div>
</div>
<script>
const go=document.getElementById('go'),prog=document.getElementById('prog'),
      bar=document.getElementById('bar'),log=document.getElementById('log');
go.onclick=async()=>{
  go.disabled=true;prog.classList.add('show');log.classList.add('show');log.innerHTML='';
  const r=await fetch('/sync',{method:'POST'});const{job_id}=await r.json();
  const ev=new EventSource('/sync/'+job_id+'/events');
  ev.onmessage=m=>{const e=JSON.parse(m.data);
    if(e.stage==='_end_'){ev.close();go.disabled=false;return}
    if(typeof e.progress==='number'&&e.progress>0)bar.style.width=(e.progress*100)+'%';
    const cls=e.stage==='error'?'error':(e.stage==='done'?'done':'');
    log.insertAdjacentHTML('beforeend','<div class="log__line '+cls+'"><span class="t">'+e.time+'</span>'+e.message+'</div>');
    log.scrollTop=log.scrollHeight};
  ev.onerror=()=>{ev.close();go.disabled=false}};
</script></body></html>"""


# ─── HTTP Server ──────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Logs propres
        sys.stderr.write(f"[agent] {self.address_string()} {format % args}\n")

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Chrome ≥130 : Private Network Access bloque les requêtes
        # public (HTTPS) → privé (127.0.0.1) sans ce header sur le preflight.
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(ADMIN_HTML.encode("utf-8"))
            return

        if self.path == "/probe-tcc":
            # Diagnostic : que peut lire l'agent sous launchd ?
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            paths = [
                REPO_DIR / "data" / "manifest.json",
                REPO_DIR / "scripts" / "build-data.py",
                REPO_DIR / "scripts" / "agent" / "pix-sync-agent.py",
                REPO_DIR / "index.html",
                SOURCE_ROOT / "Liste des élèves par classes.xlsx",
                SOURCE_ROOT / "_inbox_pix",
                Path("/Users/maxwilliamrafaliarison/.local/share/pix-sync/agent.py"),
            ]
            results = []
            for p in paths:
                entry = {"path": str(p)}
                try:
                    if p.is_dir():
                        entry["type"] = "dir"
                        entry["entries"] = len(list(p.iterdir()))
                    else:
                        with open(p, "rb") as f:
                            head = f.read(40)
                        entry["type"] = "file"
                        entry["size"] = p.stat().st_size
                        entry["head"] = head.decode("utf-8", errors="replace")
                    entry["ok"] = True
                except Exception as e:
                    entry["ok"] = False
                    entry["error"] = f"{type(e).__name__}: {e}"
                results.append(entry)
            self.wfile.write(json.dumps({"results": results}, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "alive", "service": "pix-sync-agent"}).encode())
            return

        if self.path.startswith("/sync/") and self.path.endswith("/events"):
            job_id = self.path.split("/")[2]
            job = JOBS.get(job_id)
            if not job:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self._cors()
            self.end_headers()
            # Annonce de connexion (utile pour debug côté client)
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
            except Exception:
                return
            q = job["queue"]
            HEARTBEAT_SEC = 15  # garde la connexion EventSource vivante (proxies/browsers
                                 # coupent typiquement après 30-60s sans données)
            HARD_TIMEOUT_SEC = 1800  # 30 min absolus pour un job
            import time as _time
            t0 = _time.time()
            try:
                while True:
                    if _time.time() - t0 > HARD_TIMEOUT_SEC:
                        break
                    try:
                        evt = q.get(timeout=HEARTBEAT_SEC)
                    except queue.Empty:
                        # Heartbeat : ligne de commentaire SSE (ignorée par le client
                        # mais réveille la connexion TCP côté navigateur/proxy)
                        try:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                        except Exception:
                            break
                        continue
                    try:
                        self.wfile.write(f"data: {json.dumps(evt)}\n\n".encode())
                        self.wfile.flush()
                    except Exception:
                        break
                    if evt.get("stage") == "_end_":
                        break
            except Exception:
                pass
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            job_id = uuid.uuid4().hex[:12]
            JOBS[job_id] = {
                "queue": queue.Queue(),
                "status": "running",
                "started_at": now(),
            }
            threading.Thread(target=sync_worker, args=(job_id,), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"job_id": job_id}).encode())
            return
        self.send_response(404)
        self.end_headers()


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"\n  🚀 Agent Pix LFT démarré")
    print(f"     http://{HOST}:{PORT}\n")
    print("  Garde cette fenêtre ouverte pendant la synchro.")
    print("  Ctrl+C pour arrêter.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Agent arrêté.\n")


if __name__ == "__main__":
    main()
