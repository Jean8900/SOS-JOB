# SOS-JOB — Roadmap

Chaque MVP est utilisable seul. On ne passe au suivant que si le précédent tourne vraiment.

## MVP1 — Scraper + matching + CV adaptés (local, terminal)
- [x] Généraliser le scraper WTJ : liste d'entreprises suivies (`input/companies.yaml`) + recherche élargie par critères, dédoublonnage par slug
- [x] Filtre strict selon `input/criteria.yaml` (localisation, contrat, métier, stack, séniorité) → table de résultats, max 100 lignes
- [x] TUI `textual` (cases à cocher) + `cv_builder.py` : édite le header du `.tex` de référence et compile un PDF par offre cochée (latexmk)

## MVP2 — Lettres de motivation
- [x] Génération LM via Claude Code (`claude -p`, abonnement Pro, pas d'API) → `output/LM/`, détails dans [`src/LM/`](src/LM/README.md)
- [ ] Historique des LM passées comme guide de style (moins de review quand l'historique s'accumule)
- [ ] Boucle de review : demande de validation explicite si peu d'historique, sinon génération directe

## MVP3 — Data visualisation
- [ ] Géocodage des localisations d'offres (ville/région → coordonnées)
- [ ] Carte de France interactive des offres de la semaine (nouvelles offres par région/métier)
- [ ] Suivi de tendance semaine après semaine (volume, stack, localisation)

## MVP4 — App persistante
- [ ] Stockage persistant réel (SQLite) des offres + candidatures dans le temps (plus de limite "100 lignes/semaine")
- [ ] Interface web qui remplace le TUI, affiche LM + diff du CV par candidature
- [ ] Historique consultable : qui a été adressé, quand, avec quelle version de CV/LM

## MVP5 — App mobile + multi-plateformes + notifications
- [ ] Connecteurs multi-sites (WTJ, LinkedIn, Indeed...) avec dédoublonnage best-effort entre plateformes
- [ ] Notifications programmées (heure fixe) ou instantanées à l'apparition d'une offre
- [ ] App mobile (ou PWA) pour candidater en un geste depuis le téléphone
