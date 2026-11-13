// node configurator/e2e_demo.js <demo page url> <screenshot dir>   (run by tests/test_configurator_browser.py)
'use strict';
const { chromium } = require('playwright');
const assert = require('assert');
const [PAGE, SHOTS] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const apiCalls = [], errors = [];
  p.on('request', r => { if (/\/api\/save\.php/.test(r.url())) apiCalls.push(r.method() + ' ' + r.url()); });
  p.on('pageerror', e => errors.push(e.message));
  await p.goto(PAGE);
  await p.waitForSelector('#picker:not([hidden])');
  assert.strictEqual(await p.isVisible('#demo-banner'), true, 'demo banner');
  assert.match(await p.textContent('#demo-banner'), /Nothing is saved or published/);
  assert.strictEqual(await p.title(), 'Customize flash flood colors (demo)');
  await p.fill('#mq', 'columbus'); await p.click('#mlist button');
  await p.waitForSelector('#tools:not([hidden])');
  await p.waitForFunction(() => /Standard colors for Columbus/.test(document.getElementById('ffg-title').textContent));
  // a preset + a hidden band + save: works inside the page, claims nothing real
  await p.click('[data-preset="blues"]'); await p.uncheck('#v-5');
  await p.click('#save');
  await p.waitForFunction(() => /Demo: saved in this window only/.test(document.getElementById('ffg-state').textContent));
  assert.strictEqual(await p.textContent('#ffg-title'), 'Custom colors for Columbus, OH');
  await p.screenshot({ path: SHOTS + '/demo-saved.png', fullPage: true });
  // a validation error is shown like the real page does (all bands hidden)
  for (let i = 0; i < 7; i++) await p.uncheck('#v-' + i);
  assert.strictEqual(await p.textContent('#rows-err'), 'Show at least one band.');
  await p.check('#v-0');
  // reset to standard and save again
  await p.click('#standard'); await p.click('#save');
  await p.waitForFunction(() => /Standard colors for Columbus/.test(document.getElementById('ffg-title').textContent));
  // "saved" colors live only in memory: a reload forgets them
  await p.reload(); await p.waitForSelector('#demo-banner:not([hidden])');
  assert.deepStrictEqual(apiCalls, [], 'the demo must never call the real save service');
  assert.deepStrictEqual(errors, [], 'no page errors');
  await browser.close();
  console.log('demo e2e OK (nothing sent to the save service)');
})().catch(e => { console.error(e); process.exit(1); });
