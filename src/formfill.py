"""Pré-remplissage des formulaires de candidature (Ctrl+Alt+F du copilot).

Lit les champs de la page ouverte dans le Chrome du copilot (port de débogage,
via Playwright), fait rédiger les réponses par Claude (`claude -p`) à partir du
CV, de la LM et des faits de input/copilot.yaml, puis les écrit dans les champs
vides et les surligne pour la relecture. Ne touche ni aux fichiers à uploader,
ni aux cases à cocher / boutons radio, ni au bouton d'envoi : l'envoi reste manuel.
"""
from __future__ import annotations

import datetime
import json
import random
import re
import time
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from . import config, language, lm_builder
from .offer import Offer

# Marque chaque champ vide et visible d'un attribut data-sosjob pour le retrouver au remplissage.
_EXTRACT_JS = r"""(prefix) => {
  const out = [];
  const selOf = (el) => {
    const q = (v) => String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    if (el.id) return '[id="' + q(el.id) + '"]';
    if (el.name && el.type === 'radio') return 'input[name="' + q(el.name) + '"][value="' + q(el.value) + '"]';
    if (el.name) return el.tagName.toLowerCase() + '[name="' + q(el.name) + '"]';
    return null;
  };
  const label = (el) => {
    const bits = [];
    if (el.getAttribute('aria-label')) bits.push(el.getAttribute('aria-label'));
    const by = el.getAttribute('aria-labelledby');
    if (by) by.split(/\s+/).forEach(i => { const n = document.getElementById(i); if (n) bits.push(n.innerText); });
    if (el.id) document.querySelectorAll('label[for="' + CSS.escape(el.id) + '"]').forEach(l => bits.push(l.innerText));
    const wrap = el.closest('label'); if (wrap) bits.push(wrap.innerText);
    if (!bits.length) { const p = el.closest('div,fieldset,li'); if (p) bits.push(p.innerText.slice(0, 200)); }
    if (el.placeholder) bits.push(el.placeholder);
    return bits.join(' | ').replace(/\s+/g, ' ').trim().slice(0, 300);
  };
  document.querySelectorAll('input, textarea, select').forEach((el, n) => {
    const type = (el.type || '').toLowerCase();
    if (['hidden','file','submit','button','reset','image','password','checkbox','radio'].includes(type)) return;
    if (el.disabled || el.readOnly) return;
    if (/^(rechercher|search)/i.test(el.placeholder || '')) return;  // champ de recherche interne d'une liste
    const r = el.getBoundingClientRect(), st = getComputedStyle(el);
    if (r.width < 5 || r.height < 5 || st.visibility === 'hidden' || st.display === 'none') return;
    const isSelect = el.tagName === 'SELECT';
    if (!isSelect && el.value) return;
    if (isSelect && el.selectedIndex > 0) return;
    const id = prefix + '-' + n;
    el.setAttribute('data-sosjob', id);
    out.push({id, sel: selOf(el), kind: isSelect ? 'select' : (el.tagName === 'TEXTAREA' ? 'textarea' : 'input'), type,
              label: label(el), min_chars: el.minLength > 0 ? el.minLength : undefined,
              max_chars: el.maxLength > 0 ? el.maxLength : undefined, required: el.required || el.getAttribute('aria-required') === 'true',
              options: isSelect ? [...el.options].map(o => o.text.trim()).filter(Boolean) : undefined});
  });
  const seen = new Set();
  document.querySelectorAll('input[type=radio]').forEach((el, n) => {
    if (!el.name || seen.has(el.name)) return;
    seen.add(el.name);
    const group = [...document.querySelectorAll('input[type=radio]')].filter(r => r.name === el.name);
    if (group.some(r => r.checked)) return;  // déjà choisi
    const box = el.closest('fieldset, [role=radiogroup], [role=group]') || el.parentElement.parentElement;
    const rb = box.getBoundingClientRect();
    if (rb.width < 5 || rb.height < 5) return;
    const opts = group.map(r => {
      const l = r.id && document.querySelector('label[for="' + CSS.escape(r.id) + '"]');
      const w = r.closest('label');
      return ((l && l.innerText) || (w && w.innerText) || r.value || '').replace(/\s+/g, ' ').trim();
    });
    let q = (box.innerText || '').replace(/\s+/g, ' ').trim();
    opts.forEach(o => { if (o) q = q.replace(o, ''); });
    const id = prefix + '-r' + n;
    group.forEach((r, k) => r.setAttribute('data-sosjob', id + '-' + k));
    out.push({id, sels: group.map(selOf), kind: 'radio', type: 'radio', label: q.trim().slice(0, 300), required: false, options: opts});
  });
  document.querySelectorAll('button[aria-haspopup=listbox]').forEach((el, n) => {
    const txt = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!/s[ée]lectionn|select|choisi|choose/i.test(txt)) return;  // seulement les listes encore vides
    if (el.closest('header, nav, [role=banner]') || el.disabled) return;
    const r = el.getBoundingClientRect();
    if (r.width < 5 || r.height < 5) return;
    const id = prefix + '-d' + n;
    el.setAttribute('data-sosjob', id);
    out.push({id, sel: selOf(el), kind: 'dropdown', type: '', label: (el.getAttribute('aria-label') || txt).slice(0, 300), required: false});
  });
  return out;
}"""

MUST_ANSWER = (
    "SECONDE PASSE : ces champs sont OBLIGATOIRES et sont restés vides à la première passe. Chacun DOIT recevoir une vraie réponse : "
    "ni null, ni \".\", ni phrase vide. Question ouverte (motivation, pourquoi nous rejoindre, expérience...) : 3 à 5 phrases sincères "
    "tirées du CV, de la lettre déjà écrite et de l'offre ; sans fait inventé (si le CV ne couvre pas le sujet, dis honnêtement ce qui s'en "
    "rapproche et la motivation à apprendre). Question à choix (OUI/NON, liste) : choisis l'option la plus honnête d'après le CV et les FAITS PERSO, copiée à l'identique parmi les options ; NON si le CV ne prouve pas l'expérience demandée ; OUI pour la mobilité sur Paris (candidat basé en Île-de-France).\n\n"
)

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
                            input=prompt, capture_output=True, text=True, timeout=180, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"claude -p a échoué (code {result.returncode}) : {result.stderr[-300:]}")
    start = result.stdout.find("{")
    if start < 0:
        raise RuntimeError(f"réponse sans JSON : {result.stdout[-300:]}")
    answers, _ = json.JSONDecoder().raw_decode(result.stdout[start:])  # premier objet JSON, tolère du texte avant ou après
    return answers if isinstance(answers, dict) else {}


_SUGGESTION_JS = """(input) => {
  const r = input.getBoundingClientRect(), full = input.value.trim().toLowerCase();
  const v = full.split(',')[0].trim();
  if (!v) return false;
  const tokens = full.split(/[\\s,]+/).filter(t => t.length >= 3);
  const overlay = (e) => { for (; e && e !== document.body; e = e.parentElement) {
    const pos = getComputedStyle(e).position; if (pos === 'absolute' || pos === 'fixed') return true; } return false; };
  document.querySelectorAll('[data-sosjob-sug]').forEach(e => e.removeAttribute('data-sosjob-sug'));
  const all = [...document.querySelectorAll('body *')].filter(e => {
    if (e === input || e.contains(input) || input.contains(e) || e.children.length > 3) return false;
    const b = e.getBoundingClientRect();
    if (b.width < 20 || b.height < 10 || b.top < r.bottom - 4 || b.top > r.bottom + 400) return false;
    const t = (e.innerText || '').trim().toLowerCase();
    return t.length < 120 && t.startsWith(v) && overlay(e);
  });
  const hits = all.filter(h => !all.some(o => o !== h && h.contains(o)));  // éléments les plus profonds : une suggestion, pas toute la liste
  // la suggestion qui ressemble le plus à la valeur voulue, à égalité la plus haute dans la liste
  const score = (e) => tokens.filter(t => e.innerText.toLowerCase().includes(t)).length;
  hits.sort((a, b) => score(b) - score(a) || a.getBoundingClientRect().top - b.getBoundingClientRect().top);
  if (hits[0]) hits[0].setAttribute('data-sosjob-sug', '1');
  return hits.length > 0;
}"""


def _retype_with_suggestion(frame, loc, value: str) -> None:
    """Champ à auto-complétion (ville, entreprise...) que le site vide s'il n'a pas été choisi dans sa liste :
    frappe réelle, puis clic sur la première suggestion qui commence par le texte tapé."""
    loc.fill("")
    loc.press_sequentially(value, delay=60)
    frame.page.wait_for_timeout(1200)
    if loc.evaluate(_SUGGESTION_JS):
        frame.locator("[data-sosjob-sug]").first.click(timeout=2000)


def _loc(frame, field: dict, k: int | None = None):
    """Le champ vivant dans la page : sélecteur stable (id/name) d'abord, puis l'attribut posé à l'extraction."""
    if k is not None:
        sels = field.get("sels") or []
        sel = sels[k] if k < len(sels) else None
        return frame.locator(sel).first if sel else frame.locator(f'[data-sosjob="{field["id"]}-{k}"]').first
    sel = field.get("sel")
    return frame.locator(sel).first if sel else frame.locator(f'[data-sosjob="{field["id"]}"]').first


def _read_dropdown_options(frame, loc) -> list[str]:
    """Ouvre la liste déroulante, lit ses options visibles, la referme."""
    try:
        loc.click(timeout=2000)
        frame.page.wait_for_timeout(600)
        options = frame.evaluate("""() => [...document.querySelectorAll('[role=option]')]
            .filter(e => e.getBoundingClientRect().width > 0).map(e => e.innerText.replace(/\\s+/g, ' ').trim()).filter(t => t && !/^s[ée]lectionnez/i.test(t))""")
        frame.page.keyboard.press("Escape")
        frame.page.wait_for_timeout(200)
        return options
    except Exception:
        return []


def _fill_choice(frame, field: dict, value: str) -> bool:
    """Bouton radio ou liste déroulante : choisit l'option dont le texte correspond à `value`."""
    wanted = value.strip().lower()
    if field["kind"] == "radio":
        for k, option in enumerate(field["options"]):
            if option.strip().lower() == wanted:
                radio = _loc(frame, field, k)
                try:
                    radio.check(force=True, timeout=2000)
                except Exception:
                    radio.evaluate("e => e.click()")
                radio.evaluate("e => { const t = e.closest('label') || e.parentElement; t.style.outline = '3px solid #f5a623'; }")
                return True
        return False
    loc = _loc(frame, field)
    loc.click(timeout=2000)
    frame.page.wait_for_timeout(500)
    for option in frame.get_by_role("option").all():
        if option.is_visible() and option.inner_text().strip().lower() == wanted:
            option.click(timeout=2000)
            loc.evaluate("e => { e.style.outline = '3px solid #f5a623'; }")
            return True
    frame.page.keyboard.press("Escape")
    return False


def _active_page(browser):
    pages = [p for ctx in browser.contexts for p in ctx.pages if p.url.startswith(("http://", "https://"))]
    for page in reversed(pages):
        try:
            if page.evaluate("document.visibilityState") == "visible":
                return page
        except Exception:
            continue
    return pages[-1] if pages else None


_TOAST_JS = """([text, ms]) => {
  let t = document.getElementById('sosjob-toast');
  if (!t) { t = document.createElement('div'); t.id = 'sosjob-toast';
    t.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;max-width:360px;padding:10px 14px;'
      + 'background:#1e325a;color:#fff;font:14px system-ui,sans-serif;border-radius:8px;box-shadow:0 2px 12px #0006';
    document.documentElement.appendChild(t); }
  t.textContent = text; clearTimeout(window.__sosjobToast);
  if (ms) window.__sosjobToast = setTimeout(() => t.remove(), ms);
}"""


def _toast(page, text: str, ms: int = 0) -> None:
    try:
        page.evaluate(_TOAST_JS, [text, ms])
    except Exception:
        pass  # page en navigation : le message reste affiché dans le terminal


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
    for field in fields:  # liste de pays (souvent > 60 options, donc tronquée avant France) : réponse sûre, tirée du profil (Île-de-France)
        if field.get("kind") in ("combobox", "dropdown", "select") and _empty(answers, field) and re.search(r"^\s*(country|pays)\b", field.get("label", ""), re.I):
            answers[field["id"]] = "France"
    city = (config.load_form_profile() or {}).get("city", "")
    for field in fields:  # champ de localisation à suggestions : ville du profil (la suggestion est choisie par l'extension)
        if city and field.get("kind") == "combobox" and _empty(answers, field) and re.search(r"(location|localisation|city|ville|lieu)", field.get("label", ""), re.I):
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


def _offer_from_page(page) -> Offer:
    """Contexte d'un site quelconque (hors file du copilot) : titre, domaine et texte visible de la page."""
    try:
        text = page.evaluate("document.body.innerText")[:3000]
    except Exception:
        text = ""
    return offer_from_context(page.url, page.title(), text)


def fill_active_page(offer: Offer | None, cfg: dict) -> str:
    """Remplit le formulaire de l'onglet actif. `offer` = None : n'importe quel site (contexte tiré de la page).
    Retourne un message d'état pour le tableau de bord / le terminal."""
    from playwright.sync_api import sync_playwright

    port = int(cfg.get("debug_port", 9222))
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception as exc:
            return f"Remplissage impossible : Chrome du copilot injoignable ({type(exc).__name__})"
        page = _active_page(browser)
        if page is None:
            return "Remplissage impossible : aucun onglet web ouvert"
        if is_excluded(page.url, cfg):
            return f"Remplissage désactivé sur {urlparse(page.url).hostname} (conditions d'utilisation)"
        if offer is None:
            offer = _offer_from_page(page)
        _toast(page, "SOS-JOB : lecture du formulaire et rédaction des réponses...")
        fields: list[tuple] = []
        for i, frame in enumerate(page.frames):
            try:
                fields += [(frame, f) for f in frame.evaluate(_EXTRACT_JS, str(i))]
            except Exception:
                continue  # iframe détachée ou inaccessible
        if not fields:
            _toast(page, "SOS-JOB : aucun champ vide à remplir sur cette page", 5000)
            return "Aucun champ vide à remplir sur cette page"
        for frame, field in list(fields):  # les options d'une liste déroulante ne se lisent qu'en l'ouvrant
            if field["kind"] == "dropdown":
                field["options"] = _read_dropdown_options(frame, _loc(frame, field))
                if not field["options"]:
                    fields.remove((frame, field))
        answers = generate_answers(offer, [f for _, f in fields], cfg)
        filled, short, filled_inputs = 0, [], []
        for frame, field in fields:
            value = answers.get(field["id"])
            if not isinstance(value, str) or not value.strip():
                continue
            if field["kind"] in ("radio", "dropdown"):
                try:
                    filled += _fill_choice(frame, field, value)
                    page.wait_for_timeout(random.randint(150, 400))
                except Exception:
                    pass
                continue
            lo, hi = _limits(field)
            value = clamp(value, lo, hi)
            if lo and len(value) < lo:
                short.append(field["label"][:40])
            loc = _loc(frame, field)
            try:
                loc.scroll_into_view_if_needed(timeout=2000)
                if field["kind"] == "select":
                    loc.select_option(label=value, timeout=2000)
                else:
                    loc.fill(value.strip(), timeout=3000)  # déclenche les événements input/change comme une saisie
                    if field["kind"] == "input":
                        filled_inputs.append((frame, field, value.strip()))
                loc.evaluate("e => { e.style.outline = '3px solid #f5a623'; e.style.outlineOffset = '1px'; }")
                filled += 1
                if field["kind"] == "input":
                    try:  # liste d'auto-complétion ouverte : choisir la 1re suggestion (non bloquant)
                        page.wait_for_timeout(900)
                        if loc.evaluate(_SUGGESTION_JS):
                            frame.locator("[data-sosjob-sug]").first.click(timeout=2000)
                    except Exception:
                        pass
                page.wait_for_timeout(random.randint(150, 400))
            except Exception:
                continue
        for frame, field, value in filled_inputs:  # le site a-t-il vidé le champ (auto-complétion) ?
            loc = _loc(frame, field)
            try:
                if not loc.input_value():
                    _retype_with_suggestion(frame, loc, value)
                    if not loc.input_value():
                        filled -= 1
            except Exception:
                filled -= 1
        note = f" ; trop court (min non atteint) : {', '.join(short)}" if short else ""
        message = f"{filled} champ(s) pré-rempli(s) sur {len(fields)} (surlignés en orange){note} -- relis avant d'envoyer"
        _toast(page, "SOS-JOB : " + message, 9000)
        return message
