// CzGram connector. Reads the active tab only when the CzGram app asks for it
// (PrintScreen pressed); it sends nothing anywhere except the local app.
const api = globalThis.browser || globalThis.chrome;
const HOST = "cz.czgram.bridge";
const MAX_FRAMES = 20;
const MAX_TOTAL = 1000000;
let port = null;

// Runs inside the page. Emits simplified HTML of what's in view, using live form
// state (value attributes in the source are often stale or absent).
function pageSnapshot(full, armed, key) {
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "SVG", "CANVAS", "IFRAME", "OBJECT", "EMBED", "VIDEO", "AUDIO"]);
  const LIMIT = 400000;
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const attr = (s) => esc(s).replace(/"/g, "&quot;");
  const vh = window.innerHeight, vw = window.innerWidth;
  // Exercises are plain text boxes. Never copy what could be a secret: passwords, card
  // details, one-time codes, hidden values, or anything the page marks as such.
  const TEXT_TYPES = new Set(["text", "search", ""]);
  const SECRET = /passw|passcode|cc-|card.?(num|no\b|code|cvc)|cvc|cvv|csc|iban|one-time|(^|[^a-z])(otp|pin|ssn)([^a-z]|$)|secret|token/i;
  const secretField = (el) => !TEXT_TYPES.has((el.type || "").toLowerCase())
    || SECRET.test([el.autocomplete, el.name, el.id].join(" "));
  let out = "";

  // Bulk mode: a double tap of the chosen key (Alt unless set otherwise in CzGram) accepts the
  // offer, and each answer the user gives moves CzGram on to the next one. Listeners only count;
  // they never read or change the page.
  const state = globalThis.__czgram || (globalThis.__czgram = (() => {
    const st = { alt: 0, answers: 0, lastAltUp: 0, altClean: false, lastAnswer: 0, armedAt: 0, key: "Alt" };
    addEventListener("keydown", (e) => {
      if (e.key === st.key) { if (!e.repeat) st.altClean = true; } else { st.altClean = false; st.lastAltUp = 0; }
    }, true);
    addEventListener("keyup", (e) => {
      if (e.key !== st.key || !st.altClean) return;
      const now = Date.now();
      // While CzGram is offering bulk mode, Alt mustn't open the browser's menu bar, or the
      // second tap would go to the menu instead of the page.
      if (now - st.armedAt < 3000) e.preventDefault();
      if (now - st.lastAltUp < 450) { st.alt++; st.lastAltUp = 0; } else { st.lastAltUp = now; }
    }, true);
    const answered = () => {
      const now = Date.now();
      if (now - st.lastAnswer > 300) st.answers++;  // a click on a radio also fires change
      st.lastAnswer = now;
    };
    const CHOICE = 'button,select,label,input[type=radio],input[type=checkbox],input[type=button],input[type=submit],' +
      '[role=radio],[role=checkbox],[role=option],[role=button],[data-data=option]';
    addEventListener("click", (e) => {
      const el = e.target && e.target.closest && e.target.closest(CHOICE);
      if (el && e.isTrusted) answered();
    }, true);
    addEventListener("change", (e) => {
      const el = e.target;
      // Typing into a gap counts once it's done (Enter or leaving the box), not on the first click.
      if (e.isTrusted && el && (el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && TEXT_TYPES.has((el.type || "").toLowerCase())))) answered();
    }, true);
    return st;
  })());
  if (armed) state.armedAt = Date.now();
  state.key = ["Alt", "Control", "Shift"].includes(key) ? key : "Alt";

  // Whatever is highlighted here, with its sentence, for the app's manual mode.
  function selectedText() {
    const active = document.activeElement;
    let text = "", context = "";
    if (active && typeof active.selectionStart === "number" && active.selectionEnd > active.selectionStart) {
      if (active.tagName === "INPUT" && secretField(active)) return "";
      text = active.value.slice(active.selectionStart, active.selectionEnd);
      context = active.value;
    } else {
      const sel = window.getSelection();
      text = sel ? sel.toString() : "";
      const from = sel && sel.anchorNode && sel.anchorNode.parentElement;
      const block = from && from.closest("p,li,td,div,section,article,blockquote,h1,h2,h3,h4");
      context = block ? block.textContent : "";
    }
    text = text.trim();
    if (!text) return "";
    context = context.replace(/\s+/g, " ").trim().slice(0, 400);
    return `<czgram-selection data-context="${attr(context)}">${esc(text.slice(0, 500))}</czgram-selection>`;
  }

  function walk(node) {
    if (out.length > LIMIT) return;
    if (node.nodeType === Node.TEXT_NODE) { out += esc(node.nodeValue); return; }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName.toUpperCase();
    if (SKIP.has(tag)) return;
    const style = getComputedStyle(node);
    if (style.display === "none" || style.visibility === "hidden") return;
    const r = node.getBoundingClientRect();
    const sized = r.width > 0 && r.height > 0;
    if (!full && sized && (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw)) return;
    const name = tag.toLowerCase();
    if (tag === "INPUT") {
      if (secretField(node)) return;
      out += `<input type="${attr(node.type || "text")}" value="${attr(node.value || "")}">`;
      return;
    }
    if (tag === "TEXTAREA") {
      if (!SECRET.test([node.autocomplete, node.name, node.id].join(" "))) out += `<textarea>${esc(node.value || "")}</textarea>`;
      return;
    }
    if (tag === "SELECT") {
      out += "<select>";
      for (const o of node.options) out += `<option>${esc(o.text)}</option>`;
      out += "</select>";
      return;
    }
    if (node.isContentEditable && !node.textContent.trim()) {
      if (!node.parentElement || !node.parentElement.isContentEditable) {
        out += '<input type="text" value="">';
      }
      return;
    }
    // Exercise parts on the Umíme sites; the app needs to tell them apart.
    const role = node.id === "next" ? "next" : node.id === "question-wrapper" ? "wrapper"
      : node.getAttribute("data-data");
    const mark = ["question", "option", "next", "wrapper"].includes(role) ? ` data-data="${role}"` : "";
    out += `<${name}${mark}>`;
    for (const child of (node.shadowRoot || node).childNodes) walk(child);
    out += `</${name}>`;
  }
  if (document.body) walk(document.body);
  return `<czgram-state data-alt="${state.alt}" data-answers="${state.answers}"></czgram-state>` + selectedText() + out;
}

async function takeSnapshot(full, armed, key) {
  const win = await api.windows.getLastFocused();
  const [tab] = await api.tabs.query({ active: true, windowId: win.id });
  if (!tab) return { error: "no active tab" };
  let frames;
  try {
    if (api.scripting) {
      const res = await api.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: pageSnapshot,
        args: [!!full, !!armed, String(key || "Alt")],
      });
      frames = res.map((r) => r.result);
    } else {
      // Firefox manifest v2
      frames = await api.tabs.executeScript(tab.id, {
        allFrames: true,
        code: `(${pageSnapshot.toString()})(${full ? "true" : "false"}, ${armed ? "true" : "false"}, ${JSON.stringify(String(key || "Alt"))})`,
      });
    }
  } catch (e) {
    return { error: "this page can't be read (" + e.message + ")" };
  }
  // A page with many frames mustn't flood the app: keep the first ones, up to 1 MB in all.
  const kept = [];
  let total = 0;
  for (const f of frames || []) {
    if (typeof f !== "string" || !f.length || kept.length >= MAX_FRAMES) continue;
    if (total + f.length > MAX_TOTAL) break;
    kept.push(f);
    total += f.length;
  }
  return {
    focused: !!win.focused,
    url: tab.url || "",
    title: (tab.title || "").slice(0, 300),
    frames: kept,
  };
}

function connect() {
  if (port) return;
  port = api.runtime.connectNative(HOST);
  port.onMessage.addListener(async (msg) => {
    if (msg.cmd !== "snapshot") return;
    let reply;
    try {
      reply = await takeSnapshot(msg.full, msg.armed, msg.key);
    } catch (e) {
      reply = { error: String(e.message || e) };
    }
    reply.id = msg.id;
    if (port) port.postMessage(reply);
  });
  port.onDisconnect.addListener(() => {
    port = null;
    // The app may be mid-update; a retry costs nothing.
    setTimeout(connect, 15000);
  });
}

api.runtime.onStartup.addListener(connect);
api.runtime.onInstalled.addListener(connect);
connect();
