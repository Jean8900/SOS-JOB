"""Prépare un lot WTJ : N offres d'un métier (ex. « technicien de maintenance »), une par entreprise,
avec CV et LM générés pour chacune. Écrit output/copilot/wtj_lot.json (lu par batch.py --lot).

Usage : python wtj_prepare.py "technicien de maintenance" -n 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config, cv_builder, lm_builder, scraper  # noqa: E402
from src.connectors.welcome_to_the_jungle import _to_offer  # noqa: E402

OUT = Path(__file__).resolve().parent / "output" / "copilot" / "wtj_lot.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+", help="un ou plusieurs mots-clés (résultats cumulés)")
    parser.add_argument("-n", type=int, default=10)
    args = parser.parse_args()

    companies_cfg = config.load_companies()
    anchor = scraper.get_company_jobs_config(scraper.company_url(companies_cfg.get("anchor_company") or companies_cfg["companies"][0], "fr"))
    hits = [h for q in args.query for h in scraper.fetch_broad_search_hits(anchor, query=q, max_pages=10)]
    previous = OUT.parent / "wtj_lot_1.json"  # premier lot : on n'y repostule pas
    org_of = lambda o: o["url"].split("/companies/")[1].split("/")[0]  # noqa: E731
    lot = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() and "--reset" not in sys.argv else []  # on complète le lot en cours
    seen = {org_of(o) for o in lot} | ({org_of(o) for o in json.loads(previous.read_text(encoding="utf-8"))} if previous.exists() else set())
    for hit in hits:
        org = (hit.get("organization") or {}).get("slug")
        title = (hit.get("name") or "").lower()
        if not org or org in seen or "maintenance" not in title or not any(w in title for w in ("technicien", "technicienne", "tech ")):
            continue
        try:
            job = scraper.fetch_job_detail(org, hit["slug"])
            if job.get("ats") != "wkit":  # candidature intégrée à WTJ (les autres renvoient vers le site de l'employeur)
                continue
            offer = _to_offer(job, org)
            cv_builder.generate_cv_for_job(offer)
            lm_builder.generate_lm_for_job(offer)
        except Exception as exc:  # noqa: BLE001 -- une offre ratée n'arrête pas le lot
            print(f"  ignorée ({org}) : {exc}")
            continue
        seen.add(org)
        lot.append({"company": offer.company, "title": offer.title, "url": offer.url, "source": offer.source,
                    "source_id": offer.source_id, "location": offer.location})
        print(f"  {len(lot)}/{args.n} {offer.company} : {offer.title}")
        OUT.write_text(json.dumps(lot, ensure_ascii=False, indent=1), encoding="utf-8")
        if len(lot) >= args.n:
            break
    OUT.write_text(json.dumps(lot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(lot)} offre(s) -> {OUT}")


if __name__ == "__main__":
    main()
