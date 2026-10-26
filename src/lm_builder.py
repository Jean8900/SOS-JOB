"""Génère une lettre de motivation (LM) adaptée par offre, via Claude Code en
mode non-interactif (`claude -p`, abonnement Pro -- pas d'appel API séparé).

Structure (voir src/LM/README.md et src/LM/TODO.md) : plan en 4 blocs
(Journal du Net). Blocs 1 et 4 sont fixes (substitution de données connues).
Blocs 2 et 3 sont remplis par Claude Code, à partir UNIQUEMENT des faits
extraits de input/CV_originel.tex -- jamais d'invention.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import config, cv_builder

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_TEX = REPO_ROOT / "input" / "CV_originel.tex"
SIGNATURE_PNG = REPO_ROOT / "input" / "LM" / "Signature.png"
OUTPUT_TEX_DIR = REPO_ROOT / "output" / "LM" / "tex"
OUTPUT_PDF_DIR = REPO_ROOT / "output" / "LM" / "pdf"
ARCHIVE_TEX_DIR = REPO_ROOT / "output" / "LM" / "archive" / "tex"
ARCHIVE_PDF_DIR = REPO_ROOT / "output" / "LM" / "archive" / "pdf"


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


def extract_cv_facts(reference_text: str | None = None) -> str:
    """Extrait les faits vérifiables du CV (puces + stack technique), nettoyés."""
    reference_text = reference_text if reference_text is not None else REFERENCE_TEX.read_text(encoding="utf-8")
    items = re.findall(r"\\item\s+(.*?)(?=\\item|\\end\{itemize\})", reference_text, re.DOTALL)
    facts = [_latex_to_text(item) for item in items]
    stack_match = re.search(r"\\textbf\{Tech Stack:\}(.*?)\\\\", reference_text)
    if stack_match:
        facts.insert(0, "Tech Stack: " + _latex_to_text(stack_match.group(1)))
    return "\n".join(f"- {fact}" for fact in facts if fact)


def _job_description_text(job: dict) -> str:
    from . import scraper
    return scraper.html_to_text(job.get("description"))[:3000]


def _find_claude() -> str:
    for candidate in ("claude", "claude.cmd", "claude.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    raise RuntimeError("Claude Code CLI (`claude`) introuvable dans le PATH.")


_ATOUTS_MARKER = "###ATOUTS###"
_ENTREPRISE_MARKER = "###ENTREPRISE###"


def generate_blanks(job: dict, cv_facts: str) -> dict:
    """Appelle `claude -p` (abonnement Pro, aucune clé API) pour remplir les
    2 blancs de la LM. Sortie texte avec délimiteurs explicites -- plus fiable
    sur un prompt long que --json-schema (qui peut être ignoré par le modèle)."""
    prompt = f"""Tu rédiges 2 paragraphes courts d'une lettre de motivation, à partir UNIQUEMENT des faits vérifiés ci-dessous. N'invente RIEN : aucun fait, aucun chiffre, aucune techno qui n'y figure pas.

OFFRE :
Poste : {job.get('name')}
Entreprise : {(job.get('organization') or {}).get('name', '')}
Description : {_job_description_text(job)}

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
        input=prompt, capture_output=True, text=True, timeout=120, encoding="utf-8",
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
\textbf{{Objet : Candidature au poste de {job_title}}}

\vspace{{0.5cm}}
Madame, Monsieur,

Suite à votre offre de {job_title} chez {company_name}, je me permets de vous adresser ma candidature.

{atouts}

{entreprise}

Je me tiens à votre disposition pour échanger plus en détail sur ma candidature lors d'un entretien. Dans l'attente de votre retour, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

\vspace{{1cm}}
{signature_block}

\end{{document}}
"""


def render_lm_tex(job: dict, blanks: dict) -> str:
    identity = config.load_cv_template()
    name = identity["candidate_name"]
    contact = f"{identity['candidate_location']} · {identity['candidate_phone']} · {identity['candidate_email']}"
    company_name = (job.get("organization") or {}).get("name", "")
    job_title = job.get("name") or ""

    if SIGNATURE_PNG.exists():
        signature_block = f"\\includegraphics[height=2cm]{{{SIGNATURE_PNG.as_posix()}}}"
    else:
        signature_block = cv_builder.escape_latex(name)

    return _LM_TEMPLATE.format(
        candidate_name=cv_builder.escape_latex(name),
        candidate_contact=cv_builder.escape_latex(contact),
        company_name=cv_builder.escape_latex(company_name),
        job_title=cv_builder.escape_latex(job_title),
        atouts=cv_builder.escape_latex(blanks["atouts"]),
        entreprise=cv_builder.escape_latex(blanks["entreprise"]),
        signature_block=signature_block,
    )


def basename_for_job(job: dict, company_slug: str) -> str:
    return f"{cv_builder.slugify(company_slug)}_{cv_builder.slugify(job.get('slug') or job.get('name', 'job'))}"


def is_archived(basename: str) -> bool:
    return (ARCHIVE_PDF_DIR / f"{basename}.pdf").exists()


def generate_lm_for_job(job: dict, company_slug: str) -> Path:
    OUTPUT_TEX_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    basename = basename_for_job(job, company_slug)

    cv_facts = extract_cv_facts()
    blanks = generate_blanks(job, cv_facts)
    tex_content = render_lm_tex(job, blanks)

    tex_path = OUTPUT_TEX_DIR / f"{basename}.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    return cv_builder.compile_pdf(tex_path, OUTPUT_PDF_DIR)
