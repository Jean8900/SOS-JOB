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

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_TEX = REPO_ROOT / "input" / "CV_originel.tex"
OUTPUT_TEX_DIR = REPO_ROOT / "output" / "CV" / "tex"
OUTPUT_PDF_DIR = REPO_ROOT / "output" / "CV" / "pdf"

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


def _job_city(job: dict) -> str:
    offices = job.get("offices") or ([job["office"]] if job.get("office") else [])
    for office in offices:
        if office and office.get("city"):
            return office["city"]
    if job.get("remote") in ("full", "partial"):
        return "Remote"
    return "France"


def _job_role_label(job: dict) -> str:
    profession = job.get("profession") or {}
    category_name = profession.get("category_name") or {}
    label = category_name.get("en") or category_name.get("fr")
    if label:
        return label
    name = job.get("name") or ""
    return " ".join(name.split()[:4]) or "Open to new opportunities"


def render_header(reference_text: str, objective: str, location: str) -> str:
    header_start = reference_text.index("% --- HEADER ---")
    header_end = reference_text.index(r"\end{center}", header_start)
    header_block = reference_text[header_start:header_end]

    if "AI Engineer -- Centrale Lyon Graduate" not in header_block:
        raise ValueError("Ancre du header introuvable (sous-titre) -- input/CV_originel.tex a changé, adapte cv_builder.py.")
    if "Paris \\quad$\\cdot$\\quad" not in header_block:
        raise ValueError("Ancre du header introuvable (localisation) -- input/CV_originel.tex a changé, adapte cv_builder.py.")

    new_header_block = header_block.replace(
        "AI Engineer -- Centrale Lyon Graduate",
        f"{escape_latex(objective)}", 1,
    ).replace(
        "Paris \\quad$\\cdot$\\quad",
        f"{escape_latex(location)} \\quad$\\cdot$\\quad", 1,
    )
    return reference_text[:header_start] + new_header_block + reference_text[header_end:]


def build_tex_for_job(job: dict, reference_text: str | None = None) -> str:
    reference_text = reference_text if reference_text is not None else REFERENCE_TEX.read_text(encoding="utf-8")
    objective = f"{_job_role_label(job)} -- Open to {_job_city(job)}"
    return render_header(reference_text, objective, _job_city(job))


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


def generate_cv_for_job(job: dict, company_slug: str) -> Path:
    OUTPUT_TEX_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    basename = f"{slugify(company_slug)}_{slugify(job.get('slug') or job.get('name', 'job'))}"
    tex_content = build_tex_for_job(job)
    tex_path = OUTPUT_TEX_DIR / f"{basename}.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    return compile_pdf(tex_path, OUTPUT_PDF_DIR)
