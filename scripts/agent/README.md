# Agent local Pix LFT — Synchronisation automatique

Agent Python qui automatise la récupération des exports Pix Orga
et la mise à jour du site PIX LFT en un clic depuis le dashboard prof.

> **Sécurité** : tes identifiants Pix Orga sont stockés UNIQUEMENT dans le
> Keychain macOS (chiffrés par le système), jamais dans un fichier ni transmis
> via le navigateur. L'agent écoute sur 127.0.0.1 (localhost) — non accessible
> depuis le réseau.

## Setup une fois

```bash
cd /chemin/vers/PIX/site/scripts/agent

# 1. Installation des dépendances Python (Playwright + Chromium)
./install.sh

# 2. Stockage des identifiants Pix Orga dans le Keychain
./setup-keychain.sh
```

## Utilisation

### Option 1 — Bouton dans le dashboard prof (recommandé)

1. **Démarrer l'agent local** : double-clique sur `start.command` (ou lance-le depuis un terminal). Une fenêtre s'ouvre avec le message :

   ```
   🚀 Agent Pix LFT démarré
      http://127.0.0.1:7777
   ```

   Garde cette fenêtre ouverte pendant la synchro.

2. **Connexion au site** : va sur https://lyceefrancaisdetananarive.github.io/PIX/, connecte-toi avec ton code prof (BUGATTI).

3. **Bouton "Synchroniser Pix Orga"** apparaît en haut à droite (visible uniquement pour toi). Clique dessus.

4. **Modal de progression** s'ouvre avec :
   - Barre de progression de 0 % à 100 %
   - Logs en direct de chaque étape (login, listing campagnes, téléchargement, build, push…)
   - Indication finale ✓ ou ✗

5. **C'est fini** : le site GitHub Pages est mis à jour en ~1 minute après le push.

### Option 2 — Page admin locale

Quand l'agent tourne, ouvre dans ton navigateur :
**http://127.0.0.1:7777/**

Page minimaliste avec un seul bouton, identique au comportement du site mais sans avoir besoin d'aller sur le dashboard public.

### Option 3 — En ligne de commande

```bash
curl -X POST http://127.0.0.1:7777/sync
```

## Que fait l'agent exactement ?

1. **Lecture du Keychain** → email + mot de passe Pix Orga
2. **Lancement Chromium headless** (invisible)
3. **Connexion à orga.pix.fr** (formulaire login)
4. **Récupération de la liste des campagnes** Collecte et Récup
5. **Téléchargement de chaque export CSV** dans `_inbox_pix/`
6. **Régénération des JSON** (`build-data.py`)
7. **Git add / commit / push** sur le repo GitHub PIX
8. **Site GitHub Pages** rebuilt automatiquement (~1 min)

## Désinstallation / changement de mot de passe

```bash
# Supprimer les identifiants Keychain
security delete-generic-password -s pix-lft-sync -a pix-orga
security delete-generic-password -s pix-lft-sync -a pix-orga-email

# Relancer le setup
./setup-keychain.sh
```

## Limites connues

- Le Mac doit être **allumé** au moment de la sync.
- Une mise à jour de l'UI Pix Orga peut casser temporairement le sélecteur Playwright.
- Une fois par jour ou à la demande est OK ; éviter les syncs > 1×/heure (risque détection).
- Les CSV téléchargés vont d'abord dans `_inbox_pix/` ; pour l'instant le rangement
  automatique dans les bons dossiers groupes est à faire (extension de `build-data.py` à venir).

## Dépannage

| Problème | Solution |
|---|---|
| "Identifiants introuvables" | `./setup-keychain.sh` puis réessayer |
| "Playwright non installé" | `./install.sh` puis `playwright install chromium` |
| Bouton bleu absent du dashboard | Tu n'es pas connecté avec **BUGATTI** (compte Max). |
| "Agent local non lancé" dans la modal | Double-clique sur `start.command` puis réessayer. |
| Erreur de login Pix Orga | Vérifie tes identifiants : `./setup-keychain.sh` pour les mettre à jour. |
