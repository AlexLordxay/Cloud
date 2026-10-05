// The site as one page: planetarium/index.html with its stylesheet and scripts (css/, js/) put inline, in the same
// order as the browser loads them. The video tools patch this text, so it behaves exactly like the live site.
const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '../../planetarium');

function sitePage() {
  let html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8');
  html = html.replace(/<link rel="stylesheet" href="(css\/[^"]+)">/g, (_, f) => `<style>\n${fs.readFileSync(path.join(SITE, f), 'utf8')}</style>`);
  html = html.replace(/<script src="(js\/[^"]+)"><\/script>/g, (_, f) => `<script>\n${fs.readFileSync(path.join(SITE, f), 'utf8')}</script>`);
  return html;
}
module.exports = { SITE, sitePage };
