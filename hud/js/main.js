import { startBackground } from "./background.js";
import { call, connect } from "./link.js";
import { countdown, el, startClock, Telemetry, Timers, toast, updateWeather } from "./panels.js";
import { Reactor } from "./reactor.js";
import { sfx } from "./sfx.js";

const $ = id => document.getElementById(id);
const hud = $("hud");
const reactor = new Reactor($("reactor"));
const telemetry = new Telemetry();
const timers = new Timers();

const STATE_LABEL = {
  booting: "INITIALIZING", idle: "ONLINE", listening: "LISTENING", thinking: "PROCESSING",
  speaking: "RESPONDING", error: "FAULT", standby: "STANDBY",
};

const ctx = { name: "SIMON", metric: true, state: "booting", booted: false, entries: 0, lastStatus: {} };

startBackground($("bg"));
startClock();

function setState(state) {
  ctx.state = state;
  hud.dataset.state = state;
  reactor.setState(state);
  $("state-text").textContent = STATE_LABEL[state] ?? state.toUpperCase();
  $("caption-state").textContent = STATE_LABEL[state] ?? state.toUpperCase();
  $("ro-mic").textContent = micLabel();
  if (state === "listening") $("caption-text").replaceChildren(el("span", "cursor"));
  else if (state === "thinking") typewrite("Analyzing…", 18);
}

function micLabel() {
  if (ctx.state === "listening") return "CAPTURING";
  const mic = ctx.lastStatus.mic;
  return mic === "online" ? "ARMED" : (mic ?? "—").toUpperCase();
}

let typing = null;
function typewrite(text, speed = 22) {
  clearInterval(typing);
  const box = $("caption-text");
  let i = 0;
  box.textContent = "";
  const cursor = el("span", "cursor");
  const span = el("span");
  box.append(span, cursor);
  typing = setInterval(() => {
    i += Math.max(1, Math.round(text.length / 120));
    span.textContent = text.slice(0, i);
    if (i >= text.length) {
      clearInterval(typing);
      setTimeout(() => cursor.remove(), 1200);
    }
  }, speed);
}

function addEntry({ role, text, source, latency, actions = [], ts }) {
  const log = $("log");
  log.querySelector(".log-empty")?.remove();
  const entry = el("div", `entry ${role}`);
  const meta = el("div", "entry-meta");
  const time = new Date((ts ?? Date.now() / 1000) * 1000).toLocaleTimeString([], { hour12: false });
  meta.append(el("span", "", time), el("span", "entry-who", role === "user" ? "YOU" : ctx.name));
  if (source) meta.append(el("span", "entry-tag", `${source.replace("skill:", "").toUpperCase()}${latency != null ? ` · ${latency}MS` : ""}`));
  entry.append(meta, el("div", "entry-text", text));
  if (actions.length) {
    const row = el("div", "entry-actions");
    actions.forEach(a => row.append(el("span", "", a.action.replace(/_/g, " "))));
    entry.append(row);
  }
  log.append(entry);
  while (log.children.length > 80) log.firstElementChild.remove();
  log.scrollTop = log.scrollHeight;
  ctx.entries += 1;
  $("log-count").textContent = `${ctx.entries} ENTRIES`;
}

function setDot(id, label, status) {
  const good = ["online", "armed", "synced"].includes(status);
  const warn = ["paused", "disabled", "connecting"].includes(status);
  $(`dot-${id}`).className = `dot ${good ? "ok" : warn ? "warn" : "bad"}`;
  $(`tk-${id}`).textContent = label;
}

function applyConfig(c) {
  ctx.name = (c.name || "Simon").toUpperCase();
  document.title = c.codename || "S.I.M.O.N.";
  $("brand-name").textContent = c.codename || ctx.name;
  $("brand-sub").textContent = c.expansion || "";
  $("ro-model").textContent = c.model || "—";
  $("ro-voice").textContent = (c.voice || "—").replace(/Neural$/, "").replace(/^[a-z]{2}-[A-Z]{2}-/, "");
  $("console-input").placeholder = `Type a command, or say “Hey ${c.name || "Simon"}”…`;
  sfx.enabled = c.sound_effects !== false;
  reactor.showAvatar = c.avatar !== false;
  if (c.accent && /^#[0-9a-f]{6}$/i.test(c.accent)) {
    const n = parseInt(c.accent.slice(1), 16);
    document.documentElement.style.setProperty("--accent", c.accent);
    document.documentElement.style.setProperty("--accent-rgb", `${n >> 16}, ${(n >> 8) & 255}, ${n & 255}`);
  }
}

const handlers = {
  config: applyConfig,
  state: e => {
    if (!ctx.booted) { ctx.pendingState = e.state; return; }
    setState(e.state);
    if (e.state === "speaking" && e.text) typewrite(e.text);
  },
  level: e => reactor.setLevel(e.value),
  transcript: e => {
    addEntry(e);
    if (e.role === "user") {
      const heard = $("heard");
      heard.textContent = `“${e.text}”`;
      heard.classList.add("show");
      sfx.play("send");
    } else {
      $("heard").classList.remove("show");
      if (e.latency != null) $("ro-latency").textContent = `${e.latency} MS`;
      sfx.play("reply");
    }
  },
  status: e => {
    Object.assign(ctx.lastStatus, e);
    if (e.llm) setDot("llm", e.llm === "online" ? e.model : e.llm, e.llm);
    if (e.mic) {
      setDot("mic", e.mic, e.mic);
      $("ro-mic").textContent = micLabel();
    }
  },
  telemetry: e => telemetry.update(e),
  weather: e => updateWeather(e, ctx.metric),
  timers: e => timers.set(e.timers),
  notify: e => {
    toast(e.title, e.text, e.level);
    if (e.level === "alert") sfx.play("alert");
  },
  countdown: e => countdown(e.mode, e.seconds),
  diagnostics: () => {
    const scan = $("scan");
    scan.classList.remove("run");
    void scan.offsetWidth;
    scan.classList.add("run");
  },
  visibility: e => {
    hud.classList.toggle("standby", !e.visible);
    reactor.setState(e.visible ? ctx.state : "standby");
    if (!e.visible) sfx.play("down");
  },
  sfx: e => sfx.play(e.name),
  action: e => {
    if (!e.ok) toast("ACTION FAILED", e.name.replace(/_/g, " ").toUpperCase(), "warn", 3500);
  },
};

connect(
  e => handlers[e.type]?.(e),
  online => setDot("link", online ? "synced" : "lost", online ? "synced" : "lost"),
);

async function boot() {
  const lines = [
    ["SIMON CORE BIOS v2", "hi"],
    ["Initializing neural core", "OK"],
    ["Loading language model", () => (ctx.lastStatus.llm === "online" ? "OK" : ctx.lastStatus.llm ? "LOCAL" : "OK")],
    ["Calibrating audio array", () => (ctx.lastStatus.mic === "offline" ? "TEXT ONLY" : "OK")],
    ["Establishing voice synthesis link", "OK"],
    ["Mounting telemetry subsystems", "OK"],
    ["Syncing environmental data", "OK"],
    ["Arming security protocols", "ARMED"],
  ];
  const log = $("boot-log");
  const bar = $("boot-progress");
  sfx.play("boot");
  for (let i = 0; i < lines.length; i++) {
    const [label, result] = lines[i];
    if (result === "hi") {
      log.append(el("span", "hi", `${label}\n`));
    } else {
      log.append(`> ${label.padEnd(36, ".")} `);
      await wait(150 + Math.random() * 180);
      const value = typeof result === "function" ? result() : result;
      log.append(el("span", value === "OK" || value === "ARMED" ? "ok" : "warn", `${value}\n`));
    }
    bar.style.width = `${((i + 1) / lines.length) * 100}%`;
    await wait(90);
  }
  log.append(el("span", "hi", "\nALL SYSTEMS NOMINAL"));
  await wait(450);
  $("boot").classList.add("done");
  hud.classList.remove("booting");
  reactor.ignite();
  ctx.booted = true;
  setState(ctx.pendingState && ctx.pendingState !== "booting" ? ctx.pendingState : "idle");
}

const wait = ms => new Promise(r => setTimeout(r, ms));

$("console").addEventListener("submit", ev => {
  ev.preventDefault();
  const input = $("console-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  call("command", { text });
});

$("console-input").addEventListener("keydown", ev => {
  if (ev.key.length === 1) sfx.play("key");
  if (ev.key === "Escape") ev.target.blur();
});

$("mic-btn").addEventListener("click", () => call("activate"));
document.querySelector(".core").addEventListener("click", () => call("activate"));
document.querySelectorAll("[data-api]").forEach(b => b.addEventListener("click", () => call(b.dataset.api)));

document.addEventListener("keydown", ev => {
  sfx.unlock();
  if (document.activeElement === $("console-input")) return;
  if (ev.code === "Space" && !ev.ctrlKey) { ev.preventDefault(); call("activate"); }
  else if (ev.key === "/") { ev.preventDefault(); $("console-input").focus(); }
  else if (ev.key === "Escape") call("hide");
  else if (ev.key === "F11") { ev.preventDefault(); call("fullscreen"); }
});
document.addEventListener("pointerdown", () => sfx.unlock(), { once: true });

setDot("llm", "connecting", "connecting");
setDot("mic", "connecting", "connecting");
boot();
