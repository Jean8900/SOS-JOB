# Session du 2026-11-03 : cap et idée d'outil

## Décision de cap
On met la collecte d'offres (lot 2 par mail compris) de côté. Le besoin : tu donnes des liens d'offre, le système candidate jusqu'au bouton d'envoi, sans le cliquer. Priorité : le plus de sites possible en « candidater bêtement » (Cadremploi, Station F, talent.io, Workday réel).

## À faire plus tard : arbre des features (skill local, commité automatiquement)
**But.** Rester lucide en divergeant. Chaque idée ou divergence = une feuille ; la feuille est un tableau à critères fixes.

**Critères (fixes).** type (idée / divergence) · statut (todo / dev / validé) · achievement · blocage · essayé sans succès · test (commande ou CI) · dernière preuve (commit, capture) · prochaine action · dernière MAJ.

**Méthode.** Le skill parcourt la codebase (git, TODO, `EDGE_CASES.md`, rapports de lots), remplit le plus possible de façon déterministe, et l'IA ne complète que le reste (synthèse, blocages, prochaine action).

### 3 versions MVP
1. **Fichier unique.** Script Python : lit `git log`, les chemins touchés, `onboarding_state.json` et les ✓/✗ des rapports, puis écrit `FEATURES.md` (une table par feuille). Les champs d'IA sont remplis à la main. Commit à la main.
2. **Une feuille = un fichier** `features/<branche>/<feuille>.yaml`. Skill `feature-tree` en fin de session : calcule les critères déterministes, l'IA propose le reste, tu valides, commit automatique `chore(features)`.
3. **Vue visuelle.** Arbre HTML généré à chaque commit (branches repliables, couleur par statut, filtre « divergences ouvertes », liens vers commits, tests, captures) et vue « reprise » : les 3 feuilles à rouvrir. Détection des divergences non référencées.
(si possible faudrait que ce skill soit adaptable à d'autre projet, si besoin faut le lancer une première fois avant de faire un projet pour que ca m'aide à choisir les bonnes pratiques et critères spécifiques à ce projet... voir l'existant)
