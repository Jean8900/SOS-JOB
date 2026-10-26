# SOS-JOB
Customable script to help you to knowning the trend of job market and candidate more efficiently (choice of jobs, LM &amp; CV)

## Commandes

```powershell
.\companies.ps1                # liste des entreprises par métier (ouvre un .html)
.\companies.ps1 "AI Engineer"  # métier au choix
.\run.ps1                      # scrape -> filtre -> TUI -> génère CV + LM
.\run.ps1 all                  # pas de TUI, prend toutes les offres filtrées
.\run.ps1 force                # régénère les LM même si déjà archivées
.\run.ps1 all force            # combinables, dans n'importe quel ordre
.\archive_lm.ps1                # déplace toutes les LM générées vers l'archive (écrase les doublons)
```
Points d'entrée : [`list_companies.py`](list_companies.py), [`run.py`](run.py), [`archive_lm.py`](archive_lm.py).

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

## Roadmap

Voir [`TODO.md`](TODO.md). Suggestions et contributions bienvenues, libre d'ajouter/modifier.
