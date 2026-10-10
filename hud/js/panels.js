const $ = id => document.getElementById(id);

export function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

const pad = n => String(n).padStart(2, "0");

export function formatBytes(bps) {
  const units = ["B/s", "KB/s", "MB/s", "GB/s"];
  let i = 0;
  while (bps >= 1024 && i < units.length - 1) { bps /= 1024; i++; }
  return `${bps < 10 && i ? bps.toFixed(1) : Math.round(bps)} ${units[i]}`;
}

export function formatUptime(s) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}D ${pad(h)}H` : `${pad(h)}:${pad(m)}`;
}

export function startClock() {
  const tick = () => {
    const now = new Date();
    $("clock-time").innerHTML = `${pad(now.getHours())}:${pad(now.getMinutes())}<small>:${pad(now.getSeconds())}</small>`;
    $("clock-date").textContent = now.toLocaleDateString(undefined, { weekday: "long", day: "2-digit", month: "short", year: "numeric" });
  };
  tick();
  setInterval(tick, 1000);
}

function buildSegments(id) {
  const bar = $(id);
  for (let i = 0; i < 24; i++) bar.appendChild(el("span"));
  return [...bar.children];
}

export class Telemetry {
  constructor() {
    this.ram = buildSegments("ram-bar");
    this.disk = buildSegments("disk-bar");
    this.cores = [];
    this.history = Array.from({ length: 60 }, () => ({ up: 0, down: 0 }));
    this.graph = $("net-graph");
  }

  fillSegments(segs, pct) {
    const lit = Math.round((pct / 100) * segs.length);
    segs.forEach((s, i) => {
      s.className = i < lit ? (pct > 90 ? "crit" : pct > 75 ? "hot" : "on") : "";
    });
  }

  update(t) {
    $("cpu-value").textContent = Math.round(t.cpu);
    const gauge = $("cpu-gauge");
    gauge.style.strokeDashoffset = 314.16 * (1 - t.cpu / 100);
    gauge.style.stroke = t.cpu > 85 ? "var(--red)" : t.cpu > 65 ? "var(--amber)" : "var(--accent)";

    const cores = $("cores");
    if (this.cores.length !== t.per_core.length) {
      cores.replaceChildren(...t.per_core.map(() => el("span")));
      this.cores = [...cores.children];
    }
    t.per_core.forEach((v, i) => (this.cores[i].style.height = `${Math.max(4, v)}%`));

    $("ram-value").textContent = `${Math.round(t.ram)}%`;
    $("ram-detail").textContent = `${t.ram_used_gb.toFixed(1)} / ${Math.round(t.ram_total_gb)} GB`;
    this.fillSegments(this.ram, t.ram);
    $("disk-value").textContent = `${Math.round(t.disk)}%`;
    $("disk-detail").textContent = `${Math.round(t.disk_free_gb)} GB FREE`;
    this.fillSegments(this.disk, t.disk);

    $("net-up").textContent = formatBytes(t.net_up);
    $("net-down").textContent = formatBytes(t.net_down);
    this.history.push({ up: t.net_up, down: t.net_down });
    this.history.shift();
    this.drawGraph();

    $("uptime").textContent = formatUptime(t.uptime);
    $("procs").textContent = t.processes;
    $("battery").textContent = t.battery ? `${t.battery.percent}%${t.battery.plugged ? " ⚡" : ""}` : "AC";
    $("host").textContent = (t.host || "LOCALHOST").toUpperCase();
  }

  drawGraph() {
    const c = this.graph;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = c.clientWidth, h = c.clientHeight;
    if (c.width !== w * dpr) { c.width = w * dpr; c.height = h * dpr; }
    const ctx = c.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(1024 * 16, ...this.history.map(p => Math.max(p.up, p.down))) * 1.15;
    const plot = (key, rgb) => {
      ctx.beginPath();
      this.history.forEach((p, i) => {
        const x = (i / (this.history.length - 1)) * w;
        const y = h - (p[key] / max) * (h - 4) - 1;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      });
      ctx.strokeStyle = `rgba(${rgb},0.95)`;
      ctx.lineWidth = 1.4;
      ctx.stroke();
      ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath();
      const g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, `rgba(${rgb},0.25)`);
      g.addColorStop(1, `rgba(${rgb},0)`);
      ctx.fillStyle = g;
      ctx.fill();
    };
    plot("down", "0,229,255");
    plot("up", "61,255,168");
  }
}

const ICONS = {
  sun: '<circle cx="32" cy="32" r="11"/><g stroke-linecap="round">' +
    [...Array(8)].map((_, i) => { const a = (i * Math.PI) / 4; return `<line x1="${32 + Math.cos(a) * 17}" y1="${32 + Math.sin(a) * 17}" x2="${32 + Math.cos(a) * 24}" y2="${32 + Math.sin(a) * 24}"/>`; }).join("") + "</g>",
  cloud: '<path d="M20 46h26a10 10 0 0 0 0-20 14 14 0 0 0-27-2A11 11 0 0 0 20 46z"/>',
  partly: '<circle cx="24" cy="24" r="8"/><path d="M24 50h22a9 9 0 0 0 0-18 12 12 0 0 0-23-1A9.5 9.5 0 0 0 24 50z"/>',
  rain: '<path d="M20 38h26a10 10 0 0 0 0-20 14 14 0 0 0-27-2A11 11 0 0 0 20 38z"/><g stroke-linecap="round"><line x1="24" y1="44" x2="21" y2="52"/><line x1="33" y1="44" x2="30" y2="52"/><line x1="42" y1="44" x2="39" y2="52"/></g>',
  snow: '<path d="M20 38h26a10 10 0 0 0 0-20 14 14 0 0 0-27-2A11 11 0 0 0 20 38z"/><g><circle cx="23" cy="47" r="1.6"/><circle cx="32" cy="51" r="1.6"/><circle cx="41" cy="47" r="1.6"/></g>',
  storm: '<path d="M20 36h26a10 10 0 0 0 0-20 14 14 0 0 0-27-2A11 11 0 0 0 20 36z"/><path d="M34 38l-6 9h6l-4 9" stroke-linejoin="round"/>',
  fog: '<g stroke-linecap="round"><line x1="12" y1="26" x2="52" y2="26"/><line x1="16" y1="34" x2="48" y2="34"/><line x1="12" y1="42" x2="52" y2="42"/></g>',
};

function iconFor(code) {
  if (code === 113) return "sun";
  if (code === 116) return "partly";
  if ([119, 122].includes(code)) return "cloud";
  if ([143, 248, 260].includes(code)) return "fog";
  if ([200, 386, 389, 392, 395].includes(code)) return "storm";
  if ([179, 182, 185, 227, 230, 323, 326, 329, 332, 335, 338, 350, 368, 371, 374, 377].includes(code)) return "snow";
  return "rain";
}

export function updateWeather(w, metric = true) {
  const u = metric ? "c" : "f";
  $("wx-location").textContent = `${w.location}${w.country ? ", " + w.country : ""}`.toUpperCase();
  $("wx-temp").textContent = w[`temp_${u}`];
  $("wx-desc").textContent = w.description;
  $("wx-high").textContent = `${w[`high_${u}`]}°`;
  $("wx-low").textContent = `${w[`low_${u}`]}°`;
  $("wx-rain").textContent = `${w.rain_chance}%`;
  $("wx-wind").textContent = `${w.wind_kph} ${w.wind_dir}`;
  $("wx-icon").innerHTML = `<svg viewBox="0 0 64 64" fill="none" stroke="var(--accent)" stroke-width="2.4">${ICONS[iconFor(w.code)]}</svg>`;
}

export class Timers {
  constructor() {
    this.list = [];
    setInterval(() => this.render(), 250);
  }

  set(timers) {
    this.list = timers;
    $("timer-count").textContent = timers.length;
    const box = $("timers");
    if (!timers.length) {
      box.replaceChildren(el("div", "log-empty", "NO ACTIVE TIMERS"));
      return;
    }
    box.replaceChildren(...timers.map(t => {
      const row = el("div", "timer");
      row.dataset.id = t.id;
      row.innerHTML = `<svg viewBox="0 0 46 46"><circle class="t-track" cx="23" cy="23" r="20"/><circle class="t-fill" cx="23" cy="23" r="20"/></svg>`;
      const info = el("div");
      info.append(el("div", "timer-label", t.label), el("div", "timer-kind", t.reminder ? "REMINDER" : "COUNTDOWN"));
      row.append(info, el("div", "timer-left", "--:--"));
      return row;
    }));
    this.render();
  }

  render() {
    const now = Date.now() / 1000;
    for (const t of this.list) {
      const row = document.querySelector(`.timer[data-id="${t.id}"]`);
      if (!row) continue;
      const left = Math.max(0, t.ends_at - now);
      const h = Math.floor(left / 3600), m = Math.floor((left % 3600) / 60), s = Math.floor(left % 60);
      row.querySelector(".timer-left").textContent = h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
      row.querySelector(".t-fill").style.strokeDashoffset = 125.66 * (1 - left / t.duration);
      row.classList.toggle("urgent", left < 10);
    }
  }
}

export function toast(title, text, level = "info", ms = 5200) {
  const node = el("div", `toast ${level}`);
  node.append(el("h3", "", title), el("p", "", text));
  $("toasts").prepend(node);
  setTimeout(() => {
    node.classList.add("out");
    setTimeout(() => node.remove(), 400);
  }, ms);
}

let countdownTimer = null;
export function countdown(mode, seconds) {
  const box = $("countdown");
  clearInterval(countdownTimer);
  if (mode === "abort" || seconds <= 0) {
    box.classList.remove("show");
    return;
  }
  $("countdown-label").textContent = mode === "restart" ? "REBOOT SEQUENCE" : "SHUTDOWN SEQUENCE";
  let left = seconds;
  $("countdown-num").textContent = left;
  box.classList.add("show");
  countdownTimer = setInterval(() => {
    left -= 1;
    $("countdown-num").textContent = Math.max(0, left);
    if (left <= 0) clearInterval(countdownTimer);
  }, 1000);
}
