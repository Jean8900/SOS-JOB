# Session du 2026-11-02 : candidatures automatisées multi-sites

## Réalisé
Niveau « WTJ » atteint sur 4 sites : WTJ, Apec, HelloWork (10 offres chacun) et Free-Work (offres internes validées). Pour chaque offre, l'extension Chrome ouvre le formulaire, remplit les champs, pose le CV adapté et la LM, écrit un message personnalisé, répond aux questions OUI/NON, puis s'arrête avant l'envoi (jamais cliqué par le code).
Restent : Cadremploi (import du CV bloqué), Station F (exploré).

## Appris
- Un « Postuler » peut envoyer d'un coup (Free-Work, HelloWork) : un envoi de test par site, sur une offre hors profil.
- Un message prérempli par le site se remplace par le nôtre.
- Page rechargée ou clic ignoré = parcours cassé : rapport par offre (trace, ✓/✗, capture) pour diagnostiquer.
- Les offres qui sortent du site sont écartées, pas comptées en échec.
- Free-Work ajoute un CV et une LM à chaque candidature : nettoyage manuel (l'extension ne supprime rien).

## Commandes
`.\fill.ps1 install` puis `.\login.ps1 --all` (une fois)
`.\batch.ps1 prepare "métier" -n 10` : lot WTJ
`.\batch.ps1 --lot -n 3` : tester WTJ
`.\batch.ps1 --lot-file output\copilot\<site>_lot.json -n 3 --debug` : tester un autre site
Nouveau site : skill `site-onboarding` (10 offres réelles, boucle essai/correction, section dans `extension/EDGE_CASES.md`).

>>
.\login.ps1 #--all
>>
.\batch.ps1 --lot -n 3                                                    # WTJ (lot de technicien de maintenance)
>>
.\batch.ps1 --lot-file output\copilot\apec_lot.json -n 3                  # Apec (génie chimique)
>>
.\batch.ps1 --lot-file output\copilot\hellowork_lot.json -n 3             # HelloWork (technicien de maintenance)
>>
.\batch.ps1 --lot-file output\copilot\freework_lot.json -n 3 --generate   # Free-Work
