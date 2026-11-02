# Brouillon — session du 30/10/2026

## Résumé de la journée

Lots 1 (7 sites) et 1.5 (Greenhouse, Lever, Ashby via entreprises WTJ) testés de bout en bout ; ChooseYourBoss passé en lot 2, aijobs.net mis de côté. Copilot de candidature (`apply.ps1`) : Chrome, dossier d'upload aux noms fixes, tableau de bord HTML, raccourcis Ctrl+Alt. Suivi Excel avec colonne « Mise à jour » fusionnée devant les notes. Cas limites corrigés (formules, liens, état corrompu). Filtres coupés temporairement. 3 commits, rien poussé.

## Perspectives (nouveaux sites, profils AI / forward deployed / agentique)

- **Sans code** : ajouter à la main dans `input/ats_companies.yaml` les labs et scale-ups IA (Anthropic, OpenAI, Mistral, Cohere, Perplexity, Scale AI, Databricks, Hugging Face, LangChain, Palantir, Sierra, Glean, Harvey, ElevenLabs) ; requêtes de découverte « Forward Deployed Engineer / Agentic / LLM » ; métiers « Forward Deployed / Applied AI / Agent » dans `criteria.yaml`.
- **Peu de code** : VIE (Business France), Remotive / RemoteOK (API), We Work Remotely (RSS), « Ask HN: Who is hiring ? ».
- **Grands groupes** : connecteurs Workday, SmartRecruiters, Workable (API par entreprise, même principe que les ATS).
- **Pas de scraping** : LinkedIn, Indeed, Glassdoor (anti-bot) -> alertes email (lot 2).
- **International** : CV et LM selon la langue de l'offre (voir ci-dessous), lieux étrangers à autoriser.

## Recette : les 10 features à vérifier et améliorer (UX / UI)

Pour chacune : vérifier que ça marche (OK), puis noter ce qui gêne.

1. **Collecte multi-sites** (`.\run.ps1`) — les 10 sites répondent ; un site en échec n'arrête pas les autres.
   - [ ] OK  [ ] UX/UI : lisibilité des messages de collecte
2. **Découverte ATS** (Greenhouse / Lever / Ashby) — entreprises issues de WTJ, cache, 5 offres max par entreprise.
   - [ ] OK  [ ] UX/UI : faux positifs d'entreprise (ex. « vinci »), durée du 1er run
3. **Filtre + sélection TUI** — critères `criteria.yaml`, `disable_filters`, cases à cocher.
   - [ ] OK  [ ] UX/UI : remettre les filtres, plafond 100 réparti par site
4. **CV adapté** (PDF) — accroche et lieu changés, texte échappé.
   - [ ] OK  [ ] UX/UI : relecture rapide du CV généré
5. **Lettre de motivation** (Claude) — archive, `force`, pas de régénération inutile.
   - [ ] OK  [ ] UX/UI : qualité du style, boucle de relecture
6. **File d'attente du copilot** — offres générées enregistrées sans doublon après `run`.
   - [ ] OK  [ ] UX/UI : message quand des offres sont ignorées (PDF manquant)
7. **Disposition des fenêtres** (`.\apply.ps1`) — Chrome gauche, Explorateur haut droit, tableau de bord bas droit.
   - [ ] OK (à tester sur ton PC)  [ ] UX/UI : bannières cookies / navigateur par défaut, onglets qui s'accumulent
8. **Raccourcis Ctrl+Alt** (→ candidaté, ← précédente, S passer, Q quitter) + PDF aux noms fixes écrasés.
   - [ ] OK (vrai clavier)  [ ] UX/UI : conflits de raccourcis, retour visuel
9. **Tableau de bord HTML** — progression, reste, par site, offre en cours.
   - [ ] OK  [ ] UX/UI : lisibilité en quart d'écran, état « lot terminé »
10. **Suivi Excel** (`.\suivi.ps1`) — « Mise à jour // Notes », lignes manuelles conservées.
    - [ ] OK (avec Excel/LibreOffice)  [ ] UX/UI : ouverture sans Excel, colonnes réponse / relance

## Ajout en fin de session : CV et LM selon la langue

Détection fr/en de l'offre (mots-outils, `src/language.py`), `CV_originel_fr.tex` (traduction du CV anglais), gabarits de LM français et anglais. Vérifié sur 266 offres (WTJ, Free-Work, CNRS, Station F en français ; ATS surtout en anglais) et sur une offre de chaque langue (CV + LM en PDF). À améliorer : offres sans description, localisation trop longue dans le header du CV.
