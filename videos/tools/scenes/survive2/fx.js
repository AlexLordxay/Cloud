// «Скільки ти протримаєшся…» v2 — the effects that happen TO the astronaut (characters/astronaut.js, its look unchanged:
// everything here is laid over it and is off by default).
//
//   const fx = window.__astroFX(THREE, a);   // patches every lit material of the figure once, before the first render
//   fx.U.uHeat.value = 0..1                  // the suit glows: dull red → orange → yellow-white (hotter near the burn front)
//   fx.U.uChar.value / uMelt.value           // two fronts climbing from the boots (-0.3) to past the helmet (1.3), in the
//                                            // figure's normalised height with noise: below uChar the cloth is charred
//                                            // black with glowing cracks, below uMelt it is gone (a white-hot edge)
//   fx.U.uFrost.value = 0..1                 // ice grows from the fingers, boots and helmet in toward the chest
//   fx.update()                              // each frame, after the figure is posed (the figure's frame for the pattern)
//
// The pattern lives in the figure's own space (a.group), so it rides along as he moves; burnCoord(p) gives the same
// front coordinate in JS (same hash/noise as the shader, in float32-ish arithmetic: close enough to spawn the sparks
// where the front passes).
(() => {
  const GLSL_NOISE = `
    float fxH(vec3 p) { p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419)); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
    float fxN(vec3 x) { vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(fxH(i), fxH(i + vec3(1, 0, 0)), f.x), mix(fxH(i + vec3(0, 1, 0)), fxH(i + vec3(1, 1, 0)), f.x), f.y),
                 mix(mix(fxH(i + vec3(0, 0, 1)), fxH(i + vec3(1, 0, 1)), f.x), mix(fxH(i + vec3(0, 1, 1)), fxH(i + vec3(1, 1, 1)), f.x), f.y), f.z); }
    float fxF(vec3 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { s += a * fxN(p); p = p * 2.07 + vec3(3.1, 1.7, 5.3); a *= 0.5; } return s / 0.9375; }
    // a blackbody-ish ramp: 0 dark → deep red → orange → yellow → white, times a brightness that climbs steeply
    vec3 fxBB(float t) { t = clamp(t, 0.0, 1.0);
      vec3 c = vec3(1.0, 0.05 + 0.75 * smoothstep(0.5, 1.0, t), 0.01 + 0.6 * smoothstep(0.8, 1.0, t));
      return c * (0.15 * t + 6.0 * t * t * t * t); }
  `;
  // the same noise in JS (for the sparks)
  const fr = x => x - Math.floor(x);
  function H(x, y, z) {
    x = fr(x * 0.3183099 + 0.71) * 17; y = fr(y * 0.3183099 + 0.113) * 17; z = fr(z * 0.3183099 + 0.419) * 17;
    return fr(x * y * z * (x + y + z));
  }
  function N(x, y, z) {
    const i = Math.floor(x), j = Math.floor(y), k = Math.floor(z); let fx = x - i, fy = y - j, fz = z - k;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz);
    const L = (a, b, t) => a + (b - a) * t;
    return L(L(L(H(i, j, k), H(i + 1, j, k), fx), L(H(i, j + 1, k), H(i + 1, j + 1, k), fx), fy),
             L(L(H(i, j, k + 1), H(i + 1, j, k + 1), fx), L(H(i, j + 1, k + 1), H(i + 1, j + 1, k + 1), fx), fy), fz);
  }
  function F(x, y, z) { let s = 0, a = 0.5; for (let i = 0; i < 4; i++) { s += a * N(x, y, z); x = x * 2.07 + 3.1; y = y * 2.07 + 1.7; z = z * 2.07 + 5.3; a *= 0.5; } return s / 0.9375; }

  window.__astroFX = (T, a) => {
    const U = {
      uHeat: { value: 0 }, uGlowK: { value: 1 }, uChar: { value: -1 }, uMelt: { value: -1 }, uFrost: { value: 0 }, uTime: { value: 0 },
      uFig: { value: new T.Matrix4() }, uY: { value: new T.Vector2(-1, 1) }, uCore: { value: new T.Vector3() }, uReach: { value: 1 },
      uFrostCol: { value: new T.Color(0.80, 0.90, 1.0) },
    };
    // the figure's extent at rest (its own space), for the normalised height and the frost's reach
    a.group.updateMatrixWorld(true);
    const inv = new T.Matrix4().copy(a.group.matrixWorld).invert();
    const box = new T.Box3().setFromObject(a.group).applyMatrix4(inv);
    U.uY.value.set(box.min.y, box.max.y);
    U.uCore.value.set(0, box.min.y + 0.62 * (box.max.y - box.min.y), 0);            // the chest
    U.uReach.value = 1.0;

    const VERT_DECL = 'varying vec3 vFig;\nuniform mat4 uFig;\n';
    const VERT_BODY = '\n  vFig = (uFig * modelMatrix * vec4(transformed, 1.0)).xyz;\n';
    const FRAG_DECL = `uniform float uHeat, uGlowK, uChar, uMelt, uFrost, uTime, uReach; uniform vec2 uY; uniform vec3 uCore, uFrostCol; varying vec3 vFig;
      ${GLSL_NOISE}
      float fxBurn(vec3 p) { float h = (p.y - uY.x) / (uY.y - uY.x); return h + 0.34 * (fxF(p * 4.0) - 0.5) + 0.07 * (fxN(p * 21.0) - 0.5); }
    `;
    // after the colour is known: char, frost, the melt (discard) and the glow
    const FRAG_COL = `
      vec3 fxGlow = vec3(0.0); float fxCharK = 0.0, fxFrostK = 0.0;
      {
        float b = fxBurn(vFig);
        if (uMelt > -0.9 && b < uMelt) discard;
        float n2 = fxN(vFig * 31.0), n3 = fxF(vFig * 9.0 + 4.0);
        fxCharK = smoothstep(uChar + 0.015, uChar - 0.05, b);
        // scorch: ahead of the char the white cloth yellows and browns with the heat, in blotches
        float scorch = uHeat * (0.5 + 0.5 * n3) * (0.55 + 0.45 * smoothstep(0.75, 0.0, b - uChar));
        diffuseColor.rgb *= mix(vec3(1.0), vec3(0.3, 0.12, 0.04), clamp(scorch * 1.3, 0.0, 1.0));
        // the char: black with a brown-grey bloom of soot, blistered
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.03, 0.022, 0.018) * (0.6 + 0.8 * n3), fxCharK);
        // the heat: the cloth glows, hottest just ahead of the char front, pulsing a little
        float near = 1.0 - smoothstep(0.0, 0.45, b - uChar);
        float temp = uHeat * (0.5 + 0.22 * near + 0.2 * (n3 - 0.5)) * (1.0 - 0.55 * fxCharK);
        fxGlow += fxBB(temp) * 0.7 * uGlowK;
        // hot spots: where the scorch is deepest the cloth smoulders
        fxGlow += fxBB(0.55 + 0.2 * n2) * smoothstep(0.62, 0.8, scorch) * (1.0 - uGlowK) * 0.6 * (0.7 + 0.3 * sin(uTime * 7.0 + n2 * 30.0));
        // glowing cracks in the char (like burnt paper), flickering
        float vein = 1.0 - smoothstep(0.0, 0.025 + 0.02 * n2, abs(fxF(vFig * 13.0 + vec3(0.0, uTime * 0.25, 0.0)) - 0.5));
        vein = max(vein, 0.6 * smoothstep(0.72, 0.9, fxF(vFig * 24.0 - 3.0)));
        float flick = 0.7 + 0.3 * sin(uTime * 9.0 + n2 * 20.0);
        fxGlow += fxCharK * vein * fxBB(0.62 + 0.12 * n2) * flick * 0.9;
        // the white-hot edge where it is about to go
        if (uMelt > -0.9) { float e = 1.0 - smoothstep(0.0, 0.03, b - uMelt); fxGlow += e * fxBB(0.66) * 1.3; diffuseColor.rgb *= 1.0 - 0.8 * e; }
        // the frost: from the extremities (far from the chest) inward, crystals and a white crust
        float d = length((vFig - uCore) * vec3(1.0, 0.8, 1.0)) / uReach;
        float fc = d + 0.35 * (fxF(vFig * 6.0) - 0.5), th = 1.2 - uFrost * 1.45;
        fxFrostK = smoothstep(th - 0.06, th + 0.02, fc) * step(0.001, uFrost);
        // ice: blue-grey glaze with white feathery crystals and darker cracks in it, the whole suit going cold blue first
        diffuseColor.rgb *= mix(vec3(1.0), vec3(0.7, 0.8, 0.95), smoothstep(0.0, 0.6, uFrost));
        float cr = fxF(vFig * 38.0), feath = 1.0 - smoothstep(0.0, 0.07, abs(fxF(vFig * 70.0 + 2.0) - 0.5)), crack = 1.0 - smoothstep(0.0, 0.03, abs(fxF(vFig * 17.0 + 9.0) - 0.5));
        vec3 ice = mix(vec3(0.22, 0.34, 0.5), vec3(0.72, 0.82, 0.92), 0.25 + 0.6 * cr) + 0.3 * feath;
        ice *= 1.0 - 0.55 * crack;
        float edge = (1.0 - smoothstep(th + 0.02, th + 0.14, fc)) * fxFrostK;   // the growing rim: bright rime
        ice += 0.3 * edge;
        diffuseColor.rgb = mix(diffuseColor.rgb, ice, fxFrostK);
      }
    `;
    const FRAG_RM = `
      roughnessFactor = mix(roughnessFactor, 0.97, fxCharK); metalnessFactor = mix(metalnessFactor, 0.0, fxCharK);
      roughnessFactor = mix(roughnessFactor, 0.22, fxFrostK); metalnessFactor = mix(metalnessFactor, 0.0, fxFrostK);
    `;
    const FRAG_EMIT = `
      totalEmissiveRadiance += fxGlow;
      // the frost's glints: tiny facets that catch the light
      totalEmissiveRadiance += fxFrostK * uFrostCol * pow(fxN(vFig * 260.0 + vViewPosition * 3.0), 16.0) * 2.0;
    `;
    const patched = new Set();
    a.group.traverse(o => {
      if (!o.isMesh || !o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (patched.has(m) || !(m.isMeshStandardMaterial)) continue;
        patched.add(m);
        const prev = m.onBeforeCompile;
        m.onBeforeCompile = (sh, r) => {
          if (prev) prev.call(m, sh, r);
          Object.assign(sh.uniforms, U);
          sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + VERT_DECL)
            .replace('#include <project_vertex>', '#include <project_vertex>' + VERT_BODY);
          sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + FRAG_DECL)
            .replace('#include <color_fragment>', '#include <color_fragment>\n' + FRAG_COL)
            .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\n' + FRAG_RM)
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + FRAG_EMIT);
        };
        m.customProgramCacheKey = () => 'astroFX';
        m.needsUpdate = true;
      }
    });
    // the bits that are not lit materials (the lamps' halos, LEDs): hidden once the melt has passed their height
    const extras = [];
    a.group.traverse(o => { if ((o.isSprite || (o.isMesh && o.material && !o.material.isMeshStandardMaterial && o.material.visible !== false))) extras.push(o); });

    const tmp = new T.Matrix4(), v = new T.Vector3();
    function update() {
      a.group.updateMatrixWorld(true);
      U.uFig.value.copy(a.group.matrixWorld).invert();
      for (const o of extras) {
        o.getWorldPosition(v); v.applyMatrix4(U.uFig.value);
        o.visible = !(U.uMelt.value > -0.9 && burnCoord(v) < U.uMelt.value + 0.02);
      }
    }
    // the front coordinate at a point in the figure's space (as fxBurn in the shader)
    function burnCoord(p) {
      const [y0, y1] = [U.uY.value.x, U.uY.value.y];
      return (p.y - y0) / (y1 - y0) + 0.34 * (F(p.x * 4, p.y * 4, p.z * 4) - 0.5) + 0.07 * (N(p.x * 21, p.y * 21, p.z * 21) - 0.5);
    }
    // points on the figure's surface in its own space (for sparks, flames, frost flakes), taken at its current pose
    function samplePoints(n, seed = 1) {
      a.group.updateMatrixWorld(true);
      const inv = new T.Matrix4().copy(a.group.matrixWorld).invert(), all = [];
      a.group.traverse(o => {
        if (!o.isMesh || !o.visible || !o.geometry || !o.geometry.attributes.position) return;
        if (o.material && o.material.visible === false) return;
        const P = o.geometry.attributes.position; all.push({ o, P, n: P.count });
      });
      const total = all.reduce((s, x) => s + x.n, 0), out = [];
      let s = seed * 9301 + 49297; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
      for (let k = 0; k < n; k++) {
        let r = Math.floor(rnd() * total), e = 0; while (r >= all[e].n) { r -= all[e].n; e++; }
        const { o, P } = all[e];
        v.fromBufferAttribute(P, r);
        if (o.isSkinnedMesh) o.boneTransform(r, v);
        v.applyMatrix4(o.matrixWorld).applyMatrix4(inv);
        out.push(v.clone());
      }
      return out;
    }
    return { U, update, burnCoord, samplePoints };
  };
})();
