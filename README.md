# SOS-JOB
Customable script to help you to knowning the trend of job market and candidate more efficiently (choice of jobs, LM & CV)

## Commandes

```powershell
# Collecte, filtre, génération
.\companies.ps1                # liste des entreprises par métier (ouvre un .html)
.\companies.ps1 "AI Engineer"  # métier au choix
.\go.ps1                       # formulaire : critères, sites, nb d'offres -> connexion -> CV/LM + remplissage de bout en bout (envoi à ta main)
.\go.ps1 --record              # pareil, et filme l'écran du lancement au message de fin (output\demo\<horodatage>\go.mp4 ; exemple : docs/demo/go_demo.mp4)
.\run.ps1                      # tous les sites actifs -> filtre -> TUI -> génère CV + LM
.\run.ps1 sites                # liste à cocher pour choisir les sites à interroger
.\run.ps1 all                  # pas de TUI, prend toutes les offres filtrées
.\run.ps1 force                # régénère les LM même si déjà archivées
.\run.ps1 sites all force      # combinables, dans n'importe quel ordre
.\archive_lm.ps1               # déplace toutes les LM générées vers l'archive (écrase les doublons)

# Candidature
.\login.ps1                    # tournée de connexion : ouvre tes sites un à un, tu t'y connectes une fois (session gardée) ; --all repasse sur tous, --list montre l'état
.\fill.ps1 install             # lance le programme local de remplissage au démarrage de Windows (aussi `status`, `uninstall`) ; l'extension se charge une fois, voir extension/README.md
.\apply.ps1                    # copilot : parcourt les offres générées une à une (Chrome / Explorateur / tableau de bord), upload à la main
.\suivi.ps1                    # génère output/suivi.xlsx (une ligne par candidature ; tape une info dans « Mise à jour » : à la prochaine génération elle passe devant Notes ; tes lignes manuelles sont conservées ; Excel/LibreOffice, ou import dans Google Sheets)

# Candidatures en lot (WTJ, Apec, HelloWork, Free-Work) : un onglet par offre dans ton Chrome, remplissage jusqu'au bouton d'envoi, jamais cliqué
.\batch.ps1 prepare "technicien de maintenance" -n 10                 # lot WTJ : offres à candidature intégrée, une par entreprise, CV + LM générés (~8 min)
.\batch.ps1 --lot -n 3                                                # ouvre et remplit les 3 premières offres du lot WTJ
.\batch.ps1 --lot-file output\copilot\<site>_lot.json -n 3 --debug    # autre site : apec_lot.json, hellowork_lot.json, freework_lot.json
#   options : --generate (CV/LM manquants) · --skip k · --no-files (sans CV ni LM, pour déboguer les champs) · --wait s · --force-replay (plafond de 5 passages par offre et par jour) · --source

# Alertes email et démo
.\.venv\Scripts\python.exe alertes.py                         # mails d'alerte Apec + HelloWork (Gmail, lecture seule) -> output\copilot\alertes_lot.json, à remplir avec batch.ps1 --lot-file
.\demo.ps1                                                      # démo filmée + TNR : alertes, 3 offres WTJ « Software Engineer » (CV/LM, remplissage, jamais d'envoi), diaporama, verdict -> output\demo\<date>\demo.mp4 + rapport.md
.\demo.ps1 --no-video                                           # TNR seul (code de sortie 0 = vert)
```

Raccourcis globaux (marchent quelle que soit la fenêtre active) :
- `Ctrl+Alt+Espace` : remplit le formulaire de l'onglet actif dans Chrome ou Edge (extension + programme local).
- copilot (`apply.ps1`) : `Ctrl+Alt+→` candidaté, `Ctrl+Alt+←` précédente, `Ctrl+Alt+S` passer, `Ctrl+Alt+Q` quitter.
- tournée de connexion (`login.ps1`) : `Ctrl+Alt+→` connecté, `Ctrl+Alt+S` passer, `Ctrl+Alt+←` précédent, `Ctrl+Alt+Q` quitter.

Prérequis des lots : `.\fill.ps1 install`, l'extension chargée dans Chrome, tes sessions ouvertes (`.\login.ps1`) ; ne touche ni clavier ni souris pendant un lot (l'extension n'agit que sur l'onglet actif de la fenêtre au premier plan). Un nouveau site se développe avec le skill `site-onboarding` (10 offres réelles, boucle essai / correction), puis se teste avec la même commande `.\batch.ps1 --lot-file ...`. Banc d'essai isolé : `python extension\test\run_case.py <url>` (Chromium de test, jamais ta session).

Points d'entrée : [`list_companies.py`](list_companies.py), [`run.py`](run.py), [`archive_lm.py`](archive_lm.py), [`apply.py`](apply.py), [`suivi.py`](suivi.py), [`login.py`](login.py), [`fill.py`](fill.py), [`batch.py`](batch.py), [`wtj_prepare.py`](wtj_prepare.py).

## Sources (lot 1)

Chaque site vit dans [`src/connectors/<slug>.py`](src/connectors), convertit ses données brutes en [`Offer`](src/offer.py) (schéma unique) et expose `fetch(max_results) -> list[Offer]`. Liste et activation : [`input/sites.yaml`](input/sites.yaml). Les lots 1 et 1.5 servent à **trouver** des offres ; le lot 2 et la partie « Candidature » servent à **candidater**.

### Lot 1 : 7 sites actifs

| Site | Détail |
|---|---|
| Welcome to the Jungle | entreprises suivies + recherche élargie (API publique, [`src/scraper.py`](src/scraper.py), [`src/company_finder.py`](src/company_finder.py)) |
| Free-Work | API JSON interne (`/api/job_postings`), pas d'anti-bot rencontré |
| Choisir le service public | API REST custom WordPress ; **limite** : le filtre mot-clé serveur n'a pas d'effet mesuré, le filtrage se fait côté `matcher.py` |
| Inria | formulaire HTML server-rendu (session + jeton CSRF) ; une requête = un mot-clé (le site traite une phrase en ET) |
| CNRS | idem Inria (POST direct, pas de session) |
| Station F | plateforme WelcomeKit/Algolia ; clé de recherche injectée côté client, donc navigateur headless (Playwright, [`src/connectors/browser.py`](src/connectors/browser.py)) |
| Jobs that make sense | Nuxt 3, données sérialisées côté serveur, même principe Playwright ; le paramètre `query` n'a pas d'effet mesurable, tri côté `matcher.py` |

Station F et Jobs that make sense : `pip install -r requirements.txt` puis, une fois, `playwright install chromium`.

### Lot 1.5 : ATS par entreprise

- **Greenhouse / Lever / Ashby** (actifs) : APIs publiques par entreprise, sans clé ni anti-bot. Pas de recherche globale : les entreprises viennent de WTJ (`discovery_queries` dans [`input/ats_companies.yaml`](input/ats_companies.yaml), par défaut « AI Engineer »), puis on teste si leur nom correspond à un board sur l'un des 3 ATS (~20 % retrouvées). Résultat en cache dans `output/ats_cache.json` (1re exécution ~3 min). Max 5 offres par entreprise. Correction manuelle possible via `companies:` dans le même fichier. **Limite** : Greenhouse n'expose pas le type de contrat, déduit du titre. Code commun : [`src/connectors/ats.py`](src/connectors/ats.py).

### Lot 2 : alertes email (`alertes.py`)

aijobs.net / aijobs.com, Foorilla : utiles pour la collecte (international), à coder ; renvoient vers d'autres sites.

Apec, HelloWork : collecte par les alertes email (Gmail, API lecture seule : liens de suivi décodés, offres mises en lot puis remplies). Cadremploi : alerte à créer (voir [`TODO.md`](TODO.md)). Les 3 sites ont aussi la **candidature** (ci-dessous).

### Candidature (codé le 2026-11-02)

Niveau « WTJ » : pour chaque offre l'extension ouvre le formulaire, remplit les champs, pose le CV adapté et la LM, écrit un message personnalisé, répond aux questions OUI/NON, puis s'arrête avant l'envoi. Les offres qui renvoient chez l'employeur sont écartées (pas comptées en échec). Un envoi de test a été fait à la main par site, sur une offre hors profil, pour identifier le bouton qui envoie.

| Site | Liste d'offres | Parcours (fonction de [`extension/content.js`](extension/content.js)) | Bouton jamais cliqué | Statut |
|---|---|---|---|---|
| Welcome to the Jungle | `wtj_prepare.py` (offres `ats == "wkit"`, une par entreprise) | « Postuler » -> formulaire, identité, 2 questions, lettre, consentement, CV (`onWtj`) | « J'envoie ma candidature ! » | ✅ lot de 10 (8 formulaires prêts au premier essai) |
| Apec | relevées depuis ton Chrome (l'API refuse les scripts : 403), `typeCandidature == "EMAIL_ONLY"` | « Postuler » x2 -> « joindre uniquement un CV » -> import, LM ou message au recruteur (`apecNext`) | « Envoyer ma candidature » | ✅ 10 offres |
| HelloWork | page de recherche | lien « Postuler » -> formulaire, CV importé, message personnalisé (`helloNext`) | bouton noir « Postuler » | ✅ 10 offres |
| Free-Work | connecteur `free_work.py` / page de recherche | CV adapté mis par défaut, LM en document additionnel, message, questions (`freeNext`) | « Je postule » / « Apply to this job » | ✅ 4 offres internes validées, 1 hors site écartée |
| Cadremploi | — | formulaire sur la page ; le bouton du CV agit comme un envoi | « Postuler » du formulaire | ✅ import du CV OK |
| Station F Jobs | connecteur `station_f.py` | fenêtre « Formulaire de Candidature » (WelcomeKit) explorée | non relevé | ⏳ parcours à coder |
| Lever, Greenhouse, Ashby | lot 1.5 | remplissage par `Ctrl+Alt+Espace` | — | ✅ champs ; dépôt de CV testé sur Lever et Greenhouse |

Cas limites site par site, pièges et décisions : [`extension/EDGE_CASES.md`](extension/EDGE_CASES.md). Free-Work ajoute un CV et une LM au compte à chaque candidature (nettoyage à la main).

## Entrées modifiables

Tout ce que tu peux régler toi-même vit dans [`input/`](input/README.md) :
- Critères de matching → [`input/criteria.yaml`](input/criteria.yaml) (`disable_filters: true` désactive tout le filtrage, temporaire : à remettre à `false`)
- Entreprises suivies → [`input/companies.yaml`](input/companies.yaml)
- Sites interrogés par `run.ps1` → [`input/sites.yaml`](input/sites.yaml) ; entreprises des ATS (lot 1.5) → [`input/ats_companies.yaml`](input/ats_companies.yaml)
- Colonnes du tableau interactif → [`input/table_columns.yaml`](input/table_columns.yaml)
- Ton CV source → [`input/CV_originel.tex`](input/CV_originel.tex) (anglais) et [`input/CV_originel_fr.tex`](input/CV_originel_fr.tex) (français) ; textes d'adaptation du header → [`input/cv_template.yaml`](input/cv_template.yaml)
- Ta signature pour les LM (facultatif) → [`input/LM/Signature.png`](input/LM/Signature.png)
- Copilot et remplissage → [`input/copilot.yaml`](input/copilot.yaml) : nom des fichiers déposés (`CV_<file_name>.pdf`, `LM_<file_name>.pdf`), dossier d'upload, disposition des fenêtres, port du programme local (`fill_server_port`, identique à `PORT` dans `extension/background.js`), sites exclus du remplissage (`fill_excluded_domains`, LinkedIn)
- Tes infos perso pour les formulaires (adresse, salaire, préavis, permis, disponibilité...) → `input/form_profile.yaml`, **local et ignoré par git**, jamais dans le CV ni la LM (modèle : [`input/form_profile.example.yaml`](input/form_profile.example.yaml))
- Sites de la tournée de connexion → [`input/login_sites.yaml`](input/login_sites.yaml) (état dans `output/logins.json`, ignoré par git)

Logique du filtre ([`src/matcher.py`](src/matcher.py)) :
- **entre catégories** (lieu / contrat / métier / stack / séniorité) = **ET** strict
- **dans une même catégorie** (ex: plusieurs métiers dans `professions:`) = **OU**

Langue : chaque offre est classée français / anglais par un comptage de mots-outils ([`src/language.py`](src/language.py), sans modèle) ; CV et LM sont générés dans la langue de l'offre. Limite : une offre sans description est classée sur son titre seul (français par défaut).

## Technique

**Collecte**
- Point d'entrée WTJ : l'API publique JSON `api.welcometothejungle.com` ([`src/scraper.py`](src/scraper.py)), celle que le site utilise lui-même. La recherche élargie interroge la même API **sans filtre entreprise**, avec un mot-clé ([`src/company_finder.py`](src/company_finder.py)). Ce qui NE marche PAS : scraper la page web `welcometothejungle.com/fr/companies` (403 CloudFront), volontairement non contourné.
- Un site qui échoue ne doit jamais interrompre les autres : l'erreur est loguée, on continue.

**CV et LM**
- CV : le header du `.tex` de référence est adapté par offre et compilé en PDF (latexmk, repli `pdflatex` sans `perl`) dans `output/CV/` (jamais l'original). Tout texte injecté passe par `cv_builder.escape_latex()`.
- LM : générées par Claude Code en non-interactif (`claude -p`, abonnement Pro, pas de clé API), voir [`src/lm_builder.py`](src/lm_builder.py) et [`src/LM/README.md`](src/LM/README.md). Piège Windows : le prompt passe par **stdin** (`claude.cmd` tronque un argument multi-lignes). Une LM déjà dans `output/LM/archive/` n'est pas régénérée (sauf `force`) ; `output/LM/` : `tex/` et `pdf/` pour le lot du jour, `archive/` pour le traité. `LM_<nom>.txt` (lettre sans signature) sert aux formulaires qui demandent un texte.

**Copilot (`apply.ps1`)**
- Chrome sur l'offre (moitié gauche), Explorateur sur le dossier d'upload (quart haut droit, `CV_` / `LM_<nom>.pdf` écrasés à chaque offre), tableau de bord HTML d'avancement (quart bas droit). Passer à l'offre suivante recharge l'onglet actif. Statuts dans `output/applications.json` (suivi, pas de doublon) ; `suivi.ps1` en tire `output/suivi.xlsx`. L'exclusion d'employeur (Illuin) s'applique même sans filtres.

**Tournée de connexion (`login.ps1`)** : ouvre un à un les sites de `login_sites.yaml` dans ton Chrome ; tu te connectes toi-même (le gestionnaire de mots de passe remplit) et Chrome garde la session des semaines. Le programme ne lit pas les pages, ne prend aucune capture et ne voit aucun identifiant.

**Extension et programme local**
- Extension Chrome/Edge ([`extension/`](extension/README.md), Manifest V3, chargée une fois par navigateur) : `content.js` lit et remplit la page (champs, listes, radios, cases de consentement, import de fichiers par `DataTransfer`) et contient un parcours par site gardé par le nom d'hôte ; `background.js` enchaîne les étapes (remplir, passer à l'étape suivante par un bouton autorisé, attendre le changement d'écran, 8 étapes max) et s'arrête sur : connexion demandée, révision, plus de bouton, écran qui n'avance pas.
- Programme local ([`fill.py`](fill.py), `.\fill.ps1 install`) : serveur sur 127.0.0.1 seulement (en-tête dédié, origine `chrome-extension://`, aucune page web ne peut l'appeler) et raccourci global `Ctrl+Alt+Espace`. Routes : `/poll`, `/answers`, `/file` (CV, LM), `/trigger` et `/result` (pour `batch.py`), `/report` et `/shot`.
- Réponses : [`src/formfill.py`](src/formfill.py) fait rédiger par `claude -p` (CV, LM de l'offre, `form_profile.yaml`, texte de la page) dans la langue des questions, longueurs min/max respectées ; la LM est posée telle quelle dans un champ « motivation », puis une seconde passe force une vraie réponse sur les champs obligatoires restés vides (jamais de fait inventé). Désactivé sur LinkedIn.
- **Garde-fous** : le code ne clique jamais un bouton d'envoi (liste de mots interdits, boutons de passage autorisés par liste blanche) ni ne saisit d'identifiant ; un écran de connexion est laissé à l'utilisateur.

**Lots et diagnostic**
- `batch.py` ouvre chaque offre dans le Chrome habituel (nouvel onglet, fenêtre remise au premier plan), prépare le dossier d'upload, commande le remplissage (`/trigger`) et lit le rapport.
- Rapport par offre : étapes, erreurs classées (`login`, `review`, `submit_ready`, `no_button`, `no_progress`, `page_rechargee`, `exception`...), état final vérifié par critère (CV adapté, message personnalisé, LM jointe, questions répondues, bouton d'envoi actif), instantané des boutons et champs en cas d'échec, capture de l'onglet. Fichiers : `output/copilot/trace.log`, `reports/`, `shots/` (3 derniers par offre). Aucune valeur perso dans la trace, rien relevé si un champ mot de passe est visible.
- Développement d'un site : skill [`site-onboarding`](.claude/skills/site-onboarding/SKILL.md) (méthode), [`form-fill-testing`](.claude/skills/form-fill-testing/SKILL.md) (cas isolés), journal [`extension/EDGE_CASES.md`](extension/EDGE_CASES.md).

## Roadmap

Voir [`TODO.md`](TODO.md). Suggestions et contributions bienvenues, libre d'ajouter/modifier.
