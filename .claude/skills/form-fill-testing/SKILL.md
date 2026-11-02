---
name: form-fill-testing
description: Tester, corriger et documenter l'extension de remplissage de formulaires de candidature (extension/ + fill.py + src/formfill.py) sur de vrais sites d'offres d'emploi. À utiliser quand on demande de tester le remplissage sur des offres, de chasser des cas limites, ou de corriger un champ mal rempli.
---

# Tester et corriger le remplissage de formulaires

Boucle : **ouvrir un vrai formulaire -> remplir avec l'extension -> constater l'échec -> corriger -> rejouer -> documenter**.

## Garde-fous (non négociables)

- **Jamais cliquer sur l'envoi final** : `envoyer`, `soumettre`, `postuler`, `candidater`, `valider`, `confirmer`, `submit`, `apply`, `send`, `finish`, `terminer`. En cas de doute sur un bouton, ne pas cliquer.
- Jamais saisir de mot de passe, créer de compte, résoudre un captcha, cocher un consentement, uploader un fichier.
- **Identifiants : jamais d'IA dans la boucle.** Quand un mot de passe (ou un code) est saisi dans une page, par l'utilisateur ou par son gestionnaire de mots de passe, **aucune capture d'écran, aucun `read_page` / `get_page_text`, aucun JavaScript qui lit la valeur d'un champ** tant que la page de connexion est affichée : une capture ou la lecture du DOM peut exposer la valeur (champ affiché en clair, bouton « afficher »). Attendre que l'utilisateur dise que la connexion est faite, puis seulement reprendre.
- Pas de connexion à la place de l'utilisateur : seuls les formulaires accessibles sans compte, ou dans une session que l'utilisateur a ouverte lui-même, sont testés.
- Ne pas commiter, ne pas pousser. Ne pas lire `~/.sos-job`.
- Les infos perso (adresse...) restent dans `input/form_profile.yaml` (hors git) : ne jamais les copier dans un fichier versionné, ni dans `EDGE_CASES.md`, ni dans les captures montrées.

## Où sont les instructions (et où ne pas les mettre)

| Ce que lit... | Où vivent ses instructions |
|---|---|
| Claude Code (moi, quand on travaille dans le repo) | `CLAUDE.md` (règles du repo) et `.claude/skills/*/SKILL.md` (ce fichier) : **tout le repo** est accessible, pas seulement `extension/` |
| `claude -p` appelé par le programme local pour rédiger les réponses (sans outils, sans fichiers) | le prompt écrit en dur dans `src/formfill.py` (`generate_answers`) : c'est là qu'on règle le comportement du remplissage |
| Le navigateur | `extension/` uniquement (code, pas d'instructions) |

`extension/EDGE_CASES.md` est un journal de cas, pas un endroit d'instructions.

## Outils

- État du programme local : `.\fill.ps1 status` ; journal : `output\copilot\fill.log`.
- Banc d'essai : `python extension\test\run_case.py <url> [--browser chrome|edge] [--name cas]` (Chromium qui charge l'extension, vrai `Ctrl+Alt+Espace`, champs remplis affichés, capture dans `output\copilot\ext_tests\`).
- Les modifications de `fill.py` demandent de relancer le programme (`.\fill.ps1 uninstall` puis `install`). Celles de `extension/` demandent de recharger l'extension (Chromium de test : automatique à chaque lancement ; Chrome de l'utilisateur : bouton « recharger » de `chrome://extensions`).
- Attention : l'extension de l'utilisateur écoute le même programme local. Un ordre peut aussi lui parvenir ; seule l'instance dont la fenêtre a le focus agit (version courante de `background.js`).

## Boucle de test

1. Choisir un formulaire : la liste des ATS de `output/ats_cache.json` (Lever, Greenhouse, Ashby), ou n'importe quelle offre publique (Workable, SmartRecruiters, Teamtailor, Recruitee, Personio...).
2. Lancer `run_case.py`. Lire le message, la liste « rempli » et la capture.
3. Comparer avec le formulaire : champs vides restants, valeurs fausses, langue, longueurs, erreurs de validation affichées par la page.
4. Pour chaque défaut : trouver la cause (inspecter le DOM avec Playwright, ne pas deviner), corriger au plus petit endroit (`extension/content.js` pour la page, `src/formfill.py` pour la rédaction), rejouer.
5. Ajouter une ligne à `extension/EDGE_CASES.md` (site, symptôme, cause, correction, statut). Un défaut non résolu = statut « ouvert », avec ce qui a été essayé.
6. Vérifier qu'un cas déjà corrigé ne régresse pas (rejouer un Lever et un Ashby de référence).

## Étapes multiples

Passer à l'étape suivante est permis uniquement par les boutons listés dans « Étapes multiples » de `EDGE_CASES.md`, jamais par un bouton d'envoi, et on s'arrête à l'étape de révision.

## Compte rendu

À la fin : nombre de sites testés, cas corrigés, cas ouverts, et ce qui a été modifié. Ne rien présenter comme corrigé sans l'avoir rejoué.

## Parcours par site (WTJ, Apec...)

Un site au parcours propre (bouton d'entrée, import de CV, étapes) a **une fonction dédiée dans `extension/content.js`** (gardée par le nom d'hôte : `onWtj`, `onApec`) et **une section dans `extension/EDGE_CASES.md`** (parcours, pièges, cas écartés). On n'y touche pas pour un autre site. L'exception sur « postuler » ne vaut que pour le **bouton d'entrée** de ces parcours (il ouvre le formulaire) ; le bouton qui envoie (WTJ : « J'envoie ma candidature ! », Apec : « Envoyer ma candidature ») n'est jamais cliqué. Méthode : lot de 10 offres réelles, `.\batch.ps1`, captures de l'écran final, une ligne de journal par piège.

Pour amener un **nouveau site** au niveau de WTJ (lot de 10 offres réelles, parcours dédié) : voir le skill `site-onboarding`.
