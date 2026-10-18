// survive "mars" wave (stand + wave) at two phases, and astrodance wave; side-by-side via __views not possible per pose,
// so this file is parameterised by window.W (phase)
{
  const J = a.joints, w = WPH;
  const set = (k, v) => J[k].rotation.set(...v);
  // survive stand
  set('body',[0.02,0,0]); set('shoulderL',[0.1,0,-0.3]); set('elbowL',[0.35,0,0]); set('wristL',[0.1,0,0]);
  set('hipL',[0.04,0,-0.06]); set('hipR',[0.04,0,0.06]); set('kneeL',[-0.08,0,0]); set('kneeR',[-0.08,0,0]); set('ankleL',[0.04,0,0]); set('ankleR',[0.04,0,0]);
  set('head',[-0.05,0,0.12]); set('shoulderR',[0.5,0,2.3]); set('elbowR',[0.55+0.45*w,0,0]); set('wristR',[0,0,0.2*w]);
  window.__views = [[0, 0.9, -5.2], [2.5, 1.2, -4.0], [5.2, 0.6, 0], [0, 3.5, -3]];
}
