# Cas limites du remplissage de formulaires

Journal vivant : chaque cas rencontré sur un vrai site, ce qui a cassé, pourquoi, et ce qu'on a fait.
Statuts : **corrigé** (testé), **par conception** (volontairement non géré), **ouvert** (observé, pas résolu), **hypothèse** (attendu d'après la technique, pas encore vu).
Pour reproduire un cas : `python extension\test\run_case.py <url>` (voir « Protocole »).

## Règles qui ne changent pas

- Jamais de clic sur le bouton d'envoi final (liste de mots interdits dans la section « Étapes multiples »).
- Jamais de mot de passe, de compte créé, de captcha, de case de consentement cochée, de fichier uploadé.
- Les mots de passe ne passent jamais par ce code ni par l'IA : champs `type=password` ignorés, connexion et création de compte faites par l'utilisateur et son gestionnaire de mots de passe. Pendant une connexion : pas de capture d'écran, pas de lecture de la page par l'IA.
- Un fait absent des sources laisse le champ vide ; la civilité et la diversité ne sont jamais devinées.
- Désactivé sur les domaines de `fill_excluded_domains` (`input/copilot.yaml`, LinkedIn).

## Cas observés

| # | Site / situation | Symptôme | Cause | Correction | Statut |
|---|---|---|---|---|---|
| 1 | Lever, champ « Current location » | Texte tapé effacé par le site | Champ à auto-complétion : il faut choisir une suggestion | Clic sur la suggestion qui ressemble le plus à la valeur (liste en surimpression sous le champ) ; frappe caractère par caractère si le champ a été vidé | corrigé |
| 2 | Lever (suite) | « Paris, Gabon » choisi au lieu de « Paris, Île-de-France » | Élément choisi = conteneur de toute la liste | Ne garder que les éléments les plus profonds ; classer par ressemblance (mots de la valeur) | corrigé |
| 3 | Workday, adresse | Code postal vide, compteur de champs faux | La page recrée les champs après une saisie : l'étiquette posée au départ disparaît | Retrouver chaque champ par `id` puis `name` (stables) | corrigé |
| 4 | Workday, « Titre (préfixe) » | Liste déroulante non remplie | Ce sont des `button[aria-haspopup=listbox]`, pas des `<select>` ; options visibles seulement ouvertes | Ouvrir, lire les options, choisir par texte exact | corrigé |
| 5 | Workday, même liste | Options d'un autre composant (« France (+33) ») mélangées ; liste laissée ouverte | Plusieurs `[role=option]` sur la page | Prendre la liste `[role=listbox]` visible la plus proche sous le bouton ; refermer en recliquant le bouton | corrigé |
| 6 | Workday, indicatif téléphone | Champ « Rechercher » rempli à tort | Champ de recherche interne d'une liste, vide | Ignorer les champs dont le placeholder commence par « Rechercher / Search » | corrigé |
| 7 | Workday, nom de famille | « Alerte : plus de 2 majuscules » | CV : « MARTINI » | Consigne au modèle : casse normale pour les noms | corrigé |
| 8 | Workday, civilité | « Monsieur » choisi d'après le prénom | Déduction de genre par le modèle | Civilité = information sensible, laissée vide | par conception |
| 9 | Ashby, questions ouvertes | Réponse en français sur un formulaire anglais | Langue prise sur le texte de la page, pas sur les questions | Langue = celle des libellés des champs | corrigé |
| 10 | Tous, questions avec limites | Réponses trop longues | Aucune limite transmise | `minlength`/`maxlength` ou « max 500 caractères » dans le libellé ; réponse coupée à la dernière phrase entière | corrigé |
| 11 | Tous | Premier essai sans effet après un redémarrage du programme local | Ordre pris par l'attente d'un navigateur déjà fermé | Remise en file de l'ordre si la livraison échoue | corrigé |
| 12 | Tous | Requêtes de l'extension refusées (403) | Pas d'en-tête `Origin` sur les GET | Accepter « pas d'Origin » ou `chrome-extension://`, l'en-tête dédié bloque les pages web | corrigé |
| 13 | Tous | Extension « endormie » (service worker) | Chrome arrête les service workers inactifs | Alarme toutes les 30 s qui relance l'écoute | corrigé (à surveiller) |
| 14 | Ashby, « Yes / No » (boutons, pas des radios) | Non rempli | Groupe de `<button>` sans `input[type=radio]` | Détection des groupes de 2-3 boutons « Yes/No/Oui/Non » dont aucun n'est déjà choisi ; clic sur le bon bouton | corrigé |
| 15 | Greenhouse, listes « Select... » (Mirakl, Liberis) | Texte tapé puis effacé, liste non choisie, compteur faux | Listes `react-select` : le vrai `<input>` fait 3 px, souvent sans `id`, et vide le texte non choisi dans la liste | Type « combobox » : ouvrir la liste, lire les options, cliquer celle qui correspond | corrigé |
| 16 | Workday, plusieurs étapes | Un seul écran rempli par appui | Pas de passage à l'étape suivante | Boucle remplir -> bouton de passage -> remplir (`Ctrl+Alt+Espace`, voir « Étapes multiples ») ; testé sur `extension/test/multistep.html` (3 étapes, arrêt à « Réviser », envoi non cliqué) | corrigé (page de test ; à valider sur Workday réel) |
| 17 | Tests enchaînés | Message « aucun champ vide » alors que le formulaire est rempli, compteur à 0 | Un ordre récent livré à une instance d'extension qui se connecte juste après : la page suivante était remplie deux fois | Identifiant d'instance stable (`chrome.storage`), pas d'ordre « d'écho » pour une instance jamais vue, profil de test neuf à chaque essai | corrigé |
| 18 | Premier appui juste après le démarrage du navigateur | Rien ne se passe (« 0 instance d'extension ») | L'extension n'écoutait pas encore le programme local | Ordre valable 20 s pour une instance connue qui se réveille ; le banc d'essai attend la connexion de l'extension (`/status`) | corrigé |
| 19 | Recruitee (Personio), téléphone | Champ téléphone non rempli | Il contient déjà l'indicatif du pays (`+49`) : vu comme rempli | Un champ `tel` qui ne contient que l'indicatif compte comme vide (le drapeau bascule tout seul sur +33) | corrigé |
| 20 | Funding Circle (Ashby), « Comment avez-vous connu l'offre ? » | Réponse « Job board » inventée | Le modèle déduisait une source plausible | Source de candidature = information non devinable ; fait perso optionnel `how_did_you_hear` dans `input/form_profile.yaml` | corrigé |
| 21 | Ashby, champ « Location » (liste avec recherche) | Non rempli | Les options n'apparaissent qu'après avoir tapé ; ouverte vide, la liste est ignorée | — (idée : taper la valeur puis choisir la suggestion, comme le champ à auto-complétion de Lever) | ouvert |
| 22 | SmartRecruiters | Page « Faites glisser pour sécuriser votre accès » | Anti-robot déclenché par le navigateur de test piloté | Non contourné ; à tester dans le vrai Chrome de l'utilisateur | par conception |
| 23 | Recruitee (bunq) | `/c/new` ouvre la fiche, pas le formulaire ; bandeau de cookies | Le formulaire s'ouvre par le bouton « Apply now » | Banc d'essai : `--click "Apply now"` (les boutons d'envoi sont refusés) | corrigé (banc d'essai) |
| 24 | Lever, Greenhouse, Ashby : droit de travail, parrainage de visa, pronoms, ethnicité, aménagements, consentements | Champs laissés vides | Questions sensibles ou juridiques, jamais devinées ; cases à cocher jamais touchées | — | par conception |
| 25 | Lever (Brevo, BlaBlaCar), prétentions salariales | Champ vide | Aucune valeur dans `input/form_profile.yaml` (`salary_expectation`) | Renseigner le fichier pour que ce soit rempli | par conception |
| 26 | Tous : captures pleine page | Un bandeau (logo) fixe masque des champs sur l'image | Éléments `position: fixed` répétés par la capture pleine page | Aucune : artefact de mesure, les champs sont bien remplis (vérifié par la liste « rempli ») | sans objet |

## Hypothèses à vérifier

- Recruitee : la lettre de motivation peut s'écrire dans un champ de texte caché derrière « Stattdessen hier schreiben » : la LM texte de `apply.ps1` irait bien là.
- Listes de plus de 60 options (pays) : tronquées, la bonne option peut ne pas être proposée au modèle.
- Champs dans un Shadow DOM (non parcourus).
- Éditeurs de texte riche (`contenteditable`) pour les questions ouvertes.
- Sélecteurs de date, champs de téléphone avec indicatif (`intl-tel-input`), curseurs de salaire.
- Cases à cocher « J'ai lu... » : jamais cochées (par conception), mais certaines bloquent l'envoi.
- Pages où un cadre `iframe` d'un autre domaine porte le formulaire.
- Bandeaux de cookies recouvrant le formulaire.

## Étapes multiples (implémenté : un seul `Ctrl+Alt+Espace` pour tout le parcours)

But : après avoir rempli une étape, cliquer sur « Enregistrer et continuer » / « Suivant » pour passer à la suivante, puis recommencer, **sans jamais envoyer**.

- Boutons de passage autorisés (texte, insensible à la casse) : `enregistrer et continuer`, `continuer`, `suivant`, `étape suivante`, `next`, `continue`, `save and continue`.
- Boutons **interdits**, jamais cliqués : `envoyer`, `soumettre`, `postuler`, `candidater`, `valider ma candidature`, `confirmer`, `submit`, `apply`, `send`, `finish`, `terminer`, `réviser` n'est pas interdit mais l'étape « Réviser / Review » est une **arrêt obligatoire**.
- Arrêt : étape de révision, plus de champ vide à remplir, étape sans bouton de passage, 8 étapes au maximum, ou un bouton à la fois « passage » et « envoi » dans le texte (ambigu).
- Déclenchement : le même `Ctrl+Alt+Espace` (remplit, passe, recommence). Écran de connexion (champ mot de passe visible) : arrêt immédiat, l'utilisateur se connecte lui-même puis rappuie. Étape qui n'avance pas après le clic (champ obligatoire manquant) : arrêt.
- À savoir : « Enregistrer et continuer » enregistre un brouillon dans ton compte candidat chez l'ATS ; il n'est pas soumis et en général pas visible du recruteur (non vérifié site par site). Sans effet sur les sites où « Continuer » ne fait que changer d'écran.

## Protocole de test

1. Programme local lancé : `.\fill.ps1 status`.
2. `python extension\test\run_case.py <url>` : ouvre Chromium avec l'extension, envoie un vrai `Ctrl+Alt+Espace`, affiche le message de l'extension et les champs remplis, et enregistre une capture dans `output\copilot\ext_tests\`.
3. Un cas qui échoue : noter ici (symptôme, cause), corriger dans `extension/content.js` ou `src/formfill.py`, rejouer, passer le statut à « corrigé ».
4. Ne jamais cliquer sur l'envoi final, ne pas créer de compte, ne pas saisir de mot de passe.

## Journal des tests du 02/11/2026 (formulaires publics, sans envoi)

| ATS | Offres testées | Résultat |
|---|---|---|
| Lever | Brevo, Swile, BlaBlaCar (+ Doctrine) | 9 à 10 champs sur 13 : identité, ville (suggestion choisie), entreprise, liens, listes, radios, questions ouvertes. Salaire vide (pas de valeur), consentements non cochés |
| Greenhouse | Doctolib, Mirakl, Liberis | Champs texte et question ouverte (Mirakl) ; listes « Select... » après le cas 15 ; droit de travail et consentements vides (sensibles) |
| Ashby | Inato (x2), Funding Circle, Reedsy, Amo | Nom, e-mail, téléphone, LinkedIn, questions ouvertes (Reedsy 4/4, Amo 4/4) ; Oui/Non après le cas 14 ; questions sans fait dans le CV laissées vides |
| Recruitee | Personio, bunq | Nom, e-mail, téléphone (indicatif, cas 19), pays |
| SmartRecruiters | SmartRecruiters | Bloqué par un anti-robot (cas 22), non contourné |
| Workable, Teamtailor, Personio (site propre), BambooHR | — | Non testés (pas d'offre publique trouvée par l'API dans le temps imparti) |

Aucun bouton d'envoi n'a été cliqué.

## Upload CV / LM et lot sur le vrai Chrome (batch.py)

- **Upload** : l'extension demande le PDF au programme local (`/file?k=cv|lm`, dossier d'upload `output/copilot/a_uploader`), crée un `File` et le pose dans `input[type=file]` (événements `input` + `change`). Champ « lettre/cover/motivation » = LM ; « resume/cv » = CV ; un seul champ sans libellé = CV ; le reste est ignoré. Validé : Lever (« Success! » affiché) et, en vrai Chrome, Greenhouse (2 fichiers). Piège rencontré : la route `/file` exige `?b=<navigateur>` comme les autres (400 sinon).
- **Lot** (`python batch.py -n 10`) : offres variées (une source après l'autre), un onglet chacune dans le Chrome habituel, remplissage puis arrêt avant l'envoi. Connexion demandée = offre mise de côté, reprise après `Ctrl+Alt+Droite`. Compte rendu : `output/copilot/batch_report.json`.
- **Premier lot (2026-11-02, vrai Chrome, 10 offres)** : Greenhouse x2 (8 et 15 champs + 2 fichiers chacun), Lever (8 champs + 1 fichier), Free-Work x2 (2 champs), WTJ x2 / Inria x2 / CNRS x1 : « rien à remplir ». Cause : ces adresses sont des pages de description, pas le formulaire ; le bouton « Postuler » mène à l'ATS de l'employeur. **Ouvert** : décider si on suit ce lien d'entrée (voir ci-dessous). Aucun parcours multi-pages dans ce lot : le multi-étapes reste à valider sur un vrai Workday.

## Welcome to the Jungle : candidature intégrée (2026-11-02)

- **Seules les offres `ats: "wkit"` ont un formulaire sur WTJ** (champ `ats` de l'API de détail). Les autres (`external`, la grande majorité des offres de technicien) renvoient vers le site de l'employeur : hors périmètre. Pour « technicien de maintenance », seules ~12 offres étaient intégrées (`wtj_prepare.py` filtre dessus, un lot de 10 entreprises distinctes est impossible sur cette recherche).
- **Déroulé** : page de l'offre -> bouton « Postuler » (`data-testid=job_*-button-apply`, ouvre juste le formulaire, n'envoie rien) -> fenêtre `role=dialog` : identité préremplie par le compte WTJ, 2 questions libres, lettre de motivation, case de consentement, CV (`input[name=resume]` masqué) -> bouton `apply-form-submit` « J'envoie ma candidature ! ».
- **Formulaire changé (constaté le 2026-11-06)** : bouton d'envoi « Envoyer ma candidature » (`type=button`), lettre `textarea[name=coverLetter]`, adresse en `/apply`, et les anciens sélecteurs `[role=dialog]` ne trouvaient plus le formulaire : l'extension recliquait « Postuler » à chaque étape. Détection désormais sans dépendre de la fenêtre.
- **Échap ferme le formulaire WTJ** : refermer la liste de « Lieu de résidence actuel » par un Échap qui remonte fermait toute la fenêtre, les réponses tombaient dans le vide (0 champ) et « Postuler » était recliqué à chaque étape. Dans une fenêtre modale, l'Échap reste sur le champ.
- **« J'envoie ma candidature ! » envoie réellement la candidature** (confirmé par l'utilisateur : il n'y a pas de 2e confirmation). L'extension ne le clique jamais ; `submitReady()` détecte juste le bouton pour s'arrêter.
- **Piège** : le bouton d'entrée peut être masqué (en-tête) : on clique le bouton « bas de page » visible. L'ancienne version de `background.js` n'appelle que `clickNext()` : l'ouverture du formulaire y est donc câblée aussi (`clickNext` -> `clickEntry`), pour fonctionner sans recharger l'extension.
- **Ouvert** : après rechargement de l'extension, la LM (texte du fichier `LM_*.txt`) est posée dans le champ lettre ; avant, ce champ reçoit une réponse rédigée par Claude. Offre déjà remplie dans un onglet : seul le CV est reposé.
- **Lot 1 (10 onglets)** : 8/10 formulaires ouverts, remplis, CV posé ; HappyVore (déjà rempli, 1 fichier) ; AISPRID (« rien à remplir », à revoir : page lente ou formulaire différent).

## Champs obligatoires laissés vides, permis (2026-11-02)

- **Symptôme** : la question « Expliquez-nous pourquoi vous souhaitez nous rejoindre ! » restait vide (ou « . ») sur 4 offres WTJ sur 10. **Cause** : le programme local recevait une offre générique (page web), donc le modèle ne voyait pas la LM de l'offre ; devant une question sans fait dans le CV il répondait `null`, qui devenait « . ».
- **Correction** (`src/formfill.py` : `staged_letter`, `complete_answers`) : (1) le texte de la LM déposée dans le dossier d'upload (moins d'1 h) est donné au modèle et posé tel quel dans un champ dont le libellé évoque la motivation ; (2) seconde passe de `claude -p`, uniquement sur les champs obligatoires encore vides ou à « . », avec la consigne « tu DOIS répondre » (réponse honnête, rien d'inventé). Les champs déjà remplis ne sont pas repris. Testé hors navigateur (permis, question de motivation, question sans expérience).
- **Permis B boîte manuelle** : fait perso `driving_license` dans `input/form_profile.yaml` (exemple dans `form_profile.example.yaml`) : oui.

## Apec : candidature intégrée (2026-11-02)

- **Offres visées** : `typeCandidature == "EMAIL_ONLY"` dans l'API de détail (`/cms/webservices/offre/public?numeroOffre=...`) = candidature sur l'Apec. `URL_ONLY` (renvoi chez l'employeur : aplitrak, basf.jobs...) et `EMAIL_URL` : écartés.
- **Lister les offres** : l'API de recherche (`/cms/webservices/rechercheOffre`, POST) répond 403 à Python et à Playwright (anti-bot), mais fonctionne depuis une page Apec de ton Chrome connecté. Le lot est donc établi depuis ce navigateur et déposé dans `output/copilot/apec_lot.json` (ce n'est pas encore une commande autonome).
- **Parcours** (code : `apecNext()` dans `content.js`, appelé par `clickNext` sur `apec.fr` seulement ; le code WTJ n'est pas touché) :
  1. page de l'offre : lien « Postuler » vers `postuler-a-une-offre.html` ;
  2. `#/candidature/promotion/<id>` : bouton « Postuler » (bis), sans prendre l'échange avec un conseiller ;
  3. `#/candidature/formulaire/<id>` : radio « Je préfère joindre uniquement un CV », puis « Importer un CV », import du CV (`input[type=file]`, 3 Mo max), puis soit « Joindre ma lettre de motivation » + import de la LM, soit (offre sans LM) bloc repliable « Ajouter un message au recruteur ? » à déplier ;
  4. arrêt : « Envoyer ma candidature » (actif quand le formulaire est complet) n'est **jamais** cliqué : il envoie vraiment.
- **Pièges rencontrés** : (a) radios Angular sans `for=` (`<div><input><label>`) : l'entrée est le frère qui précède le libellé ; (b) cocher/décocher une case ne change pas l'écran, donc l'étape paraît « ne pas avancer » : le décochage est fait pendant le remplissage, pas comme étape de passage ; (c) les champs fichier n'existent qu'une fois « Importer » choisi : sur Apec, seuls les champs visibles reçoivent un fichier ; (d) Apec **pré-remplit** le message (« Bonjour, je me permets de vous solliciter… ») : il est effacé puis remplacé par un message personnalisé (3 à 4 phrases) ; (e) un champ mot de passe masqué existe dans le menu : ce n'est pas un écran de connexion (vérifier sa visibilité, pas sa seule présence).
- **Compte Apec** : « Enregistrer le CV / la lettre dans mon compte » est coché par défaut ; l'extension le décoche pour ne pas empiler dix CV adaptés dans le compte. « Données complémentaires » : jamais touchée.
- **Lot du jour** : 10 offres « génie chimique » (10 entreprises), toutes jusqu'à « Envoyer ma candidature » activé (voir compte rendu de session).

## Free-Work : deux boutons, un seul à utiliser (2026-11-02)

- **« Je postule » = candidature rapide : envoie immédiatement** la candidature avec le profil et le CV du compte, sans message (message « Envoyé »). Découvert par un clic involontaire à l'exploration (offre hors profil, ALLEGIS GROUP). **Ne jamais le cliquer** : on n'y choisit ni le CV ni le message.
- **« Postuler » (bouton distinct) = candidature avec formulaire** (« Postuler à cette offre » : CV, message). C'est celui à traiter pour envoyer **le CV adapté** et **un message personnalisé** (quelques centaines de caractères, comme sur Apec/WTJ).
- **Problèmes constatés** (à corriger) : (1) le CV du compte est utilisé, pas le CV adapté à l'offre ; (2) aucun message personnalisé n'est écrit ; (3) une offre sur 10 renvoie hors de Free-Work (site de l'employeur) : à repérer et à **écarter**.
- **Erreur de méthode (à ne pas refaire)** : j'ai d'abord **exclu Free-Work entier du remplissage** (`fill_excluded_domains`) pour éviter le clic qui envoie. C'est un contournement, pas un parcours : retiré, on traite les offres internes au site.
- **Corrigé (vérifié à l'écran)** : le message personnalisé est écrit (champ `job-application-message`, 559/2000 caractères), avec un libellé qui force un message court et non générique.
- **CV adapté : en cours.** Le CV « partagé » est le CV de la CVthèque publique (visible des recruteurs) : on ne le remplace pas. Piste retenue : le joindre en « Document additionnel » (bouton « Ajouter » / « Add » -> fenêtre « Mes documents » / « My documents » -> onglet « Ajouter un document » -> champ fichier `.pdf` **dans un shadow DOM** (parcours via `deepAll`) -> « Envoyer le document » -> « Joindre le document »). Fait : ouverture de la fenêtre. **Reste** : onglet, import, envoi, jointure (la fenêtre « My documents » dépasse de l'écran de test, donc relevé visuel incomplet). Piège : la page s'affiche parfois en **anglais** (`/en-gb/`, « Apply to this job » = le bouton qui envoie) : les motifs de boutons sont bilingues. Chaque document ajouté reste dans le compte (empreinte à surveiller).
- **Parcours validé (2026-11-02, 3 offres internes, critères ✓ au rapport)** : « Éditer » (le **clic recharge la page** : rendre la main aussitôt, sans attendre) -> importer le CV -> « Envoyer mon CV » (pas de rechargement) -> menu ⋮ du **dernier** CV de la liste -> entrée `button[role=menuitem]` « Make Default CV » / « Partager le CV » (cliquer le `li` autour ou le bouton « Make Default CV » du bas ne fait rien : ce dernier vise le CV déjà sélectionné) -> « Document additionnel » -> « Ajouter » -> importer la LM -> « Envoyer le document » -> **sélectionner la carte de la LM**, puis « Joindre le document » (inactif sinon).
- **Pièges** : (a) un clic sur « Éditer » avant l'hydratation de la page est ignoré : attendre 2,5 s ; (b) ouvrir `/fr/...` fait recharger la page tard vers `/en-gb/` (`apply.py` ouvre donc `/en-gb/` directement) ; (c) les flux ne changent pas toujours l'écran : un compteur (`data-sosjob-ticks`) dans `stepSig` évite le faux « n'avance pas » ; (d) le site renomme parfois les fichiers : le critère `cv_adapte` lit le nom du CV **par défaut** ; (e) **offre hors site** : « Apply to this job » est un lien `A` (et non un `button` submit) et il n'y a pas de formulaire -> critère `hors_site` (écartée, pas un échec).
- **Effets dans le compte Free-Work** : le CV adapté devient le CV **par défaut** (donc celui de la CVthèque) et chaque passage ajoute un CV et un document : à nettoyer après les tests.
- **Statut** : validé sur 3 offres internes ; offre n° 633 : hors site (détectée, `hors_site` pas encore rejoué).

## HelloWork : candidature intégrée (2026-11-02)

- **Offres** : `https://www.hellowork.com/fr-fr/emplois/<id>.html`. Lister depuis le Chrome connecté (page de recherche `emploi/recherche.html?k=...`). Le CV importé remplace le CV enregistré du compte pour cette candidature.
- **Parcours** (`helloNext()` dans `content.js`, gardé par `onHello`) : lien « Postuler » de l'en-tête (`a[data-cy=applyButtonHeader]`, ancre `#postuler`) -> formulaire sur la même page : prénom, nom, e-mail (préremplis par le compte), CV (liste des CV enregistrés + « Utiliser un nouveau CV », champ fichier masqué `input#upload`, 2 Mo max), bloc « Personnaliser mon message au recruteur » -> bouton noir « Postuler » (`button[data-cy=submitButton]`, dans le formulaire) = **l'envoi** : jamais cliqué.
- **Pièges** : (a) le bloc message est une case cachée `#cover-letter-collapse-funnel` pilotée par son `<label>` ; le champ `MotivationLetter` est « visible » (largeur) même replié (conteneur `max-h-0`) : se fier à l'état de la case, pas à la géométrie ; (b) déplier ne change pas l'écran, donc le faire pendant le remplissage (`helloOpenMessage`, appelé par `fileInputs`), pas comme étape de passage ; (c) le champ fichier est masqué : on y pose le PDF directement (pas de clic sur « Utiliser un nouveau CV » : un clic de script n'ouvre pas le sélecteur de fichiers) ; (d) le message reçoit le texte de la LM (limite 2900 caractères).
- **Bouton qui soumet (HelloWork, vérifié par un envoi de test sur une offre Reisel, technicien de maintenance)** : le bouton noir « Postuler » du formulaire (`button[data-cy=submitButton]`) envoie immédiatement : toast « Votre candidature … va être transmise à <entreprise> », puis redirection vers `/fr-fr/bounce/skills?origin=ResponseOffer` (« Enrichissez votre profil »). **Pas de 2e confirmation.** Le CV du formulaire est celui du compte (liste), le fichier importé le remplace. Un clic souris à l'aveugle sur une autre offre n'a produit aucune confirmation visible : se fier à « Mes candidatures » (`/fr-fr/candidat/mes-candidatures.html`) pour vérifier un envoi.

## Cadremploi : candidature « un clic » (2026-11-03, validé sur 10 offres)

- **Offres** : liste `emploi/liste_offres?query=...` (relevée depuis le Chrome connecté) ; page `emploi/detail_offre?offreId=<id>`. Deux types : **formulaire « Envoyez votre candidature ! » sur la page** (traité) ou **renvoi vers le site de l'entreprise** (écarté). Pour trier sans ouvrir chaque offre : un `iframe` même origine par offre, présence de `input[name=nom]` (le HTML brut ne suffit pas, le formulaire est rendu côté navigateur).
- **Parcours** (`cadNext()` dans `content.js`, gardé par `onCad`) : formulaire (Nom, Prénom, e-mail préremplis, CV enregistré, case « offres similaires » jamais cochée) -> bouton du CV rendu inoffensif puis cliqué -> champ fichier visible `.pdf/.doc/.docx/.rtf` 3 Mo -> CV adapté posé -> « Personnaliser ma lettre de motivation » déplié -> lettre de motivation collée telle quelle.
- **Pièges** : (a) **le bouton du CV n'a pas d'attribut `type` : c'est un bouton submit** ; un clic par script provoque une tentative d'envoi (« Une erreur est survenue lors de l'envoi »). On force `type="button"` sur tout bouton sans type du formulaire avant tout clic ; (b) la lettre est **préremplie par le site** (« ...pour lequel je souhaite vous proposer ma candidature ») : effacée et remplacée ; (c) le formulaire s'affiche parfois après 10 s : l'attendre (14 s) avant de conclure ; (d) la clé de rapport doit contenir `offreId`, sinon toutes les offres partagent le même rapport ; (e) la génération de LM peut échouer sur un caractère Unicode (« − » U+2212) : `escape_latex` le remplace maintenant.
- **Bouton qui envoie** (envoi de test, offre « Ingénieur Procédés & Risques Industriels », Centurion Search) : le « Postuler » rouge du formulaire (`button[type=submit]`) envoie **immédiatement** : « Votre candidature a bien été envoyée », puis une fenêtre propose de créer une alerte (non cliquée). Pas de 2e confirmation.
- **Résultat** : 10 offres de génie chimique/procédés, toutes ✓ (CV adapté, lettre, bouton d'envoi actif non cliqué). Quelques passages ont dû être rejoués (focus perdu, formulaire tardif).
## Station F Jobs : candidature WelcomeKit (2026-11-03, validé sur 10 offres)

- **Offres** : liste `jobs.stationf.co/search?query=...` (relevée depuis le Chrome connecté), page `/companies/<entreprise>/jobs/<slug>`. Pas de connexion. Deux types : **formulaire WelcomeKit** (traité) ou **renvoi chez l'employeur** (ex. toutes les offres L'Oréal de la recherche « génie chimique » : site L'Oréal ; Joko) : écarté (`hors_site`).
- **Recherche demandée** (« génie chimique ») : 5 offres, toutes L'Oréal, toutes hors site. Les 10 offres de test viennent donc de la liste générale (métiers hors profil : commercial, marketing, formateur...).
- **Parcours** (`sfNext()` dans `content.js`, gardé par `onSf`) : lien « POSTULER » (en anglais « APPLY NOW » : le Chrome du lot sert le site en anglais, tout motif de bouton doit être bilingue) -> fenêtre colorbox dont le **formulaire est un cadre d'un autre domaine** (`www.welcomekit.co/candidates/new`) -> l'extension remplit dans le cadre (champs, CV, lettre en anglais ou français selon le formulaire, consentement de traitement des données).
- **Pièges** : (a) l'ouverture du formulaire ne change rien dans la page elle-même : compteur `data-sosjob-ticks` dans `stepSig` pour éviter le faux « n'avance pas » ; (b) la page ne peut pas lire le cadre : **le cadre publie lui-même son état** (`postMessage` toutes les 0,8 s, booléens et longueurs seulement), que la page principale lit pour le rapport ; lecture finale différée de 1,5 s ; (c) **reCAPTCHA** dans le formulaire : jamais touché ; l'envoi de test demande l'utilisateur.
- **Bouton qui envoie** : le bouton jaune « Apply » du formulaire (derrière le reCAPTCHA). **Envoi de test non fait par moi** (captcha) : à faire à la main par l'utilisateur sur une offre hors profil.
- **Résultat** : 10 offres essayées, 9 ✓ (CV adapté, lettre, consentement, champs obligatoires, bouton visible) et 1 hors site.
## Observabilité : rapport structuré par offre (2026-11-02)

- **Ce que l'extension envoie au programme local** (`background.js` -> `/report`, `/shot`) : étapes (champs, fichiers, libellé cliqué, écran avancé ou non), erreurs avec leur cause classée, **état final vérifié par critère** (`siteState()` de `content.js` : CV adapté affiché, message personnalisé et non celui du site, LM jointe, bouton d'envoi actif), **instantané** de la page en cas d'échec (`snapshot()` : boutons avec type et état, champs avec nom et longueur, jamais de valeur) et **capture de l'onglet** après défilement vers la zone utile (`captureVisibleTab`, sans dépendre du focus).
- **Classement des arrêts** : `login`, `review`, `submit_ready`, `no_button`, `no_progress` (clic sans effet), `max_steps`, `excluded`, `page_rechargee` (la page se recharge en cours d'étape, ex. Free-Work « Éditer »), `exception`.
- **Où lire** : `output/copilot/trace.log` (une section par offre), `output/copilot/reports/<offre>__<date>.json` et `output/copilot/shots/<offre>__<date>.png` (3 derniers par offre). Dans le lot : `.\batch.ps1 ... --debug` affiche trace, état, boutons et chemin de la capture ; sans `--debug`, une ligne ✓/✗ par critère.
- **Garde-fous** : ni capture ni relevé quand un champ mot de passe est visible ; aucune valeur perso (noms de fichiers, longueurs, booléens seulement) ; plafond de 5 passages par offre et par jour (`--force-replay` pour passer outre).
- **Nécessite un rechargement de l'extension** (`background.js` a changé) ; avec l'ancienne version, le lot n'affiche pas de critères.

### Free-Work : encombrement du compte (décision)

- Chaque passage ajoute au compte un CV et un document : les anciens s'accumulent (plusieurs `CV_Jean_Martini.pdf`, `LM_Jean_Martini.pdf`).
- **L'extension ne supprime rien** (« Delete » du menu ⋮ = suppression définitive de données du compte : à faire à la main). À la place, le rapport affiche `cv_dans_compte` (nombre de CV déjà présents avant le passage) et le signale au-delà de 6.
- **Réutiliser un fichier de même nom n'est pas possible** : le CV est adapté à chaque offre, le contenu change alors que le nom reste `CV_Jean_Martini.pdf`.
- **Nettoyage conseillé** : `Edit` (CV par défaut) -> menu ⋮ de chaque ancien CV -> Delete ; garder le CV par défaut du moment et ton CV d'origine.

### Free-Work : questions personnalisées de l'offre (2026-11-02)

- **Symptôme** : l'offre « Technicien de Proximité Référent » pose 4 questions OUI/NON obligatoires (`Etes vous mobile sur Paris ? *`, TJM/salaire, technologies Citrix/ITIL/Office 365, 5 ans d'expérience) ; seul le message était rempli.
- **Cause** : de vrais radios `custom-answer-0..3`, mais le texte de la question est **un niveau plus haut** que le conteneur des deux libellés « OUI / NON » ; l'extraction ne voyait qu'un groupe sans question, donc sans réponse possible.
- **Correction** : (1) `extract()` remonte jusqu'à trouver un texte (hors options) pour un groupe radio sans `fieldset` ; (2) la seconde passe de `claude -p` couvre aussi les choix obligatoires (radio, oui/non, listes) avec la consigne « option la plus honnête d'après le CV, NON si le CV ne prouve pas l'expérience, OUI pour la mobilité sur Paris » ; (3) critère `questions_a_choix` (toutes les questions répondues) dans le rapport ; (4) la capture défile jusqu'aux questions.
- **Vérifié** : 4/4 répondues sur l'offre (mobile OUI, TJM OUI, technologies NON, 5 ans NON attendu). **À relire par l'utilisateur** : une réponse OUI/NON engage (TJM, expérience).
- **Déboguer sans polluer le compte** : `.atch.ps1 ... --no-files` ne dépose ni CV ni LM (le compte Free-Work en contient déjà 19 : critère `cv_dans_compte` ✗, à nettoyer à la main).

## Greenhouse via MyGreenhouse (2026-11-03, validé sur 10 offres)

- **Offres** : `my.greenhouse.io/jobs/search?query=...` (liste lue dans le Chrome connecté), page `my.greenhouse.io/jobs/<entreprise>/<id>` : l'offre s'ouvre en fenêtre, le formulaire « Apply for this job » est dans la même fenêtre (Prénom, Nom, E-mail préremplis par le compte, pays + téléphone, localisation, CV, LM, consentements). Bouton qui envoie : **« Submit application »** (`button[type=submit]`).
- **Pièges** : (a) la liste des pays (react-select, 200+ options) est tronquée aux 60 premières : « France » n'y est pas ; règle côté `formfill.py` : un champ « Country / Pays » vide reçoit « France » ; (b) la **localisation** est un react-select à suggestions asynchrones, sans option tant qu'on n'a rien tapé, avec le libellé « Location » en guise de texte : (i) il n'était pas lu comme champ vide, (ii) il était écarté faute d'options. Corrigé : option « saisie libre », réponse = ville du profil, saisie caractère par caractère (`execCommand('insertText')`), attente de la suggestion, clic sur la première ; (c) une offre fermée retombe sur la liste de recherche : critère `offre_indisponible` (écartée) ; (d) deux onglets sur la même offre font retomber l'autre sur la recherche : n'ouvrir qu'un onglet par offre ; (e) le champ obligatoire est signalé par `*` dans le libellé, sans attribut `required` : `champs_obligatoires` lit aussi l'astérisque ; (f) le modèle peut renvoyer du texte autour du JSON : lecture du premier objet JSON.
- **Consentements** : la case de traitement des données est cochée ; la case de conservation 730 jours (facultative) ne l'est pas ; « Dream Job » et « Apply faster next time » non touchés.
- **Envoi de test** : non fait par moi (l'extension n'a pas agi sur mon onglet de contrôle et le bas de la fenêtre dépasse la zone que je capture). Un clic sur « Submit application » dans mon onglet a été refusé par le site (champs obligatoires manquants : rien n'est parti). **À faire à la main** sur un onglet rempli.
- **Résultat** : 10 offres essayées, 8 à 9 ✓ (CV, LM, localisation, consentement, bouton visible), 1 offre fermée.
