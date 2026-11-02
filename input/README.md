# input/ — tout ce que tu peux modifier toi-même

- Tes critères de matching → [`criteria.yaml`](criteria.yaml)
- Tes entreprises suivies → [`companies.yaml`](companies.yaml)
- Les colonnes du tableau interactif → [`table_columns.yaml`](table_columns.yaml)
- Ton CV source → [`CV_originel.tex`](CV_originel.tex) (anglais) et sa traduction [`CV_originel_fr.tex`](CV_originel_fr.tex) (français) : l'offre en français utilise le CV et la LM français, l'offre en anglais les anglais. Si tu modifies l'un, répercute sur l'autre.
- Les textes du CV utilisés pour l'adaptation automatique du header → [`cv_template.yaml`](cv_template.yaml)
- Ta signature pour les LM (facultatif, `.png`) → [`LM/Signature.png`](LM/Signature.png)

- Les sites de la tournée de connexion → [`login_sites.yaml`](login_sites.yaml)
- Tes infos perso pour les formulaires (adresse, salaire...), **local et hors git** → `form_profile.yaml` (modèle : [`form_profile.example.yaml`](form_profile.example.yaml))

Rien d'autre à éditer : le code dans `src/` ne contient plus de valeur "à toi".
