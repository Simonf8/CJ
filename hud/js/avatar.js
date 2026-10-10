const TAU = Math.PI * 2;
const ROWS = 56;
const COLS = 100;
const BUCKETS = 10;
const MOUTH_Y = -0.39;
const EYES = [[-0.29, 0.13, 0.7], [0.29, 0.13, 0.7]];

const bump = (x, y, cx, cy, sx, sy) => Math.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2));
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));

function relief(x, y) {
  const ax = Math.abs(x);
  return 0.24 * bump(x, y, 0, -0.06, 0.08, 0.2)
    + 0.09 * bump(x, y, 0, -0.21, 0.13, 0.06)
    - 0.14 * bump(ax, y, 0.29, 0.13, 0.12, 0.075)
    + 0.08 * bump(ax, y, 0.29, 0.26, 0.2, 0.05)
    + 0.07 * bump(ax, y, 0.43, -0.08, 0.15, 0.13)
    + 0.08 * bump(x, y, 0, MOUTH_Y + 0.03, 0.19, 0.04)
    + 0.07 * bump(x, y, 0, MOUTH_Y - 0.06, 0.17, 0.04)
    - 0.05 * bump(x, y, 0, MOUTH_Y - 0.015, 0.2, 0.018)
    + 0.07 * bump(x, y, 0, -0.72, 0.17, 0.1);
}

function scatter() {
  return [(Math.random() - 0.5) * 3, (Math.random() - 0.5) * 3, (Math.random() - 0.5) * 3];
}

function buildMesh() {
  const points = [];
  for (let r = 0; r < ROWS; r++) {
    const y = 1 - (r / (ROWS - 1)) * 2;
    const rad = Math.sqrt(Math.max(0, 1 - y * y));
    const jaw = y < -0.2 ? 1 - 0.24 * Math.pow((-0.2 - y) / 0.8, 1.4) : 1;
    const crown = y > 0.6 ? 1 - 0.08 * ((y - 0.6) / 0.4) : 1;
    for (let c = 0; c < COLS; c++) {
      const a = (c / COLS) * TAU;
      const x = Math.cos(a) * rad * 0.8 * jaw * crown;
      let z = Math.sin(a) * rad * 0.86 * (y < -0.15 ? 0.9 + 0.1 * jaw : 1);
      if (z > 0) z += relief(x, y) * Math.min(1, z / 0.5);
      const lip = z > 0 && Math.abs(x) < 0.24 && Math.abs(y - MOUTH_Y) < 0.13;
      points.push({ x, y, z, row: r, lip, fade: 1, s: scatter() });
    }
  }
  for (let r = 0; r < 12; r++) {
    const y = -0.84 - r * 0.05;
    const cols = 56;
    for (let c = 0; c < cols; c++) {
      const a = (c / cols) * TAU;
      points.push({ x: Math.cos(a) * 0.32, y, z: Math.sin(a) * 0.3, row: ROWS + r, lip: false, fade: 1 - r / 12, s: scatter() });
    }
  }
  return points;
}

export class HoloAvatar {
  constructor() {
    this.points = buildMesh();
    this.buckets = Array.from({ length: BUCKETS }, () => []);
    this.blinkAt = 2;
    this.glitchUntil = 0;
    this.glitchRows = [0, 0, 0];
    this.motes = Array.from({ length: 34 }, () => ({ p: Math.random(), x: Math.random() * 2 - 1, v: 0.15 + Math.random() * 0.35 }));
  }

  draw(ctx, { R, t, level, state, rgba, reveal }) {
    if (reveal <= 0) return;
    const unit = R * 0.4;
    const top = -R * 0.08 + Math.sin(t * 1.1) * R * 0.018;
    this.drawBeam(ctx, R, unit, top, t, rgba, reveal);

    const thinking = state === "thinking";
    const listening = state === "listening";
    const yaw = thinking ? Math.sin(t * 0.9) * 0.12 + 0.18 : listening ? Math.sin(t * 0.5) * 0.08 : Math.sin(t * 0.35) * 0.32;
    const pitch = thinking ? 0.1 : listening ? -0.06 : Math.sin(t * 0.3) * 0.05;
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const mouth = state === "speaking" || listening ? level : level * 0.3;
    const scanPeriod = thinking ? 1.1 : 3.2;
    const scanY = 1.1 - ((t % scanPeriod) / scanPeriod) * 2.6;
    const spread = (1 - reveal) ** 2;

    if (Math.random() < 0.005 && t > this.glitchUntil) {
      this.glitchUntil = t + 0.12;
      const row = Math.floor(Math.random() * ROWS);
      this.glitchRows = [row, row + 2 + Math.floor(Math.random() * 6), (Math.random() - 0.5) * unit * 0.25];
    }
    const glitching = t < this.glitchUntil;

    this.buckets.forEach(b => (b.length = 0));
    const size = Math.max(1.1, unit / 70);
    for (const p of this.points) {
      let { x, y, z } = p;
      if (p.lip) {
        const d = y - MOUTH_Y;
        const w = 1 - Math.abs(x) / 0.24;
        y += d < 0 ? -mouth * 0.08 * w : mouth * 0.015 * w;
      }
      x += p.s[0] * spread; y += p.s[1] * spread; z += p.s[2] * spread;

      const x1 = x * cy + z * sy;
      const z1 = -x * sy + z * cy;
      const y2 = y * cp - z1 * sp;
      const z2 = y * sp + z1 * cp;
      const persp = 3.2 / (3.2 - z2);
      let px = x1 * unit * persp;
      const py = top - y2 * unit * persp;
      if (glitching && p.row >= this.glitchRows[0] && p.row <= this.glitchRows[1]) px += this.glitchRows[2];

      let a = (0.1 + 0.9 * clamp((z2 + 0.35) / 1.15)) * p.fade;
      if (Math.abs(y - scanY) < 0.05) a = Math.min(1, a + 0.55);
      const b = Math.min(BUCKETS - 1, Math.floor(a * BUCKETS));
      this.buckets[b].push(px, py);
    }

    for (let b = 0; b < BUCKETS; b++) {
      const list = this.buckets[b];
      if (!list.length) continue;
      ctx.fillStyle = rgba(((b + 1) / BUCKETS) * 0.85 * reveal, b > 7 ? 0.45 : 0.1);
      ctx.beginPath();
      for (let i = 0; i < list.length; i += 2) ctx.rect(list[i] - size / 2, list[i + 1] - size / 2, size, size);
      ctx.fill();
    }

    this.drawEyes(ctx, { unit, top, cy, sy, cp, sp, t, state, rgba, reveal, level });
  }

  drawEyes(ctx, { unit, top, cy, sy, cp, sp, t, state, rgba, reveal, level }) {
    if (t > this.blinkAt + 0.16) this.blinkAt = t + 2.5 + Math.random() * 4;
    const blink = t > this.blinkAt ? Math.abs(Math.sin(((t - this.blinkAt) / 0.16) * Math.PI)) : 0;
    const open = 1 - blink * 0.92;
    const glow = state === "listening" ? 1 : state === "thinking" ? 0.85 : 0.65 + level * 0.3;
    for (const [x, y, z] of EYES) {
      const x1 = x * cy + z * sy;
      const z1 = -x * sy + z * cy;
      const y2 = y * cp - z1 * sp;
      const z2 = y * sp + z1 * cp;
      const persp = 3.2 / (3.2 - z2);
      const ex = x1 * unit * persp;
      const ey = top - y2 * unit * persp;
      const w = unit * 0.11;
      const g = ctx.createRadialGradient(ex, ey, 0, ex, ey, w * 1.8);
      g.addColorStop(0, rgba(glow * reveal, 0.85));
      g.addColorStop(0.35, rgba(glow * 0.5 * reveal, 0.3));
      g.addColorStop(1, rgba(0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.ellipse(ex, ey, w * 1.8, w * 1.8 * Math.max(0.15, open), 0, 0, TAU);
      ctx.fill();
      ctx.fillStyle = rgba(glow * reveal, 0.95);
      ctx.beginPath();
      ctx.ellipse(ex, ey, w * 0.55, w * 0.22 * open + 0.6, 0, 0, TAU);
      ctx.fill();
    }
  }

  drawBeam(ctx, R, unit, top, t, rgba, reveal) {
    const baseY = R * 0.5;
    const headY = top + unit * 0.7;
    const g = ctx.createLinearGradient(0, baseY, 0, top - unit);
    g.addColorStop(0, rgba(0.22 * reveal));
    g.addColorStop(0.45, rgba(0.06 * reveal));
    g.addColorStop(1, rgba(0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(-R * 0.07, baseY);
    ctx.lineTo(-unit * 1.0, headY - unit * 1.9);
    ctx.lineTo(unit * 1.0, headY - unit * 1.9);
    ctx.lineTo(R * 0.07, baseY);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = rgba(0.8 * reveal, 0.3);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(0, baseY, R * 0.1, R * 0.022, 0, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = rgba(0.9 * reveal, 0.7);
    ctx.beginPath();
    ctx.ellipse(0, baseY, R * 0.035, R * 0.008, 0, 0, TAU);
    ctx.fill();

    for (const m of this.motes) {
      m.p += 0.004 * m.v;
      if (m.p > 1) { m.p = 0; m.x = Math.random() * 2 - 1; }
      const y = baseY - m.p * (baseY - top + unit);
      const width = R * 0.07 + (unit * 0.9 - R * 0.07) * m.p;
      ctx.fillStyle = rgba(0.6 * (1 - m.p) * reveal, 0.5);
      ctx.fillRect(m.x * width, y, 1.6, 1.6);
    }
  }
}
