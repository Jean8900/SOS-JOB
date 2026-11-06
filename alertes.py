"""Alertes email -> lot d'offres. Lit (en lecture seule) les mails d'alerte Apec et HelloWork de Gmail,
décode les liens de suivi en offres, et écrit output/copilot/alertes_lot.json (lu par batch.py --lot-file).

Décodage, sans requête vers les sites :
- Apec : lien neomarket.diffusion.apec.fr/r/?e=<base64> ; e décodé = « p1=www.apec.fr&p2=<n° d'offre>&... »
- HelloWork : lien emails.hellowork.com/clic/.../<base64> ; dernier segment décodé = « <email>🪢<url de l'offre> »

Usage : python alertes.py [--days 3] [--out output/copilot/alertes_lot.json] [--sites apec hellowork]
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import gmail  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
OUT = REPO_ROOT / "output" / "copilot" / "alertes_lot.json"
SITES = {  # requête Gmail par site d'alertes
    "apec": "from:offres@diffusion.apec.fr",
    "hellowork": "from:alerte@emails.hellowork.com",
}


class _Anchors(HTMLParser):
    """(href, texte) de chaque lien du mail."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[list[str]] = []
        self._open: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._open = [dict(attrs).get("href") or "", ""]
            self.links.append(self._open)

    def handle_endtag(self, tag):
        if tag == "a":
            self._open = None

    def handle_data(self, data):
        if self._open is not None:
            self._open[1] += data


def _b64(s: str) -> str:
    try:
        return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")
    except ValueError:
        return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def apec_id(href: str) -> str | None:
    if "diffusion.apec.fr/r/" not in href:
        return None
    e = (parse_qs(urlparse(href).query).get("e") or [""])[0]
    m = re.search(r"p2=(\d{6,}W)", _b64(e))
    return m.group(1) if m else None


def hellowork_id(href: str) -> str | None:
    if "emails.hellowork.com/clic/" not in href:
        return None
    m = re.search(r"hellowork\.com/fr-fr/emplois/(\d+)\.html", _b64(href.rstrip("/").rsplit("/", 1)[-1]))
    return m.group(1) if m else None


def parse(site: str, mail: dict) -> list[dict]:
    """Offres d'un mail d'alerte : une par identifiant, titre = premier texte de lien non vide qui la pointe."""
    parser = _Anchors()
    parser.feed(mail["html"])
    decode = apec_id if site == "apec" else hellowork_id
    texts: dict[str, list[str]] = {}
    for href, text in parser.links:
        oid = decode(html.unescape(href))
        if oid:
            texts.setdefault(oid, [])
            if _clean(text):
                texts[oid].append(_clean(text))
    day = time.strftime("%d/%m/%Y", time.localtime(mail["date_ms"] / 1000))
    offers = []
    for oid, parts in texts.items():
        title = next((t for t in parts if not re.fullmatch(r"(voir|postuler|je postule|consulter).*", t, re.I)), "")
        url = (f"https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{oid}" if site == "apec"
               else f"https://www.hellowork.com/fr-fr/emplois/{oid}.html")
        offers.append({"source": site, "source_id": oid, "company": "", "title": title, "location": "",
                       "description": f"{title}, offre issue de l'alerte {site} du {day}.", "url": url})
    return offers


def collect(days: int, sites: list[str], interactive: bool = True) -> list[dict]:
    service = gmail.get_service(interactive=interactive)
    lot, seen = [], set()
    for site in sites:
        ids = gmail.search(service, f"{SITES[site]} newer_than:{days}d", limit=20)
        found = 0
        for msg_id in ids:
            mail = gmail.get_message(service, msg_id)
            for offer in parse(site, mail):
                if (site, offer["source_id"]) not in seen:
                    seen.add((site, offer["source_id"]))
                    lot.append(offer)
                    found += 1
        print(f"  {site} : {len(ids)} mail(s) d'alerte, {found} offre(s)")
    return lot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="mails des N derniers jours")
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--sites", nargs="*", default=list(SITES), choices=list(SITES))
    parser.add_argument("--no-browser", action="store_true", help="jeton invalide : erreur au lieu d'ouvrir le consentement")
    args = parser.parse_args()
    try:
        lot = collect(args.days, args.sites, interactive=not args.no_browser)
    except gmail.GmailError as exc:
        raise SystemExit(f"Gmail : {exc}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lot, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in lot[:10]:
        print(f"    [{o['source']}] {o['title'][:70]}")
    print(f"{len(lot)} offre(s) -> {out}")


if __name__ == "__main__":
    main()
