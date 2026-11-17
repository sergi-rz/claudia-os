// La Sala del Consejo · lógica común a todos los temas.
// Lee la sesión que va escribiendo Claudia (/api/session/<id>) y la cuenta en tres modos:
// Escena (mesa animada, mensajes paginados), Rápido (fichas plegables) y Acta (texto completo).
// Los temas solo cambian el aspecto y el sonido: ver THEMES.md.

const params = new URLSearchParams(location.search);
const SPEED = parseFloat(params.get("speed") || "1");
const CHAR_MS = 26 / SPEED;
const PAGE_CHARS = 230;

const DEFAULT_STRINGS = {
  brand: "La Sala del Consejo", host: "Claudia", enter: "{name} toma asiento",
  convoked: "Se convoca el consejo", openLine: "Os he reunido para pensar esto: {q}",
  tableIdle: "El consejo se reúne", tableLive: "El consejo delibera", tableReplies: "Réplicas", tableDone: "Veredicto",
  replies: "Ronda de réplicas", repliesLine: "Que empiecen las réplicas: ahora se contestan entre ellos.",
  verdict: "Veredicto del consejo", verdict2: "Veredicto tras las réplicas",
  options: "Opciones sobre la mesa", optionsLine: "Estas son las opciones que han salido, con quién las defiende y quién les pone pegas.",
  rebate: "rebate a", completa: "completa a", matiza: "matiza a", replyTo: "responde a",
  backs: "la defienden", objects: "le ponen pegas", sources: "Fuentes",
  hint: "espacio para seguir", empty: "Todavía no hay ningún consejo. Pídele a Claudia un Council y dile que lo enseñe en La Sala.",
};

const ICON = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ROLE_ICONS = {
  pragm: ICON('<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.5-.5-.5-2.5z"/>'),
  escép: ICON('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'), escep: ICON('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
  vision: ICON('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  usuario: ICON('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  guard: ICON('<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>'),
  contrar: ICON('<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>'),
  experto: ICON('<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>'),
  cliente: ICON('<path d="M3 7h18v13H3z"/><path d="M8 7V4h8v3"/>'),
  inversor: ICON('<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
  host: ICON('<path d="M12 3v18M5 21h14M4 7h16"/><path d="M7 7l-3 7a3 3 0 0 0 6 0zM17 7l-3 7a3 3 0 0 0 6 0z"/>'),
};

const state = {
  sessionId: params.get("s") || "latest", data: null, theme: null, themeCfg: {},
  mode: localStorage.getItem("sala.mode") || "scene",
  auto: localStorage.getItem("sala.auto") === "1", rec: false, autoBeforeRec: false,
  sound: localStorage.getItem("sala.sound") !== "0",
  shown: 0, typing: false, generation: 0, pumping: false, opened: false, entered: false,
  advance: null, skipTyping: false, openCards: new Set(), seats: {}, expandVoice: false, narratingVoice: false,
  geo: { cx: 50, cy: 50, rx: 37, ry: 40 },   // dónde está la mesa y a qué distancia se sientan (en % de la escena)
};

// ---------- utilidades ----------
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const hue = (n) => { let h = 0; for (const c of n) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const initials = (n) => n.replace(/^(el|la|los|las)\s+/i, "").split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const roleIcon = (n) => { n = n.toLowerCase(); for (const k in ROLE_ICONS) if (n.includes(k)) return ROLE_ICONS[k]; return null; };
const S = (k) => (state.themeCfg.strings || {})[k] ?? DEFAULT_STRINGS[k];
// Algunas fuentes (las pixeladas) no tienen mayúsculas con tilde: el tema lo pide con "label_case".
const L = (s) => state.themeCfg.label_case === "upper-plain"
  ? String(s).toUpperCase().normalize("NFD").replace(/[̀-ͯ]/g, "") : String(s);
const member = (name) => (state.data && state.data.members.find((x) => x.name === name)) || { name, kind: "rol" };
const kindLabel = (m) => m.kind === "real" ? `voz real${m.entries ? " · " + m.entries + " entradas" : ""}` : m.kind === "inferida" ? "voz inferida" : m.kind === "host" ? "anfitriona" : "rol";
const firstSentence = (t) => (String(t).replace(/[*_]/g, "").split(/(?<=[.!?…])\s+/)[0] || "").slice(0, 160);
const norm = (s) => String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w ]/g, "").trim();
const replyVerb = (v) => S(v.type || "replyTo");

// Markdown mínimo. Las citas «Título» se convierten en enlace si la voz trae esa fuente.
function render(md, sources) {
  const h = esc(md)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/«([^»]+)»/g, (all, title) => {
      const src = (sources || []).find((s) => norm(s.title) === norm(title) || norm(s.title).startsWith(norm(title)) || norm(title).startsWith(norm(s.title)));
      return src ? `<a class="cite" href="${esc(src.url)}" target="_blank" rel="noopener">«${title}»</a>` : `<span class="cite">«${title}»</span>`;
    })
    .replace(/\b(\d{4}-\d{2}-\d{2})\b/g, '<span class="date">$1</span>');
  return h.split(/\n{2,}/).map((b) => {
    const lines = b.split("\n");
    if (lines.every((l) => /^\s*[-•]\s+/.test(l))) return "<ul>" + lines.map((l) => `<li>${l.replace(/^\s*[-•]\s+/, "")}</li>`).join("") + "</ul>";
    return `<p>${lines.join("<br>")}</p>`;
  }).join("");
}

function sourcesHtml(sources) {
  if (!sources || !sources.length) return "";
  return `<div class="sources"><span class="sources-label">${esc(S("sources"))}:</span> ` +
    sources.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> <span class="date">${esc(s.date || "")}</span>`).join(" · ") + "</div>";
}

// Trocea un texto en páginas cortas, como los diálogos de los juegos: por frases, sin pasarse de PAGE_CHARS.
function paginate(md) {
  const pages = [];
  for (const block of md.split(/\n{2,}/)) {
    const units = /^\s*[-•]\s+/.test(block) ? block.split("\n") : block.split(/(?<=[.!?…:])\s+/);
    let cur = "";
    for (let u of units) {
      while (u.length > PAGE_CHARS) {          // una frase larguísima: se corta por palabras
        const cut = u.lastIndexOf(" ", PAGE_CHARS);
        const head = u.slice(0, cut > 40 ? cut : PAGE_CHARS);
        if (cur) { pages.push(cur); cur = ""; }
        pages.push(head); u = u.slice(head.length).trim();
      }
      const joiner = /^\s*[-•]\s+/.test(u) ? "\n" : " ";
      if (cur && (cur + joiner + u).length > PAGE_CHARS) { pages.push(cur); cur = u; }
      else cur = cur ? cur + joiner + u : u;
    }
    if (cur) pages.push(cur);
  }
  return pages.length ? pages : [""];
}

function portrait(m, el) {
  el.innerHTML = "";
  if (m.photo) {
    const img = new Image();
    img.onload = () => {
      // pixelate: false, true (28 px) o un número (tamaño en px de la foto pixelada)
      const pv = state.themeCfg.pixelate, pix = !!pv;
      const c = document.createElement("canvas"), n = typeof pv === "number" ? pv : pix ? 28 : 192;
      c.width = c.height = n;
      const ctx = c.getContext("2d"); ctx.imageSmoothingEnabled = !pix;
      const s = Math.min(img.width, img.height);
      ctx.drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, n, n);
      if (pix) c.style.imageRendering = "pixelated";
      el.appendChild(c);
    };
    img.src = `/photos/${encodeURIComponent(m.photo)}`;
    return el;
  }
  const t = document.createElement("div");
  t.className = "tile";
  t.style.background = `hsl(${hue(m.name)} var(--tile-s, 50%) var(--tile-l, 64%))`;
  const icon = m.kind === "host" ? ROLE_ICONS.host : m.kind === "rol" ? roleIcon(m.name) : null;
  t.innerHTML = icon || `<span>${esc(initials(m.name))}</span>`;
  el.appendChild(t);
  return el;
}

function mini(name, cls) {
  const m = member(name);
  const d = document.createElement("span");
  d.className = `mini ${cls} kind-${m.kind}`; d.title = name;
  portrait(m, d);
  return d;
}

// ---------- sonido (sintetizado, sin ficheros) ----------
const Sound = {
  ctx: null,
  unlock() {
    if (!this.ctx) { try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch { return; } }
    if (this.ctx.state === "suspended") this.ctx.resume();
  },
  tone(freq, { at = 0, dur = 0.12, type = "square", vol = 0.05, slide = null, decay = null } = {}) {
    const c = this.ctx; if (!c) return;
    const t0 = c.currentTime + at, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t0);
    if (slide) o.frequency.exponentialRampToValueAtTime(slide, t0 + dur);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(vol, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + (decay || dur));
    o.connect(g).connect(c.destination); o.start(t0); o.stop(t0 + (decay || dur) + 0.05);
  },
  bell(freq, at = 0, vol = 0.05) {   // campana: fundamental + parciales con caída larga
    [[1, 1], [2.76, 0.35], [5.4, 0.15]].forEach(([k, v]) => this.tone(freq * k, { at, type: "sine", vol: vol * v, decay: 1.4 }));
  },
  play(name) {
    if (!state.sound || !this.ctx) return;
    const p = state.themeCfg.sounds || "soft";
    if (p === "none") return;
    if (p === "8bit") {
      const seq = { tick: [[1200, 0.02, 0.012]], turn: [[660, 0.06], [880, 0.08]], enter: [[440, 0.05], [660, 0.07]],
        page: [[520, 0.04]], reply: [[330, 0.07], [247, 0.09]], decree: [[523, 0.09], [659, 0.09], [784, 0.09], [1046, 0.18]], option: [[784, 0.05]] }[name];
      if (!seq) return;
      let at = 0; for (const [f, d, v] of seq) { this.tone(f, { at, dur: d, type: "square", vol: v || 0.035 }); at += d; }
    } else if (p === "medieval") {
      if (name === "turn") this.bell(659);
      else if (name === "reply") { this.bell(494); this.bell(392, 0.18, 0.035); }
      else if (name === "enter") { this.tone(98, { type: "sine", vol: 0.12, slide: 55, dur: 0.25 }); }       // tambor
      else if (name === "page") this.tone(880, { type: "triangle", vol: 0.025, dur: 0.06 });                  // pluma
      else if (name === "option") this.bell(988, 0, 0.03);
      else if (name === "decree") [392, 523, 659, 784].forEach((f, i) => this.tone(f, { at: i * 0.16, type: "triangle", vol: 0.06, dur: 0.15, decay: i === 3 ? 0.9 : 0.2 }));
    } else {   // soft
      const f = { turn: 660, reply: 494, enter: 523, page: 0, option: 784, decree: 523 }[name];
      if (f) this.tone(f, { type: "sine", vol: 0.035, dur: 0.18 });
      if (name === "decree") this.tone(784, { at: 0.15, type: "sine", vol: 0.035, dur: 0.3 });
    }
  },
};

// ---------- línea de tiempo ----------
function timeline() {
  const d = state.data;
  const r1 = d.voices.filter((v) => (v.round || 1) === 1), r2 = d.voices.filter((v) => v.round === 2);
  const t = r1.map((v) => ({ type: "voice", v }));
  if (d.synthesis) t.push({ type: "synth", s: d.synthesis, round: 1 });
  if (r2.length || d.round === 2) { t.push({ type: "divider" }); r2.forEach((v) => t.push({ type: "voice", v })); }
  if (d.synthesis2) t.push({ type: "synth", s: d.synthesis2, round: 2 });
  return t;
}
const narrated = () => timeline().slice(0, state.shown).filter((i) => i.type === "voice").map((i) => i.v);

// ---------- escena ----------
function buildSeats() {
  Object.values(state.seats).forEach((e) => e.remove());
  state.seats = {};
  const n = state.data.members.length;
  state.data.members.forEach((m, i) => {
    const a = (-90 + (360 / n) * i) * Math.PI / 180, g = state.geo;
    const seat = document.createElement("div");
    seat.className = `seat kind-${m.kind} state-waiting` + (state.entered ? "" : " absent");
    seat.style.left = g.cx + g.rx * Math.cos(a) + "%";
    seat.style.top = g.cy + g.ry * Math.sin(a) + "%";
    seat.title = "Ver su ficha";
    seat.onclick = (e) => { e.stopPropagation(); openSheet(m.name); };
    const p = document.createElement("div"); p.className = "portrait";
    const pic = document.createElement("div"); pic.className = "pic"; portrait(m, pic);
    p.appendChild(pic);
    seat.insertAdjacentHTML("beforeend", '<div class="bubble"><span>.</span><span>.</span><span>.</span></div>');
    seat.appendChild(p);
    seat.insertAdjacentHTML("beforeend", `<div class="plate"><span class="name">${esc(m.name)}</span><span class="kind">${esc(kindLabel(m))}</span></div>`);
    $("stage").appendChild(seat);
    state.seats[m.name] = seat;
  });
}

function seatState(m) {
  const d = state.data, tl = timeline(), cur = tl[state.shown];
  if (state.typing && cur && cur.type === "voice" && cur.v.member === m.name) return "speaking";
  const spoke = narrated().some((v) => v.member === m.name);
  const caughtUp = !state.typing && state.shown >= tl.length;
  const spokeR1 = d.voices.filter((v) => (v.round || 1) === 1).map((v) => v.member);
  const next = d.members.map((x) => x.name).find((n) => !spokeR1.includes(n));
  if (d.status === "deliberando" && d.round !== 2 && caughtUp && state.entered && next === m.name) return "thinking";
  return spoke ? "spoken" : "waiting";
}

function drawSeats() {
  for (const m of state.data.members) {
    const el = state.seats[m.name]; if (!el) continue;
    const st = seatState(m);
    el.classList.remove("state-speaking", "state-thinking", "state-spoken", "state-waiting");
    el.classList.add("state-" + st);
    el.querySelector(".bubble").innerHTML = st === "speaking" ? "¡!" : "<span>.</span><span>.</span><span>.</span>";
  }
}

function phase() {
  const tl = timeline(), div = tl.findIndex((i) => i.type === "divider");
  const caughtUp = state.shown >= tl.length && !state.typing;
  const live = !caughtUp || state.data.status === "deliberando";
  return { live, caughtUp, inReplies: div !== -1 && state.shown > div };
}

function drawStatus() {
  const d = state.data, { live, inReplies } = phase();
  const r1 = narrated().filter((v) => (v.round || 1) === 1).length, r2 = narrated().filter((v) => v.round === 2).length;
  const totalR2 = d.voices.filter((v) => v.round === 2).length;
  let txt, label;
  if (!state.entered) { txt = "El consejo se reúne"; label = S("tableIdle"); }
  else if (live && inReplies) { txt = `<b>● Réplicas</b> · ${r2} hasta ahora`; label = S("tableReplies"); }
  else if (live) { txt = `<b>● Deliberando</b> · ${r1} de ${d.members.length} voces`; label = S("tableLive"); }
  else { txt = `Consejo cerrado · ${d.members.length} voces` + (totalR2 ? ` · ${totalR2} ${totalR2 === 1 ? "réplica" : "réplicas"}` : ""); label = S("tableDone"); }
  $("status").innerHTML = txt;
  $("tableLabel").innerHTML = `<span class="emblem"></span><span class="label-text">${esc(L(label))}</span>`;
}

// Rayos entre asientos. Sin filtros SVG: en líneas verticales u horizontales (caja de ancho 0) el brillo desaparece.
function beamLine(from, to, cls) {
  const a = state.seats[from], b = state.seats[to];
  if (!a || !b) return "";
  const xy = `x1="${a.style.left}" y1="${a.style.top}" x2="${b.style.left}" y2="${b.style.top}"`;
  return `<line class="glow ${cls}" ${xy}/><line class="ray ${cls}" ${xy}/>`;
}
function drawBeam(v) {
  $("beam").innerHTML = v && v.to ? beamLine(v.member, v.to, "type-" + (v.type || "responde")) : "";
}
// Al cerrar, el mapa de relaciones: todas las réplicas a la vez, con su color según el tipo.
function drawRelations() {
  const replies = state.data.voices.filter((v) => v.round === 2 && v.to);
  $("beam").innerHTML = replies.map((v) => beamLine(v.member, v.to, `map type-${v.type || "responde"}`)).join("");
  $("legend").innerHTML = replies.length ? [...new Set(replies.map((v) => v.type || "responde"))]
    .map((t) => `<span class="legend-item type-${t}"><i></i>${esc(t === "responde" ? "responde" : t)}</span>`).join("") : "";
}

function toast(text) {
  const t = $("toast");
  t.innerHTML = `<span>${esc(L(text))}</span>`;
  t.classList.add("show");
}

async function opening(gen) {
  const host = { name: S("host"), kind: "host" }, q = state.data.question;
  $("decree").innerHTML = `<h3>${esc(L(S("convoked")))}</h3><p>${esc(q)}</p>`;
  $("decree").classList.add("show", "opening");
  setDialog(host, `<span class="who">${esc(L(S("host")))}</span>`);
  Sound.play("decree");
  await typePage(S("openLine").replace("{q}", q), gen);
  await waitAdvance(q.length + 40);
  $("decree").classList.remove("show", "opening");
  state.opened = true;
  await sleep(350 / SPEED);
}

async function entrance(gen) {
  for (const m of state.data.members) {
    if (gen !== state.generation) return;
    const el = state.seats[m.name]; if (!el) continue;
    el.classList.remove("absent"); el.classList.add("entering");
    toast(S("enter").replace("{name}", m.name));
    Sound.play("enter");
    await sleep(560 / SPEED);
    el.classList.remove("entering");
  }
  $("toast").classList.remove("show");
  state.entered = true;
  drawSeats(); drawStatus();
  await sleep(350 / SPEED);
}

// ---------- diálogo paginado ----------
function setDialog(m, headerHtml) {
  portrait(m, $("dlgPortrait"));
  $("dlgPortrait").className = `portrait kind-${m.kind}`;
  $("dlgSpeaker").innerHTML = headerHtml;
  $("dialog").classList.remove("waiting");
}

function waitAdvance(chars) {
  if (state.auto || state.rec) return sleep((900 + chars * 30) / SPEED);
  $("dialog").classList.add("waiting");
  return new Promise((resolve) => { state.advance = () => { $("dialog").classList.remove("waiting"); resolve(); }; });
}

function advance() {
  if ($("sheet").classList.contains("show")) return;
  if (state.typing && !state.skipTyping) { state.skipTyping = true; return; }   // completa la página de golpe
  if (state.advance) { const a = state.advance; state.advance = null; Sound.play("page"); a(); }
}

async function typePage(md, gen, sources) {
  const line = $("dlgLine");
  state.skipTyping = false;
  for (let i = 1; i <= md.length; i += 2) {
    if (gen !== state.generation) return false;
    if (state.skipTyping) break;
    line.innerHTML = render(md.slice(0, i), sources).replace(/<\/(p|li)>(<\/ul>)?$/, '<span class="caret">▍</span></$1>$2');
    if (i % 6 === 1) Sound.play("tick");
    await sleep(CHAR_MS * 2);
  }
  line.innerHTML = render(md, sources);
  return true;
}

// «Ver todo»: enseña la exposición entera de quien habla, sin ir página a página.
function expandCurrent() {
  if (!state.narratingVoice || $("sheet").classList.contains("show")) return;
  state.expandVoice = true; state.skipTyping = true;
  if (state.advance) { const a = state.advance; state.advance = null; a(); }
}

async function narrateVoice(v, gen) {
  state.typing = true; state.narratingVoice = true; state.expandVoice = false; drawSeats(); drawStatus(); drawBeam(v);
  const m = member(v.member);
  const to = v.to ? ` <span class="to type-${esc(v.type || "responde")}">${esc(L(replyVerb(v) + " " + v.to))}</span>` : "";
  setDialog(m, `<span class="who">${esc(L(m.name))}</span>${to}`);
  Sound.play(v.to ? "reply" : "turn");
  const pages = paginate(v.text);
  $("dialog").classList.toggle("multi", pages.length > 1);
  let counted = false;
  const finish = () => { if (!counted) { counted = true; state.shown++; } state.typing = false; drawSeats(); drawStatus(); };
  for (let p = 0; p < pages.length && !state.expandVoice; p++) {
    state.typing = true; drawSeats();
    if (!(await typePage(pages[p], gen, v.sources))) { state.narratingVoice = false; return; }
    if (state.expandVoice) break;
    if (p === pages.length - 1) finish();      // en la última página ya ha terminado de hablar
    await waitAdvance(pages[p].length);
    if (gen !== state.generation) { state.narratingVoice = false; return; }
  }
  if (state.expandVoice) {                      // «Ver todo»: el texto completo y espera para seguir
    state.expandVoice = false;
    $("dlgLine").innerHTML = render(v.text, v.sources);
    $("dlgLine").scrollTop = 0;
    $("dialog").classList.add("expanded");
    $("dialog").scrollIntoView({ behavior: "smooth", block: "nearest" });
    finish();
    await waitAdvance(v.text.length);
    $("dialog").classList.remove("expanded");
  }
  $("dialog").classList.remove("multi");
  state.narratingVoice = false;
  state.typing = false;
  drawBeam(null);
}

function verdictRows(s) {
  return [["Acuerdo", s.acuerdo], ["Tensión central", s.tension], ["Recomendación", s.recomendacion]]
    .filter(([, v]) => v).map(([k, v]) => `<div class="row"><div class="label">${esc(L(k))}</div><div>${render(v)}</div></div>`).join("");
}

function optionsHtml(opciones) {   // versión en texto, para el modo Rápido y el Acta
  if (!opciones || !opciones.length) return "";
  return `<div class="options-list"><div class="label">${esc(L(S("options")))}</div><ol>` + opciones.map((o) =>
    `<li><strong>${esc(o.titulo)}</strong>${o.detalle ? ` · ${esc(o.detalle)}` : ""}` +
    `${o.apoyan?.length ? `<br><span class="pro-txt">${esc(S("backs"))}: ${esc(o.apoyan.join(", "))}</span>` : ""}` +
    `${o.pegas?.length ? `<br><span class="con-txt">${esc(S("objects"))}: ${esc(o.pegas.join(", "))}</span>` : ""}</li>`).join("") + "</ol></div>";
}

async function showBoard(opciones, gen) {
  const board = $("board");
  board.innerHTML = "";
  board.style.gridTemplateColumns = `repeat(${Math.min(3, opciones.length)}, 1fr)`;   // como mucho 3, del ancho de la mesa
  $("decree").classList.remove("show");
  board.classList.add("show");
  setDialog({ name: S("host"), kind: "host" }, `<span class="who">${esc(L(S("options")))}</span>`);
  $("dlgLine").innerHTML = render(S("optionsLine"));
  for (const o of opciones) {
    if (gen !== state.generation) return;
    const card = document.createElement("div");
    card.className = "option";
    card.innerHTML = `<div class="opt-title">${esc(o.titulo)}</div>${o.detalle ? `<div class="opt-detail">${esc(o.detalle)}</div>` : ""}<div class="opt-people"></div>`;
    const people = card.querySelector(".opt-people");
    (o.apoyan || []).forEach((n) => people.appendChild(mini(n, "pro")));
    (o.pegas || []).forEach((n) => people.appendChild(mini(n, "con")));
    board.appendChild(card);
    requestAnimationFrame(() => card.classList.add("in"));
    Sound.play("option");
    await sleep(500 / SPEED);
  }
  await waitAdvance(80 + opciones.length * 60);
}

async function narrateStatic(item, gen) {
  const host = { name: S("host"), kind: "host" };
  if (item.type === "divider") {
    $("decree").classList.remove("show"); $("board").classList.remove("show");
    setDialog(host, `<span class="who">${esc(L(S("host")))}</span>`);
    state.shown++; drawSeats(); drawStatus();
    await typePage(S("repliesLine"), gen);
    await waitAdvance(60);
  } else {
    const title = item.round === 2 ? S("verdict2") : S("verdict");
    $("board").classList.remove("show");
    $("decree").innerHTML = `<h3>${esc(L(title))}</h3>${render(item.s.recomendacion || item.s.acuerdo || "")}`;
    $("decree").classList.add("show");
    setDialog(host, `<span class="who">${esc(L(title))}</span>`);
    $("dlgLine").innerHTML = `<div class="verdict">${verdictRows(item.s)}</div>`;
    Sound.play("decree");
    state.shown++; drawSeats(); drawStatus();
    await waitAdvance(160);
    if (item.s.opciones && item.s.opciones.length) await showBoard(item.s.opciones, gen);
  }
}

async function pump(gen) {
  if (state.pumping) return;
  state.pumping = true;
  try {
    if (!state.opened) await opening(gen);
    if (gen === state.generation && !state.entered) await entrance(gen);
    while (gen === state.generation && state.shown < timeline().length) {
      const item = timeline()[state.shown];
      if (item.type === "voice") await narrateVoice(item.v, gen);
      else await narrateStatic(item, gen);
    }
    if (gen === state.generation && state.data.status === "cerrado" && phase().caughtUp) drawRelations();
  } finally { state.pumping = false; }
  if (gen !== state.generation) pump(state.generation);
}

function resetScene() {
  state.generation++; state.shown = 0; state.typing = false; state.entered = false; state.opened = false;
  if (state.advance) { const a = state.advance; state.advance = null; a(); }
  ["dlgLine", "dlgSpeaker", "dlgPortrait", "board", "legend"].forEach((id) => { $(id).innerHTML = ""; });
  $("decree").classList.remove("show", "opening"); $("board").classList.remove("show"); $("toast").classList.remove("show");
  $("dialog").classList.remove("waiting"); $("beam").innerHTML = "";
}

// ---------- ficha de un miembro ----------
function openSheet(name) {
  const m = member(name), d = state.data;
  const said = d.voices.filter((v) => v.member === name);
  const cited = [];
  said.forEach((v) => (v.sources || []).forEach((s) => { if (!cited.some((c) => c.url === s.url)) cited.push(s); }));
  const card = $("sheetCard");
  card.innerHTML = "";
  const p = document.createElement("div"); p.className = "portrait sheet-portrait"; portrait(m, p);
  card.appendChild(p);
  card.insertAdjacentHTML("beforeend", `<div class="sheet-body">
    <div class="sheet-name">${esc(m.name)}</div>
    <div class="sheet-kind">${esc(kindLabel(m))}</div>
    ${m.description ? `<p class="sheet-desc">${esc(m.description)}</p>` : ""}
    ${m.kind === "inferida" ? `<p class="sheet-desc">Sin corpus en el vault: habla desde lo que el modelo sabe de esta persona.</p>` : ""}
    ${said.length ? `<div class="sheet-h">En este consejo</div><div class="sheet-said">${said.map((v) => `<details><summary>${v.to ? `<em>${esc(replyVerb(v))} ${esc(v.to)}:</em> ` : ""}${esc(v.headline || firstSentence(v.text))}</summary><div class="sheet-text">${render(v.text, v.sources)}</div></details>`).join("")}</div>` : ""}
    ${cited.length ? `<div class="sheet-h">Piezas citadas</div><ul>${cited.map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> <span class="date">${esc(s.date || "")}</span></li>`).join("")}</ul>` : ""}
  </div><button class="sheet-close" title="Cerrar (Esc)">✕</button>`);
  card.querySelector(".sheet-close").onclick = closeSheet;
  $("sheet").classList.add("show");
}
function closeSheet() { $("sheet").classList.remove("show"); }

// ---------- modo rápido y acta (siempre con todo lo que hay) ----------
function itemKey(item, i) { return item.type === "voice" ? `v${state.data.voices.indexOf(item.v)}` : `${item.type}${item.round || ""}${i}`; }

function buildQuick() {
  const box = $("quick"); box.innerHTML = "";
  timeline().forEach((item, i) => {
    const key = itemKey(item, i);
    if (item.type === "divider") { box.insertAdjacentHTML("beforeend", `<div class="quick-divider">${esc(L(S("replies")))}</div>`); return; }
    const card = document.createElement("details");
    card.dataset.key = key;
    card.open = state.openCards.has(key);
    card.ontoggle = () => card.open ? state.openCards.add(key) : state.openCards.delete(key);
    const sum = document.createElement("summary");
    const p = document.createElement("div"); p.className = "portrait";
    if (item.type === "voice") {
      const v = item.v, m = member(v.member);
      card.className = `card kind-${m.kind}` + (v.round === 2 ? ` reply type-${v.type || "responde"}` : "");
      portrait(m, p); p.onclick = (e) => { e.preventDefault(); openSheet(m.name); }; sum.appendChild(p);
      sum.insertAdjacentHTML("beforeend", `<div class="who"><span class="name">${esc(m.name)}${v.to ? ` <span class="to type-${esc(v.type || "responde")}">${esc(replyVerb(v))} ${esc(v.to)}</span>` : ""}</span>
        <span class="headline">${esc(v.headline || firstSentence(v.text))}</span></div><span class="chev">›</span>`);
      card.appendChild(sum);
      card.insertAdjacentHTML("beforeend", `<div class="text">${render(v.text, v.sources)}${sourcesHtml(v.sources)}</div>`);
    } else {
      card.className = "card synth";
      portrait({ name: S("host"), kind: "host" }, p); sum.appendChild(p);
      const title = item.round === 2 ? S("verdict2") : S("verdict");
      sum.insertAdjacentHTML("beforeend", `<div class="who"><span class="name">${esc(L(title))}</span>
        <span class="headline">${esc(firstSentence(item.s.recomendacion || item.s.acuerdo || ""))}</span></div><span class="chev">›</span>`);
      card.appendChild(sum);
      card.insertAdjacentHTML("beforeend", `<div class="text verdict">${verdictRows(item.s)}${optionsHtml(item.s.opciones)}</div>`);
    }
    box.appendChild(card);
  });
}

function buildLog() {
  const box = $("log"); box.innerHTML = "";
  timeline().forEach((item) => {
    const e = document.createElement("article");
    if (item.type === "divider") { e.className = "entry divider"; e.textContent = L(S("replies")); }
    else if (item.type === "synth") {
      e.className = "entry synth";
      e.innerHTML = `<div><h4>${esc(L(item.round === 2 ? S("verdict2") : S("verdict")))}</h4><div class="verdict">${verdictRows(item.s)}</div>${optionsHtml(item.s.opciones)}</div>`;
    } else {
      const v = item.v, m = member(v.member);
      e.className = `entry kind-${m.kind}` + (v.round === 2 ? ` reply type-${v.type || "responde"}` : "");
      const p = document.createElement("div"); p.className = "portrait"; portrait(m, p); p.onclick = () => openSheet(m.name); e.appendChild(p);
      e.insertAdjacentHTML("beforeend", `<div><h4>${esc(m.name)}${v.to ? ` <span class="to type-${esc(v.type || "responde")}">${esc(replyVerb(v))} ${esc(v.to)}</span>` : ""}</h4>${render(v.text, v.sources)}${sourcesHtml(v.sources)}</div>`);
    }
    box.appendChild(e);
  });
}

// ---------- modos, auto, sonido y grabación ----------
function setMode(mode) {
  state.mode = mode; localStorage.setItem("sala.mode", mode);
  document.body.classList.remove("mode-scene", "mode-quick", "mode-log");
  document.body.classList.add("mode-" + mode);
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
}

function setAuto(on) {
  state.auto = on; localStorage.setItem("sala.auto", on ? "1" : "0");
  document.body.classList.toggle("auto", on);
  $("autoBtn").classList.toggle("active", on);
  if (on && state.advance) advance();
}

function setSound(on) {
  state.sound = on; localStorage.setItem("sala.sound", on ? "1" : "0");
  $("soundBtn").classList.toggle("active", on);
  if (on) Sound.unlock();
}

function setRec(on) {
  state.rec = on;
  document.body.classList.toggle("rec", on);
  if (on) { setMode("scene"); state.autoBeforeRec = state.auto; setAuto(true); }
  else setAuto(state.autoBeforeRec);
}

// ---------- temas ----------
async function loadTheme(name) {
  let cfg = {};
  try { const r = await fetch(`/themes/${name}/theme.json`, { cache: "no-store" }); if (r.ok) cfg = await r.json(); else throw 0; }
  catch { if (name !== "arturo") return loadTheme("arturo"); }
  state.theme = name; state.themeCfg = cfg;
  localStorage.setItem("sala.theme", name);
  $("themeCss").href = `/themes/${name}/theme.css`;
  document.querySelectorAll("link[data-theme-font]").forEach((l) => l.remove());
  for (const href of cfg.fonts || []) {
    const l = document.createElement("link"); l.rel = "stylesheet"; l.href = href; l.dataset.themeFont = "1";
    document.head.appendChild(l);
  }
  document.body.className = document.body.className.replace(/\btheme-\S+/g, "").trim() + " theme-" + name;
  // Escena ilustrada: la imagen de fondo trae la sala y la mesa; los asientos se colocan alrededor de esa mesa.
  const sc = cfg.scene, stage = $("stage");
  state.geo = Object.assign({ cx: 50, cy: 50, rx: 37, ry: 40 }, sc && sc.seats);
  stage.classList.toggle("has-scene", !!(sc && sc.image));
  stage.style.backgroundImage = sc && sc.image ? `url(/themes/${name}/${sc.image})` : "";
  stage.style.setProperty("--cx", state.geo.cx + "%");
  stage.style.setProperty("--cy", state.geo.cy + "%");
  $("brandTitle").textContent = L(S("brand"));
  document.querySelector(".dialog .hint").textContent = S("hint");
  $("empty").textContent = S("empty");
  $("themeSel").value = name;
  if (state.data) { buildSeats(); drawSeats(); drawStatus(); buildQuick(); buildLog(); }
}

async function loadThemeList() {
  try {
    const [themes, cfg] = await Promise.all([
      fetch("/api/themes", { cache: "no-store" }).then((r) => r.json()),
      fetch("/api/config", { cache: "no-store" }).then((r) => r.json()),
    ]);
    $("themeSel").innerHTML = themes.map((t) => `<option value="${esc(t.name)}">${esc(t.label)}</option>`).join("");
    const wanted = params.get("theme") || localStorage.getItem("sala.theme") || cfg.default_theme || "arturo";
    await loadTheme(themes.some((t) => t.name === wanted) ? wanted : (cfg.default_theme || "arturo"));
  } catch { await loadTheme("arturo"); }
}

// ---------- datos ----------
async function load(first) {
  let res;
  try { res = await fetch(`/api/session/${state.sessionId}`, { cache: "no-store" }); } catch { return; }
  if (!res.ok) { $("empty").hidden = false; return; }
  $("empty").hidden = true;
  const next = await res.json();
  const changed = !state.data || next.id !== state.data.id;
  const grew = !state.data || JSON.stringify(next) !== JSON.stringify(state.data);
  state.data = next;
  $("question").textContent = next.question;
  document.title = `${S("brand")} · ${next.question}`;
  if (changed || first) { resetScene(); buildSeats(); state.openCards.clear(); }
  if (grew) { buildQuick(); buildLog(); }
  drawSeats(); drawStatus();
  pump(state.generation);
}

async function loadSessions() {
  try {
    const list = await (await fetch("/api/sessions", { cache: "no-store" })).json();
    $("sessionSel").innerHTML = `<option value="latest">Última sesión</option>` +
      list.map((s) => `<option value="${esc(s.id)}">${esc(s.question.slice(0, 40))}${s.status === "deliberando" ? " · en directo" : ""}</option>`).join("");
    $("sessionSel").value = state.sessionId;
  } catch {}
}

// ---------- arranque ----------
document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
$("autoBtn").onclick = () => setAuto(!state.auto);
$("soundBtn").onclick = () => setSound(!state.sound);
$("replayBtn").onclick = () => { resetScene(); buildSeats(); setMode("scene"); drawSeats(); drawStatus(); pump(state.generation); };
$("recBtn").onclick = () => setRec(true);
$("openAll").onclick = () => document.querySelectorAll("#quick details").forEach((d) => (d.open = true));
$("closeAll").onclick = () => document.querySelectorAll("#quick details").forEach((d) => (d.open = false));
$("themeSel").onchange = (e) => loadTheme(e.target.value);
$("sessionSel").onchange = (e) => { state.sessionId = e.target.value; state.data = null; load(true); };
$("dialog").onclick = (e) => { if (e.target.closest(".fullbtn")) return; advance(); };
$("fullBtn").onclick = (e) => { e.stopPropagation(); expandCurrent(); };
$("sheet").onclick = (e) => { if (e.target === $("sheet")) closeSheet(); };
document.addEventListener("pointerdown", () => { if (state.sound) Sound.unlock(); });
document.addEventListener("keydown", (e) => {
  if (state.sound) Sound.unlock();
  if (e.target.tagName === "SELECT") return;
  if (e.key === "Escape") { if ($("sheet").classList.contains("show")) closeSheet(); else if (state.rec) setRec(false); return; }
  if (e.key === " " || e.key === "Enter") { e.preventDefault(); advance(); }
  else if (e.key === "1") setMode("scene"); else if (e.key === "2") setMode("quick"); else if (e.key === "3") setMode("log");
  else if (e.key.toLowerCase() === "a") setAuto(!state.auto);
  else if (e.key.toLowerCase() === "v") expandCurrent();
  else if (e.key.toLowerCase() === "m") setSound(!state.sound);
});

(async () => {
  setMode(params.get("mode") || state.mode);
  setAuto(state.auto);
  setSound(state.sound);
  await loadThemeList();
  if (params.get("rec") === "1") setRec(true);
  loadSessions();
  await load(true);
  setInterval(() => load(false), 1200);
  setInterval(loadSessions, 10000);
})();
