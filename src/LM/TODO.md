# TODO — Génération des LM (A à Z)

À cocher au fur et à mesure. Un item non coché = pas encore fait, pas de suppositions.

## A. Décisions de contenu
- [x] Choix de la structure fixe de la LM → plan en 4 blocs, [Journal du Net](https://www.journaldunet.com/management/guide-du-management/1200753-lettre-de-motivation-conseils-et-un-exemple-gratuit/) :
  1. **Origine de la candidature** — fixe, pas de génération (poste + entreprise, pure substitution de données déjà connues)
  2. **Atouts en lien avec le poste** — bloc variable (blanc)
  3. **L'entreprise elle-même** — bloc variable (blanc)
  4. **Conclusion** — fixe (formule de politesse + signature)
- [x] Consignes des blancs :
  - **Bloc 2 (atouts)** : 80-120 mots, 2-3 réalisations chiffrées, ton humain/direct/concret, 1re personne. Phrases courtes. Aucun superlatif vague sans chiffre à l'appui.
  - **Bloc 3 (entreprise)** : 40-60 mots, pourquoi CETTE entreprise précisément (à partir de sa description scrapée), pas de généralités interchangeables.
  - **Règle commune aux deux blancs** : uniquement des faits/chiffres/stack technique présents dans `input/CV_originel.tex` — zéro invention, zéro extrapolation.
- [x] Source des "faits CV" : v1 = extraction automatique des `\item` + ligne Tech Stack de `input/CV_originel.tex` (`lm_builder.extract_cv_facts`), nettoyage LaTeX→texte simple. Pas encore un format structuré dédié (JSON) — amélioration possible plus tard si le nettoyage LaTeX montre ses limites.
- [x] Format de sortie final : `.tex` compilé en PDF (même toolchain que le CV, `cv_builder.compile_pdf` réutilisé telle quelle).
- [x] Signature : image PNG incluse via `\includegraphics` si `input/LM/Signature.png` existe, sinon nom tapé en toutes lettres.

## B. Génération (Claude Code, pas d'API)
- [x] Caching : **non applicable**. Le caching de prompt (`prompt caching`, `Batch API`) est une optimisation de coût propre aux appels API facturés au token — ça ne s'applique pas ici puisqu'on passe par Claude Code en interactif, dans l'abonnement Pro. L'équivalent le plus proche : garder `CLAUDE.md` + ce dossier `src/LM/` stables d'une session à l'autre, pour ne pas avoir à réexpliquer les consignes à chaque LM.
- [x] Déclenchement : intégré dans `run.py`, après la génération des CV, pour chaque offre sélectionnée (TUI ou suffixe `all`).
- [x] Consignes (prompt) écrites dans `lm_builder.generate_blanks` — sortie texte avec délimiteurs `###ATOUTS###` / `###ENTREPRISE###` (plus fiable que `--json-schema` sur un prompt long, qui peut être ignoré par le modèle).
- [x] Garde-fou "rien d'inventé" vérifié manuellement sur un cas réel (génération pour une offre Illuin : chiffres et faits cités correspondent exactement à `input/CV_originel.tex`).
- [x] **Piège Windows découvert et corrigé** : `claude.cmd` passe par `cmd.exe`, qui tronque un prompt multi-lignes passé en argument au premier saut de ligne. Le prompt doit être envoyé par **stdin** (`subprocess.run(..., input=prompt)`), jamais en argument CLI.

## C. Apprentissage de style
- [ ] Définir comment les LM validées (post-relecture utilisateur) sont conservées comme exemples de style pour les suivantes
- [ ] Définir le seuil "peu d'historique → relecture complète" vs "historique riche → relecture allégée"

## D. Intégration projet
- [x] Nommage et rangement : `output/LM/tex/`, `output/LM/pdf/`, `output/LM/archive/{tex,pdf}/` (cohérent avec `output/CV/`)
- [x] `input/README.md` référence `input/LM/Signature.png`
- [x] Commande d'archivage : `archive_lm.ps1` (déplace tout, écrase les doublons dans l'archive)
- [x] Suffixes `run.ps1` : `all` (saute la TUI), `force` (régénère malgré l'archive), combinables — testés tous les trois en conditions réelles (voir `README.md` racine)
- [ ] Mise à jour de `TODO.md` (racine, roadmap MVP2) une fois l'apprentissage de style (section C) fait aussi
