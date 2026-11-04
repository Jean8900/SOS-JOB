---
name: site-onboarding
description: Amener un ou plusieurs sites de candidature (Apec, Indeed, Hellowork, Free-Work, WTJ...) au niveau de maturité de WTJ. Deux questions (quels sites ? sites connectés dans Chrome ?), puis boucle d'essais sur 10 offres réelles par site dans le vrai Chrome, y compris UN envoi réel de test par site (offre hors profil) pour identifier le bouton qui soumet. À utiliser quand on demande « fais la même chose pour le site X ».
---

# Amener des sites au niveau WTJ

**Mature = on essaie 10 offres réelles d'entreprises différentes ; celles qui restent sur le site arrivent au dernier écran (bouton d'envoi actif mais non cliqué par le code, CV adapté et message/LM posés, champs remplis), les cas limites sont documentés, et le bouton qui soumet est identifié pour de bon.** Une offre qui renvoie hors du site (site de l'employeur) est **écartée, sans échec** : le critère n'est pas 10/10 mais « toutes les offres internes réussissent » (par ex. 5/10 si 5 sont internes), **après avoir essayé les 10**. Noter chaque offre écartée.

La méthode est l'essentiel : **Claude ouvre 10 offres réelles sur le site, constate, corrige, rejoue, jusqu'à 10/10.** Pas de code « théorique » sans lot réel.

## 0. Au lancement : 2 questions, dans cet ordre

1. **Quels sites ?** (AskUserQuestion, cases à cocher `multiSelect`) : les sites de `input/login_sites.yaml` pas encore matures (WTJ et Apec le sont), 4 maximum par question ; « Autre » pour un site absent. Rien d'autre n'est demandé.
2. **Ouvrir les sites** cochés dans le Chrome de l'utilisateur (une URL de connexion par site, `chrome.exe <url>`), puis poser la seconde question : « **Les sites sont connectés et ouverts dans Chrome ?** » (oui / pas encore). L'utilisateur se connecte lui-même (gestionnaire de mots de passe) et revient répondre. Sur « oui » seulement, la boucle démarre. Aucune capture ni lecture de page tant que l'utilisateur n'a pas répondu « oui ».

La session est donc supposée ouverte. **Aucune question sur le bouton d'envoi** : on le découvre en allant une fois jusqu'au bout (étape 7). **Aucune question d'autorisation d'envoi** : c'est acquis, par défaut, **un envoi réel de test par site**, sur une offre sans rapport avec le profil AI engineer (technicien de maintenance, génie chimique, commercial...), pour que l'ATS refuse sans conséquence.

## 1. Aller jusqu'au bout, sur chaque site et au global (sans compter sur `/goal`)

`/goal` est une commande de l'utilisateur : le skill ne peut pas la taper. Ce qui garantit la mission complète, c'est une **liste de contrôle persistée**, pas la mémoire de la conversation :

- Écrire dès le début `output/copilot/onboarding_state.json` : pour chaque site coché, les 5 portes `lot_10_sur_10`, `ecran_final_vu`, `envoi_test_fait`, `bouton_soumission_note`, `doc_a_jour` (toutes à faux).
- **Relire ce fichier avant chaque étape et à chaque reprise** ; ne cocher une porte qu'avec une preuve (capture d'écran, compte rendu de lot, ligne dans EDGE_CASES.md).
- **Interdit de conclure tant qu'une porte est fausse**, sauf blocage qui dépend de l'utilisateur (session expirée, captcha) : dans ce cas, le dire en une ligne, passer au site suivant, et reprendre ce site plus tard.
- **Fin globale** : tous les sites ont leurs 5 portes vraies (ou un blocage nommé). Le compte rendu final est généré depuis ce fichier.
- Filet facultatif : après la question 2, afficher **une seule ligne `/goal` globale** à coller (« tous les sites de onboarding_state.json ont leurs 5 portes vraies »). Le skill fonctionne sans.

Les sites se traitent **l'un après l'autre** : un seul Chrome, un seul focus (l'extension n'agit que sur l'onglet actif de la fenêtre au premier plan), donc jamais en parallèle, ni sous-agents, ni lots simultanés.

## Garde-fous (recadrages de l'utilisateur, non négociables)

- **Le code (extension, `batch.py`) ne clique JAMAIS le bouton qui envoie** (WTJ : « J'envoie ma candidature ! », Apec : « Envoyer ma candidature »). Seul **Claude, à la main, une seule fois par site**, le clique, sur une offre hors profil, après avoir atteint le dernier écran et l'avoir vu à l'écran. But unique : **identifier avec certitude quel bouton soumet réellement** et ce qui suit (confirmation ou non), puis l'écrire dans EDGE_CASES.md. Ne jamais supposer qu'une « 2e confirmation » existe (hypothèse fausse sur WTJ). Après ce test : plus aucun envoi sur ce site.
- Choisir pour l'envoi de test une entreprise que l'utilisateur ne veut pas contacter plus tard (un doublon de candidature peut être refusé par la suite) ; le dire à l'utilisateur dans le compte rendu.
- Le bouton d'entrée « Postuler » (qui ouvre le formulaire) est permis dans le code, lui seul.
- **Identifiants : jamais d'IA dans la boucle.** Aucune saisie de mot de passe, aucun compte créé. Sur un écran de connexion réel : pas de capture, pas de lecture de champ ; demander à l'utilisateur de se connecter. Un champ mot de passe **masqué** (menu, fenêtre cachée) n'est pas un écran de connexion : vérifier sa visibilité, pas sa seule présence.
- **Vrai Chrome de l'utilisateur** pour les lots, pas le Chromium de test (`run_case.py` = profil de test ; sert à un cas isolé, jamais à la recette).
- **Aucun pilotage de souris pour recharger l'extension** (a ouvert des fenêtres Windows parasites). Demander **un** rechargement à l'utilisateur, ou câbler le changement dans `content.js` (relu à chaque injection) via un point d'entrée que l'ancienne extension appelle déjà (`clickNext`).
- **Données perso** : uniquement `input/form_profile.yaml` (hors git). Jamais dans CV, LM, doc versionnée.
- **Ne pas casser ce qui marche** : un `if` sur le nom d'hôte, code du site dans des fonctions à part (`onWtj`, `onApec`). Aucun refactor des autres sites.
- **Ne pas commiter ni pousser sans demande.** Frugal : pas de fioriture, pas de commande de plus si inutile.
- Si l'utilisateur dit « n'exécute pas / juste dis-moi » : ne rien lancer. Répondre court à « oui / non / merde ? ».

## Boucle (par site, dans cet ordre)

1. **Lister 10 offres, 10 entreprises, candidature native.** Chercher dans l'API du site le champ qui dit « candidature intégrée » (WTJ : `ats == "wkit"` ; Apec : `typeCandidature == "EMAIL_ONLY"`). Si l'API répond 403 aux scripts (cas Apec, même avec Playwright), l'appeler depuis une page du site dans le Chrome connecté. Sorties du navigateur tronquées (~1500 caractères) et bloquées si elles contiennent des URL à paramètres : sortir des lots courts, sans `=`. Écrire le lot dans `output/copilot/<site>_lot.json` (source, source_id, url, title, company, description), sur un métier hors profil (technicien de maintenance, génie chimique, commercial...).
2. **Explorer UNE offre en lecture seule** dans le Chrome connecté : cliquer d'étape en étape jusqu'au dernier écran, lister à chaque écran les contrôles (type, nom, libellé, visible, cochée), capture d'écran. Noter : boutons d'entrée, choix intermédiaires, champs fichier, champs préremplis, cases par défaut, bloc dépliable, bouton d'envoi présumé.
3. **Coder** la fonction du site dans `extension/content.js`, appelée par `clickNext()` seulement sur ce nom d'hôte. Une action par appel ; l'écran doit changer après chaque action (voir pièges).
4. **Générer CV/LM** des 10 offres (`python batch.py --lot-file ... --generate`), en arrière-plan.
5. **Lancer le lot dans le vrai Chrome** : `.\batch.ps1 --lot-file output\copilot\<site>_lot.json -n 10`. Ne pas toucher clavier/souris pendant. Lire le compte rendu, puis **regarder l'écran** : le journal ne prouve rien tout seul. Lire d'abord le **rapport structuré** (✓/✗ par critère, trace, cause de l'arrêt : `output/copilot/trace.log`, ou `--debug`), puis seulement la capture de l'extension (`output/copilot/shots/`) si ça ne suffit pas ; ne pas piloter l'écran à la main.
6. **Corriger, rejouer UNE offre (`--skip k -n 1`), puis les 10.** Ne jamais annoncer « corrigé » sans rejouer.
7. **Envoi de test (acquis par défaut, un par site)** : sur UNE offre du lot, hors profil, une fois le formulaire complet et vérifié à l'écran, Claude clique à la main le bouton présumé, relève précisément ce qui se passe (message, 2e fenêtre ou non, page de suivi), capture. Noter dans EDGE_CASES.md le libellé, le sélecteur et la conséquence. Le code garde son arrêt avant ce bouton.
8. **Documenter au fil de l'eau** dans `extension/EDGE_CASES.md`, section du site : parcours, piège, cause, correction, statut (une ligne par piège). Une ligne au README si une commande change. Mettre à jour le brouillon du jour.
9. **Compte rendu honnête** : x/10 au dernier écran (vus à l'écran, vs seulement dans le journal), bouton qui soumet identifié (oui/non, et ce qu'il a fait), onglets laissés ouverts pour la recette, ce qui n'est pas vérifié, la commande exacte à copier.
* **IMPORTANT :** MAX retry par site = 30 tentatives de fill (sur une ou plusieurs offres, au total). Si tu trouve pas 10 offres sur le site tu fais avec le nb d'offre que tu as et tu applique la regle du 30. En gros après 30 tentatives de fill sur le site tu passes au site suivant et tu note dans le compte rendu que tu n'as pas pu finir le site. Le but est d'avoir un compte rendu honnête et complet, pas de forcer à 10/10 si c'est impossible.


## Pièges transversaux déjà rencontrés (vérifier d'abord)

- **Candidature native vs renvoi employeur** : filtrer avant de préparer CV/LM (ne pas générer pour rien).
- **Boutons radio sans `for=`** (Angular) : l'entrée est le frère qui précède le libellé.
- **Étape « qui n'avance pas »** : une action qui ne change pas l'écran (cocher/décocher) fait croire à un blocage. La faire pendant le remplissage, ou l'enchaîner avec une action visible.
- **Champs fichier masqués ou absents** tant qu'un mode n'est pas choisi : sur le site, ne remplir que les champs visibles ; choisir le mode « importer » avant.
- **Valeur préremplie par le site mais bidon** (ex. Apec : « Bonjour, je me permets de vous solliciter… ») : l'effacer et la remplacer par une réponse personnalisée ; un champ non vide est sinon ignoré.
- **Un bouton « Postuler » peut envoyer d'un coup** (Free-Work : candidature en un clic, sans formulaire). Ne jamais le cliquer à l'exploration sur une offre proche du profil : explorer d'abord sur l'offre hors profil, de sorte qu'un envoi involontaire serve d'envoi de test, et le noter aussitôt.
- **Un bouton sans attribut `type` dans un `<form>` est un bouton submit** : cliquer dessus par script peut envoyer (ou tenter d'envoyer) le formulaire (Cadremploi : le bouton du CV). Avant tout clic dans un formulaire, lister `type` et `form` de chaque bouton.
- **Offre qui sort du site** : si l'offre renvoie vers l'employeur, la contourner (la noter « hors site » dans le compte rendu et dans EDGE_CASES.md), ne pas la compter comme échec.
- **Ne jamais exclure un site entier du remplissage pour contourner une difficulté** (erreur faite sur Free-Work) : on traite le parcours, on ne le désactive pas.
- **Message préinscrit par le site** (HelloWork, Apec : « Madame, Monsieur, suite à votre offre… ») : toujours l'effacer et le remplacer par un message personnalisé de quelques centaines de caractères. Un message qui reste celui du site = parcours non terminé.
- **CV du compte vs CV adapté** : si le site utilise par défaut le CV enregistré du compte, le remplacer par le CV adapté (import). Vérifier à l'écran le nom du fichier affiché.
- **Deux boutons « Postuler » différents** (Free-Work : « Je postule » = candidature rapide qui envoie, « Postuler » = formulaire) : lister tous les boutons avec leur libellé avant de cliquer, ne jamais prendre le premier venu.
- **Blocs repliables** (« Ajouter un message… ») : déplier avant de chercher le champ.
- **« Enregistrer dans mon compte » coché par défaut** : décocher (ne pas empiler dix CV adaptés).
- **Lettre de motivation** : la joindre quand le site le permet (bug Apec noté : parfois oubliée).
- **Champ obligatoire resté vide** : lettre déjà écrite posée telle quelle, puis seconde passe Claude sur les seuls champs vides, consigne « tu DOIS répondre ». Faits perso (permis, préavis, salaire) dans `form_profile.yaml`.
- **Focus** : l'extension n'agit que sur l'onglet actif de la fenêtre au premier plan ; `batch.py` remet Chrome au premier plan avant chaque ordre.
- **Sessions** : un site peut redemander une connexion à l'étape « Postuler » ; l'offre est alors mise de côté.
- **Édition de `content.js`** : fins de ligne mélangées (CRLF/LF) ; patcher par expression régulière ou via l'outil d'édition. Chemins Windows (`.\batch.ps1`) : vérifier qu'aucun caractère de contrôle (`\b`, `\f`, `\a`) ne s'est glissé quand un script les écrit.

## Ce qu'on ne fait pas

Pas de connexion automatique, pas de captcha, pas de création de compte. Aucun envoi par le code. Pas plus d'un envoi de test par site, ni sur une offre proche du profil AI engineer. Pas de rapport qui annonce 10/10 si seulement le journal le dit.
