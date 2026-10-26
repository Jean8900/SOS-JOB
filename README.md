# SOS-JOB
Customable script to help you to knowning the trend of job market and candidate more efficiently (choice of jobs, LM &amp; CV)

## Commandes

```powershell
.\companies.ps1                # liste des entreprises par métier (ouvre un .html)
.\companies.ps1 "AI Engineer"  # métier au choix
.\run.ps1                      # scrape -> filtre -> TUI -> génère les CV
```
Points d'entrée : [`list_companies.py`](list_companies.py), [`run.py`](run.py).

## Critères

Ça se modifie dans [`config/criteria.yaml`](config/criteria.yaml) (entreprises suivies : [`config/companies.yaml`](config/companies.yaml)).

Logique du filtre ([`src/matcher.py`](src/matcher.py)) :
- **entre catégories** (lieu / contrat / métier / stack / séniorité) = **ET** strict
- **dans une même catégorie** (ex: plusieurs métiers dans `professions:`) = **OU**

## Technique

- Point d'entrée : l'API publique JSON `api.welcometothejungle.com` ([`src/scraper.py`](src/scraper.py)) — c'est celle que le site utilise lui-même pour afficher les offres, donc pas de souci particulier à l'utiliser.
- Recherche élargie (tous métiers, toutes entreprises) : même API, interrogée **sans filtre entreprise**, avec un mot-clé ([`src/company_finder.py`](src/company_finder.py)).
- Ce qui marche : interroger cette API avec un mot-clé, même en paginant jusqu'au bout — c'est un usage normal de la recherche du site, pas un contournement.
- Ce qui NE marche PAS : scraper directement la page web `welcometothejungle.com/fr/companies` (l'annuaire brut, sans passer par une recherche) — bloquée par un pare-feu anti-bot (403 CloudFront), et volontairement non contournée.

## Roadmap

Voir [`TODO.md`](TODO.md). Suggestions et contributions bienvenues, libre d'ajouter/modifier.
