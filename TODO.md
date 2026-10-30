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

## Lot copilot — assistant de candidature (priorité)
- [x] Dossier d'upload (`CV_` + `LM_<nom>.pdf`, mêmes noms, contenus différents) et fichier d'état des candidatures
- [x] `apply.ps1` : Chrome / Explorateur / tableau de bord HTML disposés à l'écran, raccourcis globaux Ctrl+Alt, upload manuel
- [x] Suivi : `suivi.ps1` génère `output/suivi.xlsx` (Date, Entreprise, Poste, Site, Lien, Notes) depuis les candidatures validées
- [x] Suivi : colonne « Mise à jour » fusionnée devant les Notes (`update // legacy`), lignes manuelles conservées
- [ ] Suivi : colonnes réponse / relance J+7, pré-remplies via Gmail en lecture seule
- [ ] ATS : valider les correspondances entreprise -> board (faux positifs possibles, ex. « vinci » sur Ashby) + liste d'exclusions
- [ ] Plafond `max_results` : répartir par site (avec `disable_filters`, les derniers sites sont coupés)
- [ ] Remettre `disable_filters: false` (criteria.yaml) et relever `max_results_per_site`

## MVP3 — Data visualisation
- [ ] Géocodage des localisations d'offres (ville/région → coordonnées)
- [ ] Carte de France interactive des offres de la semaine (nouvelles offres par région/métier)
- [ ] Suivi de tendance semaine après semaine (volume, stack, localisation)

## MVP4 — App persistante
- [ ] Stockage persistant réel (SQLite) des offres + candidatures dans le temps (plus de limite "100 lignes/semaine")
- [ ] Interface web qui remplace le TUI, affiche LM + diff du CV par candidature
- [ ] Historique consultable : qui a été adressé, quand, avec quelle version de CV/LM

## MVP5 — App mobile + multi-plateformes + notifications
- [x] Connecteurs multi-sites lot 1 : schéma [`Offer`](src/offer.py) unique, 7 sites actifs (WTJ, Free-Work, Choisir le service public, Inria, CNRS, Station F, Jobs that make sense) — voir [`README.md`](README.md#sources-lot-1) pour le détail et les 2 sites encore bloqués
- [x] Débloquer Station F / Jobs that make sense via navigateur headless (Playwright, `src/connectors/browser.py`) une fois l'extension Claude in Chrome connectée pour l'analyse
- [x] Lot 1.5 : Lever/Greenhouse/Ashby — `entreprise -> identifiant ATS` découvert automatiquement depuis la liste WTJ (voir [`input/ats_companies.yaml`](input/ats_companies.yaml))
- [ ] Lot 1.5 (mis de côté, on y reviendra peut-être) aijobs.net/Foorilla : bloqué par une barrière d'inscription (nom d'entreprise tronqué, export réservé aux comptes connectés) depuis la refonte d'octobre 2026 -- pas de piste sans créer de compte
- [ ] Lot 2 (alertes email) : ChooseYourBoss (bloqué Cloudflare, alerte configurée sur le site, réception par mail), Apec, HelloWork, Cadremploi, talent.io
- [ ] Dédoublonnage inter-sources (une même offre peut apparaître sur plusieurs sites)
- [ ] Notifications programmées (heure fixe) ou instantanées à l'apparition d'une offre
- [ ] App mobile (ou PWA) pour candidater en un geste depuis le téléphone
