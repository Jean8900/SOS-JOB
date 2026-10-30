"""Connecteurs multi-sources : chaque module expose fetch(max_results) -> list[Offer].

Convention commune (voir chaque module pour le détail par site) :
- Jamais de session connectée à un compte personnel.
- User-Agent honnête, au moins 1-2s entre deux requêtes (voir connectors.http).
- Un site en échec ne doit jamais interrompre les autres (géré par le run.py appelant).
"""
