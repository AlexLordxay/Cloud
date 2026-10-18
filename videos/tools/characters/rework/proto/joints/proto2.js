// prototype: a skinned sleeve (shoulder -> elbow -> wrist) as ONE tube, three variants side by side at several elbow angles
// rows: (A) plain 2-bone linear blend, (B) + half-angle helper bone with Bernstein weights, (C) B + inner-compression morph
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = '/home/user/cloud/videos/tools';
const out = process.argv[2], KNEE = process.argv[3] === 'knee';
const ANG = [0, 45, 90, 120], W = 1000, H = 1000;
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>
const W=${W},H=${H},ANG=${JSON.stringify(ANG)};
const ren=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true}); ren.setSize(W,H); ren.outputEncoding=THREE.sRGBEncoding;
ren.toneMapping=THREE.ACESFilmicToneMapping; document.body.appendChild(ren.domElement);
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x10141c);
const kl=new THREE.DirectionalLight(0xffe2c0,2.2); kl.position.set(-1,1.2,-0.8); scene.add(kl);
const bl=new THREE.DirectionalLight(0x9fb4e0,1.0); bl.position.set(-0.6,0.3,1); scene.add(bl); scene.add(new THREE.HemisphereLight(0x8090b0,0x302018,0.6));
const R=${KNEE ? 0.1 : 0.082}, LU=0.40, LF=0.33, BAND=${KNEE ? 0.12 : 0.095}, NR=4, SG=64, NU=220;
// one tube from y=0 (root) to y=-(LU+LF); radius: sleeve profile, bellows ridges inside the band, a pad bump on the outside of the bend
const outsideZ = ${KNEE ? -1 : 1};   // elbow: outside of the bend is +z (back); knee: -z (front)
function radius(y, ph){ const d=y+LU; const t=Math.min(1,Math.max(0,(BAND-Math.abs(d))/BAND));
  const ridge = Math.abs(d)<BAND ? 0.07*Math.pow(0.5+0.5*Math.cos(2*Math.PI*NR*(d/(2*BAND))),2)*Math.sin(Math.PI*(d+BAND)/(2*BAND)) : 0;
  const cz = Math.sin(ph)*outsideZ; const pad = Math.max(0,cz-0.35)/0.65; const padH = 0.09*Math.pow(pad,0.6)*Math.exp(-((d/0.06)**2));
  const taper = R*(1 - 0.12*Math.min(1,Math.max(0,-y/(LU+LF))));
  return taper*(1+ridge*(1-padH*8) + padH); }
function build(mode){
  const pos=[],nrm=[],idx=[],si=[],sw=[],mo=[];
  for(let i=0;i<=NU;i++){ const y=-(LU+LF)*i/NU;
    for(let j=0;j<=SG;j++){ const ph=j/SG*Math.PI*2; const r=radius(y,ph); pos.push(r*Math.cos(ph), y, r*Math.sin(ph)); }
  }
  for(let i=0;i<NU;i++)for(let j=0;j<SG;j++){const a=i*(SG+1)+j,b=a+SG+1; idx.push(a,a+1,b,b,a+1,b+1);}
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3)); g.setIndex(idx); g.computeVertexNormals();
  // weights: bones 0 = upper, 1 = mid helper (half angle), 2 = lower
  for(let k=0;k<pos.length/3;k++){ const y=pos[3*k+1]; const t=Math.min(1,Math.max(0,(-LU+BAND - y)/(2*BAND)));
    if(mode==='lbs'){ const s=t*t*(3-2*t); si.push(0,2,0,0); sw.push(1-s,s,0,0); }
    else if(mode==='mid'){ si.push(0,1,2,0); sw.push((1-t)*(1-t),2*t*(1-t),t*t,0); }
    else { const c=1-t; si.push(0,1,3,2); sw.push(c*c*c,3*t*c*c,3*t*t*c,t*t*t); } }
  g.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(si,4)); g.setAttribute('skinWeight',new THREE.Float32BufferAttribute(sw,4));
  if(mode==='morph'){ g.userData.cubic=true; // corrective: on the inside of the bend push out and bunch (full at 120 deg)
    const p=g.attributes.position, n=g.attributes.normal;
    for(let k=0;k<p.count;k++){ const y=p.getY(k), d=y+LU, inside=Math.max(0,-n.getZ(k)*outsideZ), outside=Math.max(0,n.getZ(k)*outsideZ);
      const f=Math.exp(-((d/(BAND*0.9))**2)); const amt=R*(0.22*inside*inside + 0.10*outside)*f;
      mo.push(n.getX(k)*amt, n.getY(k)*amt, n.getZ(k)*amt); }
    g.morphAttributes.position=[new THREE.Float32BufferAttribute(mo,3)]; g.morphTargetsRelative=true; }
  return g; }
const mat=new THREE.MeshStandardMaterial({color:0xece6da,roughness:0.85});
const rows=[['lbs',0],['mid',1],['cubic',2],['morph',3]], rigs=[];
rows.forEach(([mode,row])=>ANG.forEach((a,col)=>{
  const root=new THREE.Group(); root.position.set(col*1.2, -row*1.25, 0); scene.add(root);
  const up=new THREE.Bone(); root.add(up);
  const mid=new THREE.Bone(); mid.position.y=-LU; up.add(mid);
  const lo=new THREE.Bone(); lo.position.y=-LU; up.add(lo);
  const h2=new THREE.Bone(); h2.position.y=-LU; up.add(h2);
  // the helper follows the public joint: half of its rotation, computed when matrices update
  const QI=new THREE.Quaternion(); const cub = mode!=='lbs' && mode!=='mid';
  mid.updateMatrix=function(){ this.quaternion.slerpQuaternions(QI, lo.quaternion, cub ? 1/3 : 0.5); THREE.Object3D.prototype.updateMatrix.call(this); };
  h2.updateMatrix=function(){ this.quaternion.slerpQuaternions(QI, lo.quaternion, 2/3); THREE.Object3D.prototype.updateMatrix.call(this); };
  root.updateMatrixWorld(true);
  const sk=new THREE.Skeleton([up,mid,lo,h2]); const m=new THREE.SkinnedMesh(build(mode),mat); m.frustumCulled=false; root.add(m); m.bind(sk);
  const rad=a*Math.PI/180; lo.rotation.x = ${KNEE ? '-rad' : 'rad'};   // the public API convention
  if(mode==='morph') m.morphTargetInfluences[0]=Math.min(1,rad/2.1);
  rigs.push(m);
}));
scene.children.filter(o=>o.isGroup).forEach((g,i)=>{ const col=i%ANG.length,row=Math.floor(i/ANG.length); g.position.set(0,-row*1.3,col*1.0); });
if(window.ZOOM){}
const cam=new THREE.OrthographicCamera(-0.27,0.27,0.27,-0.27,0.1,20); cam.rotation.set(0,-Math.PI/2,0);
scene.updateMatrixWorld(true);
// numeric check: reach of the skinned surface from the pivot along the outer and inner bisector, in units of R
const rep=[]; rigs.forEach((m,i)=>{ const col=i%ANG.length,row=Math.floor(i/ANG.length), th=ANG[col]*Math.PI/180*(${KNEE ? -1 : 1});
  m.skeleton.update(); const p=m.geometry.attributes.position, v=new THREE.Vector3(), piv=new THREE.Vector3(0,-LU,0);
  const u1=new THREE.Vector2(1,0), u2=new THREE.Vector2(-Math.cos(th), -Math.sin(th)); // (y,z): upper axis toward shoulder, lower axis
  const ob=u1.clone().add(u2); const L=ob.length(); const outer = L<1e-6 ? new THREE.Vector2(0, ${KNEE ? -1 : 1}) : ob.multiplyScalar(-1/L); const perp=new THREE.Vector2(-outer.y, outer.x);
  let mx=-1,mn=1;
  for(let k=0;k<p.count;k++){ v.fromBufferAttribute(p,k); if(m.morphTargetInfluences&&m.geometry.morphAttributes.position){ const mp=m.geometry.morphAttributes.position[0]; v.x+=mp.getX(k)*m.morphTargetInfluences[0]; v.y+=mp.getY(k)*m.morphTargetInfluences[0]; v.z+=mp.getZ(k)*m.morphTargetInfluences[0]; }
    m.boneTransform(k, v); if(Math.abs(v.x)>0.01) continue; const d=new THREE.Vector2(v.y-piv.y, v.z-piv.z);
    if(Math.abs(d.dot(perp))>0.01) continue; const a=d.dot(outer); mx=Math.max(mx,a); mn=Math.min(mn,a); }
  rep.push([['lbs','mid','cubic','morph'][row],ANG[col],(mx/R).toFixed(2),(-mn/R).toFixed(2)]); });
rep.forEach(r=>console.log('REPORT '+r.join(' ')));
ren.setScissorTest(true); const cw=W/4, ch=H/4;
for(let row=0;row<4;row++) for(let col=0;col<4;col++){ ren.setViewport(col*cw,(3-row)*ch,cw,ch); ren.setScissor(col*cw,(3-row)*ch,cw,ch);
  cam.position.set(-5, -row*1.3+0.2-LU-0.03, col*1.0-0.06); cam.updateProjectionMatrix(); ren.render(scene,cam); }
window.done=true;
</script></body></html>`;
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message)); p.on('console', m => console.log('console:', m.text().slice(0,300)));
  await p.setContent(page); await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  const url = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/jpeg', 0.92));
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64')); await br.close();
})();
