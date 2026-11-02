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

## Remplissage de formulaires (Chrome / Edge)
- [x] Extension + programme local : Ctrl+Alt+Espace, profil perso `input/form_profile.yaml` (hors git), démarrage automatique (`.\fill.ps1 install`)
- [x] Étapes multiples (un seul Ctrl+Alt+Espace, arrêt avant l envoi)
- [ ] Cases à cocher, upload de fichiers (volontairement manuel)
- [ ] Extension : icône + état (programme local arrêté), packaging pour éviter l'avertissement « mode développeur »
- [x] Tournée de connexion (`.\login.ps1`) : sites dans `input/login_sites.yaml`, état dans `output/logins.json`
- [ ] Commande « ouvrir l'offre dans ton Chrome connecté » (étape 2 : le seul geste humain devient l'upload, le captcha éventuel et l'envoi)
- [ ] Vision « mode comptes guidé » : une commande qui ouvre un à un les sites où il faut un compte, préremplit l'e-mail et les champs non secrets, laisse le gestionnaire de mots de passe générer et enregistrer le mot de passe (l'utilisateur ne le voit ni ne le tape), attend un raccourci « fait » et passe au site suivant ; l'IA n'y touche jamais aux identifiants. Pas de création de comptes 100 % automatique : e-mail de vérification, captchas et conditions d'utilisation des sites l'empêchent.
- [ ] `apply.ps1` (Ctrl+Alt+F, Playwright) et l'extension dupliquent la lecture des champs (`src/formfill.py` / `extension/content.js`) : n'en garder qu'une

## International / langues
- [x] Détection fr/en de l'offre (comptage de mots-outils) -> CV et LM dans la langue de l'offre
- [ ] Lieux étrangers à autoriser (`criteria.yaml`), localisation trop longue dans le header du CV (ex. « PARIS OFFICE or REMOTE FROM FRANCE »)
- [ ] Offres sans description : classer aussi sur le lieu / la source

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
