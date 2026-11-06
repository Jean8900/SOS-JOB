# Diagnostic SOS-JOB (2026-11-04)

Sources lues : [`README.md`](README.md), [`TODO.md`](TODO.md), [`extension/EDGE_CASES.md`](extension/EDGE_CASES.md), brouillons de session ([30/10](brouillon_session_2026-10-30.md), [02/11](brouillon_session_2026-11-02.md), [03/11](brouillon_session_2026-11-03.md), [04/11](brouillon_session_2026-11-04.md)), `git log`, le code de [`src/`](src), [`extension/`](extension) et des points d'entrée.

Sommaire : [A. Abandonné](#a-fonctionnalités-abandonnées) · [B. Incohérences métier](#b1-tableau-métier) · [B. Incohérences techniques](#b2-tableau-technique) · [C. Plan de la phase II](#c-ce-que-la-phase-ii-va-modifier) · [D. Notions à l'abandon (transcripts)](#d-notions-potentiellement-à-labandon-lecture-des-transcripts)

## A. Fonctionnalités abandonnées

Colonne « Fait autrement » : **v** = le besoin métier est couvert par un autre moyen, **x** = non couvert.

| Date abandon | Description métier | Description tech | Raison d'abandon | Fait autrement |
|---|---|---|---|---|
| 2026-10-26 | Collecte France Travail | API OAuth2 client_credentials | Priorité au lot 2 Gmail, jamais codé | x |
| 2026-10-26 | Entreprise suivie alten-1 | Slug dans [companies.yaml](input/companies.yaml) | Scraping WTJ en échec | x |
| 2026-10-26 | Gmail par mot de passe d'appli | IMAP + app password | Accès non scopé, 2FA exigée | v (OAuth lecture seule) |
| 2026-10-26 | Sortie LM structurée | `claude -p --json-schema` | Schéma ignoré sur prompt long | v ([délimiteurs](src/lm_builder.py)) |
| 2026-10-26 | Notebook MVP1 lecteur WTJ | [wtj_offer_reader.ipynb](wtj_offer_reader.ipynb) | Remplacé par le pipeline `src/` | v ([scraper.py](src/scraper.py)) |
| 2026-10-26 | Règles pour l'agent Cline | [.clinerules](.clinerules) | Travail fait avec Claude Code | v ([CLAUDE.md](CLAUDE.md)) |
| 2026-10-30 | Annuaire d'entreprises WTJ | Scraping HTML /fr/companies | 403 CloudFront, non contourné | v ([company_finder](src/company_finder.py)) |
| 2026-11-02 | Suivre son employeur actuel | `illuin-tech` retiré des suivis | Employeur actuel | v (excluded_companies) |
| 2026-11-02 | Civilité déduite du prénom | Déduction par le modèle | Info sensible, laissée vide | x (par conception) |
| 2026-11-02 | Nettoyer le compte Free-Work | Suppression CV/LM par extension | L'extension ne supprime rien | x (nettoyage manuel) |
| 2026-11-02 | Upload manuel (Explorateur) | Glisser CV/LM à la main | Remplacé par DataTransfer | v ([content.js](extension/content.js)) |
| 2026-11-03 | Collecte d'offres prioritaire | Lot 2 alertes email en pause | Cap : candidater depuis liens | v (lots `--lot-file`) |
| 2026-11-04 | Collecte aijobs.net / Foorilla | Slug `aijobs_net` (enabled:false) | Barrière d'inscription (oct.) | x |
| 2026-11-04 | Collecte ChooseYourBoss | Requête HTTP de base | Cloudflare 403, renvoie Cadremploi | v (Cadremploi) |
| 2026-11-04 | Candidature talent.io | Parcours extension | Pas de candidature intégrée | x |
| (refusé) | Création de comptes automatique | Inscription scriptée | Captchas, e-mail, CGU | v ([login.ps1](login.py) guidé) |
| (de fait) | Pré-remplissage Ctrl+Alt+F | Playwright CDP ([formfill](src/formfill.py)) | Doublon de l'extension | v (Ctrl+Alt+Espace) |

## B. Incohérences, redondances, divergences

### B1. Tableau métier

| Sujet | Où | Constat | Type |
|---|---|---|---|
| Station F | [README l.78](README.md#candidature-codé-le-2026-11-02) | « ⏳ parcours à coder » | Divergence |
| Station F (suite) | [EDGE_CASES](extension/EDGE_CASES.md) | Validé sur 10 offres le 03/11 | Divergence |
| aijobs.net / Foorilla | [README l.63](README.md#lot-2--alertes-email-non-codé) | « à coder » | Incohérence |
| aijobs.net (suite) | [TODO l.54](TODO.md) | « mis de côté », bloqué | Incohérence |
| Lot 2 alertes email | [README l.61](README.md#lot-2--alertes-email-non-codé) | Titre « non codé » mais décrit fait | Incohérence |
| Code des alertes Gmail | `sandbox/` (non versionné) | Absent du dépôt, README le promet | Divergence |
| Cases à cocher / upload | [TODO l.28](TODO.md) | Non coché alors que fait | Divergence |
| Employeur exclu | [companies.yaml l.13](input/companies.yaml) | Sert encore d'ancre de recherche | Incohérence |
| Ancre « liste ci-dessus » | [companies.yaml](input/companies.yaml) | illuin-tech n'est pas dans la liste | Incohérence |
| Filtres coupés | [criteria.yaml l.6](input/criteria.yaml) | « TEMPORAIRE » toujours à true | Divergence |
| Pays forcé à « France » | [formfill.py l.332](src/formfill.py) | Valeur perso en dur dans `src/` | Incohérence |
| Mobilité « Paris » | [formfill.py l.98](src/formfill.py) | Ville perso en dur dans le prompt | Incohérence |
| « src/ sans valeur à toi » | [input/README](input/README.md) | Faux (pays, ville, métier) | Divergence |
| Métier « maintenance » | [wtj_prepare.py l.37](wtj_prepare.py) | Filtre de titre en dur, ignore la requête | Incohérence |
| Lot précédent figé | [wtj_prepare.py l.30](wtj_prepare.py) | `wtj_lot_1.json` en dur | Incohérence |
| input/README incomplet | [input/README](input/README.md) | Manque copilot, sites, ats_companies | Divergence |
| apply.ps1 en-tête | [apply.ps1 l.2](apply.ps1) | « terminal » au lieu de tableau HTML | Divergence |
| batch.py en-tête | [batch.py l.7](batch.py) | « aucune capture » : faux (shots/) | Divergence |
| Règle des 30 tentatives | [batch.py l.221](batch.py) | Compteur jamais remis à zéro | Incohérence |
| Offre hors site | [content.js l.804](extension/content.js) | Tout échec inconnu classé « écarté » | Incohérence |
| Ville sur Greenhouse | [content.js l.309](extension/content.js) | 1re suggestion prise sans vérifier | Incohérence |
| Ethnicity = Paris | [formfill.py l.335](src/formfill.py) | « city » trouvé dans « Ethnicity » | Incohérence |
| Lettre collée en LaTeX | [lm_builder.py l.250](src/lm_builder.py) | `\,` ou `$\rightarrow$` dans le texte | Incohérence |
| Deux remplissages | [TODO l.33](TODO.md) | Ctrl+Alt+F et extension coexistent | Redondance |

### B2. Tableau technique

| Sujet | Où | Constat | Type |
|---|---|---|---|
| Inverse d'escape_latex | [lm_builder.py l.250](src/lm_builder.py) | N'inverse pas `_UNICODE_FIXES` | Incohérence |
| Placeholder d'options | [content.js l.207](extension/content.js) | Faux choix envoyé au modèle | Incohérence |
| Regex localisation | [formfill.py l.335](src/formfill.py) | Sans `\b` (aussi content.js) | Incohérence |
| Suggestion de ville | [content.js l.309](extension/content.js) | `comboOptions(el)[0]` sans contrôle | Incohérence |
| Catch-all hors_site | [content.js l.804](extension/content.js) | Masque les KO des autres hôtes | Incohérence |
| `__sosjobFillLog` | [content.js l.349](extension/content.js) | Jamais remis à zéro entre passes | Incohérence |
| postMessage WelcomeKit | [content.js l.904](extension/content.js) | Origine de l'émetteur non vérifiée | Incohérence |
| JSON du modèle | [formfill.py l.187](src/formfill.py) | Seul le 1er `{` est essayé | Incohérence |
| Compteur de tentatives | [batch.py l.152](batch.py) | Pas de clé jour (≠ replays.json) | Divergence |
| Variable `n_try` | [batch.py l.237](batch.py) | Affectée, jamais lue | Redondance |
| Erreurs WTJ avalées | [welcome_to_the_jungle.py l.50](src/connectors/welcome_to_the_jungle.py) | `except: pass` sans log (CLAUDE.md) | Incohérence |
| Erreurs détail WTJ | [welcome_to_the_jungle.py l.66](src/connectors/welcome_to_the_jungle.py) | `except: continue` sans log | Incohérence |
| Recherche Algolia x2 | [company_finder.py l.18](src/company_finder.py) | Copie de `scraper._algolia_search` | Redondance |
| User-Agent | [scraper.py l.19](src/scraper.py) | « Mozilla/5.0 » vs « UA honnête » | Divergence |
| Convention UA | [connectors/\_\_init\_\_](src/connectors/__init__.py) | Non appliquée par scraper.py | Divergence |
| `REFERENCE_TEX` | [lm_builder.py l.21](src/lm_builder.py) | Doublon de cv_builder, inutilisé | Redondance |
| `status_of()` | [applications.py l.85](src/applications.py) | Jamais appelée | Redondance |
| `offer_key()` x2 | [fill.py l.57](fill.py) | Même nom, autre sens qu'applications | Redondance |
| Port du serveur local | [background.js l.3](extension/background.js) | Copie de `fill_server_port` | Redondance |
| `_find_chrome` | [apply.py](apply.py) | Importé par batch.py et login.py | Divergence |
| `_find_claude` privé | [lm_builder.py](src/lm_builder.py) | Appelé depuis formfill.py | Divergence |
| Docstring formfill | [formfill.py l.1](src/formfill.py) | Dit « ni radios », « copilot.yaml » | Divergence |
| Docstring WTJ | [welcome_to_the_jungle.py](src/connectors/welcome_to_the_jungle.py) | « scraper.py (inchangé) » périmé | Divergence |
| Docstring scraper | [scraper.py l.3](src/scraper.py) | Renvoie au notebook MVP1 | Divergence |
| Filtre métier | [matcher.py l.38](src/matcher.py) | Titre testé 2 fois (titre ⊂ full) | Redondance |
| `--source` / `--lot` | [batch.py](batch.py) | `--source` ignoré avec `--lot` | Incohérence |
| sandbox/ | [.clinerules](.clinerules) | Cité, ni versionné ni ignoré | Divergence |

## C. Ce que la phase II va modifier

1. [lm_builder.lm_text](src/lm_builder.py) : inverser aussi `_UNICODE_FIXES` pour ne plus coller `\,` ou `$\rightarrow$` dans les formulaires.
2. [formfill.py](src/formfill.py) : pays lu dans `form_profile.yaml` (`country`) et mobilité tirée de la ville du profil, plus de « France » / « Paris » en dur.
3. Regex localisation à mots entiers (`\b`) dans [formfill.py](src/formfill.py) et [content.js](extension/content.js) ; la suggestion de ville doit contenir la ville tapée.
4. [content.js](extension/content.js) : plus de placeholder « (saisie libre…) » comme option ; le profil remplit la ville via `complete_answers`.
5. [content.js](extension/content.js) : `hors_site` seulement sans formulaire visible, journal `__sosjobFillLog` remis à zéro, origine WelcomeKit vérifiée.
6. [formfill.generate_answers](src/formfill.py) : essayer chaque `{` de la réponse du modèle jusqu'à un objet JSON valide.
7. [batch.py](batch.py) : compteur des 30 tentatives remis à zéro chaque jour, `n_try` supprimé, en-tête (captures) corrigé.
8. [wtj_prepare.py](wtj_prepare.py) : filtre de titre tiré des mots de la requête (plus « maintenance » en dur) ; lot précédent passé en option.
9. [Connecteur WTJ](src/connectors/welcome_to_the_jungle.py) : erreurs loguées au lieu d'être avalées ; [company_finder](src/company_finder.py) réutilise la recherche de `scraper`.
10. Nettoyage : `REFERENCE_TEX` et `status_of` morts, notebook MVP1 supprimé, docstrings périmées, ancre WTJ sur une entreprise suivie.

## D. Notions potentiellement à l'abandon (lecture des transcripts)

Source : les sessions réelles du projet (`~/.claude/projects/C--Users-jeanm-SOS-JOB/*.jsonl`), soit 235 messages humains. Les ~480 appels automatiques `claude -p` (LM, formulaires) sont exclus. Rien de ce qui figure déjà en [A](#a-fonctionnalités-abandonnées) ou [B](#b-incohérences-redondances-divergences) n'est repris. Chaque passe a un angle différent : **[remplacé]** = on a trouvé mieux, **[silence]** = c'était très attendu au début, puis on n'en a plus parlé.

### D.v1 — Messages humains : ce qui a été remplacé par mieux

- **[remplacé] Cockpit apply.ps1** : 3 fenêtres + swipe Ctrl+Alt ←/→/S/Q ([hotkeys](src/hotkeys.py), [winlayout](src/winlayout.py)). Supplanté par batch.py ; Ctrl+Alt+→ survit dans login/batch.
- **[remplacé] Tableau de bord HTML** (quart bas droit, [dashboard.py](src/dashboard.py) en `--app`) : tu ne l'as plus cité après le 30/10 ; le rapport ✓/✗ par offre de batch.py le remplace.
- **[remplacé] Ctrl+Alt+Entrée multi-étapes** : 2e raccourci prévu le 02/11 pour enchaîner les écrans, fusionné dans un seul Ctrl+Alt+Espace (boucle de [background.js](extension/background.js), 8 étapes).
- **[remplacé] Chrome de test / profil dédié** : Chromium isolé ([run_case.py](extension/test/run_case.py)) et `chrome_profile`. Abandonnés le 02/11 au profit de ta vraie session Chrome (cookies, connexions).
- **[remplacé] Mots de passe en secret** (nano, Bitwarden relié à l'extension, idée du 02/11) : remplacés par le gestionnaire de Chrome + [login.ps1](login.py) ; l'IA ne voit aucun identifiant.
- **[remplacé] LM par API Sonnet/Haiku + cache + Batch** (~4 $/mois, 26/10) : remplacées par `claude -p` sur l'abonnement Pro, prompt par stdin ([lm_builder](src/lm_builder.py)), zéro coût API.
- **[remplacé] Candidature envoyée de bout en bout** : le 02/11, « faut vraiment candidater » sur 10 offres. Recadré en arrêt avant l'envoi + 1 envoi de test manuel par site.
- **[remplacé] Remplissage générique de tout ATS** (10 sites variés, Workday multi-pages) : jugé « trop complexe » le 02/11 → parcours codés site par site (`onWtj`, `apecNext`…).

### D.v2 — Premiers jours : ce qui était très attendu puis abandonné en silence (pourquoi)

- **[silence] Apprentissage de style des LM** (cas 1 relecture / cas 2 historique) : au cœur du brief du 26/10, jamais codé. Pourquoi : le goulot est devenu le formulaire, pas la LM.
- **[silence] Carte de France des offres** (MVP3, géocodage) : « on skip pour l'instant » le 26/10, plus jamais cité. Pourquoi : du reporting pur, aucun gain pour candidater.
- **[silence] App mobile / notifications** (MVP5) : vision du 26/10, puis plus rien. Pourquoi : le pilotage de Claude Code à distance depuis le téléphone couvre déjà le besoin « candidater de loin ».
- **[silence] SQLite + interface web** (MVP4) : prévus pour l'historique, jamais rouverts. Pourquoi : `applications.json` + `suivi.xlsx` suffisent pour quelques dizaines d'offres.
- **[silence] TUI à cases à cocher** ([ui.py](src/ui.py), textual) : la star du MVP1, dernier mot de toi le 28/10. Pourquoi : on ne choisit plus dans une liste, on prépare des lots par mot-clé.
- **[silence] Suffixe `sites` de run.ps1** (liste à cocher des sources) : décidé le 28/10, puis oublié. Pourquoi : run.ps1 lui-même n'est plus lancé depuis le 30/10 (cap « candidater »).
- **[silence] companies.ps1** (page HTML des entreprises par métier) : « laissons tomber les dev » dès le 28/10 ; ne sert plus qu'en coulisse à la découverte ATS (lot 1.5).
- **[silence] Archive des LM** ([archive_lm](archive_lm.py), suffixe `force`) : dernière mention le 28/10. Les lots génèrent CV et LM à la volée et ne passent jamais par l'archive.

### D.v3 — Transcripts croisés avec le code : branchements morts

- **[silence] Suivi Excel alimenté par les lots** : batch.py n'appelle jamais `applications.set_status`, donc tes candidatures en lot ne vont pas dans suivi.xlsx. Le suivi est figé sur apply.ps1.
- **[silence] Support Edge** : l'extension et fill.py gèrent Chrome et Edge, mais [batch.py](batch.py) a « chrome » en dur ; aucun lot n'a été lancé sur Edge depuis le 03/11.
- **[silence] Sources sans parcours de candidature** : Inria, CNRS, Choisir le service public. Collecte OK, aucun formulaire codé, plus citées par toi après le 30/10. Utiles pour le profil IA ?
- **[silence] Jobs that make sense** : « enlève ce site inutile » le 02/11 (tournée de connexion), mais le connecteur reste `enabled: true` dans [sites.yaml](input/sites.yaml).
- **[remplacé] Découverte ATS via WTJ** (lot 1.5, ~20 % de boards retrouvés, cache) : pour candidater, remplacée le 03/11 par la recherche my.greenhouse.io, sans passer par le nom d'entreprise.
- **[silence] Lever et Ashby en candidature** : la collecte marche, mais il n'y a pas d'espace candidat (03/11) ; jamais passés par site-onboarding, seul Greenhouse a atteint le niveau WTJ.
- **[remplacé] Lot tiré des offres en attente** (`batch.py` sans `--lot`, `pick()`) : depuis le 02/11, tout passe par `--lot` / `--lot-file` ; le mélange de sources via applications.json ne sert plus.

### D.v4 — Perspectives du 30/10 jamais reprises

- **[silence] Profil cible AI engineer** : tous les lots réels visent technicien / génie chimique (offres de test hors profil). Le pipeline n'a jamais tourné sur ton vrai métier.
- **[silence] Labs IA dans ats_companies.yaml** (Anthropic, Mistral, Hugging Face…) : quick win « sans code » du 30/10, jamais fait ; `companies: []` est toujours vide.
- **[silence] VIE, Remotive, RemoteOK, We Work Remotely** : sources « peu de code » listées le 30/10, une seule mention. Pourquoi : le cap « candidater » du 03/11 a gelé la collecte.
- **[silence] Connecteurs Workday / SmartRecruiters / Workable** (grands groupes) : listés le 30/10. SmartRecruiters bloque les robots, et Workday n'apparaît plus que dans la tournée de connexion.
- **[silence] Relance J+7 et réponses via Gmail** dans le suivi : TODO depuis le 30/10. L'accès Gmail existe (alertes) mais n'a jamais été branché sur suivi.xlsx.
- **[silence] Dédoublonnage inter-sources** (TODO MVP5) : sans objet tant que chaque lot vient d'une seule source ; redeviendra utile si run.ps1 multi-sites reprend.
- **[silence] Lieux étrangers + header du CV trop long** : TODO international du 30/10, jamais traité ; la détection FR/EN marche, mais `locations` reste Paris/Lyon/Remote.

### D.v5 — Outillage et méthode autour du code

- **[silence] OpenRouter multi-modèles** (notebook sandbox, 28/10) : comparer 20 modèles, audit de sécurité. Une journée puis plus rien : pour un usage intensif, Claude Code Pro reste moins cher.
- **[remplacé] Arbre des features** (skill en 3 MVP, 03/11) : jamais codé ; ce diagnostic.md tient le rôle (abandons, divergences), sans skill ni commit automatique.
- **[remplacé] Lot 2 intégré à run.ps1** (30/10) : un LLM devait lire les alertes, les filtrer par critères puis générer CV et LM. C'est devenu un décodage ponctuel de liens (Apec base64, HelloWork 302).
- **[silence] Notebooks comme banc d'essai** (sandbox, nbconvert, cité par .clinerules) : les essais passent désormais par l'extension et le vrai Chrome ; seul gmail_test.ipynb sert encore.
- **[remplacé] Brouillons de session quotidiens** : 4 fichiers à la racine, souvent refondus (README refait 4 fois le 02-03/11) ; le savoir durable vit dans EDGE_CASES.md et les skills.
