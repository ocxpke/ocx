// Rasteriza un SVG a PNG con Chromium (playwright).  Uso: node svg-a-png.js entrada.svg salida.png [escala]
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [entrada, salida, escalaTxt] = process.argv.slice(2);
  const svg = fs.readFileSync(entrada, 'utf8');
  const m = svg.match(/width="([\d.]+)" height="([\d.]+)"/);
  const w = Math.ceil(+m[1]), h = Math.ceil(+m[2]);
  const escala = +(escalaTxt || (w > 1400 ? 1.6 : 1.8));
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: escala });
  await pagina.setContent(`<html><body style="margin:0">${svg}</body></html>`);
  await pagina.screenshot({ path: salida, clip: { x: 0, y: 0, width: w, height: h } });
  await navegador.close();
})();
