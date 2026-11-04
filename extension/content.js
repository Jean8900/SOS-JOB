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
  const PLACEHOLDER = /^(search for|select|choisir|s[ée]lectionn|start typing|commencez|\.\.\.|--)/i;
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
    if (onApec()) apecClearDefaultMessage();
    const out = [];
    document.querySelectorAll('input, textarea, select').forEach((el, n) => {
      const type = (el.type || '').toLowerCase();
      if (['hidden', 'file', 'submit', 'button', 'reset', 'image', 'password', 'checkbox', 'radio'].includes(type)) return;
      if (el.disabled || el.readOnly) return;
      if (/^(rechercher|search)/i.test(el.placeholder || '')) return;  // champ de recherche interne d'une liste
      if (isCombo(el)) {
        if (!visible(comboControl(el)) || el.value) return;
        const shown = (comboControl(el).innerText || '').replace(/\s+/g, ' ').trim();
        if (shown && !PLACEHOLDER.test(shown) && !/^(location|localisation|city|ville|country|pays)\s*\*?$/i.test(shown)) return;  // déjà choisi
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
        label: el.getAttribute('data-sosjob-label') || labelOf(el), min_chars: el.minLength > 0 ? el.minLength : undefined,
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
      let box = el.closest('fieldset, [role=radiogroup], [role=group]') || el.parentElement.parentElement;
      // le texte de la question peut être un niveau plus haut (<div><p>Question *</p><div><label>OUI</label><label>NON</label></div></div>)
      for (let up = 0; up < 3 && box.parentElement && !el.closest('fieldset, [role=radiogroup], [role=group]'); up++) {
        const labels = group.map((r) => { const l = r.id && document.querySelector('label[for="' + CSS.escape(r.id) + '"]'); const w = r.closest('label'); return ((l && l.innerText) || (w && w.innerText) || r.value || '').replace(/\s+/g, ' ').trim(); });
        let rest = (box.innerText || '').replace(/\s+/g, ' ').trim();
        labels.forEach((o) => { if (o) rest = rest.replace(o, ''); });
        if (rest.trim().length > 3) break;
        box = box.parentElement;
      }
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
      // suggestions asynchrones (localisation) : aucune option tant qu'on n'a rien tapé ; on annonce une saisie libre (la ville est tapée puis la suggestion choisie)
      if (!options.length && /location|localisation|city|ville|lieu/i.test(field.label || '')) return ['(saisie libre : ville de résidence)'];
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
      if (!opt) {
        // suggestions asynchrones (localisation) : taper la ville, laisser le site proposer, choisir la première suggestion
        if (/location|localisation|city|ville|lieu/i.test(field.label || '')) {
          await typeText(el, wanted.split(',')[0].trim());
          await sleep(1500);
          const sug = comboOptions(el)[0];
          if (sug) { click(sug); await sleep(250); highlight(comboControl(el)); return true; }
        }
        closeCombo(el); return false;
      }
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
          { const okc = await fillChoice(field, value); (window.__sosjobFillLog = window.__sosjobFillLog || []).push((field.label || '').slice(0, 14) + (okc ? '=ok' : '=KO')); if (okc) filled++; }
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
    return location.href + '#' + ctl + '#' + h + '#' + (document.documentElement.getAttribute('data-sosjob-ticks') || '');
  }

  // Écran de connexion : jamais rempli, l'utilisateur se connecte lui-même (gestionnaire de mots de passe).
  const needsLogin = () => [...document.querySelectorAll('input[type=password]')].some(visible);
  const isReview = () => [...document.querySelectorAll('h1,h2,[role=heading]')].filter(visible).some((e) => REVIEW.test(e.innerText.trim()));

  // Clique sur le bouton de passage autorisé ; jamais sur un bouton d'envoi.
  function clickNext() {
    if (clickEntry()) return 'Postuler (ouverture du formulaire)';  // WTJ : ouvre le formulaire, n'envoie rien
    if (onApec()) return apecNext();  // Apec : son propre parcours, rien d'autre n'est cliqué
    if (onHello()) return helloNext();  // HelloWork : son propre parcours
    if (onFree()) return freeNext();  // Free-Work : son propre parcours
    if (onCad()) return cadNext();  // Cadremploi : son propre parcours
    if (onSf()) return sfNext();  // Station F Jobs : son propre parcours
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
    if (onCad()) cadClearDefaultLetter();
    if (onFree()) freeLabelMessage();
    if (onApec()) apecNoSave();
    if (onHello()) helloOpenMessage();
    if (onFree()) {
      const F = freeFiles();
      return [!F.cv && { id: 'free-cv', kind: 'cv', label: 'CV' }, !F.lm && { id: 'free-lm', kind: 'lm', label: 'LM' }].filter(Boolean);
    }
    const out = [];
    (onFree() ? deepAll('input[type=file]') : [...document.querySelectorAll('input[type=file]')]).forEach((el, n) => {
      if (el.disabled || (el.files && el.files.length)) return;
      if (onApec() && !visible(el)) return;  // Apec : les champs fichier n'existent qu'une fois le mode « importer » choisi
      const own = [labelFromAncestors(el), el.name, el.id, el.getAttribute('data-qa')].join(' ');
      const kind = FILE_LM.test(own) ? 'lm' : (FILE_CV.test(own) || FILE_CV.test(labelOf(el))) ? 'cv' : 'other';
      el.setAttribute('data-sosjob-file', 'f' + n);
      out.push({ id: 'f' + n, kind, label: own.replace(/\s+/g, ' ').trim().slice(0, 100) });
    });
    return out;
  }
  // Pose un fichier dans le champ comme si l'utilisateur l'avait choisi (le PDF vient du programme local, en base64).
  function attachFile(id, b64, name) {
    if (id === 'free-cv' || id === 'free-lm') { freeFiles()[id.slice(5)] = { b64, name }; return true; }
    const el = (onFree() ? deepAll('input[type=file]') : [...document.querySelectorAll('input[type=file]')]).find((x) => x.getAttribute('data-sosjob-file') === id);
    if (!el) return false;
    const bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const dt = new DataTransfer();
    dt.items.add(new File([bytes], name, { type: 'application/pdf' }));
    el.files = dt.files;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    if (onApec()) { setTimeout(apecNoSave, 700); setTimeout(apecNoSave, 2000); }  // la case « enregistrer » apparaît après l'import
    if (onFree() && el.files.length === 1) document.documentElement.setAttribute('data-sosjob-attached', '1');
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

  // Apec : parcours « Postuler » -> « Postuler » (bis) -> « Je préfère joindre uniquement un CV » -> import du CV -> LM.
  // Jamais de clic sur « Envoyer ma candidature » (il envoie réellement) : on s'arrête avant. « Données complémentaires » : intouchée.
  const onApec = () => /(^|\.)apec\.fr$/.test(location.hostname);
  // Les CV adaptés ne doivent pas s'accumuler dans le compte Apec : on décoche « Enregistrer le CV dans mon compte » (coché par défaut), et de même pour la lettre.
  function apecNoSave() {
    for (const l of [...document.querySelectorAll('label')].filter((x) => /^enregistrer (le cv|la lettre de motivation) dans mon compte/i.test(clean(x.innerText)) && visible(x))) {
      const c = l.querySelector('input') || l.control || (l.previousElementSibling && l.previousElementSibling.tagName === 'INPUT' ? l.previousElementSibling : null) || l.parentElement.querySelector('input');
      if (c && c.type === 'checkbox' && c.checked) c.click();
    }
  }
  // Apec pré-remplit « Bonjour, je me permets de vous solliciter... » : on l'efface pour le remplacer par un message personnalisé.
  function apecClearDefaultMessage() {
    for (const t of document.querySelectorAll('textarea')) {
      if (!visible(t) || !/^\s*bonjour,?\s+je me permets de vous solliciter/i.test(t.value)) continue;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(t, '');
      t.dispatchEvent(new Event('input', { bubbles: true }));
      t.setAttribute('data-sosjob-label', 'Ajouter un message au recruteur ? * (message court de 3 à 4 phrases, personnalisé pour cette offre à partir du CV et de la lettre de motivation ; pas de formule générique)');
    }
  }
  function apecNext() {
    const labelled = (re) => [...document.querySelectorAll('label')].find((l) => re.test(clean(l.innerText)) && visible(l));
    // Angular : <div><input type=radio><label>texte</label></div> (pas de for=) : l'entrée est le frère qui précède le libellé
    const inputOf = (l) => l && (l.querySelector('input') || l.control || (l.previousElementSibling && l.previousElementSibling.tagName === 'INPUT' ? l.previousElementSibling : null) || l.parentElement.querySelector('input'));
    // 1. page de l'offre : lien « Postuler » interne à l'Apec (pas celui qui renvoie chez l'employeur)
    if (/detail-offre/.test(location.pathname)) {
      const a = [...document.querySelectorAll('a')].find((x) => /^postuler$/i.test(clean(x.innerText)) && /postuler-a-une-offre/.test(x.getAttribute('href') || '') && visible(x));
      if (a) { a.click(); return 'Postuler (offre)'; }
      return '';
    }
    // 2. « Vous êtes sur le point de postuler » : « Postuler » (bis), sans prendre l'échange avec un conseiller
    if (/#\/candidature\/promotion\//.test(location.hash)) {
      const b = [...document.querySelectorAll('button')].find((x) => /^postuler$/i.test(clean(x.innerText)) && visible(x) && !x.disabled);
      if (b) { b.click(); return 'Postuler (bis)'; }
      return '';
    }
    // 3. formulaire : CV seul, import d'un CV (sans l'enregistrer dans le compte), LM à joindre
    if (/#\/candidature\/formulaire\//.test(location.hash)) {
      for (const [re, name] of [[/^je préfère joindre uniquement un cv/i, 'CV seul'], [/^importer un cv/i, 'Importer un CV']]) {
        const r = inputOf(labelled(re));
        if (r && r.type === 'radio' && !r.checked) { r.click(); return name; }
      }
      const lm = inputOf(labelled(/^joindre ma lettre de motivation/i));
      if (lm && lm.type === 'radio' && !lm.checked) { lm.click(); return 'Joindre la LM'; }
      // Pas de LM demandée : bloc repliable « Ajouter un message au recruteur ? » à déplier (le champ texte est ensuite rempli)
      const head = [...document.querySelectorAll('div, button, a, h2, h3, span')]
        .filter((e) => visible(e) && /^ajouter un message au recruteur/i.test(clean(e.innerText)) && e.innerText.length < 60).pop();
      if (head && !lm && ![...document.querySelectorAll('textarea')].some(visible) && !document.documentElement.hasAttribute('data-sosjob-msgopen')) {
        document.documentElement.setAttribute('data-sosjob-msgopen', '1');
        head.click();
        return 'Message au recruteur (déplier)';
      }
    }
    return '';
  }

  // HelloWork : lien « Postuler » (en-tête) -> formulaire sur la page (#postuler) -> CV importé -> message au recruteur.
  // Jamais de clic sur le bouton noir « Postuler » du formulaire (data-cy=submitButton) : il envoie la candidature.
  const onHello = () => /(^|\.)hellowork\.com$/.test(location.hostname);
  // « Personnaliser mon message au recruteur » : case cachée (cover-letter-collapse-funnel) pilotée par son <label> ; dépliée pendant le remplissage
  function helloOpenMessage() {
    const toggle = document.getElementById('cover-letter-collapse-funnel');
    if (toggle && toggle.type === 'checkbox' && !toggle.checked) {
      const head = document.querySelector('label[for="cover-letter-collapse-funnel"]');
      if (head) head.click();
    }
    // message prérempli par HelloWork (« Madame, Monsieur, Suite à votre offre… ») : on l'efface pour le remplacer par un message personnalisé
    const t = document.querySelector('textarea[name="MotivationLetter"]');
    if (t && /^\s*madame,? monsieur,?\s+suite à votre offre/i.test(t.value)) {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(t, '');
      t.dispatchEvent(new Event('input', { bubbles: true }));
      t.setAttribute('data-sosjob-label', 'Message au recruteur * (message court de 3 à 5 phrases, quelques centaines de caractères, personnalisé pour cette offre à partir du CV et de la lettre de motivation ; pas de formule générique)');
    }
  }
  function helloNext() {
    if (!/\/emplois\/\d+/.test(location.pathname)) return '';
    if (!location.hash.includes('postuler')) {
      const a = document.querySelector('a[data-cy="applyButtonHeader"]');
      if (a && visible(a)) { a.click(); return 'Postuler (ouvrir le formulaire)'; }
      return '';
    }
    return '';
  }

  // Free-Work : message personnalisé + CV adapté joint comme « document additionnel » (le CV partagé du compte est le CVthèque public :
  // on n'y touche pas). Jamais de clic sur « Je postule » (bouton submit du formulaire = envoi).
  const onFree = () => /(^|\.)free-work\.com$/.test(location.hostname);
  function deepAll(sel, root = document, out = []) {
    root.querySelectorAll(sel).forEach((e) => out.push(e));
    root.querySelectorAll('*').forEach((e) => { if (e.shadowRoot) deepAll(sel, e.shadowRoot, out); });
    return out;
  }
  function freeLabelMessage() {
    const t = document.querySelector('textarea[name="job-application-message"]');
    if (t && !t.getAttribute('data-sosjob-label')) {
      t.setAttribute('data-sosjob-label', 'Message au recruteur * (message court de 3 à 5 phrases, quelques centaines de caractères, personnalisé pour cette offre à partir du CV et de la lettre de motivation ; pas de formule générique)');
    }
  }
  // Les PDF (CV, LM) arrivent par l'étape de remplissage : fileInputs() annonce deux champs fictifs (free-cv, free-lm), attachFile() les garde ici.
  const tickFlow = () => { const r = document.documentElement; r.setAttribute('data-sosjob-ticks', String(Number(r.getAttribute('data-sosjob-ticks') || 0) + 1)); };
  const freeFiles = () => (window.__sosjobFree = window.__sosjobFree || {});
  // « Éditer » (CV partagé) RECHARGE la page avec ?resumeOnly=true et la fenêtre « Mes documents » ouverte : le parcours est donc en étapes,
  // chacune relancée par l'étape de passage (les PDF sont re-fournis par fileInputs/attachFile après chaque rechargement).
  //  a. page de l'offre : cliquer « Éditer »  ->  b. page rechargée : importer le CV, « Envoyer mon CV », menu ⋮, « Partager le CV »
  //  c. « Document additionnel » -> « Ajouter » -> onglet « Ajouter un document » -> importer la LM -> « Envoyer le document » -> « Joindre le document »
  const freeHelpers = () => {
    const sleepMs = (ms) => new Promise((r) => setTimeout(r, ms));
    const waitFor = async (fn, ms = 9000) => { const t0 = Date.now(); for (;;) { const v = fn(); if (v) return v; if (Date.now() - t0 > ms) return null; await sleepMs(300); } };
    const btn = (re) => [...document.querySelectorAll('button')].find((b) => re.test(clean(b.innerText)) && visible(b) && !b.disabled);
    const putFile = (input, f) => {
      const bin = atob(f.b64), bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const dt = new DataTransfer();
      dt.items.add(new File([bytes], f.name, { type: 'application/pdf' }));
      input.files = dt.files;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    };
    const shownInput = () => deepAll('input[type=file]').filter((i) => { const h = i.getRootNode().host; return h && visible(h); }).pop() || deepAll('input[type=file]').pop();
    const modalOpen = () => [...document.querySelectorAll('div,h2,h3,span')].some((e) => e.children.length === 0 && visible(e) && /^(mes documents|my documents)$/i.test(clean(e.textContent)));
    const note = (m) => {
      let o = document.getElementById('sosjob-dbg');
      if (!o) { o = document.createElement('div'); o.id = 'sosjob-dbg'; o.style.cssText = 'position:fixed;left:8px;top:140px;z-index:2147483647;background:#111;color:#fff;font:14px monospace;padding:6px 10px;border-radius:6px;max-width:90vw'; document.body.appendChild(o); }
      o.textContent = 'SOS-JOB ' + m;
      return m;
    };
    return { sleepMs, waitFor, btn, putFile, shownInput, modalOpen, note };
  };
  // Temps 1 : importer le CV et « Envoyer mon CV » (le site recharge ensuite la page). L'état vit dans sessionStorage (propre à l'onglet).
  async function freeCvSubmit() {
    const { sleepMs, waitFor, btn, putFile, shownInput, modalOpen, note } = freeHelpers(), F = freeFiles();
    if (!(await waitFor(() => modalOpen()))) return note('CV : fenêtre « Mes documents » non ouverte');
    const input = await waitFor(() => shownInput());
    if (!input) return note('CV : champ fichier introuvable');
    putFile(input, F.cv); note('CV importé'); await sleepMs(1200);
    const send = await waitFor(() => btn(/^(envoyer mon cv|(send|submit|upload) my cv)$/i));
    if (!send) return note('CV : bouton « Envoyer mon CV » introuvable');
    sessionStorage.setItem('sosjob-cv-count', String(document.querySelectorAll('figcaption').length));
    sessionStorage.setItem('sosjob-cv-stage', 'submitted');
    send.click(); note('CV envoyé');
    await sleepMs(3500);  // si la page ne se recharge pas, on enchaîne ; sinon l'étape suivante reprend sur la page rechargée
    return await freeCvPick();
  }
  // Temps 2 (page rechargée, fenêtre ouverte) : le CV importé est le dernier de la liste ; menu ⋮ -> « Partager le CV » (= Make Default CV).
  async function freeCvPick() {
    const { sleepMs, waitFor, btn, modalOpen, note } = freeHelpers();
    if (!(await waitFor(() => modalOpen()))) return note('CV : fenêtre non rouverte');
    const before = Number(sessionStorage.getItem('sosjob-cv-count') || 0);
    const caps = await waitFor(() => { const c = [...document.querySelectorAll('figcaption')]; return c.length > before ? c : null; }, 8000);
    if (!caps) return note('CV : le CV envoyé n\'apparaît pas (' + document.querySelectorAll('figcaption').length + ' fichiers, avant ' + before + ')');
    let card = caps[caps.length - 1]; while (card && !card.querySelector('button')) card = card.parentElement;
    const dots = card.querySelector('button');
    dots.click(); note('menu ⋮'); await sleepMs(900);
    const dr = dots.getBoundingClientRect(), dx = dr.left + dr.width / 2, dy = dr.top + dr.height / 2;
    const dist = (e) => { const r = e.getBoundingClientRect(); return Math.abs(r.left + r.width / 2 - dx) + Math.abs(r.top + r.height / 2 - dy); };
    // l'entrée du menu ouvert par ⋮ (et non le bouton « Make Default CV » du bas de la fenêtre, qui vise le CV déjà sélectionné)
    const item = await waitFor(() => [...document.querySelectorAll('button[role=menuitem], [role=menuitem]')]
      .filter((e) => e.children.length <= 2 && visible(e) && /^(partager le cv|make default cv|share (the )?cv|set as default cv)$/i.test(clean(e.textContent)))
      .sort((x, y) => dist(x) - dist(y))[0]);
    if (!item) return note('CV : entrée « Partager le CV » introuvable');
    sessionStorage.setItem('sosjob-cv-stage', 'done');
    item.click(); note('CV par défaut changé'); tickFlow();
    return 'CV : défini par défaut';
  }
  async function freeLmFlow() {
    const { sleepMs, waitFor, btn, putFile, shownInput, modalOpen, note } = freeHelpers(), F = freeFiles();
    if (!modalOpen()) {
      const add = await waitFor(() => btn(/^(ajouter|add)$/i));
      if (!add) return note('LM : bouton « Ajouter » introuvable');
      add.scrollIntoView({ block: 'center' }); add.click(); note('document additionnel');
    }
    if (!(await waitFor(() => modalOpen()))) return note('LM : fenêtre non ouverte');
    const tab = await waitFor(() => btn(/^(ajouter un document|add a document)$/i));
    if (tab) { tab.click(); await sleepMs(900); }
    const input = await waitFor(() => shownInput());
    if (!input) return note('LM : champ fichier introuvable');
    putFile(input, F.lm); note('LM importée'); await sleepMs(800);
    const send = await waitFor(() => btn(/^(envoyer le document|(send|submit|upload) (the )?document)$/i));
    if (!send) return note('LM : bouton « Envoyer le document » introuvable');
    send.click(); note('LM envoyée'); await sleepMs(2500);
    // la LM envoyée apparaît comme une carte : la sélectionner, puis « Joindre le document » (inactif tant que rien n'est sélectionné)
    const prefix = F.lm.name.toLowerCase().slice(0, 12);
    const cap = await waitFor(() => [...document.querySelectorAll('figcaption')].filter((f) => f.textContent.trim().toLowerCase().startsWith(prefix)).pop(), 8000);
    if (cap) { (cap.closest('figure') || cap.parentElement).click(); note('LM sélectionnée'); await sleepMs(700); }
    const join = await waitFor(() => btn(/^(joindre le document|join (the )?document)$/i), 6000);
    if (join) { join.click(); note('LM jointe'); await sleepMs(1500); }
    tickFlow();
    return 'LM : ' + (join ? 'jointe' : 'envoyée');
  }
  function freeNext() {
    if (!/\/job-mission\//.test(location.pathname)) return '';
    const root = document.documentElement, F = freeFiles();
    const resumePage = () => /resumeOnly=true/.test(location.search);
    const stage = sessionStorage.getItem('sosjob-cv-stage') || '';
    const runCv = () => { root.setAttribute('data-sosjob-cv-started', '1'); return (sessionStorage.getItem('sosjob-cv-stage') === 'submitted' ? freeCvPick() : freeCvSubmit()).catch((e) => String(e).slice(0, 80)); };
    if (F.cv && stage !== 'done') {
      if (resumePage()) return root.hasAttribute('data-sosjob-cv-started') ? '' : runCv();
      const clickedAt = Number(sessionStorage.getItem('sosjob-edit-ts') || 0);
      if (Date.now() - clickedAt < 20000) {  // « Éditer » vient d'être cliqué : attendre le chargement de la fenêtre, ne pas recliquer
        return freeHelpers().waitFor(() => resumePage(), 12000).then((ok) => (ok && !root.hasAttribute('data-sosjob-cv-started') ? runCv() : ''));
      }
      return (async () => {  // la page se charge lentement et ignore un clic trop précoce (avant « hydratation ») : attendre, cliquer, réessayer
        const H = freeHelpers();
        const getEdit = () => [...document.querySelectorAll('button')].find((b) => (b.name || b.id) === 'default-resume-edit');
        if (!(await H.waitFor(getEdit, 12000))) return '';
        await H.sleepMs(2500);
        const edit = getEdit();
        if (!edit) return '';
        sessionStorage.setItem('sosjob-edit-ts', String(Date.now()));
        edit.scrollIntoView({ block: 'center' }); edit.click();
        return 'Éditer le CV partagé';  // la page se recharge : rendre la main tout de suite (attendre ici ferait échouer l'appel)
      })();
    }
    if (F.lm && !root.hasAttribute('data-sosjob-lm-started')) { root.setAttribute('data-sosjob-lm-started', '1'); return freeLmFlow().catch((e) => String(e).slice(0, 80)); }
    return '';
  }

  // ---- Retour structuré : état final vérifié par critère, instantané en cas d'échec, défilement vers la zone utile.
  // Jamais de valeur perso : seulement des noms de fichiers, des longueurs, des booléens. Rien si un champ mot de passe est visible.
  const pwVisible = () => [...document.querySelectorAll('input[type=password]')].some(visible);
  const lenOf = (el) => (el && typeof el.value === 'string' ? el.value.length : 0);
  const pdfNames = () => [...document.querySelectorAll('span, a, div, figcaption, p, label')]
    .filter((e) => e.children.length === 0 && visible(e) && /\.pdf\s*$/i.test((e.textContent || '').trim()))
    .map((e) => e.textContent.trim().slice(0, 50));
  function siteState(exp) {
    exp = exp || {};
    if (onSf() && !exp.late) return sleep(1500).then(() => siteState({ ...exp, late: true }));
    if (pwVisible()) return { site: location.hostname, skipped: 'mot de passe visible' };
    const c = [];
    const add = (k, ok, v) => c.push({ k, ok: !!ok, v: v === undefined ? '' : String(v).slice(0, 60) });
    if ((onApec() || onHello()) && !document.querySelector('input[type=file], textarea') && [...document.querySelectorAll('a, button')].some((e) => visible(e) && /postuler\s+sur\s+le\s+site\s+(de l.entreprise|du recruteur)/i.test(e.innerText || ''))) {
      c.push({ k: 'hors_site', ok: true, skip: true, v: 'candidature chez l’employeur' });
      return { site: location.hostname, criteria: c };
    }
    const names = pdfNames();
    const btnOk = (re) => { const b = [...document.querySelectorAll('button')].find((x) => re.test(clean(x.innerText))); return !!(b && visible(b) && !b.disabled); };
    if (onWtj()) {
      const ta = document.querySelector('[role=dialog] textarea[name="cover_letter"]');
      add('message_lettre', lenOf(ta) > 80, lenOf(ta));
      add('envoi_visible', submitReady());
    } else if (onApec()) {
      add('cv_adapte', exp.cv && names.includes(exp.cv), names.join(', '));
      const ta = [...document.querySelectorAll('textarea')].find(visible);
      add('lm_jointe_ou_message', names.length > 1 || !!ta);
      if (ta) add('message_perso', lenOf(ta) > 80 && !/^\s*bonjour,?\s+je me permets de vous solliciter/i.test(ta.value), lenOf(ta));
      add('envoi_actif', btnOk(/^envoyer ma candidature$/i));
    } else if (onHello()) {
      add('cv_adapte', exp.cv && names.includes(exp.cv), names.join(', '));
      const ta = document.querySelector('textarea[name="MotivationLetter"]');
      add('message_perso', ta && lenOf(ta) > 80 && !/^\s*madame,? monsieur,?\s+suite à votre offre/i.test(ta.value), lenOf(ta));
      const send = document.querySelector('[data-cy="submitButton"]');
      add('envoi_actif', send && visible(send) && !send.disabled);
    } else if (onCad()) {
      const form = cadForm();
      if (!form) {
        if ([...document.querySelectorAll('a, button')].some((e) => /site de l.entreprise|candidature externe|postuler sur/i.test(e.innerText || ''))) {
          c.push({ k: 'hors_site', ok: true, skip: true, v: 'candidature chez l’employeur' });
          return { site: location.hostname, criteria: c };
        }
      }
      const posed = form ? [...form.querySelectorAll('input[type=file]')].map((i) => i.files && i.files[0] && i.files[0].name).filter(Boolean) : [];
      add('cv_adapte', exp.cv && (posed.includes(exp.cv) || names.includes(exp.cv)), (posed.concat(names)).join(', ') || 'aucun fichier relevé');
      const ta = form && [...form.querySelectorAll('textarea')].find(visible);
      add('message_perso', ta && lenOf(ta) > 80, lenOf(ta));
      const send = form && [...form.querySelectorAll('button[type="submit"]')].find((b) => /^postuler$/i.test(clean(b.innerText)));
      add('envoi_actif', send && visible(send) && !send.disabled);
    } else if (onAts()) {
      if (/^\/jobs\/search/.test(location.pathname) && ![...document.querySelectorAll('button')].some((b) => /submit application/i.test(clean(b.innerText)))) {
        c.push({ k: 'offre_indisponible', ok: true, skip: true, v: 'la page retombe sur la recherche (offre fermée ou retirée)' });
        return { site: location.hostname, criteria: c };
      }
      // Greenhouse / Lever / Ashby : formulaire d'entreprise (candidature invité ou MyGreenhouse)
      add('cv_adapte', exp.cv && (names.includes(exp.cv) || [...document.querySelectorAll('input[type=file]')].some((i) => i.files && i.files[0] && i.files[0].name === exp.cv)), names.join(', ').slice(0, 60) || 'aucun fichier relevé');
      const starred = (e) => /\*\s*$/.test(labelFromAncestors(e) || '') || /\*\s*$/.test(labelOf(e) || '');
      const req = [...document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]):not([type=submit]), textarea, select')].filter((e) => (visible(e) || isCombo(e)) && (e.required || e.getAttribute('aria-required') === 'true' || starred(e)) && !e.value && !(isCombo(e) && (comboControl(e).innerText || '').trim() && !PLACEHOLDER.test((comboControl(e).innerText || '').trim())));
      { const lab = [...document.querySelectorAll('label, div, span')].find((e) => e.children.length === 0 && /^location\s*\*?$/i.test((e.textContent || '').trim()) && visible(e));
        if (lab) { const box = lab.closest('div') && lab.closest('div').parentElement; const txt = ((box && box.innerText) || '').replace(/^\s*location\s*\*?/i, '').trim(); const filled = txt.length > 2 && !/^(search for|select)/i.test(txt); add('localisation', filled, filled ? 'renseignée' : 'vide'); } }
      add('trace_choix', true, (window.__sosjobFillLog || []).join(' ; ').slice(0, 160));
      add('champs_obligatoires', req.length === 0, req.length + ' vide(s)' + (req.length ? ' : ' + req.slice(0, 4).map((e) => (e.name || e.id || e.getAttribute('aria-label') || '?').slice(0, 16)).join(', ') : ''));
      const send = [...document.querySelectorAll('button, input[type=submit]')].find((b) => /^(submit application|submit|envoyer ma candidature|apply)$/i.test(clean(b.innerText || b.value || '')) && (b.type === 'submit' || /submit/i.test(clean(b.innerText || b.value || ''))) && visible(b));
      add('envoi_actif', !!send && !send.disabled, send ? clean(send.innerText || send.value).slice(0, 24) : '');
    } else if (onSf()) {
      const apply = [...document.querySelectorAll('a')].find((a) => /^(postuler|apply|apply now)$/i.test(clean(a.innerText)) && visible(a));
      const wk = window.__sosjobWk;
      if (!wk && !document.querySelector('iframe[src*="welcomekit"]') && apply) c.push({ k: 'hors_site', ok: true, skip: true, v: 'le lien n’ouvre pas le formulaire WelcomeKit : candidature chez l’employeur' });
      else (wk || [{ k: 'formulaire', ok: false, v: 'aucun rapport du cadre welcomekit' }]).forEach((x) => c.push(x));
    } else if (onFree()) {
      // offre qui renvoie chez l'employeur : pas de formulaire, « Apply to this job » est un lien -> écartée (pas un échec)
      if (!document.querySelector('textarea[name="job-application-message"]') && [...document.querySelectorAll('a')].some((a) => /^(apply to this job|je postule|postuler)$/i.test(clean(a.innerText)) && visible(a))) {
        c.push({ k: 'hors_site', ok: true, skip: true, v: 'candidature chez l’employeur' });
        return { site: location.hostname, criteria: c };
      }
      const rowPdf = (re) => { const l = [...document.querySelectorAll('div, span')].find((e) => e.children.length === 0 && visible(e) && re.test(clean(e.textContent))); const row = l && (l.parentElement && l.parentElement.parentElement); return row ? [...row.querySelectorAll('span, a, div')].filter((e) => e.children.length === 0 && /\.pdf\s*$/i.test((e.textContent || '').trim())).map((e) => e.textContent.trim()) : []; };
      const def = rowPdf(/^(default cv|cv partagé)$/i), extra = rowPdf(/^(additional document|document additionnel)$/i);
      add('cv_adapte', exp.cv && def.includes(exp.cv), 'défaut : ' + def.join(', '));
      add('lm_jointe', exp.lm && extra.includes(exp.lm), 'additionnel : ' + extra.join(', '));
      { const n = Number(sessionStorage.getItem('sosjob-cv-count') || 0); if (n) add('cv_dans_compte', n <= 6, n + ' CV déjà dans le compte avant ce passage (à nettoyer à la main si trop)'); }
      const ta = document.querySelector('textarea[name="job-application-message"]');
      add('message_perso', ta && lenOf(ta) > 80, lenOf(ta));
      add('envoi_actif', btnOk(/^(je postule|apply to this job)$/i));
    }
    if (!c.length && !onWtj() && !onApec() && !onHello() && !onFree() && !onCad() && !onSf()) c.push({ k: 'hors_site', ok: true, skip: true, v: 'page finale : ' + location.hostname });
    // questions à choix (radios) : toutes répondues ?
    { const radios = [...document.querySelectorAll('input[type=radio]')].filter((r) => r.name && (visible(r) || visible(r.parentElement)));
      const names = [...new Set(radios.map((r) => r.name))];
      const open = names.filter((n) => !radios.some((r) => r.name === n && r.checked));
      if (names.length) add('questions_a_choix', open.length === 0, (names.length - open.length) + '/' + names.length + ' répondues'); }
    return { site: location.hostname, criteria: c };
  }
  function snapshot() {
    if (pwVisible()) return { skipped: 'mot de passe visible' };
    return {
      url: location.origin + location.pathname,
      dialogs: document.querySelectorAll('[role=dialog],[aria-modal=true]').length,
      deepFiles: typeof deepAll === 'function' ? deepAll('input[type=file]').length : -1,
      buttons: [...document.querySelectorAll('button, a.btn, [role=button]')].slice(0, 80)
        .map((b) => ({ tag: b.tagName, type: b.getAttribute('type') || '', label: clean(b.innerText || b.getAttribute('aria-label') || '').slice(0, 40), disabled: !!b.disabled, visible: visible(b) })),
      fields: [...document.querySelectorAll('input:not([type=hidden]), textarea, select')].slice(0, 80)
        .map((f) => ({ tag: f.tagName, type: f.type || '', name: (f.name || f.id || '').slice(0, 40), visible: visible(f), len: (f.value || '').length })),
    };
  }
  function scrollToForm() {
    if (pwVisible()) return false;
    const el = (onCad() && cadForm() && (cadForm().querySelector('input[type=file]') || cadForm().querySelector('button[type="submit"]'))) || document.querySelector('input[name="custom-answer-0"]') || document.querySelector('[role=dialog] button[data-testid="apply-form-submit"], [data-cy="submitButton"], textarea[name="job-application-message"]')
      || [...document.querySelectorAll('button')].find((b) => /^envoyer ma candidature$/i.test(clean(b.innerText)));
    if (el) el.scrollIntoView({ block: 'center' });
    return !!el;
  }

  // Cadremploi : formulaire « Envoyez votre candidature ! » sur la page de l'offre (offres « un clic » internes ; les autres renvoient chez l'employeur).
  // PIÈGE : le bouton qui affiche le CV enregistré n'a pas d'attribut type = bouton submit : un clic provoque une tentative d'envoi.
  // On le rend inoffensif (type=button) avant tout clic. Jamais de clic sur le « Postuler » du formulaire (type=submit) : il envoie.
  const onCad = () => /(^|\.)cadremploi\.fr$/.test(location.hostname);
  const cadForm = () => { const n = document.querySelector('input[name="nom"]'); return n && n.closest('form'); };
  // Cadremploi préremplit une lettre générique (« ... pour lequel je souhaite vous proposer ma candidature ») : on l'efface pour la remplacer.
  function cadClearDefaultLetter() {
    const form = cadForm();
    for (const t of form ? form.querySelectorAll('textarea') : []) {
      if (!visible(t) || !/je souhaite vous proposer ma candidature/i.test(t.value)) continue;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(t, '');
      t.dispatchEvent(new Event('input', { bubbles: true }));
      t.setAttribute('data-sosjob-label', 'Lettre de motivation / message au recruteur * (message court de 3 à 5 phrases, quelques centaines de caractères, personnalisé pour cette offre à partir du CV et de la lettre de motivation ; pas de formule générique)');
    }
  }
  function cadNext() {
    if (!/detail_offre/.test(location.pathname)) return '';
    const form = cadForm();
    // le formulaire s'affiche parfois tard : l'attendre avant de conclure qu'il n'y en a pas
    if (!form) return freeHelpers().waitFor(() => cadForm(), 14000).then((f) => (f ? cadNext() : ''));
    const root = document.documentElement;
    // jamais de bouton sans type dans le formulaire : tout bouton non explicitement « submit » devient un simple bouton
    form.querySelectorAll('button').forEach((b) => { if (!b.hasAttribute('type')) b.setAttribute('type', 'button'); });
    if (!root.hasAttribute('data-sosjob-cad-cv')) {
      const cv = [...form.querySelectorAll('button')].find((b) => /\.(pdf|docx?|rtf)\s*$/i.test(clean(b.innerText)));
      if (cv) { root.setAttribute('data-sosjob-cad-cv', '1'); cv.scrollIntoView({ block: 'center' }); cv.click(); return 'CV : remplacer'; }
    }
    if (!root.hasAttribute('data-sosjob-cad-lm')) {
      const head = [...form.querySelectorAll('span, div')].filter((e) => e.children.length <= 1 && /^personnaliser ma lettre de motivation/i.test(clean(e.textContent)) && (e.textContent || '').length < 60).pop();
      if (head && ![...form.querySelectorAll('textarea')].some(visible)) { root.setAttribute('data-sosjob-cad-lm', '1'); head.click(); return 'Lettre : déplier'; }
    }
    return '';
  }

  // Station F Jobs (WelcomeKit) : « POSTULER » (lien) ouvre le « Formulaire de Candidature » dans une fenêtre (colorbox, cadre). Jamais de clic sur son bouton d'envoi.
  const onAts = () => /(^|\.)(greenhouse\.io|lever\.co|ashbyhq\.com)$/.test(location.hostname);
  const onSf = () => /(^|\.)jobs\.stationf\.co$/.test(location.hostname);
  function sfNext() {
    if (!/\/companies\/[^/]+\/jobs\//.test(location.pathname)) return '';
    const root = document.documentElement;
    if (root.hasAttribute('data-sosjob-sf-open')) return '';
    const a = [...document.querySelectorAll('a')].find((x) => /^(postuler|apply|apply now|apply for this job)$/i.test(clean(x.innerText)) && visible(x));
    if (!a) return '';
    root.setAttribute('data-sosjob-sf-open', '1');
    a.scrollIntoView({ block: 'center' }); a.click(); tickFlow();  // le formulaire s'ouvre dans un cadre : rien ne change dans la page elle-même
    return 'Postuler (ouvrir le formulaire)';
  }

  // WelcomeKit (formulaire de Station F, dans un cadre d'un autre domaine) : le cadre publie son état final au parent, que la page ne peut pas lire.
  // Jamais de valeur perso : booléens, longueurs, noms de fichiers. Le reCAPTCHA du formulaire n'est jamais touché (l'envoi demande l'utilisateur).
  const onWk = () => /(^|\.)welcomekit\.co$/.test(location.hostname);
  function wkState() {
    if (pwVisible()) return [];
    const c = [];
    const files = [...document.querySelectorAll('input[type=file]')].map((i) => i.files && i.files[0] && i.files[0].name).filter(Boolean).concat(pdfNames());
    c.push({ k: 'cv_adapte', ok: files.some((n) => /^cv_/i.test(n)), v: files.join(', ').slice(0, 60) || 'aucun fichier relevé' });
    const letter = [...document.querySelectorAll('textarea')].filter(visible).sort((a, b) => b.value.length - a.value.length)[0];
    c.push({ k: 'lettre_perso', ok: !!letter && letter.value.length > 80, v: String(letter ? letter.value.length : 0) });
    const inputs = [...document.querySelectorAll('input[type=checkbox]')];
    const roles = [...document.querySelectorAll('[role=checkbox]')];
    const ticked = inputs.filter((b) => b.checked).length + roles.filter((r) => r.getAttribute('aria-checked') === 'true').length;
    const total = Math.max(inputs.length, roles.length);
    if (total) c.push({ k: 'consentement', ok: ticked >= total, v: ticked + '/' + total });
    const empty = [...document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=file]):not([type=submit]), select')].filter((e) => visible(e) && !e.value && (e.required || e.getAttribute('aria-required') === 'true'));
    c.push({ k: 'champs_obligatoires', ok: empty.length === 0, v: empty.length + ' vide(s)' });
    if (document.querySelector('iframe[src*="recaptcha"], .g-recaptcha')) c.push({ k: 'captcha', ok: true, skip: true, v: 'reCAPTCHA présent : l’envoi demande l’utilisateur' });
    const send = [...document.querySelectorAll('button, input[type=submit]')].find((b) => /submit|send|envoyer|postuler|apply/i.test(clean(b.innerText || b.value || '')) && visible(b));
    c.push({ k: 'envoi_visible', ok: !!send && !send.disabled, v: send ? clean(send.innerText || send.value).slice(0, 30) : '' });
    return c;
  }
  if (onWk() && window.parent !== window && !window.__sosjobWkTimer) {
    window.__sosjobWkTimer = setInterval(() => { try { window.parent.postMessage({ sosjobWk: wkState() }, '*'); } catch (e) { /* parent injoignable */ } }, 800);
  }
  if (window.top === window) window.addEventListener('message', (e) => { if (e.data && e.data.sosjobWk) { window.__sosjobWk = e.data.sosjobWk; window.__sosjobWkN = (window.__sosjobWkN || 0) + 1; window.__sosjobWkAt = Date.now(); } });

  window.__sosjob = { siteState, snapshot, scrollToForm, clickEntry, submitReady, setCoverLetter, extract, readOptions, fill, toast, pageContext, stepSig, needsLogin, isReview, clickNext, fileInputs, attachFile };
})();
