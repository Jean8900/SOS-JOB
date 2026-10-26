# LM — lettres de motivation

Objectif : une LM par offre cochée, générée par Claude Code (pas d'API) → zéro coût hors abonnement Pro.

Structure fixe : plan en 4 blocs de [Journal du Net](https://www.journaldunet.com/management/guide-du-management/1200753-lettre-de-motivation-conseils-et-un-exemple-gratuit/).

Blancs : ton humain, concret, chiffré ; stack technique seulement si présente dans le CV. Rien d'inventé.

Frugalité : pas de tokens facturés → frugalité = contexte minimal par lettre, pas d'optimisation API.

Outil : [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). Source unique des faits : `input/CV_originel.tex`.

Commandes : `.\run.ps1` (TUI, saute les LM déjà archivées) · `.\run.ps1 all` (pas de TUI) · `.\run.ps1 force` (régénère) · `.\archive_lm.ps1` (archive, écrase les doublons). Détails : `TODO.md` + `README.md` racine.
