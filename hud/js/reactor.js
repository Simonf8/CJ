const TAU = Math.PI * 2;

const PALETTE = {
  booting:   { color: [0, 229, 255],   spin: 0.6, glow: 0.6 },
  idle:      { color: [0, 229, 255],   spin: 1.0, glow: 0.85 },
  listening: { color: [120, 245, 255], spin: 1.6, glow: 1.25 },
  thinking:  { color: [255, 176, 32],  spin: 4.2, glow: 1.1 },
  speaking:  { color: [0, 229, 255],   spin: 1.4, glow: 1.15 },
  error:     { color: [255, 59, 92],   spin: 0.5, glow: 1.0 },
  standby:   { color: [0, 140, 170],   spin: 0.3, glow: 0.35 },
};

const lerp = (a, b, t) => a + (b - a) * t;
const ease = t => 1 - Math.pow(1 - t, 3);

function noise(i, t) {
  return (Math.sin(i * 12.9898 + t * 3.1) * 0.5 + Math.sin(i * 4.137 - t * 5.7) * 0.3 + Math.sin(i * 0.71 + t * 1.3) * 0.2 + 1) / 2;
}

export class Reactor {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.state = "booting";
    this.color = [...PALETTE.booting.color];
    this.spin = PALETTE.booting.spin;
    this.glow = PALETTE.booting.glow;
    this.level = 0;
    this.target = 0;
    this.angle = 0;
    this.ignition = 0;
    this.ignitedAt = null;
    this.ripples = [];
    this.lastRipple = 0;
    this.sparks = Array.from({ length: 46 }, (_, i) => ({ a: Math.random() * TAU, r: 0.68 + Math.random() * 0.22, s: 0.2 + Math.random() * 0.8, z: Math.random() }));
    this.resize();
    new ResizeObserver(() => this.resize()).observe(canvas);
    this.last = performance.now();
    requestAnimationFrame(t => this.frame(t));
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const { width, height } = this.canvas.getBoundingClientRect();
    this.w = width; this.h = height;
    this.canvas.width = Math.max(1, width * dpr);
    this.canvas.height = Math.max(1, height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  setState(state) {
    this.state = PALETTE[state] ? state : "idle";
    if (state === "listening") this.ripples.push({ t: 0, strength: 1.4 });
  }

  setLevel(value) { this.target = Math.max(0, Math.min(1, value)); }

  ignite() { this.ignitedAt = performance.now(); }

  rgba(a, mix = 0) {
    const c = this.color.map(v => Math.round(lerp(v, 255, mix)));
    return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  }

  frame(now) {
    const dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    const p = PALETTE[this.state];
    const k = 1 - Math.pow(0.02, dt);
    this.color = this.color.map((v, i) => lerp(v, p.color[i], k));
    this.spin = lerp(this.spin, p.spin, k);
    this.glow = lerp(this.glow, p.glow, k);

    const idleBreath = this.state === "idle" || this.state === "booting" ? 0.08 + Math.sin(now / 900) * 0.05 : 0;
    const thinkPulse = this.state === "thinking" ? 0.25 + Math.sin(now / 120) * 0.12 : 0;
    const goal = Math.max(this.target, idleBreath, thinkPulse);
    this.level = lerp(this.level, goal, goal > this.level ? 0.45 : 0.12);
    this.angle += dt * this.spin;
    if (this.ignitedAt !== null) this.ignition = Math.min(1, (now - this.ignitedAt) / 1800);

    if (this.state === "listening" && now - this.lastRipple > 700 - this.level * 400) {
      this.ripples.push({ t: 0, strength: 0.6 + this.level });
      this.lastRipple = now;
    }
    this.ripples.forEach(r => (r.t += dt * 0.55));
    this.ripples = this.ripples.filter(r => r.t < 1);

    this.draw(now / 1000);
    requestAnimationFrame(t => this.frame(t));
  }

  stage(start, span = 0.35) {
    return ease(Math.max(0, Math.min(1, (this.ignition - start) / span)));
  }

  draw(t) {
    const { ctx, w, h } = this;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h * 0.43;
    const R = Math.min(w * 0.42, h * 0.36);
    const L = this.level;
    const a = this.angle;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";

    this.drawHalo(R, L);
    this.drawRipples(R);
    this.drawDial(R * 1.02, a * 0.05, this.stage(0.0));
    this.drawSegments(R * 0.9, -a * 0.32, this.stage(0.1), t);
    this.drawSweep(R * 0.97, a * 0.9, this.stage(0.2));
    this.drawBars(R * 0.6, R * 0.26, L, t, this.stage(0.25));
    this.drawDashed(R * 0.56, a * 0.6, this.stage(0.3));
    this.drawSparks(R, t, this.stage(0.4));
    this.drawCoil(R * 0.43, -a * 0.25, L, this.stage(0.45));
    this.drawInner(R * 0.3, a * 1.4, this.stage(0.55));
    this.drawCore(R * 0.2, L, t, this.stage(0.6));
    ctx.restore();
  }

  drawHalo(R, L) {
    const { ctx } = this;
    const g = ctx.createRadialGradient(0, 0, R * 0.1, 0, 0, R * 1.35);
    g.addColorStop(0, this.rgba(0.2 * this.glow + L * 0.15));
    g.addColorStop(0.45, this.rgba(0.05 * this.glow));
    g.addColorStop(1, this.rgba(0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, R * 1.35, 0, TAU);
    ctx.fill();
  }

  drawRipples(R) {
    const { ctx } = this;
    for (const r of this.ripples) {
      ctx.strokeStyle = this.rgba((1 - r.t) * 0.45 * r.strength);
      ctx.lineWidth = 2 * (1 - r.t) + 0.5;
      ctx.beginPath();
      ctx.arc(0, 0, R * (0.45 + r.t * 0.85), 0, TAU);
      ctx.stroke();
    }
  }

  drawDial(r, rot, s) {
    if (!s) return;
    const { ctx } = this;
    ctx.save();
    ctx.rotate(rot);
    const n = 180;
    const visible = Math.floor(n * s);
    for (let i = 0; i < visible; i++) {
      const ang = (i / n) * TAU;
      const major = i % 15 === 0;
      const mid = i % 5 === 0;
      const len = major ? 14 : mid ? 8 : 4;
      ctx.strokeStyle = this.rgba(major ? 0.85 : mid ? 0.45 : 0.22);
      ctx.lineWidth = major ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(Math.cos(ang) * r, Math.sin(ang) * r);
      ctx.lineTo(Math.cos(ang) * (r - len), Math.sin(ang) * (r - len));
      ctx.stroke();
    }
    ctx.fillStyle = this.rgba(0.6 * s);
    ctx.font = `500 ${Math.max(8, r * 0.032)}px "Share Tech Mono", monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let d = 0; d < 360; d += 30) {
      const ang = (d / 360) * TAU - Math.PI / 2;
      ctx.save();
      ctx.translate(Math.cos(ang) * (r + 14), Math.sin(ang) * (r + 14));
      ctx.rotate(ang + Math.PI / 2);
      ctx.fillText(String(d).padStart(3, "0"), 0, 0);
      ctx.restore();
    }
    ctx.strokeStyle = this.rgba(0.18 * s);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, r + 26, 0, TAU * s);
    ctx.stroke();
    ctx.restore();
  }

  drawSegments(r, rot, s, t) {
    if (!s) return;
    const { ctx } = this;
    const arcs = [[0.0, 0.22, 5], [0.27, 0.36, 2], [0.42, 0.64, 5], [0.7, 0.75, 9], [0.79, 0.95, 3]];
    ctx.save();
    ctx.rotate(rot);
    ctx.shadowColor = this.rgba(0.9);
    ctx.shadowBlur = 14 * this.glow;
    for (const [from, to, width] of arcs) {
      ctx.strokeStyle = this.rgba(0.75);
      ctx.lineWidth = width;
      ctx.beginPath();
      ctx.arc(0, 0, r, from * TAU, lerp(from, to, s) * TAU);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.strokeStyle = this.rgba(0.35);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, r - 10, 0, TAU * s);
    ctx.stroke();
    for (let i = 0; i < 3; i++) {
      const ang = i * (TAU / 3) + t * 0.3;
      ctx.fillStyle = this.rgba(0.9);
      ctx.beginPath();
      ctx.moveTo(Math.cos(ang) * (r + 10), Math.sin(ang) * (r + 10));
      ctx.lineTo(Math.cos(ang - 0.025) * (r + 20), Math.sin(ang - 0.025) * (r + 20));
      ctx.lineTo(Math.cos(ang + 0.025) * (r + 20), Math.sin(ang + 0.025) * (r + 20));
      ctx.fill();
    }
    ctx.restore();
  }

  drawSweep(r, rot, s) {
    if (!s) return;
    const { ctx } = this;
    const width = this.state === "thinking" ? 1.2 : 0.6;
    ctx.save();
    ctx.rotate(rot);
    if (ctx.createConicGradient) {
      const g = ctx.createConicGradient(-width, 0, 0);
      g.addColorStop(0, this.rgba(0));
      g.addColorStop(width / TAU, this.rgba(0.22 * s));
      g.addColorStop(Math.min(1, width / TAU + 0.001), this.rgba(0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, r, -width, 0);
      ctx.closePath();
      ctx.fill();
    }
    ctx.strokeStyle = this.rgba(0.5 * s);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(r * 0.5, 0);
    ctx.lineTo(r, 0);
    ctx.stroke();
    ctx.restore();
  }

  drawBars(r, maxLen, L, t, s) {
    if (!s) return;
    const { ctx } = this;
    const n = 120;
    const speaking = this.state === "speaking" || this.state === "listening";
    for (let i = 0; i < n; i++) {
      const mirror = i < n / 2 ? i : n - i;
      const ang = (i / n) * TAU - Math.PI / 2;
      const nz = noise(mirror, t * (speaking ? 2.4 : 0.8));
      const len = (3 + maxLen * (0.08 + L * nz * (speaking ? 1.05 : 0.5))) * s;
      const alpha = 0.35 + nz * 0.5 * (0.4 + L);
      ctx.strokeStyle = this.rgba(Math.min(1, alpha), L * 0.35 * nz);
      ctx.lineWidth = Math.max(1.4, (TAU * r) / n * 0.42);
      ctx.beginPath();
      ctx.moveTo(Math.cos(ang) * r, Math.sin(ang) * r);
      ctx.lineTo(Math.cos(ang) * (r + len), Math.sin(ang) * (r + len));
      ctx.stroke();
    }
  }

  drawDashed(r, rot, s) {
    if (!s) return;
    const { ctx } = this;
    ctx.save();
    ctx.rotate(rot);
    ctx.setLineDash([2, 7]);
    ctx.strokeStyle = this.rgba(0.6 * s);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, TAU);
    ctx.stroke();
    ctx.setLineDash([30, 14, 4, 14]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = this.rgba(0.4 * s);
    ctx.beginPath();
    ctx.arc(0, 0, r - 8, 0, TAU);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  drawSparks(R, t, s) {
    if (!s) return;
    const { ctx } = this;
    const fast = this.state === "thinking" ? 3.5 : 1;
    for (const p of this.sparks) {
      const ang = p.a + t * p.s * 0.35 * fast * (p.z > 0.5 ? 1 : -1);
      const rr = R * p.r;
      const x = Math.cos(ang) * rr;
      const y = Math.sin(ang) * rr * (0.96 + p.z * 0.04);
      ctx.fillStyle = this.rgba((0.25 + p.z * 0.6) * s, 0.4);
      ctx.beginPath();
      ctx.arc(x, y, 0.6 + p.z * 1.6, 0, TAU);
      ctx.fill();
    }
  }

  drawCoil(r, rot, L, s) {
    if (!s) return;
    const { ctx } = this;
    const n = 10;
    ctx.save();
    ctx.rotate(rot);
    ctx.shadowColor = this.rgba(1);
    ctx.shadowBlur = (10 + L * 20) * this.glow;
    for (let i = 0; i < n; i++) {
      const a0 = (i / n) * TAU + 0.06;
      const a1 = ((i + 1) / n) * TAU - 0.06;
      const inner = r * 0.78;
      ctx.fillStyle = this.rgba((0.22 + L * 0.35) * s, 0.15);
      ctx.strokeStyle = this.rgba(0.85 * s, 0.2);
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.arc(0, 0, r, a0, a1);
      ctx.arc(0, 0, inner, a1 - 0.03, a0 + 0.03, true);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  drawInner(r, rot, s) {
    if (!s) return;
    const { ctx } = this;
    ctx.save();
    ctx.rotate(rot);
    ctx.strokeStyle = this.rgba(0.9 * s, 0.3);
    ctx.lineWidth = 2;
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.arc(0, 0, r, (i / 3) * TAU, (i / 3) * TAU + TAU / 4.5);
      ctx.stroke();
    }
    ctx.rotate(-rot * 1.8);
    ctx.strokeStyle = this.rgba(0.5 * s);
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const ang = (i / 6) * TAU;
      const x = Math.cos(ang) * r * 0.82, y = Math.sin(ang) * r * 0.82;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }

  drawCore(r, L, t, s) {
    if (!s) return;
    const { ctx } = this;
    const pulse = r * (0.85 + L * 0.45 + Math.sin(t * 2.2) * 0.03) * s;
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, pulse * 2.4);
    g.addColorStop(0, `rgba(255,255,255,${0.95 * s})`);
    g.addColorStop(0.18, this.rgba(0.95 * s, 0.75));
    g.addColorStop(0.42, this.rgba(0.45 * s * this.glow));
    g.addColorStop(1, this.rgba(0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, pulse * 2.4, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = this.rgba(0.9 * s, 0.6);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(0, 0, pulse * 0.62, 0, TAU);
    ctx.stroke();
  }
}
