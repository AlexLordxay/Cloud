// One shot for frames.sh: node render_one.js shot|globe <name> — skipped if work/mercury_meet/<kind>_<name>/.done exists.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const [kind, name] = process.argv.slice(2);
const dir = path.join(__dirname, '../../work/mercury_meet', `${kind}_${name}`);
if (fs.existsSync(path.join(dir, '.done'))) process.exit(0);
execFileSync('node', [path.join(__dirname, kind === 'shot' ? 'terrain.js' : 'globe.js'), name, 'video'], { stdio: 'ignore' });
fs.writeFileSync(path.join(dir, '.done'), '');
console.log('done', kind, name);
