"""Génère une lettre de motivation (LM) adaptée par offre, via Claude Code en
mode non-interactif (`claude -p`, abonnement Pro -- pas d'appel API séparé).

Structure (voir src/LM/README.md et src/LM/TODO.md) : plan en 4 blocs
(Journal du Net). Blocs 1 et 4 sont fixes (substitution de données connues).
Blocs 2 et 3 sont remplis par Claude Code, à partir UNIQUEMENT des faits
extraits de input/CV_originel.tex -- jamais d'invention.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import config, cv_builder, language
from .offer import Offer

REPO_ROOT = Path(__file__).resolve().parent.parent
SIGNATURE_PNG = REPO_ROOT / "input" / "LM" / "Signature.png"
OUTPUT_TEX_ROOT = REPO_ROOT / "output" / "LM" / "tex"
OUTPUT_PDF_ROOT = REPO_ROOT / "output" / "LM" / "pdf"
ARCHIVE_TEX_ROOT = REPO_ROOT / "output" / "LM" / "archive" / "tex"
ARCHIVE_PDF_ROOT = REPO_ROOT / "output" / "LM" / "archive" / "pdf"


def tex_dir_for_source(source: str) -> Path:
    return OUTPUT_TEX_ROOT / source


def pdf_dir_for_source(source: str) -> Path:
    return OUTPUT_PDF_ROOT / source


def archive_pdf_dir_for_source(source: str) -> Path:
    return ARCHIVE_PDF_ROOT / source


def _latex_to_text(tex: str) -> str:
    """Nettoyage LaTeX -> texte brut, volontairement simple (suffisant pour
    extraire des faits lisibles, pas pour un rendu fidèle)."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\(begin|end)\{[^}]*\}", "", tex)  # environnements : jeter, pas garder le nom
    for _ in range(3):
        tex = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?\{([^{}]*)\}", r"\2", tex)
    tex = re.sub(r"\\%", "%", tex)
    tex = re.sub(r"\\&", "&", tex)
    tex = re.sub(r"\\_", "_", tex)
    tex = tex.replace(r"\cdot", "·")
    tex = re.sub(r"\\[a-zA-Z]+\*?", "", tex)  # commandes sans accolade restantes (\Huge, \small...)
    tex = re.sub(r"[{}$]", "", tex)  # groupes de scope restants + signes $ de maths
    tex = tex.replace("\\\\", "\n")
    tex = re.sub(r"[ \t]+", " ", tex)
    return tex.strip()


def extract_cv_facts(reference_text: str | None = None, lang: str = "en") -> str:
    """Extrait les faits vérifiables du CV de la langue demandée (puces + stack technique), nettoyés."""
    if reference_text is None:
        reference_text = cv_builder.reference_path(lang).read_text(encoding="utf-8")
    items = re.findall(r"\\item\s+(.*?)(?=\\item|\\end\{itemize\})", reference_text, re.DOTALL)
    facts = [_latex_to_text(item) for item in items]
    stack_match = re.search(r"\\textbf\{Tech Stack:\}(.*?)\\\\", reference_text)
    if stack_match:
        facts.insert(0, "Tech Stack: " + _latex_to_text(stack_match.group(1)))
    return "\n".join(f"- {fact}" for fact in facts if fact)


def cv_profile_text(lang: str = "en") -> str:
    """CV complet en texte brut, liens conservés (« LinkedIn (https://...) ») : pour remplir des formulaires
    (liens, poste actuel, formation), là où extract_cv_facts ne garde que les puces de réalisations."""
    tex = cv_builder.reference_path(lang).read_text(encoding="utf-8")
    body = tex[tex.index(r"\begin{document}"):]
    body = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", r"\2 (\1)", body)
    return re.sub(r"\n{3,}", "\n\n", _latex_to_text(body))



def _job_description_text(offer: Offer) -> str:
    return offer.description[:3000]


def _find_claude() -> str:
    for candidate in ("claude", "claude.cmd", "claude.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    npm = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if npm.exists():  # installation npm globale hors PATH (programme lancé au démarrage de Windows)
        return str(npm)
    raise RuntimeError("Claude Code CLI (`claude`) introuvable dans le PATH.")


_ATOUTS_MARKER = "###ATOUTS###"
_ENTREPRISE_MARKER = "###ENTREPRISE###"


def generate_blanks(offer: Offer, cv_facts: str, lang: str = "fr") -> dict:
    """Appelle `claude -p` (abonnement Pro, aucune clé API) pour remplir les
    2 blancs de la LM. Sortie texte avec délimiteurs explicites -- plus fiable
    sur un prompt long que --json-schema (qui peut être ignoré par le modèle)."""
    langue = "en français" if lang == "fr" else "EN ANGLAIS (les faits ci-dessous peuvent être en français : traduis-les fidèlement)"
    prompt = f"""Tu rédiges 2 paragraphes courts d'une lettre de motivation, rédigés {langue}, à partir UNIQUEMENT des faits vérifiés ci-dessous. N'invente RIEN : aucun fait, aucun chiffre, aucune techno qui n'y figure pas.

OFFRE :
Poste : {offer.title}
Entreprise : {offer.company}
Description : {_job_description_text(offer)}

FAITS VÉRIFIÉS DU CANDIDAT (seule source autorisée) :
{cv_facts}

Réponds EXACTEMENT dans ce format, rien d'autre avant/après/entre les deux blocs :

{_ATOUTS_MARKER}
(80-120 mots : 2-3 réalisations chiffrées et concrètes, choisies parmi les faits ci-dessus, pertinentes pour CE poste. Ton humain, direct, 1re personne, phrases courtes. Aucun superlatif vague sans chiffre à l'appui.)
{_ENTREPRISE_MARKER}
(40-60 mots : pourquoi CETTE entreprise précisément, à partir de sa description ci-dessus. Pas de généralités interchangeables.)
"""
    # Le prompt est envoyé par stdin, pas en argument CLI : sur Windows, claude.cmd
    # passe par cmd.exe qui tronque un argument multi-lignes au premier saut de ligne.
    result = subprocess.run(
        [_find_claude(), "-p",
         "--permission-mode", "dontAsk",
         "--model", "sonnet",
         "--restricted"],
        input=prompt, capture_output=True, text=True, timeout=120, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p a échoué (code {result.returncode}):\n{result.stderr[-1000:]}")

    text = result.stdout
    if _ATOUTS_MARKER not in text or _ENTREPRISE_MARKER not in text:
        raise RuntimeError(f"claude -p n'a pas respecté le format attendu:\n{text[-1500:]}")
    atouts = text.split(_ATOUTS_MARKER, 1)[1].split(_ENTREPRISE_MARKER, 1)[0].strip()
    entreprise = text.split(_ENTREPRISE_MARKER, 1)[1].strip()
    return {"atouts": atouts, "entreprise": entreprise}


_LM_TEMPLATE = r"""\documentclass[11pt, a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[margin=2.5cm]{{geometry}}
\usepackage{{hyperref}}
\usepackage{{graphicx}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{10pt}}

\begin{{document}}

{candidate_name} \\
{candidate_contact}

\vspace{{1cm}}
\begin{{flushright}}
{company_name}
\end{{flushright}}

\vspace{{0.5cm}}
\textbf{{{subject}}}

\vspace{{0.5cm}}
{salutation}

{intro}

{atouts}

{entreprise}

{closing}

\vspace{{1cm}}
{signature_block}

\end{{document}}
"""


# Parties fixes de la LM selon la langue ({job} et {company} sont échappés LaTeX avant insertion).
_LM_TEXTS = {
    "fr": {
        "subject": "Objet : Candidature au poste de {job}",
        "salutation": "Madame, Monsieur,",
        "intro": "Suite à votre offre de {job} chez {company}, je me permets de vous adresser ma candidature.",
        "closing": "Je me tiens à votre disposition pour échanger plus en détail sur ma candidature lors d'un entretien. "
                   "Dans l'attente de votre retour, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
    },
    "en": {
        "subject": "Subject: Application for the position of {job}",
        "salutation": "Dear Hiring Manager,",
        "intro": "Following your job posting for {job} at {company}, I am pleased to submit my application.",
        "closing": "I would welcome the opportunity to discuss my application with you in an interview. "
                   "Thank you for your time and consideration, and I look forward to hearing from you.\n\nYours sincerely,",
    },
}


def render_lm_tex(offer: Offer, blanks: dict, lang: str = "fr") -> str:
    identity = config.load_cv_template()
    name = identity["candidate_name"]
    contact = f"{identity['candidate_location']} · {identity['candidate_phone']} · {identity['candidate_email']}"
    company_name = offer.company
    job_title = offer.title

    if SIGNATURE_PNG.exists():
        signature_block = f"\\includegraphics[height=2cm]{{{SIGNATURE_PNG.as_posix()}}}"
    else:
        signature_block = cv_builder.escape_latex(name)

    texts = {k: v.format(job=cv_builder.escape_latex(job_title), company=cv_builder.escape_latex(company_name))
             for k, v in _LM_TEXTS[lang].items()}
    return _LM_TEMPLATE.format(
        candidate_name=cv_builder.escape_latex(name),
        candidate_contact=cv_builder.escape_latex(contact),
        company_name=cv_builder.escape_latex(company_name),
        **texts,
        atouts=cv_builder.escape_latex(blanks["atouts"]),
        entreprise=cv_builder.escape_latex(blanks["entreprise"]),
        signature_block=signature_block,
    )


def basename_for_job(offer: Offer) -> str:
    return cv_builder.basename_for_offer(offer)


def is_archived(offer: Offer) -> bool:
    basename = basename_for_job(offer)
    return (archive_pdf_dir_for_source(offer.source) / f"{basename}.pdf").exists()


def lm_text(offer: Offer) -> str | None:
    """LM en texte brut (de « Madame, Monsieur, » à la formule de politesse, sans signature),
    relue depuis le .tex pour couvrir aussi les LM déjà générées ou archivées."""
    name = f"{basename_for_job(offer)}.tex"
    tex_path = next((p for p in (tex_dir_for_source(offer.source) / name,
                                 ARCHIVE_TEX_ROOT / offer.source / name) if p.exists()), None)
    if tex_path is None:
        return None
    parts = tex_path.read_text(encoding="utf-8").split(r"\vspace{0.5cm}")
    if len(parts) < 3:
        return None
    body = parts[2].split(r"\vspace{1cm}")[0]
    # Inverse de cv_builder.escape_latex (séquences longues d'abord, puis les caractères simples) ; les remplacements
    # Unicode (\, $\rightarrow$...) redeviennent des caractères lisibles, jamais du LaTeX collé dans un formulaire.
    inverse = {v: k for k, v in cv_builder._LATEX_SPECIAL_CHARS.items()}
    inverse.update({v: k for k, v in cv_builder._UNICODE_FIXES.items() if v.startswith(("\\", "$"))})  # pas les tirets (« - » reste « - »)
    body = re.sub("|".join(re.escape(s) for s in sorted(inverse, key=len, reverse=True)),
                  lambda m: inverse[m.group(0)], body)
    return re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"


def generate_lm_for_job(offer: Offer) -> Path:
    tex_dir = tex_dir_for_source(offer.source)
    pdf_dir = pdf_dir_for_source(offer.source)
    tex_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    basename = basename_for_job(offer)

    lang = language.detect(offer)
    cv_facts = extract_cv_facts(lang=lang)
    blanks = generate_blanks(offer, cv_facts, lang)
    tex_content = render_lm_tex(offer, blanks, lang)

    tex_path = tex_dir / f"{basename}.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    return cv_builder.compile_pdf(tex_path, pdf_dir)
