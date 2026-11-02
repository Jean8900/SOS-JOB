"""Génère un CV PDF adapté par offre, à partir du CV LaTeX de référence.

Garde-fous (cf. CLAUDE.md) :
- ne modifie jamais input/CV_originel.tex, uniquement des copies dans output/CV/
- échappe tout texte dynamique injecté dans le LaTeX (titres de poste, villes...)
- le remplacement du header est scopé au bloc \\begin{center}...\\end{center}
  pour ne jamais toucher le reste du CV (expériences, etc.)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import config, language
from .offer import Offer

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_TEX = REPO_ROOT / "input" / "CV_originel.tex"
REFERENCE_TEX_FR = REPO_ROOT / "input" / "CV_originel_fr.tex"
OUTPUT_TEX_ROOT = REPO_ROOT / "output" / "CV" / "tex"
OUTPUT_PDF_ROOT = REPO_ROOT / "output" / "CV" / "pdf"


def tex_dir_for_source(source: str) -> Path:
    return OUTPUT_TEX_ROOT / source


def pdf_dir_for_source(source: str) -> Path:
    return OUTPUT_PDF_ROOT / source

_LATEX_SPECIAL_CHARS = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def escape_latex(text: str) -> str:
    return "".join(_LATEX_SPECIAL_CHARS.get(ch, ch) for ch in text)


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "job"


def reference_path(lang: str) -> Path:
    """CV source selon la langue de l'offre : anglais (CV_originel.tex) ou français (CV_originel_fr.tex)."""
    return REFERENCE_TEX_FR if lang == "fr" else REFERENCE_TEX


def render_header(reference_text: str, objective: str, location: str, lang: str = "en") -> str:
    anchors = config.load_cv_template()
    subtitle_anchor = anchors["subtitle_anchor_fr"] if lang == "fr" else anchors["subtitle_anchor"]
    location_anchor = anchors["location_anchor"]

    header_start = reference_text.index("% --- HEADER ---")
    header_end = reference_text.index(r"\end{center}", header_start)
    header_block = reference_text[header_start:header_end]

    if subtitle_anchor not in header_block:
        raise ValueError(
            f"Ancre du header introuvable (subtitle_anchor=\"{subtitle_anchor}\") -- "
            "input/CV_originel.tex a changé, mets à jour input/cv_template.yaml."
        )
    if location_anchor not in header_block:
        raise ValueError(
            f"Ancre du header introuvable (location_anchor=\"{location_anchor}\") -- "
            "input/CV_originel.tex a changé, mets à jour input/cv_template.yaml."
        )

    new_header_block = header_block.replace(
        subtitle_anchor, escape_latex(objective), 1,
    ).replace(
        location_anchor, f"{escape_latex(location)} \\quad$\\cdot$\\quad", 1,
    )
    return reference_text[:header_start] + new_header_block + reference_text[header_end:]


def build_tex_for_job(offer: Offer, reference_text: str | None = None) -> str:
    lang = language.detect(offer)
    if reference_text is None:
        reference_text = reference_path(lang).read_text(encoding="utf-8")
    location = offer.location or "France"
    template = config.load_cv_template()[f"objective_{lang}"]
    objective = template.replace("{title}", offer.title).replace("{location}", location)
    return render_header(reference_text, objective, location, lang)


def _find_latexmk() -> str:
    found = shutil.which("latexmk")
    if found:
        return found
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\latexmk.exe"),
        r"C:\Program Files\MiKTeX\miktex\bin\x64\latexmk.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("latexmk introuvable. Vérifie l'installation de MiKTeX.")


_AUX_EXTENSIONS = (".aux", ".log", ".fls", ".fdb_latexmk", ".out", ".synctex.gz")


def compile_pdf(tex_path: Path, pdf_dir: Path) -> Path:
    """Compile tex_path en PDF dans pdf_dir.

    MiKTeX émet parfois un avertissement non bloquant ("major issue: So far,
    you have not checked for MiKTeX updates.") sur stderr qui peut faire
    remonter un code de sortie non nul alors que le PDF a bien été produit.
    Pour ne jamais confondre ça avec un vrai échec -- ni laisser un ancien
    PDF d'un run précédent faire illusion -- on supprime le PDF existant
    avant de compiler : sa (ré)apparition après coup est le seul signal de
    succès qui compte.
    """
    latexmk = _find_latexmk()
    pdf_path = pdf_dir / (tex_path.stem + ".pdf")
    pdf_path.unlink(missing_ok=True)

    pdflatex = Path(latexmk).with_name("pdflatex.exe")
    if shutil.which("perl") is None and pdflatex.exists():
        # latexmk est un script perl : sans perl dans le PATH (cas d'un PowerShell sans Git\usr\bin),
        # on appelle pdflatex directement, deux passes pour les références.
        for _ in range(2):
            result = subprocess.run(
                [str(pdflatex), "-interaction=nonstopmode", "-halt-on-error",
                 f"-output-directory={pdf_dir}", str(tex_path)],
                capture_output=True, text=True, timeout=120,
            )
    else:
        result = subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={pdf_dir}", str(tex_path)],
            capture_output=True, text=True, timeout=120,
        )

    if not pdf_path.exists():
        diagnostics = f"--- stdout ---\n{result.stdout[-2000:]}\n--- stderr ---\n{result.stderr[-1000:]}"
        raise RuntimeError(f"Compilation LaTeX échouée pour {tex_path.name} (code {result.returncode}):\n{diagnostics}")
    if result.returncode != 0:
        print(f"[cv_builder] Note: latexmk a renvoyé le code {result.returncode} pour {tex_path.name} mais le PDF a bien été produit -- stderr: {result.stderr.strip()[-300:]}")

    for ext in _AUX_EXTENSIONS:
        aux_file = pdf_dir / (tex_path.stem + ext)
        if aux_file.exists():
            aux_file.unlink()
    return pdf_path


def basename_for_offer(offer: Offer) -> str:
    return f"{slugify(offer.company)}_{slugify(offer.source_id or offer.title)}"


def generate_cv_for_job(offer: Offer) -> Path:
    tex_dir = tex_dir_for_source(offer.source)
    pdf_dir = pdf_dir_for_source(offer.source)
    tex_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    basename = basename_for_offer(offer)
    tex_content = build_tex_for_job(offer)
    tex_path = tex_dir / f"{basename}.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    return compile_pdf(tex_path, pdf_dir)
