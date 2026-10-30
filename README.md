# SOS-JOB
Customable script to help you to knowning the trend of job market and candidate more efficiently (choice of jobs, LM &amp; CV)

## Commandes

```powershell
.\companies.ps1                # liste des entreprises par métier (ouvre un .html)
.\companies.ps1 "AI Engineer"  # métier au choix
.\run.ps1                      # tous les sites actifs -> filtre -> TUI -> génère CV + LM
.\run.ps1 sites                # liste à cocher pour choisir les sites à interroger
.\run.ps1 all                  # pas de TUI, prend toutes les offres filtrées
.\run.ps1 force                # régénère les LM même si déjà archivées
.\run.ps1 sites all force      # combinables, dans n'importe quel ordre
.\apply.ps1                    # copilot de candidature (voir "Lot copilot")
.\suivi.ps1                    # génère output/suivi.xlsx (une ligne par candidature). Tape une info dans « Mise à jour » : à la prochaine génération elle passe devant Notes ("update // historique"). Tes lignes ajoutées à la main sont conservées. Nécessite Excel/LibreOffice, ou import dans Google Sheets
.\archive_lm.ps1                # déplace toutes les LM générées vers l'archive (écrase les doublons)
```
Points d'entrée : [`list_companies.py`](list_companies.py), [`run.py`](run.py), [`archive_lm.py`](archive_lm.py).

## Sources (lot 1)

Chaque site vit dans [`src/connectors/<slug>.py`](src/connectors), convertit ses données brutes en [`Offer`](src/offer.py) (schéma unique, voir ce fichier), et expose `fetch(max_results) -> list[Offer]`. Liste et activation : [`input/sites.yaml`](input/sites.yaml).

| Site | Statut | Détail |
|---|---|---|
| Welcome to the Jungle | ✅ actif | entreprises suivies + recherche élargie (API publique) |
| Free-Work | ✅ actif | API JSON interne (`/api/job_postings`), pas d'anti-bot rencontré |
| Choisir le service public | ✅ actif | API REST custom WordPress ; **limite connue** : le filtre mot-clé serveur n'a pas d'effet mesuré, le filtrage se fait entièrement côté `matcher.py` |
| Inria | ✅ actif | formulaire HTML server-rendu (session + jeton CSRF) ; une requête = un mot-clé (le site traite une phrase en ET, pas en OU) |
| CNRS | ✅ actif | idem Inria (POST direct, pas de session nécessaire ici) |
| Station F | ✅ actif | plateforme WelcomeKit/Algolia ; la clé de recherche n'est injectée que côté client (JS), donc navigateur headless (Playwright, voir `src/connectors/browser.py`) au lieu d'appeler l'API directement |
| Jobs that make sense | ✅ actif | Nuxt 3, données sérialisées côté serveur -- illisible en HTML brut, même principe Playwright ; le paramètre `query` n'a pas d'effet de filtre mesurable, tri entièrement côté `matcher.py` |
| Greenhouse / Lever / Ashby | ✅ actif (lot 1.5) | APIs publiques par entreprise, sans clé ni anti-bot. Pas de recherche globale : les entreprises viennent de WTJ (`discovery_queries` dans [`input/ats_companies.yaml`](input/ats_companies.yaml), par défaut « AI Engineer »), puis on teste si leur nom correspond à un board sur l'un des 3 ATS (~20 % retrouvées, les autres utilisent un ATS maison/Workday/etc.). Résultat en cache dans `output/ats_cache.json` (1re exécution ~3 min, ensuite instantané). Max 5 offres par entreprise (celles dont le titre colle aux métiers d'abord). Ajout/correction manuelle possible via `companies:` dans le même fichier. **Limite connue** : Greenhouse n'expose pas le type de contrat, déduit du titre (stage/alternance, sinon CDI). Code commun : [`src/connectors/ats.py`](src/connectors/ats.py) |
| aijobs.net (Foorilla, rebrandé en octobre 2026) | ❌ bloqué | le site a été refondu : nom d'entreprise tronqué (`@ I...`) et export en masse réservés aux comptes connectés -- plus un problème de rendu JS mais une vraie barrière d'inscription, pas de création de compte automatique |

Station F et Jobs that make sense utilisent un navigateur headless (Playwright) plutôt qu'un appel HTTP direct -- `pip install -r requirements.txt` puis, une seule fois, `playwright install chromium`. aijobs.net est mis de côté (lot 1.5, on y reviendra peut-être) : il reste dans `input/sites.yaml` (`enabled: false`), choisissable via le suffixe `sites`, mais aucun module `src/connectors/*.py` n'existe tant que le blocage n'est pas levé. ChooseYourBoss (pare-feu anti-bot Cloudflare, 403 dès la requête de base) est passé en lot 2 : alerte email côté site, voir [`TODO.md`](TODO.md).

Par défaut, une LM déjà présente dans `output/LM/archive/` n'est pas régénérée — c'est voulu, pour ne pas écraser une lettre déjà relue/envoyée. Utilise `force` pour passer outre. `output/LM/` : `tex/` et `pdf/` pour le lot du jour, `archive/{tex,pdf}/` pour tout ce qui a déjà été traité.

## Entrées modifiables

Tout ce que tu peux régler toi-même vit dans [`input/`](input/README.md) :
- Critères de matching → [`input/criteria.yaml`](input/criteria.yaml)
- Entreprises suivies → [`input/companies.yaml`](input/companies.yaml)
- Colonnes du tableau interactif → [`input/table_columns.yaml`](input/table_columns.yaml)
- Ton CV source → [`input/CV_originel.tex`](input/CV_originel.tex)
- Ta signature pour les LM (facultatif) → [`input/LM/Signature.png`](input/LM/Signature.png)

Logique du filtre ([`src/matcher.py`](src/matcher.py)) :
- **entre catégories** (lieu / contrat / métier / stack / séniorité) = **ET** strict
- **dans une même catégorie** (ex: plusieurs métiers dans `professions:`) = **OU**

## Technique

- Point d'entrée : l'API publique JSON `api.welcometothejungle.com` ([`src/scraper.py`](src/scraper.py)) — c'est celle que le site utilise lui-même pour afficher les offres, donc pas de souci particulier à l'utiliser.
- Recherche élargie (tous métiers, toutes entreprises) : même API, interrogée **sans filtre entreprise**, avec un mot-clé ([`src/company_finder.py`](src/company_finder.py)).
- Ce qui marche : interroger cette API avec un mot-clé, même en paginant jusqu'au bout — c'est un usage normal de la recherche du site, pas un contournement.
- Ce qui NE marche PAS : scraper directement la page web `welcometothejungle.com/fr/companies` (l'annuaire brut, sans passer par une recherche) — bloquée par un pare-feu anti-bot (403 CloudFront), et volontairement non contournée.
- LM : générées par Claude Code en non-interactif (`claude -p`, abonnement Pro, pas de clé API séparée) — voir [`src/lm_builder.py`](src/lm_builder.py) et [`src/LM/README.md`](src/LM/README.md). Piège Windows : le prompt doit être envoyé par **stdin**, pas en argument CLI (`claude.cmd` passe par `cmd.exe`, qui tronque un argument multi-lignes au premier saut de ligne).

## Lot copilot

Le goulot n'est plus la collecte ni la génération, mais le geste de candidature (ouvrir la bonne page, uploader CV et LM). `.\apply.ps1` parcourt les offres générées une à une : Chrome sur l'offre (moitié gauche), Explorateur sur le dossier d'upload (quart haut droit, `CV_` / `LM_<nom>.pdf` écrasés à chaque offre), tableau de bord HTML d'avancement (quart bas droit : %, reste, par site). Raccourcis globaux, quelle que soit la fenêtre active : `Ctrl+Alt+→` candidaté, `Ctrl+Alt+←` précédente, `Ctrl+Alt+S` passer, `Ctrl+Alt+Q` quitter. Statuts enregistrés dans `output/applications.json` (suivi, pas de doublon). Tu uploades toi-même : rien n'est soumis automatiquement. Réglages : [`input/copilot.yaml`](input/copilot.yaml).

> **Temporaire** : `disable_filters: true` dans [`input/criteria.yaml`](input/criteria.yaml) désactive tout le filtrage (aucune offre des 7 sites du lot 1 ne passait le filtre strict avec 5 offres/site). À remettre à `false` une fois le copilot en place.

## Suivi des candidatures (début)

Chaque Ctrl+Alt+→ du copilot enregistre la candidature dans `output/applications.json` (date de la première candidature conservée). `.\suivi.ps1` en tire `output/suivi.xlsx` : une ligne par offre candidatée, une colonne « Mise à jour » où tu tapes le dernier état (entretien, refus...) qui passe devant l'historique de Notes (`update // legacy`), et tes propres lignes hors outil sont conservées. Tout reste local. Excel ou LibreOffice requis (ou import dans Google Sheets).

## Roadmap

Voir [`TODO.md`](TODO.md). Suggestions et contributions bienvenues, libre d'ajouter/modifier.
