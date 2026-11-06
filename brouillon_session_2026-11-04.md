ChooseYourBoss retiré : ses offres renvoient vers Cadremploi, déjà couvert. Mentions supprimées ici.

- Gmail 8888 : le jeton OAuth (sandbox/gmail_test.ipynb) expire ou est révoqué (invalid_grant). Il faut supprimer token.json et relancer le notebook pour reconsentir (lecture seule). Difficulté récurrente.

- Alertes mail (Gmail 8888, API lecture seule) : mails Apec/HelloWork lus, liens de suivi décodés (Apec : paramètre e en base64 -> n° d'offre ; HelloWork : redirection 302 -> id), 5 offres de chacun mises dans un lot et remplies, onglets laissés ouverts. Pour boucler proprement : un script unique alertes.py (lire mails -> décoder -> lot JSON -> batch.py), à lancer chaque matin ; pas de nouveau skill, mettre à jour site-onboarding (section « source des offres »). Garder le jeton hors du dépôt.

- Fait : alertes Apec/HelloWork lues (Gmail 8888), 10 offres (5+5) remplies jusqu avant l envoi, onglets vérifiés par toi OK ; hors-site Apec/HelloWork écartés ; README mis à jour.

- j'ai l'impression que le login beug / alertes.py marche depuis mail pour wtj >>> wtf ?
- Démo / TNR V1 (.\demo.ps1) : alertes email (alertes.py, Apec + HelloWork, affichées seulement) -> WTJ « Software Engineer » : CV + LM générés puis 3 offres remplies jusqu'avant l'envoi (3 essais max par offre, 20 au total), diaporama des onglets, verdict ; écran filmé par ffmpeg dans output/demo/<date>/demo.mp4 (+ rapport.md). Versions suivantes : les autres sites (Apec, HelloWork, Free-Work...).
- Plus tard (pas en V1) : flouter les infos perso (nom, téléphone, adresse, e-mails) dans la vidéo avant de la mettre sur GitHub.

- Fait (soir) : alertes.py + src/gmail.py (Gmail lecture seule ; Apec : param e en base64 -> p2=n° d'offre ; HelloWork : dernier segment du lien /clic/ en base64 -> URL de l'offre, pas besoin de la redirection 302). 6 mails -> 151 offres (124 Apec, 27 HelloWork) ; entreprise et ville vides (pas extraites des mails). C'est pour Apec/HelloWork, pas pour WTJ : les offres WTJ viennent de la recherche WTJ (wtj_prepare.iter_offers).
- Fait : wtj_prepare.py découpé en générateur iter_offers (même CLI) ; demo.py + demo.ps1 (étapes 0-4, ffmpeg gdigrab, rapport.json/.md, code de sortie TNR) ; README mis à jour.
- 1er run de la démo (22h14, output/demo/2026-11-04_221415/demo.mkv) : vidéo OK. Alertes OK. Préparation WTJ (recherche + CV + LM) ≈ 15-30 s par offre, pas 8 min. Remplissage : 0/3, 9 essais ratés sur 3 offres (Licorne Society, Galadrim, L'Atelier), surtout « message_lettre » raté (lettre non écrite dans le textarea WTJ), parfois « envoi_visible », 1 délai dépassé (369 s). Run coupé à l'offre 4 (fin de session) : .mkv pas remuxé en .mp4, pas de rapport.md.
- À faire : comprendre pourquoi message_lettre échoue sur WTJ (régression extension ou changement du site ?) ; filtrer les offres hors France ou en stage (Galadrim Madrid) ; relancer .\demo.ps1 jusqu'au vert.
