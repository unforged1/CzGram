// CzGram connector. Reads the active tab only when the CzGram app asks for it
// (PrintScreen pressed); it sends nothing anywhere except the local app.
const api = globalThis.browser || globalThis.chrome;
const HOST = "cz.czgram.bridge";
let port = null;

// Runs inside the page. Emits simplified HTML of what's in view, using live form
// state (value attributes in the source are often stale or absent).
function pageSnapshot() {
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "SVG", "CANVAS", "IFRAME", "OBJECT", "EMBED", "VIDEO", "AUDIO"]);
  const LIMIT = 400000;
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const attr = (s) => esc(s).replace(/"/g, "&quot;");
  const vh = window.innerHeight, vw = window.innerWidth;
  let out = "";

  // Whatever is highlighted here, with its sentence, for the app's manual mode.
  function selectedText() {
    const active = document.activeElement;
    let text = "", context = "";
    if (active && typeof active.selectionStart === "number" && active.selectionEnd > active.selectionStart) {
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
    if (sized && (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw)) return;
    const name = tag.toLowerCase();
    if (tag === "INPUT") {
      out += `<input type="${attr(node.type || "text")}" value="${attr(node.value || "")}">`;
      return;
    }
    if (tag === "TEXTAREA") { out += `<textarea>${esc(node.value || "")}</textarea>`; return; }
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
  return selectedText() + out;
}

async function takeSnapshot() {
  const win = await api.windows.getLastFocused();
  const [tab] = await api.tabs.query({ active: true, windowId: win.id });
  if (!tab) return { error: "no active tab" };
  let frames;
  try {
    if (api.scripting) {
      const res = await api.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: pageSnapshot,
      });
      frames = res.map((r) => r.result);
    } else {
      // Firefox manifest v2
      frames = await api.tabs.executeScript(tab.id, {
        allFrames: true,
        code: `(${pageSnapshot.toString()})()`,
      });
    }
  } catch (e) {
    return { error: "this page can't be read (" + e.message + ")" };
  }
  return {
    focused: !!win.focused,
    url: tab.url || "",
    title: tab.title || "",
    frames: (frames || []).filter((f) => typeof f === "string" && f.length),
  };
}

function connect() {
  if (port) return;
  port = api.runtime.connectNative(HOST);
  port.onMessage.addListener(async (msg) => {
    if (msg.cmd !== "snapshot") return;
    let reply;
    try {
      reply = await takeSnapshot();
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
