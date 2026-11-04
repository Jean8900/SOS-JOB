ChooseYourBoss retiré : ses offres renvoient vers Cadremploi, déjà couvert. Mentions supprimées ici.

- Gmail 8888 : le jeton OAuth (sandbox/gmail_test.ipynb) expire ou est révoqué (invalid_grant). Il faut supprimer token.json et relancer le notebook pour reconsentir (lecture seule). Difficulté récurrente.

- Alertes mail (Gmail 8888, API lecture seule) : mails Apec/HelloWork lus, liens de suivi décodés (Apec : paramètre e en base64 -> n° d'offre ; HelloWork : redirection 302 -> id), 5 offres de chacun mises dans un lot et remplies, onglets laissés ouverts. Pour boucler proprement : un script unique alertes.py (lire mails -> décoder -> lot JSON -> batch.py), à lancer chaque matin ; pas de nouveau skill, mettre à jour site-onboarding (section « source des offres »). Garder le jeton hors du dépôt.

- Fait : alertes Apec/HelloWork lues (Gmail 8888), 10 offres (5+5) remplies jusqu avant l envoi, onglets vérifiés par toi OK ; hors-site Apec/HelloWork écartés ; README mis à jour.
