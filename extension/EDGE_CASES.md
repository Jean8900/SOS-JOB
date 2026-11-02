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
- **« J'envoie ma candidature ! » envoie réellement la candidature** (confirmé par l'utilisateur : il n'y a pas de 2e confirmation). L'extension ne le clique jamais ; `submitReady()` détecte juste le bouton pour s'arrêter.
- **Piège** : le bouton d'entrée peut être masqué (en-tête) : on clique le bouton « bas de page » visible. L'ancienne version de `background.js` n'appelle que `clickNext()` : l'ouverture du formulaire y est donc câblée aussi (`clickNext` -> `clickEntry`), pour fonctionner sans recharger l'extension.
- **Ouvert** : après rechargement de l'extension, la LM (texte du fichier `LM_*.txt`) est posée dans le champ lettre ; avant, ce champ reçoit une réponse rédigée par Claude. Offre déjà remplie dans un onglet : seul le CV est reposé.
- **Lot 1 (10 onglets)** : 8/10 formulaires ouverts, remplis, CV posé ; HappyVore (déjà rempli, 1 fichier) ; AISPRID (« rien à remplir », à revoir : page lente ou formulaire différent).

## Champs obligatoires laissés vides, permis (2026-11-02)

- **Symptôme** : la question « Expliquez-nous pourquoi vous souhaitez nous rejoindre ! » restait vide (ou « . ») sur 4 offres WTJ sur 10. **Cause** : le programme local recevait une offre générique (page web), donc le modèle ne voyait pas la LM de l'offre ; devant une question sans fait dans le CV il répondait `null`, qui devenait « . ».
- **Correction** (`src/formfill.py` : `staged_letter`, `complete_answers`) : (1) le texte de la LM déposée dans le dossier d'upload (moins d'1 h) est donné au modèle et posé tel quel dans un champ dont le libellé évoque la motivation ; (2) seconde passe de `claude -p`, uniquement sur les champs obligatoires encore vides ou à « . », avec la consigne « tu DOIS répondre » (réponse honnête, rien d'inventé). Les champs déjà remplis ne sont pas repris. Testé hors navigateur (permis, question de motivation, question sans expérience).
- **Permis B boîte manuelle** : fait perso `driving_license` dans `input/form_profile.yaml` (exemple dans `form_profile.example.yaml`) : oui.
