export function startBackground(canvas) {
  const ctx = canvas.getContext("2d");
  let w = 0, h = 0, particles = [], accent = "0,229,255", tick = 0;

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth; h = window.innerHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round((w * h) / 16000);
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.12, vy: -0.05 - Math.random() * 0.15,
      r: Math.random() * 1.4 + 0.3, a: Math.random() * 0.5 + 0.15,
    }));
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    if (tick++ % 120 === 0) accent = getComputedStyle(document.documentElement).getPropertyValue("--accent-rgb").trim() || accent;
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;
    }
    ctx.lineWidth = 0.5;
    for (let i = 0; i < particles.length; i++) {
      const a = particles[i];
      for (let j = i + 1; j < particles.length; j++) {
        const b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < 9000) {
          ctx.strokeStyle = `rgba(${accent},${0.08 * (1 - d2 / 9000)})`;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
      ctx.fillStyle = `rgba(${accent},${a.a})`;
      ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2); ctx.fill();
    }
    requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);
}
