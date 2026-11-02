# Extension SOS-JOB Remplissage (Chrome et Edge)

`Ctrl+Alt+Espace` dans Chrome ou Edge pré-remplit les champs vides du formulaire de l'onglet actif : identité, adresse, liens, entreprise actuelle, questions ouvertes (longueurs min/max respectées), boutons Oui/Non, listes. Rien n'est envoyé : tu relis, tu uploades, tu valides.

Deux morceaux : cette extension (lit et remplit la page) et le programme local [`fill.py`](../fill.py) (raccourci global, rédaction des réponses par Claude avec ton CV et `input/form_profile.yaml`). Ils se parlent sur `127.0.0.1` uniquement.

## Installation (une fois par navigateur)

1. Lancer le programme local au démarrage : `.\fill.ps1 install` (depuis la racine du repo).
2. Chrome : `chrome://extensions` -> activer **Mode développeur** -> **Charger l'extension non empaquetée** -> choisir ce dossier `extension`.
3. Edge : `edge://extensions` -> **Mode développeur** -> **Charger l'extension décompressée** -> même dossier.

Chrome et Edge affichent un avertissement « extensions en mode développeur » à chaque démarrage : c'est normal pour une extension chargée ainsi (clique « Annuler » / ferme le message).

## Sécurité

- Le programme local n'écoute que sur `127.0.0.1`, et refuse toute requête qui ne vient pas d'une extension (en-tête dédié, origine `chrome-extension://`) : une page web ne peut pas l'appeler.
- L'extension n'a aucun accès réseau externe : elle ne parle qu'au programme local.
- Désactivé sur les sites listés dans `fill_excluded_domains` (`input/copilot.yaml`, LinkedIn par défaut).
- Tes infos perso (adresse...) vivent dans `input/form_profile.yaml`, ignoré par git.
- Le port (47321) est dans `input/copilot.yaml` (`fill_server_port`) **et** dans `background.js` : les garder identiques.

## Dépannage

- « extension non connectée » dans `output/copilot/fill.log` : l'extension n'est pas chargée dans ce navigateur, ou elle dort ; elle se réveille toutes les 30 s.
- Rien ne se passe : vérifier `.\fill.ps1 status`, puis que la fenêtre active est bien Chrome ou Edge.
