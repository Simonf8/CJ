let ctx = null;
let enabled = true;

function audio() {
  if (!enabled) return null;
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

function tone(freq, start, duration, { type = "sine", gain = 0.06, to = null } = {}) {
  const a = audio();
  if (!a) return;
  const t = a.currentTime + start;
  const osc = a.createOscillator();
  const amp = a.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, t + duration);
  amp.gain.setValueAtTime(0.0001, t);
  amp.gain.exponentialRampToValueAtTime(gain, t + 0.015);
  amp.gain.exponentialRampToValueAtTime(0.0001, t + duration);
  osc.connect(amp).connect(a.destination);
  osc.start(t);
  osc.stop(t + duration + 0.05);
}

const SOUNDS = {
  boot: () => { tone(110, 0, 1.4, { type: "sawtooth", gain: 0.025, to: 440 }); tone(880, 1.1, 0.5, { gain: 0.04 }); tone(1320, 1.25, 0.6, { gain: 0.03 }); },
  listen: () => { tone(660, 0, 0.12, { gain: 0.05 }); tone(990, 0.09, 0.18, { gain: 0.05 }); },
  cancel: () => { tone(700, 0, 0.12, { gain: 0.04 }); tone(440, 0.09, 0.2, { gain: 0.04 }); },
  send: () => tone(1200, 0, 0.08, { type: "triangle", gain: 0.03, to: 1800 }),
  reply: () => tone(520, 0, 0.25, { type: "triangle", gain: 0.025, to: 780 }),
  alert: () => { [0, 0.18, 0.36].forEach(d => tone(1046, d, 0.12, { type: "square", gain: 0.03 })); },
  key: () => tone(2400 + Math.random() * 400, 0, 0.02, { type: "square", gain: 0.006 }),
  down: () => tone(600, 0, 0.6, { type: "sawtooth", gain: 0.02, to: 80 }),
};

export const sfx = {
  play(name) { SOUNDS[name]?.(); },
  set enabled(v) { enabled = !!v; },
  get enabled() { return enabled; },
  unlock() { audio(); },
};
