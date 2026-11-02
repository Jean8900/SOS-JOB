// SOS-JOB : relais entre le programme local (raccourci global Ctrl+Alt+Espace, rédaction des réponses)
// et la page. Le programme local écoute sur 127.0.0.1 (fill_server_port de input/copilot.yaml : garder identique).
const PORT = 47321;
const BASE = `http://127.0.0.1:${PORT}`;
const HEADERS = { 'X-SOSJOB': '1' };
const BROWSER = (navigator.userAgentData?.brands || []).some((b) => /Edge/i.test(b.brand)) ? 'edge' : 'chrome';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Identifiant propre à ce profil de navigateur (distingue deux profils), conservé quand le service worker se rendort.
let instanceId = null;
async function getInstance() {
  if (instanceId) return instanceId;
  const stored = await chrome.storage.local.get('instance');
  instanceId = stored.instance || Math.random().toString(36).slice(2, 10);
  if (!stored.instance) await chrome.storage.local.set({ instance: instanceId });
  return instanceId;
}
let polling = false;

async function inject(tabId) {
  await chrome.scripting.executeScript({ target: { tabId, allFrames: true }, files: ['content.js'] });
}

async function call(tabId, frameId, func, args) {
  const [res] = await chrome.scripting.executeScript({ target: { tabId, frameIds: [frameId] }, func, args });
  return res?.result;
}

async function toast(tabId, text, ms = 0) {
  try { await call(tabId, 0, (t, m) => window.__sosjob?.toast(t, m), [text, ms]); } catch (e) { /* page non scriptable */ }
}

const MAX_STEPS = 8;

// Envoi au programme local : trace, rapport, capture. Renvoie sa réponse JSON (ou {}).
async function post(path, body) {
  try {
    const r = await fetch(`${BASE}${path}?b=${BROWSER}&i=${await getInstance()}`, { method: 'POST', headers: { ...HEADERS, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    return await r.json();
  } catch (e) { return {}; }
}
// Cause de l'échec : une page rechargée en cours d'étape n'est pas un élément introuvable.
const classify = (e) => (/Frame with ID|was removed|No frame|navigated or closed|context invalidated|Cannot access/i.test(String(e)) ? 'page_rechargee' : 'exception');

// Un seul appui : remplit l'écran, passe à l'étape suivante par un bouton autorisé (jamais l'envoi), recommence.
// Arrêt classé : login, review, submit_ready, no_button, no_progress, max_steps, excluded, page_rechargee, exception.
// À la fin : état final vérifié (siteState), instantané si échec, capture de l'onglet, rapport envoyé au programme local.
async function fillAllSteps() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!tab?.id || !/^https?:/.test(tab.url || '')) return;
  const tabId = tab.id;
  const log = [];
  const rep = { url: '', steps: [], errors: [], stop: null, state: null, snapshot: null, shot: null };
  try { const u = new URL(tab.url); rep.url = u.origin + u.pathname; } catch (e) { /* url illisible */ }
  let stop = '', code = '';
  const end = (c, text) => { code = c; stop = text; };
  for (const k of Object.keys(pdfCache)) delete pdfCache[k];  // les PDF changent d'une offre à l'autre
  let step = 1;
  try {
    for (; step <= MAX_STEPS && !stop; step++) {
      const st = { n: step };
      rep.steps.push(st);
      await inject(tabId);
      if (await call(tabId, 0, () => window.__sosjob.needsLogin(), [])) {
        end('login', 'connexion demandée : connecte-toi (ton gestionnaire de mots de passe remplit), puis rappuie sur Ctrl+Alt+Espace');
        break;
      }
      // Welcome to the Jungle : ouvrir le formulaire depuis la page de l'offre
      if (await call(tabId, 0, () => window.__sosjob.clickEntry(), [])) { log.push('formulaire ouvert'); st.entry = true; await sleep(3500); await inject(tabId); }
      const r = await fillStep(tabId, step);
      st.filled = r.filled || 0; st.uploaded = r.uploaded || 0;
      if (r.fatal) { log.push(r.fatal); end(/désactiv/.test(r.fatal) ? 'excluded' : 'exception', r.fatal); break; }
      const up = r.uploaded ? ` + ${r.uploaded} fichier(s)` : '';
      log.push(r.filled ? `étape ${step} : ${r.filled} champ(s)${up}` : `étape ${step} : ${up ? up.slice(3) : 'rien à remplir'}`);
      if (await call(tabId, 0, () => window.__sosjob.isReview(), [])) { end('review', 'étape de révision : relis et envoie toi-même'); break; }

      // Welcome to the Jungle : formulaire rempli. L'envoi reste à l'utilisateur (le bouton envoie vraiment la candidature).
      if (await call(tabId, 0, () => window.__sosjob.submitReady(), [])) { end('submit_ready', "formulaire prêt : clique toi-même sur « J'envoie ma candidature ! »"); break; }

      // bouton de passage (dans le premier cadre qui en a un)
      const before = await call(tabId, 0, () => window.__sosjob.stepSig(), []);
      const frames = await chrome.webNavigation?.getAllFrames?.({ tabId }) ?? [{ frameId: 0 }];
      let clicked = '', clickErr = '';
      for (const { frameId } of frames) {
        try { clicked = await call(tabId, frameId, () => window.__sosjob?.clickNext() || '', []); }
        catch (e) { clickErr = String(e).slice(0, 160); rep.errors.push({ step, where: 'clickNext', frame: frameId, kind: classify(e), msg: clickErr }); }
        if (clicked) break;
      }
      st.clicked = clicked;
      if (!clicked) {
        if (clickErr) end(classify(clickErr), `étape ${step} interrompue : ${clickErr}`);
        else end('no_button', 'plus de bouton « Suivant » : relis et envoie toi-même');
        break;
      }

      // attendre l'écran suivant (rechargement de page ou nouveau contenu)
      let moved = false;
      for (let i = 0; i < 24 && !moved; i++) {
        await sleep(500);
        try {
          await inject(tabId);
          moved = (await call(tabId, 0, () => window.__sosjob.stepSig(), [])) !== before;
        } catch (e) { /* page en cours de chargement */ }
      }
      st.moved = moved;
      if (!moved) { end('no_progress', `l'étape ${step} n'avance pas (clic sans effet ou champ obligatoire manquant) : complète à la main`); break; }
      await sleep(800);
    }
    if (!stop) end('max_steps', `${MAX_STEPS} étapes atteintes : continue à la main`);
  } catch (e) {
    rep.errors.push({ step, where: 'boucle', kind: classify(e), msg: String(e).slice(0, 200) });
    end(classify(e), `erreur à l'étape ${step} : ${String(e).slice(0, 120)}`);
  }
  rep.stop = { code, text: stop };
  await toast(tabId, `SOS-JOB : ${log.join(' ; ')}. Arrêt : ${stop}`, 15000);

  // État final, instantané et capture : jamais si un champ mot de passe est visible.
  try {
    await inject(tabId);
    if (!(await call(tabId, 0, () => window.__sosjob.needsLogin(), []))) {
      const exp = { cv: pdfCache.cv?.name || '', lm: pdfCache.lm?.name || '' };
      rep.state = await call(tabId, 0, (e) => window.__sosjob.siteState?.(e), [exp]);
      const failed = (rep.state?.criteria || []).some((c) => !c.ok) || !['review', 'submit_ready', 'no_button'].includes(code);
      if (failed) rep.snapshot = await call(tabId, 0, () => window.__sosjob.snapshot?.(), []);
      await call(tabId, 0, () => window.__sosjob.scrollToForm?.(), []);
      await sleep(700);
      const png = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
      const saved = await post('/shot', { url: rep.url, png });
      rep.shot = saved.path || null;
    }
  } catch (e) { rep.errors.push({ step, where: 'état final', kind: classify(e), msg: String(e).slice(0, 160) }); }
  rep.log = log;
  await post('/report', rep);
  return log.join(' ; ') + ' | ' + stop;
}

// PDF préparés par le programme local pour l'offre en cours (CV / LM) ; null s'il n'y en a pas.
const pdfCache = {};
async function getPdf(kind) {
  if (pdfCache[kind] !== undefined) return pdfCache[kind];
  let pdf = null;
  try {
    const r = await fetch(`${BASE}/file?b=${BROWSER}&k=${kind}&t=${Date.now()}`, { headers: HEADERS });
    if (r.ok) {
      if (kind === 'lmtxt') return (pdfCache[kind] = { text: await r.text() });
      const bytes = new Uint8Array(await r.arrayBuffer());
      let bin = '';
      for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
      pdf = { b64: btoa(bin), name: decodeURIComponent(r.headers.get('X-Filename') || `${kind}.pdf`) };
    }
  } catch (e) { /* programme local injoignable */ }
  return (pdfCache[kind] = pdf);
}

// Pose le CV et la LM dans les champs « fichier » vides de chaque cadre. Un seul champ sans libellé clair = le CV.
async function uploadFiles(tabId, frames) {
  let done = 0;
  const inputs = [];
  for (const { frameId } of frames) {
    try {
      for (const f of await call(tabId, frameId, () => window.__sosjob?.fileInputs() ?? [], [])) inputs.push({ ...f, frameId });
    } catch (e) { /* cadre inaccessible */ }
  }
  for (const f of inputs) {
    const kind = f.kind === 'other' && inputs.length === 1 ? 'cv' : f.kind;
    if (kind === 'other') continue;
    const pdf = await getPdf(kind);
    if (!pdf) continue;
    try { if (await call(tabId, f.frameId, (id, b, n) => window.__sosjob.attachFile(id, b, n), [f.id, pdf.b64, pdf.name])) done++; }
    catch (e) { /* cadre fermé */ }
  }
  const lmText = await getPdf('lmtxt');
  if (lmText?.text && await call(tabId, 0, (t) => window.__sosjob.setCoverLetter(t), [lmText.text])) done++;
  return done;
}

async function fillStep(tabId, step) {
  await toast(tabId, `SOS-JOB : lecture du formulaire (étape ${step})...`);

  // 1. champs vides de chaque cadre (ids préfixés par le cadre : uniques sur la page)
  const frames = await chrome.webNavigation?.getAllFrames?.({ tabId }) ?? [{ frameId: 0 }];
  const uploaded = await uploadFiles(tabId, frames);
  if (uploaded) await sleep(1500);  // le site traite le fichier (analyse du CV, remplissage automatique)
  const fields = [];
  for (const { frameId } of frames) {
    try {
      const found = await call(tabId, frameId, (p) => window.__sosjob?.extract(p) ?? [], [String(frameId)]);
      for (const f of found) fields.push({ ...f, frameId });
    } catch (e) { /* cadre inaccessible */ }
  }
  if (!fields.length) return { filled: 0, uploaded };
  for (const f of fields.filter((x) => x.kind === 'dropdown' || x.kind === 'combobox')) {
    f.options = await call(tabId, f.frameId, (field) => window.__sosjob.readOptions(field), [f]);
  }
  const askable = fields.filter((f) => !['dropdown', 'combobox'].includes(f.kind) || (f.options || []).length);

  // 2. réponses rédigées par le programme local (CV + profil perso + contexte de la page)
  const context = await call(tabId, 0, () => window.__sosjob.pageContext(), []);
  const response = await fetch(`${BASE}/answers`, {
    method: 'POST', headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...context, fields: askable.map(({ frameId, ...f }) => f) }),
  });
  const data = await response.json();
  if (data.excluded) return { fatal: `remplissage désactivé sur ce site (${data.excluded})` };
  if (data.error) return { fatal: `échec (${data.error})` };

  // 3. remplissage, cadre par cadre
  let filled = 0;
  for (const { frameId } of frames) {
    const mine = askable.filter((f) => f.frameId === frameId).map(({ frameId: _, ...f }) => f);
    if (!mine.length) continue;
    try { filled += await call(tabId, frameId, (fs, a) => window.__sosjob.fill(fs, a), [mine, data.answers]) || 0; } catch (e) { /* cadre fermé */ }
  }
  return { filled, uploaded };
}

// Attente longue des ordres du programme local ; reprise à chaque réveil du service worker.
async function poll() {
  if (polling) return;
  polling = true;
  for (;;) {
    try {
      const INSTANCE = await getInstance();
      const r = await fetch(`${BASE}/poll?b=${BROWSER}&i=${INSTANCE}`, { headers: HEADERS });
      const { cmd } = await r.json();
      if (cmd === 'fill') {
        // L'ordre part vers toutes les instances : seule celle dont la fenêtre est au premier plan agit.
        const win = await chrome.windows.getLastFocused().catch(() => null);
        const me = await getInstance();
        const report = (note) => fetch(`${BASE}/done?b=${BROWSER}&i=${me}&note=${encodeURIComponent(note)}`, { headers: HEADERS }).catch(() => {});
        if (!win?.focused) { report('ordre ignoré : fenêtre de cette instance sans le focus'); continue; }
        try { report(await fillAllSteps() || ''); }
        catch (e) { console.error('SOS-JOB', e); report("erreur dans l'extension : " + String(e).slice(0, 120)); }
      }
    } catch (e) {
      await sleep(5000);  // programme local arrêté : on réessaie
    }
  }
}

chrome.alarms.create('sosjob-keepalive', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(() => poll());
chrome.runtime.onStartup.addListener(() => poll());
chrome.runtime.onInstalled.addListener(() => poll());
poll();
