"""Tableau de bord d'avancement du copilot : une page HTML locale réécrite à
chaque changement et rechargée automatiquement par le navigateur. Affichage
seul, aucun script, aucune entrée."""
from __future__ import annotations

import os
from html import escape
from pathlib import Path

REFRESH_SECONDS = 1

_CSS = """
:root { --bg:#f6f7f9; --card:#fff; --ink:#1b2430; --muted:#6b7686; --line:#e3e7ee;
        --accent:#1e6bd6; --done:#1f9d6b; --skip:#c47a14; --track:#e8ecf2; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#12161c; --card:#1b212a; --ink:#e8edf4; --muted:#93a0b2; --line:#2a323d;
          --accent:#5b9cf5; --done:#41c48f; --skip:#e0a040; --track:#2a323d; } }
* { box-sizing:border-box; }
body { margin:0; padding:8px 14px; background:var(--bg); color:var(--ink);
       font:14px/1.4 system-ui, "Segoe UI", sans-serif; height:100vh; overflow:hidden; }
.top { display:flex; align-items:baseline; gap:14px; }
.pct { font-size:28px; font-weight:700; letter-spacing:-1px; }
.count { color:var(--muted); font-size:15px; }
.state { margin-left:auto; font-size:12px; padding:2px 10px; border-radius:99px;
         background:var(--track); color:var(--muted); }
.state.done { background:var(--done); color:#fff; }
.bar { height:10px; background:var(--track); border-radius:99px; overflow:hidden; margin:4px 0 8px; }
.bar > i { display:block; height:100%; background:var(--accent); border-radius:99px; }
.cols { display:grid; grid-template-columns: 1.25fr 1fr; gap:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:7px 10px; }
.card h2 { margin:0 0 6px; font-size:11px; font-weight:600; text-transform:uppercase;
           letter-spacing:.06em; color:var(--muted); }
.offer-title { font-size:16px; font-weight:600; }
.meta { color:var(--muted); font-size:13px; margin-top:2px; }
.pill { display:inline-block; margin-top:5px; padding:1px 9px; border-radius:99px; font-size:12px;
        background:var(--track); }
.pill.applied { background:var(--done); color:#fff; } .pill.skipped { background:var(--skip); color:#fff; }
.stats { display:flex; gap:16px; margin-top:6px; }
.stats b { font-size:20px; display:block; } .stats span { color:var(--muted); font-size:12px; }
.row { display:grid; grid-template-columns: 1fr auto; gap:2px 8px; margin-bottom:4px; font-size:13px; }
.row .mini { grid-column:1 / 3; height:5px; background:var(--track); border-radius:99px; overflow:hidden; }
.row .mini > i { display:block; height:100%; background:var(--done); }
.keys { margin-top:6px; color:var(--muted); font-size:12px; }
kbd { background:var(--track); border-radius:4px; padding:0 5px; font:inherit; font-size:11px; }
.warn { margin-top:6px; color:var(--skip); font-size:12px; }
"""

_STATE_LABEL = {"running": "en cours", "done": "lot terminé", "quit": "arrêté"}
_STATUS_LABEL = {"pending": "à faire", "applied": "candidaté", "skipped": "passé"}


def render(stats: dict, state: str = "running") -> str:
    """stats : total, done, applied, skipped, current (dict), per_source ([(source, done, total)]), warnings."""
    total, done = stats["total"], stats["done"]
    pct = 100 * done // total if total else 0
    cur = stats.get("current") or {}

    offer_html = ""
    if cur:
        offer_html = (
            f'<div class="offer-title">{escape(cur["title"])}</div>'
            f'<div class="meta">{escape(cur["company"])} &middot; {escape(cur["location"] or "lieu ?")}'
            f' &middot; {escape(cur["source"])}</div>'
            f'<span class="pill {escape(cur["status"])}">{_STATUS_LABEL.get(cur["status"], "?")}</span>'
            f'<span class="meta"> &nbsp;offre {cur["index"]}/{total}</span>'
        )

    sources_html = "".join(
        f'<div class="row"><span>{escape(source)}</span><span>{d}/{t}</span>'
        f'<div class="mini"><i style="width:{100 * d // t if t else 0}%"></i></div></div>'
        for source, d, t in stats["per_source"]
    )
    warnings_html = "".join(f'<div class="warn">{escape(w)}</div>' for w in stats.get("warnings", []))

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>SOS-JOB Copilot</title><style>{_CSS}</style></head>
<body>
<div class="top"><span class="pct">{pct}&nbsp;%</span><span class="count">{done} / {total} offres traitées</span>
<span class="state {'done' if state == 'done' else ''}">{_STATE_LABEL.get(state, state)}</span></div>
<div class="bar"><i style="width:{pct}%"></i></div>
<div class="cols">
  <div class="card"><h2>Offre en cours</h2>{offer_html or '<div class="meta">&mdash;</div>'}
    <div class="stats"><div><b>{stats["applied"]}</b><span>candidatées</span></div>
    <div><b>{stats["skipped"]}</b><span>passées</span></div>
    <div><b>{total - done}</b><span>restantes</span></div></div></div>
  <div class="card"><h2>Par site</h2>{sources_html}</div>
</div>
<div class="keys"><kbd>Ctrl</kbd>+<kbd>Alt</kbd>+ <kbd>&rarr;</kbd> candidaté &nbsp; <kbd>&larr;</kbd> précédente
 &nbsp; <kbd>S</kbd> passer &nbsp; <kbd>Q</kbd> quitter</div>
{warnings_html}
</body></html>"""


def write(path: Path, html: str) -> None:
    """Écriture atomique : le navigateur ne lit jamais une page à moitié écrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, path)
