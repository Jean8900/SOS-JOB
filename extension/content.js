// SOS-JOB : lecture et remplissage des formulaires, dans la page (injecté par background.js).
// Même logique d'extraction que src/formfill.py (chemin Playwright de apply.ps1) : à garder alignées.
// Rien n'est envoyé : jamais de clic sur un bouton d'envoi. CV et LM sont posés dans les champs « fichier ».
(() => {
  if (window.__sosjob) return;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const rand = (a, b) => a + Math.random() * (b - a);
  const esc = (v) => String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  const visible = (el) => {
    const r = el.getBoundingClientRect(), st = getComputedStyle(el);
    return r.width >= 5 && r.height >= 5 && st.visibility !== 'hidden' && st.display !== 'none';
  };

  // Sélecteur stable : les frameworks recréent les éléments après une saisie.
  const selOf = (el) => {
    if (el.id) return '[id="' + esc(el.id) + '"]';
    if (el.name && el.type === 'radio') return 'input[name="' + esc(el.name) + '"][value="' + esc(el.value) + '"]';
    if (el.name) return el.tagName.toLowerCase() + '[name="' + esc(el.name) + '"]';
    return null;
  };

  const labelOf = (el) => {
    const bits = [];
    if (el.getAttribute('aria-label')) bits.push(el.getAttribute('aria-label'));
    const by = el.getAttribute('aria-labelledby');
    if (by) by.split(/\s+/).forEach((i) => { const n = document.getElementById(i); if (n) bits.push(n.innerText); });
    if (el.id) document.querySelectorAll('label[for="' + CSS.escape(el.id) + '"]').forEach((l) => bits.push(l.innerText));
    const wrap = el.closest('label'); if (wrap) bits.push(wrap.innerText);
    if (!bits.length) { const p = el.closest('div,fieldset,li'); if (p) bits.push(p.innerText.slice(0, 200)); }
    if (el.placeholder) bits.push(el.placeholder);
    return bits.join(' | ').replace(/\s+/g, ' ').trim().slice(0, 300);
  };

  // Listes « Select... » des frameworks (react-select...) : le vrai <input> fait quelques pixels, n'a souvent pas d'id,
  // et le site vide le texte tapé s'il n'est pas choisi dans la liste : il faut ouvrir la liste et cliquer une option.
  const PLACEHOLDER = /^(select|choisir|s[ée]lectionn|start typing|commencez|\.\.\.|--)/i;
  const isCombo = (el) => el.tagName === 'INPUT' && (el.getAttribute('role') === 'combobox'
    || el.getAttribute('aria-autocomplete') === 'list' || /^(true|listbox)$/.test(el.getAttribute('aria-haspopup') || ''));
  const comboControl = (el) => el.closest('[class*="control"]') || el.parentElement.parentElement;
  const comboOptions = (el) => {
    const r = comboControl(el).getBoundingClientRect();
    return [...document.querySelectorAll('[role=option]')].filter(visible).filter((o) => {
      const b = o.getBoundingClientRect();
      return b.top >= r.bottom - 8 && b.top <= r.bottom + 700 && b.left < r.right && b.right > r.left;
    });
  };
  const labelFromAncestors = (el) => {
    for (let p = el.parentElement, i = 0; p && i < 6; p = p.parentElement, i++) {
      const lab = p.querySelector('label, legend, [class*="label"], h3, strong');
      if (lab && lab.innerText.trim() && !lab.contains(el)) return lab.innerText.replace(/\s+/g, ' ').trim().slice(0, 300);
    }
    return labelOf(el);
  };
  const YESNO = /^(yes|no|oui|non)$/i;

  // Champs vides et visibles de la page (texte, listes, radios, listes déroulantes à boutons).
  function extract(prefix) {
    const out = [];
    document.querySelectorAll('input, textarea, select').forEach((el, n) => {
      const type = (el.type || '').toLowerCase();
      if (['hidden', 'file', 'submit', 'button', 'reset', 'image', 'password', 'checkbox', 'radio'].includes(type)) return;
      if (el.disabled || el.readOnly) return;
      if (/^(rechercher|search)/i.test(el.placeholder || '')) return;  // champ de recherche interne d'une liste
      if (isCombo(el)) {
        if (!visible(comboControl(el)) || el.value) return;
        const shown = (comboControl(el).innerText || '').replace(/\s+/g, ' ').trim();
        if (shown && !PLACEHOLDER.test(shown)) return;  // déjà choisi
        const cid = prefix + '-c' + n;
        el.setAttribute('data-sosjob', cid);
        out.push({ id: cid, sel: selOf(el), kind: 'combobox', type: '', label: labelFromAncestors(el),
                   required: el.getAttribute('aria-required') === 'true' });
        return;
      }
      if (!visible(el)) return;
      const isSelect = el.tagName === 'SELECT';
      // Un champ téléphone qui ne contient que l'indicatif du pays (« +49 ») est vide pour nous.
      const dialOnly = type === 'tel' && /^\+?\d{1,4}\s*$/.test(el.value);
      if (!isSelect && el.value && !dialOnly) return;
      if (isSelect && el.selectedIndex > 0) return;
      const id = prefix + '-' + n;
      el.setAttribute('data-sosjob', id);
      out.push({
        id, sel: selOf(el), kind: isSelect ? 'select' : (el.tagName === 'TEXTAREA' ? 'textarea' : 'input'), type,
        label: labelOf(el), min_chars: el.minLength > 0 ? el.minLength : undefined,
        max_chars: el.maxLength > 0 ? el.maxLength : undefined,
        required: el.required || el.getAttribute('aria-required') === 'true',
        options: isSelect ? [...el.options].map((o) => o.text.trim()).filter(Boolean) : undefined,
      });
    });
    const seen = new Set();
    document.querySelectorAll('input[type=radio]').forEach((el, n) => {
      if (!el.name || seen.has(el.name)) return;
      seen.add(el.name);
      const group = [...document.querySelectorAll('input[type=radio]')].filter((r) => r.name === el.name);
      if (group.some((r) => r.checked)) return;
      const box = el.closest('fieldset, [role=radiogroup], [role=group]') || el.parentElement.parentElement;
      const rb = box.getBoundingClientRect();
      if (rb.width < 5 || rb.height < 5) return;
      const opts = group.map((r) => {
        const l = r.id && document.querySelector('label[for="' + CSS.escape(r.id) + '"]');
        const w = r.closest('label');
        return ((l && l.innerText) || (w && w.innerText) || r.value || '').replace(/\s+/g, ' ').trim();
      });
      let q = (box.innerText || '').replace(/\s+/g, ' ').trim();
      opts.forEach((o) => { if (o) q = q.replace(o, ''); });
      const id = prefix + '-r' + n;
      group.forEach((r, k) => r.setAttribute('data-sosjob', id + '-' + k));
      out.push({ id, sels: group.map(selOf), kind: 'radio', type: 'radio', label: q.trim().slice(0, 300), required: false, options: opts });
    });
    document.querySelectorAll('button[aria-haspopup=listbox]').forEach((el, n) => {
      const txt = (el.innerText || '').replace(/\s+/g, ' ').trim();
      if (!/s[ée]lectionn|select|choisi|choose/i.test(txt)) return;  // seulement les listes encore vides
      if (el.closest('header, nav, [role=banner]') || el.disabled || !visible(el)) return;
      const id = prefix + '-d' + n;
      el.setAttribute('data-sosjob', id);
      out.push({ id, sel: selOf(el), kind: 'dropdown', type: '', label: (el.getAttribute('aria-label') || txt).slice(0, 300), required: false });
    });
    const seenGroups = new Set();
    document.querySelectorAll('button').forEach((btn, n) => {
      if (!YESNO.test((btn.innerText || '').trim())) return;
      const group = btn.parentElement;
      if (!group || seenGroups.has(group)) return;
      seenGroups.add(group);
      const btns = [...group.children].filter((c) => c.tagName === 'BUTTON');
      if (btns.length < 2 || btns.length > 3 || !btns.every((b) => YESNO.test((b.innerText || '').trim()))) return;
      if (btns.some((b) => b.getAttribute('aria-pressed') === 'true' || /active|selected|checked/i.test(b.className))) return;  // déjà choisi
      if (!visible(group)) return;
      const yid = prefix + '-y' + n;
      btns.forEach((b, k) => b.setAttribute('data-sosjob', yid + '-' + k));
      out.push({ id: yid, kind: 'yesno', type: '', label: labelFromAncestors(group), required: false,
                 options: btns.map((b) => b.innerText.trim()) });
    });
    document.querySelectorAll('input[type=checkbox]').forEach((el, n) => {
      if (el.checked || el.disabled) return;
      const wrap = el.closest('label') || el.parentElement;
      if (!visible(el) && !visible(wrap)) return;
      const lab = el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      const text = ((lab && lab.innerText) || (wrap && wrap.innerText) || el.parentElement.parentElement.innerText || '')
        .replace(/\s+/g, ' ').trim().slice(0, 300);
      if (!text) return;
      const kid = prefix + '-k' + n;
      el.setAttribute('data-sosjob', kid);
      out.push({ id: kid, sel: selOf(el), kind: 'checkbox', type: 'checkbox', label: text, required: el.required });
    });
    return out;
  }

  function find(field, k) {
    if (k != null) {
      const sel = (field.sels || [])[k];
      return (sel && document.querySelector(sel)) || document.querySelector('[data-sosjob="' + field.id + '-' + k + '"]');
    }
    return (field.sel && document.querySelector(field.sel)) || document.querySelector('[data-sosjob="' + field.id + '"]');
  }

  const click = (el) => {
    ['mousedown', 'mouseup', 'click'].forEach((t) => el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window })));
  };
  const escape = () => {
    [document.activeElement, document].forEach((t) => t && t.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true })));
  };
  const highlight = (el) => { el.style.outline = '3px solid #f5a623'; el.style.outlineOffset = '1px'; };
  // Options de la liste ouverte par ce bouton : la liste visible la plus proche juste sous lui
  // (la page peut contenir d'autres listes, ex. l'indicatif téléphonique).
  const optionsOf = (button) => {
    const bottom = button.getBoundingClientRect().bottom;
    const lists = [...document.querySelectorAll('[role=listbox]')].filter(visible)
      .map((l) => [l, Math.abs(l.getBoundingClientRect().top - bottom)]).sort((a, b) => a[1] - b[1]);
    if (!lists.length || lists[0][1] > 400) return [];
    return [...lists[0][0].querySelectorAll('[role=option]')].filter(visible);
  };

  // Les options d'une liste déroulante ne se lisent qu'en l'ouvrant.
  async function openCombo(el) {
    el.focus();
    click(comboControl(el));
    await sleep(500);
    if (!comboOptions(el).length) {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true }));
      await sleep(500);
    }
  }
  const closeCombo = (el) => {
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
    el.blur();
  };

  async function readOptions(field) {
    const el = find(field);
    if (!el) return [];
    if (field.kind === 'combobox') {
      await openCombo(el);
      const options = comboOptions(el).map((o) => o.innerText.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 60);
      closeCombo(el);
      await sleep(200);
      return options;
    }
    el.click();
    await sleep(600);
    const options = optionsOf(el).map((e) => e.innerText.replace(/\s+/g, ' ').trim()).filter((t) => t && !/^s[ée]lectionnez/i.test(t));
    el.click();  // referme (le bouton bascule)
    await sleep(300);
    if (optionsOf(el).length) { escape(); await sleep(200); }
    return options;
  }

  async function setText(el, value) {
    el.focus();
    if (el.select) el.select();
    let ok = false;
    try { ok = document.execCommand('insertText', false, value); } catch (e) { /* repli ci-dessous */ }
    if (!ok || el.value !== value) {
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  // Frappe caractère par caractère (champs à auto-complétion qui écoutent les touches).
  async function typeText(el, value) {
    el.focus();
    if (el.select) el.select();
    document.execCommand('delete');
    for (const ch of value) {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true }));
      document.execCommand('insertText', false, ch);
      el.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }));
      await sleep(60);
    }
  }

  // Liste d'auto-complétion en surimpression sous le champ : la suggestion qui ressemble le plus à la valeur.
  function suggestionFor(input) {
    const r = input.getBoundingClientRect(), full = input.value.trim().toLowerCase();
    const v = full.split(',')[0].trim();
    if (!v) return null;
    const tokens = full.split(/[\s,]+/).filter((t) => t.length >= 3);
    const overlay = (e) => {
      for (; e && e !== document.body; e = e.parentElement) {
        const pos = getComputedStyle(e).position;
        if (pos === 'absolute' || pos === 'fixed') return true;
      }
      return false;
    };
    const all = [...document.querySelectorAll('body *')].filter((e) => {
      if (e === input || e.contains(input) || input.contains(e) || e.children.length > 3) return false;
      const b = e.getBoundingClientRect();
      if (b.width < 20 || b.height < 10 || b.top < r.bottom - 4 || b.top > r.bottom + 400) return false;
      const t = (e.innerText || '').trim().toLowerCase();
      return t.length < 120 && t.startsWith(v) && overlay(e);
    });
    const hits = all.filter((h) => !all.some((o) => o !== h && h.contains(o)));  // le plus profond : une suggestion, pas toute la liste
    const score = (e) => tokens.filter((t) => e.innerText.toLowerCase().includes(t)).length;
    hits.sort((a, b) => score(b) - score(a) || a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    return hits[0] || null;
  }

  async function chooseSuggestion(el) {
    const hit = suggestionFor(el);
    if (hit) { click(hit); await sleep(200); }
  }

  async function fillChoice(field, value) {
    const wanted = value.trim().toLowerCase();
    if (field.kind === 'radio') {
      for (let k = 0; k < field.options.length; k++) {
        if (field.options[k].trim().toLowerCase() !== wanted) continue;
        const radio = find(field, k);
        if (!radio) return false;
        radio.click();
        highlight(radio.closest('label') || radio.parentElement);
        return true;
      }
      return false;
    }
    if (field.kind === 'yesno') {
      for (let k = 0; k < field.options.length; k++) {
        if (field.options[k].trim().toLowerCase() !== wanted) continue;
        const b = document.querySelector('[data-sosjob="' + field.id + '-' + k + '"]');
        if (!b) return false;
        b.click();
        highlight(b);
        return true;
      }
      return false;
    }
    const el = find(field);
    if (!el) return false;
    if (field.kind === 'combobox') {
      await openCombo(el);
      const opt = comboOptions(el).find((o) => o.innerText.replace(/\s+/g, ' ').trim().toLowerCase() === wanted);
      if (!opt) { closeCombo(el); return false; }
      click(opt);
      await sleep(200);
      highlight(comboControl(el));
      return true;
    }
    el.click();
    await sleep(500);
    const opt = optionsOf(el).find((o) => o.innerText.trim().toLowerCase() === wanted);
    if (opt) { opt.click(); highlight(el); return true; }
    escape();
    return false;
  }

  // answers : { id: "valeur" } ; fields : ceux de CE document. Retourne le nombre de champs remplis.
  async function fill(fields, answers) {
    let filled = 0;
    const typed = [];
    for (const field of fields) {
      const value = answers[field.id];
      if (typeof value !== 'string' || !value.trim()) continue;
      try {
        if (field.kind === 'checkbox') {
          const box = find(field);
          if (box && !box.checked && /^(oui|yes|true|coch)/i.test(value.trim())) {
            box.click();
            if (!box.checked) (box.closest('label') || box.parentElement).click();  // case personnalisée : on clique son conteneur
            highlight(box.closest('label') || box.parentElement);
            if (box.checked) filled++;
          }
          await sleep(rand(100, 250));
          continue;
        }
        const el = field.kind === 'radio' ? null : find(field);
        if (['radio', 'dropdown', 'combobox', 'yesno'].includes(field.kind)) {
          if (await fillChoice(field, value)) filled++;
        } else if (el) {
          el.scrollIntoView({ block: 'center' });
          if (field.kind === 'select') {
            const opt = [...el.options].find((o) => o.text.trim().toLowerCase() === value.trim().toLowerCase());
            if (!opt) continue;
            el.value = opt.value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          } else {
            await setText(el, value.trim());
            if (field.kind === 'input') typed.push([field, value.trim()]);
          }
          highlight(el);
          filled++;
          if (field.kind === 'input') { await sleep(900); await chooseSuggestion(el); }
        }
        await sleep(rand(150, 400));
      } catch (e) { /* un champ récalcitrant ne bloque pas les autres */ }
    }
    for (const [field, value] of typed) {  // le site a-t-il vidé un champ à auto-complétion ?
      const el = find(field);
      if (!el || el.value) continue;
      try {
        await typeText(el, value);
        await sleep(1200);
        await chooseSuggestion(el);
        if (!el.value) filled--;
      } catch (e) { filled--; }
    }
    return filled;
  }

  function toast(text, ms) {
    let t = document.getElementById('sosjob-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'sosjob-toast';
      t.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;max-width:360px;padding:10px 14px;'
        + 'background:#1e325a;color:#fff;font:14px system-ui,sans-serif;border-radius:8px;box-shadow:0 2px 12px #0006';
      document.documentElement.appendChild(t);
    }
    t.textContent = text;
    clearTimeout(window.__sosjobToast);
    if (ms) window.__sosjobToast = setTimeout(() => t.remove(), ms);
  }

  function pageContext() {
    return { url: location.href, title: document.title, text: (document.body ? document.body.innerText : '').slice(0, 3000) };
  }

  // Étapes multiples : seuls ces boutons font passer à l'écran suivant (texte entier, sans casse ni ponctuation).
  const NEXT_OK = /^(enregistrer et continuer|enregistrer et suivant|continuer|suivant|[ée]tape suivante|next|next step|continue|save (and|&) continue|save (and|&) next)$/i;
  const SUBMIT_WORDS = /envoyer|soumettre|postuler|candidater|valider|confirmer|submit|apply|send|finish|terminer|register|cr[ée]er (un )?compte|sign ?up|create account/i;
  const REVIEW = /^(r[ée]viser|r[ée]vision|review|r[ée]capitulatif|summary)\b/i;
  const clean = (s) => (s || '').replace(/[→›»>←→]/g, ' ').replace(/[.!:]+$/g, '').replace(/\s+/g, ' ').trim();
  const btnText = (b) => clean(b.innerText || b.value || b.getAttribute('aria-label') || '');
  const buttons = () => [...document.querySelectorAll('button, [role=button], input[type=submit], input[type=button], a[role=button]')].filter(visible);

  // Empreinte de l'écran : change quand le formulaire passe à l'étape suivante.
  function stepSig() {
    const ctl = [...document.querySelectorAll('input:not([type=hidden]), select, textarea')].filter(visible)
      .map((e) => e.id || e.name || e.type).join(',');
    const h = [...document.querySelectorAll('h1,h2,[role=heading]')].filter(visible).map((e) => e.innerText.trim()).join('|').slice(0, 200);
    return location.href + '#' + ctl + '#' + h;
  }

  // Écran de connexion : jamais rempli, l'utilisateur se connecte lui-même (gestionnaire de mots de passe).
  const needsLogin = () => [...document.querySelectorAll('input[type=password]')].some(visible);
  const isReview = () => [...document.querySelectorAll('h1,h2,[role=heading]')].filter(visible).some((e) => REVIEW.test(e.innerText.trim()));

  // Clique sur le bouton de passage autorisé ; jamais sur un bouton d'envoi.
  function clickNext() {
    if (clickEntry()) return 'Postuler (ouverture du formulaire)';  // WTJ : ouvre le formulaire, n'envoie rien
    for (const b of buttons()) {
      const t = btnText(b);
      if (!NEXT_OK.test(t) || SUBMIT_WORDS.test(t) || b.disabled || b.getAttribute('aria-disabled') === 'true') continue;
      b.scrollIntoView({ block: 'center' });
      b.click();
      return t;
    }
    return '';
  }

  // Champs « fichier » encore vides (souvent masqués derrière un faux bouton) : CV, lettre ou autre chose.
  const FILE_CV = /r[ée]sum[ée]|\bcv\b|curriculum/i, FILE_LM = /cover|lettre|motivation|\blm\b/i;
  function fileInputs() {
    const out = [];
    document.querySelectorAll('input[type=file]').forEach((el, n) => {
      if (el.disabled || (el.files && el.files.length)) return;
      const own = [labelFromAncestors(el), el.name, el.id, el.getAttribute('data-qa')].join(' ');
      const kind = FILE_LM.test(own) ? 'lm' : (FILE_CV.test(own) || FILE_CV.test(labelOf(el))) ? 'cv' : 'other';
      el.setAttribute('data-sosjob-file', 'f' + n);
      out.push({ id: 'f' + n, kind, label: own.replace(/\s+/g, ' ').trim().slice(0, 100) });
    });
    return out;
  }
  // Pose un fichier dans le champ comme si l'utilisateur l'avait choisi (le PDF vient du programme local, en base64).
  function attachFile(id, b64, name) {
    const el = document.querySelector('[data-sosjob-file="' + id + '"]');
    if (!el) return false;
    const bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const dt = new DataTransfer();
    dt.items.add(new File([bytes], name, { type: 'application/pdf' }));
    el.files = dt.files;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return el.files.length === 1;
  }

  // Welcome to the Jungle : la candidature s'ouvre dans une fenêtre sur la page de l'offre.
  const onWtj = () => /(^|\.)welcometothejungle\.com$/.test(location.hostname);
  const wtjForm = () => document.querySelector('[aria-modal] input[name="firstname"], [role=dialog] input[name="firstname"]');
  // Bouton d'entrée « Postuler » de la page de l'offre (ouvre le formulaire, n'envoie rien).
  function clickEntry() {
    if (!onWtj() || wtjForm()) return false;
    const b = [...document.querySelectorAll('[data-testid="job_header-button-apply"], [data-testid="job_bottom-button-apply"]')].find((x) => visible(x) && !x.disabled);
    if (!b) return false;
    b.click();
    return true;
  }
  // Le formulaire WTJ est prêt à être envoyé : le bouton « J'envoie ma candidature ! » est là. On ne le clique JAMAIS :
  // sur WTJ il envoie réellement la candidature (vérifié par l'utilisateur). On s'arrête juste avant.
  function submitReady() {
    const b = document.querySelector('[role=dialog] button[data-testid="apply-form-submit"], [aria-modal] button[data-testid="apply-form-submit"]');
    return !!(onWtj() && b && visible(b));
  }
  // Lettre de motivation : le texte de la LM générée (pas une réponse improvisée) dans le champ « lettre ».
  function setCoverLetter(text) {
    const el = [...document.querySelectorAll('textarea')].find((t) => visible(t) && !t.value && FILE_LM.test([t.name, t.id, labelOf(t)].join(' ')));
    if (!el) return false;
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  window.__sosjob = { clickEntry, submitReady, setCoverLetter, extract, readOptions, fill, toast, pageContext, stepSig, needsLogin, isReview, clickNext, fileInputs, attachFile };
})();
