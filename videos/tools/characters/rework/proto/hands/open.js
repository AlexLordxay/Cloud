for (const L of ['L','R']) { const f = F[L], s = f.s;
  f.fingers.forEach((g, i) => { g.base.rotation.set(0.05, 0, -s * (i - 1.5) * 0.14); g.tip.rotation.x = 0.05; });
  f.thumb.base.rotation.set(0.15, 0, -s * 0.35); f.thumb.tip.rotation.x = 0.05; }
