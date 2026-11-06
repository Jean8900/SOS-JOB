- À coder : commande `set`, une to-do list pour un nouvel utilisateur (coche ce qui est fait, dit quoi faire ensuite). Dans l'ordre :

  1. Créer une adresse mail dédiée uniquement à la recherche d'emploi.
  2. Créer un profil Chrome associé à ce mail (noter son dossier dans `profile_directory` de `input/login_sites.yaml`).
  3. S'abonner à Claude (20 €/mois), installer Claude Code et s'y connecter (vérifier que `claude -p` répond).
  4. Installer les prérequis : Git, Python, MiKTeX ; cloner le dépôt ; créer le `.venv` ; `pip install -r requirements.txt` ; `playwright install chromium`.
  5. Récupérer les jetons Gmail pour Python : projet Google Cloud, API Gmail activée, écran de consentement avec le mail dédié en utilisateur test, identifiant OAuth « application de bureau », fichier `credentials.json`.
  6. Remplir `~/.sos-job/.env` (`GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, `GMAIL_USER`), puis lancer `alertes.py` une fois pour donner le consentement (lecture seule).
  7. Mettre son CV : `input/CV_originel.tex` et `input/CV_originel_fr.tex`, `input/cv_template.yaml`, signature `input/LM/Signature.png`, `file_name` dans `input/copilot.yaml`.
  8. Remplir ses infos de formulaire : copier `input/form_profile.example.yaml` vers `input/form_profile.yaml`.
  9. Régler ses critères dans `input/criteria.yaml`, surtout `excluded_companies` (employeur actuel !) et les entreprises suivies dans `input/companies.yaml`.
  10. Regarder si les sites proposés conviennent (`input/sites.yaml`) ; si on en veut d'autres : utiliser le skill `site-onboarding`.
  11. Créer ses comptes sur les sites choisis avec le mail dédié, et enregistrer les mots de passe dans le gestionnaire du profil Chrome.
  12. Créer les alertes email sur Apec et HelloWork (Cadremploi : pas encore lu par `alertes.py`), avec le mail dédié.
  13. Mettre l'extension dans le Chrome associé au mail : `chrome://extensions`, mode développeur, charger le dossier `extension/`.
  14. Lancer le programme local au démarrage : `.\fill.ps1 install`.
  15. Faire un essai à blanc : `.\go.ps1` avec 1 offre sur 1 site, relire le formulaire rempli, ne pas envoyer.

## Note : pilotage de l'extension
- Les 8 étapes ne sont pas pilotées par un LLM : elles sont déterministes (sélecteurs, compteurs, règles fixes : mot de passe visible, bouton d'envoi présent, bouton « Suivant » autorisé, changement d'écran dans un délai de 12 s).
- Le LLM (`claude -p`) n'intervient qu'à l'étape de remplissage d'un formulaire, pour rédiger les réponses aux champs à partir du CV et du profil. Il ne décide ni des clics, ni du passage à l'étape suivante, ni de l'envoi.
- Même chemin pour `Ctrl+Alt+Espace` et pour `go`.
- Les CV et lettres sont générés en amont, par `go`, avant le remplissage.

## Suivi des candidatures par Gmail (à faire)
- Lecture de la boîte Gmail en lecture seule, dès l'ouverture du formulaire `go`, puis toutes les 1 min pendant que `go` tourne (fil dédié, intervalle dans `input/copilot.yaml`).
- Une première lecture au chargement du formulaire, pour que le nombre d'offres disponibles par site tienne compte des candidatures confirmées par mail.
- Mise à jour de `applications.json` : confirmation de candidature -> statut « applied » (date enregistrée). Écritures sous `apps_lock`.
- Prérequis : un exemple réel de mail de confirmation (WTJ, Free-Work) pour relier le mail à l'offre (expéditeur, titre, entreprise).
- V2 : suivre aussi les refus et les suites de process (entretien, test) dans le même fil, et les afficher sur le formulaire.
- Garde-fou : lecture seule, aucun envoi ni suppression de mail ; contenu traité en local.

## Manque à gagner : offres qui renvoient vers un autre site (à faire)
- Constat : sur 53 fiches WTJ lues, 41 renvoient vers le site de l'employeur (12 seulement sont intégrées à WTJ). `go` les écarte, donc on perd la plupart des offres.
- À faire : sur chaque site qui ressort (employeur externe, Free-Work, Apec, HelloWork...), traiter la candidature jusqu'au bout, avec `/goal` : Claude relance le parcours jusqu'à ce que tout marche, plusieurs fois, site par site.
- Piste à étudier : l'étape de connexion pourrait changer (connexion préalable de chaque site externe, ou détection de la redirection avant d'ouvrir l'offre).
- Garde-fou inchangé : aucun clic sur un bouton d'envoi final, aucun identifiant saisi par le code.

## Règle des 30 tentatives : par run de go, plus par jour
- Correction : la règle compte les tentatives de remplissage par site pour un run de `go`, et non plus par jour.
- Implémentation : `batch.reset_attempts()` supprime `output/copilot/attempts.json` au démarrage de chaque run (appel dans `go.start()`).
- Le plafond par offre (5 passages par jour, `replays.json`) reste journalier : il n'a pas été demandé de le changer.
- Constat du run du 06/11 (critères AI Engineer / Data Scientist / ML Engineer / AI Research, 0-3 ans, sans lieu ni contrat) : 0 offre. La recherche WTJ envoie tous les mots-clés ensemble, WTJ ne garde que les offres qui contiennent tous ces mots (2 résultats). À corriger : une recherche par métier, puis fusion.

## CV spécifique à l'offre : WTJ déselectionne le CV du jour (correction du diagnostic)
- Vérifié sur la vidéo : à l'upload, le CV du jour est bien posé et sélectionné, et sa taille varie selon l'onglet. Le programme ne semble pas buguer.
- Hypothèse : quand un onglet reste ouvert longtemps, WTJ désélectionne le CV du jour et remet l'ancien (04/11). C'est WTJ qui modifie la sélection, pas notre code.
- Conséquence : à tenir en compte si on attend avant d'envoyer (onglets ouverts longtemps).
- Solution systématique à appliquer, WTJ comme tous les sites : supprimer tout CV et LM existants sur le site (proposés) avant de candidater, pour qu'il ne reste que celui de l'offre.

## Affichage du formulaire `go` (à faire)
- Le formulaire doit s'ouvrir directement dans le navigateur (pas seulement dans VS Code).
- Un bouton pour cocher / décocher les sites.
- En bas, un journal des étapes en direct : génération LM / CV, collecte, remplissage, offres prêtes ou à finir à la main.
- Constat : pendant le run, l'écran affichait encore « Collecte » alors que la génération était finie et le remplissage en cours. Le libellé d'étape est à corriger.

## Archivage et relance d'un run
- Pas d'archivage automatique après `go` : les LM se déplacent vers `output/LM/archive/` seulement avec `archive_lm.py`, lancé à la main.
- Relance : les offres « filled », « applied » ou « skipped » ne reviennent pas. Les CV et LM déjà générés sont réutilisés (pas de régénération). Les offres restées « pending » reviennent.

## Pendant un run : ne pas toucher à Chrome
- Constat : ouvrir un nouvel onglet Gmail (compte 8900) dans Chrome pendant le run ne l'interrompt pas, il se poursuit.
- Règle : pendant le remplissage, ne rien faire dans Chrome (pas d'onglet, pas de clic, pas de clavier). L'extension agit sur l'onglet actif de la fenêtre au premier plan, donc tout changement peut faire remplir le mauvais onglet ou ignorer un ordre.
- À vérifier : si le focus change sans rien toucher, l'ordre est-il ignoré ou repris ?

## Divers
- On a dit bonjour à Pierre-Jean, en 200 caractères.
