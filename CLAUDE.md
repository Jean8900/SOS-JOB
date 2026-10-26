# SOS-JOB — garde-fous

- Toute valeur modifiable par l'utilisateur (critères, entreprises, colonnes du
  tableau, textes d'ancrage du CV) vit dans `input/` (voir `input/README.md`),
  lue via `src/config.py`. `src/` ne doit contenir aucune valeur "à l'utilisateur"
  en dur.
- `input/CV_originel.tex` est la source de vérité du CV : ne jamais l'écraser
  ni le modifier par un script. Les variantes générées vivent uniquement dans
  `output/CV/`.
- Tout texte dynamique injecté dans un `.tex` (titre de poste, ville, nom
  d'entreprise...) doit passer par `cv_builder.escape_latex()` avant insertion.
- Avant de committer, toujours relire `git diff` sur les fichiers `.tex`
  générés/modifiés pour repérer une injection LaTeX mal échappée.
- `output/CV/` et `output/LM/` ne sont pas versionnés (données générées,
  régénérables à tout moment via `python run.py`).
- Une entreprise qui échoue au scraping (`src/scraper.py`) ne doit jamais
  interrompre les autres : logguer l'erreur et continuer.
