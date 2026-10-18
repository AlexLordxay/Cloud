export const meta = {
  name: 'astronaut-rework',
  description: 'Rework the Nebozvid astronaut: skinned limbs that bend right, real fingers, more detail and life',
  phases: [
    { title: 'Review', detail: 'four critics render test poses and list what is wrong, each from one angle' },
    { title: 'Plan', detail: 'one architect merges the findings into an ordered implementation plan' },
    { title: 'Build', detail: 'sequential builders: rig and skinned limbs, then hands, then detail and life' },
    { title: 'Verify', detail: 'adversarial critics render and hunt defects; fixer repairs; loop until clean' },
  ],
}

const SP = args.scratch
const CTX = `
Project: /home/user/cloud (git repo; do NOT commit or push — the caller does that). The character is
videos/tools/characters/astronaut.js: a spacesuit astronaut built in code with three.js r147 (global THREE, no modules),
exposed as window.__makeAstronaut(THREE) returning { group, joints, materials, pose, rim, light, aim, lights, ready, setTint, setOpacity }.
It is used by existing video scenes (videos/tools/scenes/blackhole, survive, astrodance cam.js) that call a.pose(t), set
a.joints.<name>.rotation (names: body, head, shoulderL/R, elbowL/R, wristL/R, hipL/R, kneeL/R, ankleL/R), a.joints.head.add(...),
setTint, setOpacity, light/aim, rim. That API and its rotation conventions must keep working: figure faces -z, ~1.9 units
tall, pelvis at origin; elbow flexion = positive rotation.x (forearm swings forward to -z); knee flexion = negative rotation.x
(shin swings back to +z); shoulder abduction = rotation.z of sign s (left s=-1 at -x).
Render tool: cd /home/user/cloud/videos/tools && node characters/preview.js <out.jpg> <t> <pose.json or -> <full|hands|limbs>
  pose.json: {"elbowL":[x,y,z], ...} joint rotations applied after a.pose(t), or {"call":"method","args":[...]} to call a
  method on the character object. "full" = 4 views of the whole figure; "hands" = close-ups of both hands front/back;
  "limbs" = close-ups of elbows and knees. Output is 1600x760 JPG; look at it with the Read tool (downscale with python PIL
  if needed). Rendering is software (swiftshader), ~10-30 s per image. Write scratch files only under ${SP}/astro_wf/.
The author's request (Ukrainian, translated): "Look at the character model again, make it more alive, detailed and plastic,
so the arms bend in the right places and in the right direction, like the legs too; the fingers should look like fingers,
not sticks, etc." Current problems already seen: limbs are rigid separate pieces, so at a bent elbow/knee the shells,
bellows and pads poke out as separate slabs with gaps; fingers are stubby capsules with blue spheres on the ends;
hands are blobby; the pose is stiff.`

const FIND = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    problem: { type: 'string' }, evidence: { type: 'string' }, severity: { type: 'string', enum: ['major', 'minor'] },
    fix: { type: 'string', description: 'concrete technical recommendation (three.js r147)' } },
    required: ['problem', 'evidence', 'severity', 'fix'] } },
  images: { type: 'array', items: { type: 'string' } } }, required: ['findings', 'images'] }

const LENSES = [
  { key: 'joints', prompt: 'Lens: joints and bending. Render test poses with elbows and knees at 0, 45, 90, 120 degrees, shoulders raised forward and sideways, hips flexed, wrists bent, in "limbs" and "full" views. Judge: do limbs bend at anatomically right places (elbow/knee at the right height, right direction, right axis), does the fabric deform smoothly or do pieces separate, intersect, gap or poke out? Are the joint ranges and pivots right? Recommend how to rebuild limbs as THREE.SkinnedMesh with THREE.Bone hierarchy (and how to keep the joints API), weights at the joints, bellows that compress on the inside of a bend, volume preservation tricks.' },
  { key: 'hands', prompt: 'Lens: hands and fingers. Render "hands" views of the idle and of open/fist poses you set via the joints of the fingers if exposed (read the code to see how fingers are built). Judge against real EVA gloves (NASA Phase VI / Orlan): palm shape, knuckles, three phalanges per finger with correct lengths (proximal > middle > distal), finger taper, rounded fingertips integrated (not spheres stuck on), thumb from the base of the palm with opposition, finger spacing, glove cuff. Recommend a concrete construction (e.g. per-finger skinned tapered tubes or lathe/capsule chains with bones per phalanx, a sculpted palm), and an API to pose hands (open, relaxed, fist, point, thumbs up, wave).' },
  { key: 'detail', prompt: 'Lens: detail and materials of the whole suit compared with real spacesuits (EMU, Orlan, Apollo A7L). Render "full" views. Judge silhouette proportions (head/helmet size, torso, backpack, limb thickness, boot size), fabric folds and seams, hard parts, the helmet and visor, connectors, wear, colour. List what makes it look like a toy and what concrete geometry/material details would make it read as a real, detailed suit at video resolution (720x1280 and close-ups). Avoid suggesting things that would cost huge render time.' },
  { key: 'life', prompt: 'Lens: liveliness and motion. Read the pose(t) function and the scenes that use it (videos/tools/scenes/*/cam.js that include characters/astronaut.js). Render a few frames of the idle at t=0,1,2,3,4 in "full" view. Judge how alive it looks: breathing, secondary motion, overlapping action, asymmetry, weight, head movement, fingers. Recommend a better idle (still floating, slow, restrained), plus a small gesture API (wave, point at a direction, thumbs up, look at) that video scenes could use, keeping the existing pose(t) signature and joints API working for old scenes.' },
]

phase('Review')
const reviews = await parallel(LENSES.map(L => () => agent(
  `${CTX}\n\nYou are a critic. ${L.prompt}\nReturn concrete, evidence-based findings (which image, what you saw) and concrete fixes. Do not edit astronaut.js.`,
  { label: `review:${L.key}`, phase: 'Review', schema: FIND })))
const allFindings = reviews.filter(Boolean).flatMap((r, i) => r.findings.map(f => ({ lens: LENSES[i].key, ...f })))
log(`${allFindings.length} findings from ${reviews.filter(Boolean).length} critics`)

phase('Plan')
const PLAN = { type: 'object', properties: {
  steps: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, scope: { type: 'string', description: 'exactly what to change, where, how, with numbers' },
    acceptance: { type: 'string', description: 'renders/poses that must look right when done' } },
    required: ['title', 'scope', 'acceptance'] } },
  compatibility: { type: 'string' } }, required: ['steps', 'compatibility'] }
const plan = await agent(`${CTX}\n\nYou are the architect. Read astronaut.js fully. Here are the critics' findings:\n${JSON.stringify(allFindings, null, 1)}\n\nMerge them into an ordered implementation plan of exactly 3 build steps, each done by one engineer in sequence on the same file:\n1) the rig: limbs (arms, legs, ideally the sleeve-into-torso and thigh-into-seat joins) rebuilt as skinned meshes on a Bone hierarchy that IS the joints API (Bones are Object3Ds, so a.joints.elbowL.rotation keeps working), correct pivots, smooth weights, bellows that fold on the inner side, no gaps or poking pads at 0-130 degree bends;\n2) the hands: real glove fingers with three phalanges each, tapered, integrated rubber tips, a sculpted palm and an opposable thumb, finger bones exposed (e.g. a.joints.fingerL[i][k], thumbL[k]) and a.hand(side, shape) presets (open, relaxed, fist, point, thumbsUp, wave);\n3) detail and life: the most valuable suit detail fixes from the detail critic that are cheap to render, and a livelier but restrained idle (breathing, secondary motion, fingers alive, head) plus gesture helpers (a.gesture(name, k) or similar) — the old pose(t) must still give a similar floating idle for old scenes.\nBe concrete (numbers, functions, three.js classes). Note what must not break.`,
  { label: 'architect', phase: 'Plan', schema: PLAN })

phase('Build')
const builds = []
for (const [i, st] of plan.steps.slice(0, 2).entries()) {   // the author asked to stop after step 2 (hands)
  const r = await agent(`${CTX}\n\nYou are engineer ${i + 1} of ${plan.steps.length}, working directly on videos/tools/characters/astronaut.js (earlier steps are already in the file). Your step:\nTITLE: ${st.title}\nSCOPE: ${st.scope}\nACCEPTANCE: ${st.acceptance}\nCOMPATIBILITY: ${plan.compatibility}\n\nNote: an earlier attempt at these steps was interrupted mid-way (session limit), so the file may already hold partial, possibly broken edits of this step (e.g. a started rig section with helper functions, old limb/bellows builders removed); check "git diff videos/tools/characters/astronaut.js" first, continue from what is useful or redo it, but leave the file fully working. Implement it fully. Keep the code style of the file (comments explaining the why, compact). Render and look at your result repeatedly (full, limbs, hands views, and bent poses) until the acceptance criteria hold and nothing is broken; check the browser console for errors (preview.js prints page errors). Also run a quick check that videos/tools/scenes/astrodance/cam.js style joint rotations still work (set shoulder/elbow/hip/knee rotations via pose.json). Report what you changed, render paths, and any remaining issues honestly.`,
    { label: `build:${i + 1}`, phase: 'Build' })
  builds.push(r)
}

return { plan, builds }
