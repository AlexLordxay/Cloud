for (const L of ['L','R']) { const f = F[L], s = f.s;
  f.fingers.forEach((g, i) => { g.base.rotation.set(1.55, 0, 0); g.tip.rotation.x = 1.75; });
  f.thumb.base.rotation.set(0.9, 0, -s * 0.95); f.thumb.tip.rotation.x = 0.7; }
