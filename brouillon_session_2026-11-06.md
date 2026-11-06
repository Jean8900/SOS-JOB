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
