"""Réponses aux formulaires de candidature, rédigées par Claude (`claude -p`) à partir du CV, de la LM de
l'offre et de input/form_profile.yaml.

Appelant : le programme local fill.py (extension Chrome, Ctrl+Alt+Espace et batch.py) via
generate_answers / complete_answers / finalize_answers. Jamais de clic sur un envoi.
"""
from __future__ import annotations

import datetime
import json
import re
import time
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from . import config, language, lm_builder
from .offer import Offer

MUST_ANSWER = (
    "SECONDE PASSE : ces champs sont OBLIGATOIRES et sont restés vides à la première passe. Chacun DOIT recevoir une vraie réponse : "
    "ni null, ni \".\", ni phrase vide. Question ouverte (motivation, pourquoi nous rejoindre, expérience...) : 3 à 5 phrases sincères "
    "tirées du CV, de la lettre déjà écrite et de l'offre ; sans fait inventé (si le CV ne couvre pas le sujet, dis honnêtement ce qui s'en "
    "rapproche et la motivation à apprendre). Question à choix (OUI/NON, liste) : choisis l'option la plus honnête d'après le CV et les FAITS PERSO, copiée à l'identique parmi les options ; NON si le CV ne prouve pas l'expérience demandée ; OUI pour une mobilité vers la ville de résidence des FAITS PERSO (city).\n\n"
)

# Libellé d'un champ de localisation (mots entiers : « Ethnicity », « Milieu » ou « Velocity » ne sont pas des villes).
_LOCATION_LABEL = re.compile(r"\b(location|localisation|city|ville|lieu)\b", re.I)
_COUNTRY_LABEL = re.compile(r"^\s*(country|pays)\b(?!\s*(code|de naissance|of birth|d'origine))", re.I)

_LETTER_LABEL = re.compile(r"motivation|cover.?letter|lettre|pourquoi (?:vous|nous|tu|souhait\w+).*(?:rejoindre|postul|candidat)|why .*(?:join|apply)", re.I)
LETTER_MAX_AGE = 3600  # la LM déposée dans le dossier d'upload date de moins d'une heure : c'est celle de l'offre en cours

_UNKNOWN = (
    "genre, civilité / titre (Monsieur, Madame), origine, handicap, situation familiale, date de naissance, numéro de sécurité sociale, "
    "prétentions salariales, préavis, disponibilité, comment le candidat a connu l'offre (source de candidature), visa/autorisation de travail (sauf si présents dans les FAITS PERSO)"
)


def _limits(field: dict) -> tuple[int | None, int | None]:
    """(min, max) de caractères : attributs minlength/maxlength, sinon texte du libellé."""
    label = field.get("label", "")
    lo, hi = field.get("min_chars"), field.get("max_chars")
    if hi is None:
        m = re.search(r"(?:max(?:imum)?\.?|jusqu'à|up to|limit\w*)\D{0,12}(\d{2,5})\s*(?:car|char)|(\d{2,5})\s*(?:car\w*|char\w*)\s*max", label, re.I)
        if m:
            hi = int(m.group(1) or m.group(2))
    if lo is None:
        m = re.search(r"(?:min(?:imum)?\.?|au moins|at least)\D{0,12}(\d{2,5})\s*(?:car|char)|(\d{2,5})\s*(?:car\w*|char\w*)\s*min", label, re.I)
        if m:
            lo = int(m.group(1) or m.group(2))
    return lo, hi


def clamp(value: str, lo: int | None, hi: int | None) -> str:
    """Respecte le maximum en coupant à la dernière phrase complète qui tient."""
    value = value.strip()
    if hi is None or len(value) <= hi:
        return value
    cut = value[:hi]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rstrip().rfind("."))
    return cut[:end + 1] if end >= (lo or 0) and end > 0 else cut.rstrip()


def is_excluded(url: str, cfg: dict) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in cfg.get("fill_excluded_domains", []))


def _identity_facts() -> str:
    c = config.load_cv_template()
    return (f"Nom : {c['candidate_name']}\nEmail : {c['candidate_email']}\n"
            f"Téléphone : {c['candidate_phone']}\nVille : {c['candidate_location']}")


def generate_answers(offer: Offer, fields: list[dict], cfg: dict, letter: str = "", must_answer: bool = False) -> dict:
    for f in fields:
        lo, hi = _limits(f)
        if lo:
            f["min_chars"] = lo
        if hi:
            f["max_chars"] = hi
    # Langue des réponses = celle des questions du formulaire ; à défaut, celle de la page.
    lang = language.detect_text(" ".join(f.get("label", "") for f in fields)) or language.detect(offer)
    form_facts = "\n".join(f"{k} : {v}" for k, v in config.load_form_profile().items() if v) or "(aucun)"
    prompt = f"""Tu pré-remplis un formulaire de candidature pour le candidat ci-dessous. Le candidat relira tout avant d'envoyer.

RÈGLES : n'invente RIEN (aucun fait, chiffre, diplôme ou techno absents des sources). Pour une adresse postale (rue, code postal, ville de résidence), utilise UNIQUEMENT l'adresse des FAITS PERSO, jamais la ville du CV. Écris les noms et prénoms en casse normale (« Martini », pas « MARTINI » : certains formulaires refusent plus de 2 majuscules). REMPLIS TOUS les champs que les sources permettent de remplir : identité, ville, liens (LinkedIn ; « site web » / portfolio / GitHub = le lien GitHub du CV), entreprise actuelle et poste actuel (expérience la plus récente du CV), formation, et les questions ouvertes. Réponds null seulement si la question porte sur : {_UNKNOWN} -- SAUF si l'information figure dans les FAITS PERSO (alors utilise-la : civilité, genre, pronoms, nationalité, droit de travail, visa, salaire) --, ou si l'information est vraiment absente de toutes les sources. Questions de diversité (origine, ethnicité, handicap, religion, orientation) : choisis l'option « je préfère ne pas répondre » / « prefer not to say » si elle existe, sinon null. Pour un champ de type checkbox (case à cocher) : réponds "oui" pour la cocher, sinon null. Coche UNIQUEMENT (a) l'acceptation des conditions d'utilisation, de la politique de confidentialité ou du traitement des données pour CETTE candidature, et (b) la case de pronoms qui correspond aux FAITS PERSO. Ne coche JAMAIS : réception d'e-mails, newsletters, alertes, offres ou contacts futurs, conservation des données pour d'autres postes, enquêtes démographiques, ni aucune autre case. Pour un champ à options (select, radio, dropdown, combobox, yesno), la valeur doit être EXACTEMENT l'une des options, sinon null (radio « Avez-vous déjà travaillé pour X ? » : déduis-le du CV). Réponds dans la langue des questions du formulaire (ici : {'anglais' if lang == 'en' else 'français'}) ; les faits du CV peuvent être dans l'autre langue : traduis-les fidèlement. Pour une question ouverte (motivation, présentation), ton direct, appuyée sur la LETTRE DE MOTIVATION et les FAITS DU CV, 400 caractères environ si aucune limite n'est donnée. Si un champ a min_chars / max_chars, la réponse DOIT les respecter strictement (compte les caractères, espaces compris, et vise le milieu de la fourchette).

IDENTITÉ :
{_identity_facts()}

FAITS PERSO (config) :
{form_facts}
Date du jour : {datetime.date.today().isoformat()}. Pour un champ DATE de début / disponibilité, réponds la date du jour + 1 mois (le préavis), au format du champ (JJ/MM/AAAA, AAAA-MM-JJ...) ; pour un champ texte, reprends la disponibilité des FAITS PERSO.

CV COMPLET (liens, postes, formation) :
{lm_builder.cv_profile_text(lang)}

LETTRE DE MOTIVATION DÉJÀ ÉCRITE POUR CETTE OFFRE :
{letter or lm_builder.lm_text(offer) or "(non disponible)"}

OFFRE : {offer.title} chez {offer.company}
{offer.description[:2000]}

CHAMPS DU FORMULAIRE (JSON) :
{json.dumps(fields, ensure_ascii=False)}

{MUST_ANSWER if must_answer else ""}Réponds UNIQUEMENT par un objet JSON {{"<id du champ>": "<valeur>" ou null, ...}}, un id par champ, sans texte autour."""
    result = subprocess.run([lm_builder._find_claude(), "-p", "--permission-mode", "dontAsk", "--model", "sonnet", "--restricted"],
                            input=prompt, capture_output=True, text=True, timeout=180, encoding="utf-8",
                            creationflags=subprocess.CREATE_NO_WINDOW)  # sans console : fill.py tourne sans fenêtre, et une console volerait le focus à Chrome
    if result.returncode != 0:
        raise RuntimeError(f"claude -p a échoué (code {result.returncode}) : {result.stderr[-300:]}")
    return _first_json_object(result.stdout)


def _first_json_object(text: str) -> dict:
    """Premier objet JSON valide de la réponse : tolère du texte avant ou après, même avec des accolades dans la prose."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = decoder.raw_decode(text[start:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    raise RuntimeError(f"réponse sans JSON : {text[-300:]}")


def offer_from_context(url: str, title: str, text: str) -> Offer:
    """Contexte d'un site quelconque (hors file du copilot) : titre, domaine et texte visible de la page."""
    host = urlparse(url).hostname or "web"
    return Offer(source="web", source_id="page", url=url, url_canonique=url,
                 title=title or host, company=host, description=text[:3000])


def staged_letter(cfg: dict) -> str:
    """Texte de la LM de l'offre en cours (copié dans le dossier d'upload par apply.py / batch.py), sinon vide."""
    path = Path(__file__).resolve().parent.parent / cfg["staging_dir"] / f"LM_{cfg['file_name']}.txt"
    if not path.is_file() or time.time() - path.stat().st_mtime > LETTER_MAX_AGE:
        return ""
    return path.read_text(encoding="utf-8").strip()


def _empty(answers: dict, field: dict) -> bool:
    value = answers.get(field["id"])
    return not isinstance(value, str) or not value.strip() or value.strip() == "."


def complete_answers(offer: Offer, fields: list[dict], answers: dict, cfg: dict, letter: str = "") -> dict:
    """Garantit une vraie réponse aux champs obligatoires : la lettre déjà écrite dans un champ « motivation », puis une
    seconde passe de Claude (consigne « tu DOIS répondre ») sur les seuls champs encore vides."""
    for field in fields:
        if letter and field.get("kind") == "textarea" and _empty(answers, field) and _LETTER_LABEL.search(field.get("label", "")):
            answers[field["id"]] = letter
    profile = config.load_form_profile() or {}
    country, city = profile.get("country", ""), profile.get("city", "")
    for field in fields:  # liste de pays (souvent > 60 options, donc tronquée) : pays du profil (pas pour « Pays de naissance », « Country code »)
        if country and field.get("kind") in ("combobox", "dropdown", "select") and _empty(answers, field) and _COUNTRY_LABEL.search(field.get("label", "")):
            answers[field["id"]] = country
    for field in fields:  # champ de localisation à suggestions : ville du profil (la suggestion est choisie par l'extension)
        if city and field.get("kind") == "combobox" and _empty(answers, field) and _LOCATION_LABEL.search(field.get("label", "")):
            answers[field["id"]] = city
    todo = [f for f in fields if f.get("kind") in ("textarea", "input", "radio", "yesno", "select", "dropdown", "combobox") and _empty(answers, f)
            and (f.get("required") or "*" in f.get("label", ""))]
    if todo:
        second = generate_answers(offer, [dict(f) for f in todo], cfg, letter=letter, must_answer=True)
        for field in todo:
            value = second.get(field["id"])
            if isinstance(value, str) and value.strip() and value.strip() != ".":
                answers[field["id"]] = value
    return answers


def finalize_answers(fields: list[dict], answers: dict) -> tuple[dict, list[str]]:
    """Réponses bornées par min/max de caractères de chaque champ. Retourne (réponses, libellés sous le minimum)."""
    final, short = {}, []
    for field in fields:
        value = answers.get(field["id"])
        if not isinstance(value, str) or not value.strip():
            if field.get("kind") == "textarea" and (field.get("required") or "*" in field.get("label", "")):
                final[field["id"]] = "."  # question ouverte obligatoire sans rien à dire : un point plutôt qu'un champ bloquant
            continue
        lo, hi = _limits(field)
        value = clamp(value, lo, hi)
        if lo and len(value) < lo:
            short.append(field["label"][:40])
        final[field["id"]] = value
    return final, short
