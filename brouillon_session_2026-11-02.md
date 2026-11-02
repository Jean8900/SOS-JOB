# Brouillon — session du 02/11/2026

## Explication métier

Candidater coûte du temps surtout au moment du formulaire : retaper identité, adresse, liens, puis rédiger les mêmes réponses à « pourquoi nous ? » sur chaque site. Cette session ajoute le remplissage de ces formulaires, partout sur le web.

- **CV et LM texte.** Le dossier d'upload contient maintenant la LM en texte brut (sans signature) en plus des deux PDF : certains sites demandent un texte à coller plutôt qu'un fichier.
- **Un raccourci, tous les sites.** `Ctrl+Alt+Espace` dans Chrome ou Edge remplit les champs vides de la page : identité, adresse, liens, entreprise actuelle, questions ouvertes (dans la langue des questions, avec les limites de caractères), Oui/Non, listes. Tu relis, tu uploades, tu envoies : rien n'est jamais soumis automatiquement.
- **Infos perso à part.** L'adresse, le salaire, le préavis vivent dans un fichier local hors git : ils servent aux formulaires, jamais au CV ni à la LM.
- **Ne plus postuler chez son employeur.** Illuin est exclu, même quand les filtres sont coupés.

## Explication technique

- **Extension Chrome/Edge** (`extension/`, Manifest V3) : lit les champs vides de chaque cadre de la page, appelle le programme local, écrit les réponses (frappe simulée, événements `input`/`change`) et surligne ce qui est rempli. `content.js` est le seul code qui touche à la page.
- **Programme local** (`fill.py`) : serveur HTTP sur 127.0.0.1 (`/poll`, `/answers`) et raccourci global Windows (`RegisterHotKey`). Il identifie le navigateur actif par le nom du processus de la fenêtre, envoie l'ordre à l'extension de ce navigateur, puis fait rédiger les réponses par `claude -p` (CV complet + profil perso + texte de la page) et borne leur longueur.
- **Démarrage automatique** : `.\fill.ps1 install` (raccourci dans le dossier Démarrage, `pythonw`, journal dans `output/copilot/fill.log`).
- **Copilot (`apply.ps1`)** : navigation dans l'onglet actif (plus d'onglets accumulés), profil Chrome dédié avec port de débogage et remplissage via Playwright (`Ctrl+Alt+F`).
- **Autres** : LM texte relue depuis le `.tex` (inverse de `escape_latex`) ; compilation PDF sans `perl` (repli sur `pdflatex`) ; exclusion d'entreprises appliquée aussi sans filtres.

## Choix effectués

- **Extension plutôt que profil Chrome dédié.** Chrome et Edge refusent le port de débogage sur le profil habituel ; l'extension garde les connexions, marche dans tous les onglets et dans Edge.
- **Raccourci global côté Windows** : `Ctrl+Alt+…` est refusé par l'API de raccourcis des extensions.
- **Sécurité** : écoute 127.0.0.1 seulement, en-tête dédié, refus de toute origine non-extension ; LinkedIn exclu (conditions d'utilisation) ; pas de mot de passe, de compte ni de captcha gérés ; jamais de clic sur « Envoyer ».
- **Aucune invention** : un fait absent des sources laisse le champ vide ; la civilité et les questions de diversité ne sont pas devinées.
- **Retrouver les champs par `id`/`name`**, pas par une étiquette posée au départ : Workday recrée les éléments après chaque saisie.
- **Gardé tel quel** : lecture des champs dupliquée entre l'extension et `apply.ps1` (à unifier, voir TODO).

## Achievement (1000 caractères)

Aujourd'hui, un seul geste remplit un formulaire de candidature sur n'importe quel site, dans Chrome comme dans Edge : `Ctrl+Alt+Espace`. Testé au vrai clavier sur Lever, Ashby et Workday (Deloitte), le programme lit les champs vides, fait rédiger par Claude des réponses fidèles au CV, dans la langue du formulaire et dans les limites de caractères, puis les écrit en les surlignant pour relecture. Les cas difficiles sont couverts : listes à auto-complétion (ville), boutons Oui/Non, listes déroulantes Workday, champs recréés par la page. L'adresse reste dans un fichier local hors git, absent du CV et de la LM. Le programme se lance au démarrage de Windows, n'écoute que sur la machine et n'envoie jamais rien : le dernier clic reste à toi. Côté copilot : LM en texte pour les formulaires qui n'acceptent pas de fichier, navigation dans un seul onglet, PDF compilés même sans `perl`, et Illuin définitivement exclu des offres. Reste : charger l'extension dans tes navigateurs, puis tester sur de vraies offres.

---

## Suite de la session : lot de candidatures WTJ (upload, ouverture du formulaire, passes de réponses)

### Explication métier

On va maintenant jusqu'au bout du geste de candidature, sans l'envoyer. Un lot cherche des offres WTJ (ex. technicien de maintenance), génère CV et LM, ouvre chaque offre dans le vrai Chrome, remplit tout et pose le CV. Il ne reste qu'à relire et cliquer « J'envoie ma candidature ! ». Premier lot : 10 offres de 10 entreprises, 8 formulaires prêts sur 10 (HappyVore déjà rempli ; AISPRID à revoir).

### Explication technique

- **Upload** : l'extension demande le PDF au programme local (`/file?k=cv|lm|lmtxt`), crée un `File` et le pose dans `input[type=file]`. Validé sur Lever et WTJ.
- **Lot** : `batch.py` (+ `batch.ps1`) ouvre l'offre dans le Chrome habituel, remet la fenêtre au premier plan, commande le remplissage par `/trigger` puis lit `/result`. `wtj_prepare.py` choisit les offres (`ats == "wkit"` = formulaire intégré à WTJ) et génère CV/LM.
- **WTJ** : bouton « Postuler » (ouvre seulement le formulaire) cliqué via `clickNext`, formulaire en fenêtre `role=dialog`.
- **Réponses** : le programme local reçoit la LM de l'offre ; une question de motivation reçoit le texte de la LM, puis une seconde passe force une réponse sur les seuls champs obligatoires restés vides. Profil : permis B (boîte manuelle), préavis 1 mois, disponibilité.

### Choix effectués

- **Jamais de clic sur « J'envoie ma candidature ! »** : sur WTJ il envoie réellement (l'utilisateur l'a vérifié ; une première hypothèse d'une 2e confirmation était fausse). Le code détecte le bouton pour s'arrêter, rien de plus.
- **Pas de connexion automatique** : session WTJ ouverte par l'utilisateur ; un mot de passe demandé arrête l'offre.
- **Pas de rechargement d'extension par la souris** : deux essais ont fait apparaître des fenêtres Windows parasites ; l'ouverture du formulaire a été câblée dans une fonction que l'ancienne extension appelle déjà.
- **Ouvert** : relire les LM (réponses rédigées), la LM exacte posée dans le champ lettre demande de recharger l'extension, Workday multi-pages non validé en vrai.

### Achievement (1000 caractères)

Une commande prépare un lot d'offres WTJ (CV et LM générés), une autre les ouvre dans ton Chrome, un onglet chacune. Pour chaque offre, l'extension clique « Postuler », remplit identité, questions et lettre de motivation, coche le consentement, pose le CV, puis s'arrête juste avant « J'envoie ma candidature ! » : tu relis et tu envoies. Premier essai réel : 10 entreprises de technicien de maintenance, 8 formulaires prêts. Un champ obligatoire resté vide reçoit désormais une seconde passe de réponse, et les faits perso (permis B boîte manuelle, préavis d'un mois) sont connus. Limite : seules les offres à formulaire intégré à WTJ sont ciblées, les autres renvoient vers l'employeur.
