// Browser test for the configurator. Started by tests/test_configurator_browser.py, which runs the servers:
//   node configurator/e2e.js <page url> <control url> <screenshot dir>
'use strict';
const { chromium } = require('playwright');
const assert = require('assert');
const [PAGE, CTL, SHOTS] = process.argv.slice(2);
const ctl = async (path, body) => (await fetch(CTL + path, body ? { method: 'POST', body: JSON.stringify(body) } : {})).json();
const steps = [];
const step = (s) => { steps.push(s); console.log('  - ' + s); };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
  const p = await ctx.newPage();
  const errors = []; p.on('pageerror', e => errors.push(e.message)); p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

  await p.goto(PAGE);
  await p.waitForSelector('#picker:not([hidden])');
  await p.fill('#mq', 'wbns');
  assert.deepStrictEqual(await p.$$eval('#mlist button', bs => bs.map(b => b.firstChild.textContent)), ['Columbus, OH']);
  step('picker finds Columbus by call letters');
  await p.click('#mlist button');
  await p.waitForSelector('#tools:not([hidden])');
  assert.strictEqual(await p.textContent('#chip-name'), 'Columbus, OH');
  await p.waitForFunction(() => /built/.test(document.getElementById('pv-note').textContent));
  await p.waitForFunction(() => /Last build: FFG/.test(document.getElementById('status').textContent));
  assert.ok(!(await p.getAttribute('#status', 'class')).includes('bad'), await p.textContent('#status'));
  step('market chosen, status strip fresh, preview drawn');

  const pvColors = () => p.evaluate(() => {
    const c = document.getElementById('pv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, s = new Set();
    for (let i = 0; i < d.length; i += 4 * 97) s.add('#' + [d[i], d[i + 1], d[i + 2]].map(x => x.toString(16).padStart(2, '0')).join(''));
    return [...s];
  });
  assert.ok((await pvColors()).includes('#fc9272'), 'standard band 4 visible in preview');
  assert.strictEqual(await p.isDisabled('#save'), true);
  assert.strictEqual(await p.textContent('#ffg-title'), 'Standard colors for Columbus, OH');
  // county lines: drawn by default, and the toggle changes the picture
  await p.waitForFunction(() => document.getElementById('pv').getContext('2d') && true);
  await p.waitForTimeout(500);
  const grab = () => p.evaluate(() => { const c = document.getElementById('pv'); return Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data); });
  const withLines = await grab(); await p.uncheck('#lines'); const without = await grab(); await p.check('#lines');
  let changed = 0; for (let i = 0; i < withLines.length; i += 4) if (withLines[i] !== without[i] || withLines[i + 1] !== without[i + 1]) changed++;
  assert.ok(changed > 5000, 'county lines drawn (' + changed + ' pixels change with the toggle)');
  assert.strictEqual(await p.getAttribute('[data-preset="standard"]', 'aria-pressed'), 'true');
  step('county lines on the preview, with a toggle; Standard preset marked');
  await p.click('[data-preset="blues"]');
  assert.strictEqual(await p.inputValue('#h-0'), '#003577');
  assert.match(await p.textContent('#preset-note'), /^Blues:/);
  assert.ok((await pvColors()).includes('#62b6e9') || (await pvColors()).includes('#a5d5f4'), 'preview shows the preset');
  await p.screenshot({ path: SHOTS + '/0-preset-blues.png', fullPage: true });
  await p.click('#discard');
  assert.strictEqual(await p.inputValue('#h-0'), '#67000d');
  step('a preset fills the editor and preview; Discard returns to saved');
  await p.screenshot({ path: SHOTS + '/1-ffg-standard.png', fullPage: true });

  // edit: invalid then valid
  await p.fill('#h-4', 'zzz');
  assert.strictEqual(await p.getAttribute('#h-4', 'aria-invalid'), 'true');
  assert.strictEqual(await p.isDisabled('#save'), true);
  assert.match(await p.textContent('#e-4'), /a50f15/);
  await p.fill('#h-4', '00FF00');
  await p.locator('#h-4').blur();
  assert.strictEqual(await p.inputValue('#h-4'), '#00ff00');
  assert.ok((await pvColors()).includes('#00ff00'), 'preview recolored live');
  assert.match(await p.textContent('#ffg-state'), /Unsaved changes/);
  assert.strictEqual(await p.isDisabled('#save'), false);
  step('editing validates, recolors the preview, enables Save');

  await p.click('#save');
  await p.waitForFunction(() => /Saved\./.test(document.getElementById('ffg-state').textContent));
  let cfg = await ctl('/configs');
  assert.strictEqual(cfg.configs[0].market, 'columbus-oh');
  assert.strictEqual(cfg.configs[0].ffg.colors[4], '#00ff00');
  assert.strictEqual(await p.textContent('#ffg-title'), 'Custom colors for Columbus, OH');
  await p.screenshot({ path: SHOTS + '/2-ffg-saved.png', fullPage: true });
  step('first save commits without a prompt');

  // a later visit: replacing saved colors asks first
  await p.reload();
  await p.waitForFunction(() => /saved colors/.test(document.getElementById('ffg-state').textContent));
  assert.strictEqual(await p.inputValue('#h-4'), '#00ff00');
  await p.fill('#h-0', '#111111');
  await p.click('#save');
  await p.waitForSelector('#confirm[open]');
  assert.match(await p.textContent('#confirm-text'), /Columbus, OH already has custom colors, saved/);
  await p.screenshot({ path: SHOTS + '/3-confirm.png' });
  await p.click('#confirm-no');
  assert.strictEqual((await ctl('/configs')).configs[0].ffg.colors[0], '#67000d');
  await p.click('#save'); await p.click('#confirm-yes');
  await p.waitForFunction(() => /Saved\./.test(document.getElementById('ffg-state').textContent));
  assert.strictEqual((await ctl('/configs')).configs[0].ffg.colors[0], '#111111');
  step('replacing saved colors asks first; "Keep mine" saves nothing');

  // someone else saves meanwhile -> 409, then load theirs
  const other = JSON.parse(JSON.stringify(await ctl('/configs')));
  other.configs[0].ffg.colors[0] = '#222222'; other.configs[0].updatedUtc = '2026-11-04T09:00:00Z';
  await ctl('/set', other);
  await p.fill('#h-1', '#333333'); await p.click('#save');
  await p.waitForFunction(() => /Not saved/.test(document.getElementById('ffg-state').textContent));
  assert.match(await p.textContent('#ffg-state'), /after you opened the page/);
  await p.click('#reload-saved');
  await p.waitForFunction(() => document.getElementById('h-0').value === '#222222');
  step('a conflicting save is refused and the other colors can be loaded');

  // back to standard
  await p.click('#standard');
  assert.match(await p.textContent('#ffg-state'), /back to the standard colors/);
  await p.click('#save');
  if (await p.isVisible('#confirm[open]')) await p.click('#confirm-yes');
  await p.waitForFunction(() => /Saved\./.test(document.getElementById('ffg-state').textContent));
  assert.deepStrictEqual((await ctl('/configs')).configs, []);
  assert.strictEqual(await p.textContent('#ffg-title'), 'Standard colors for Columbus, OH');
  step('"Use the standard colors" + Save removes the market\'s entry');

  // copy, tabs, help
  await p.click('#ffg-urls button[data-copy]');
  assert.match(await p.evaluate(() => navigator.clipboard.readText()), /markets\/columbus-oh\/Custom_FFG_1hr\.kmz$/);
  await p.focus('#tab-ffg'); await p.keyboard.press('ArrowRight');
  assert.strictEqual(await p.isVisible('#panel-records'), true);
  assert.strictEqual(await p.$$eval('#rec-urls button[data-copy]', b => b.length), 28);
  await p.click('#copy-all');
  assert.strictEqual((await p.evaluate(() => navigator.clipboard.readText())).split('\n').length, 28);
  await p.waitForFunction(() => /Changing how the dots look in Max/.test(document.getElementById('rec-help').textContent));
  await p.screenshot({ path: SHOTS + '/4-records.png', fullPage: true });
  await p.focus('#tab-records'); await p.keyboard.press('ArrowRight');
  assert.strictEqual(await p.isVisible('#panel-help'), true);
  assert.strictEqual(await p.evaluate(() => document.activeElement.id), 'tab-help');
  await p.waitForFunction(() => /Adding a layer in Max/.test(document.getElementById('add-help').textContent));
  assert.ok(p.url().endsWith('#add-to-max'), p.url());
  step('copy buttons, keyboard tabs, both help texts');

  // change market
  await p.click('#change'); await p.fill('#mq', 'seattle'); await p.keyboard.press('Enter');
  await p.waitForFunction(() => document.getElementById('chip-name').textContent === 'Seattle–Tacoma, WA');
  step('change market (Enter picks the first match)');

  // phone width: no horizontal scroll on any tab
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const q = await phone.newPage(); await q.goto(PAGE); await q.fill('#mq', 'Columbus'); await q.click('#mlist button');
  await q.waitForFunction(() => /built/.test(document.getElementById('pv-note').textContent));
  for (const t of ['#tab-ffg', '#tab-records', '#tab-help']) {
    await q.click(t);
    const w = await q.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(w <= 390, t + ' scrollWidth ' + w);
  }
  await q.click('#tab-ffg'); await q.screenshot({ path: SHOTS + '/5-phone.png', fullPage: true });
  step('390 px wide: no horizontal scroll');

  // dark theme renders
  const dark = await browser.newContext({ viewport: { width: 1200, height: 900 }, colorScheme: 'dark' });
  const r = await dark.newPage(); await r.goto(PAGE); await r.fill('#mq', 'Houston'); await r.click('#mlist button');
  await r.waitForFunction(() => /built/.test(document.getElementById('pv-note').textContent));
  await r.screenshot({ path: SHOTS + '/6-dark.png', fullPage: true });
  step('dark theme');

  // The deliberate conflict test makes Chrome log one 'status of 409'; anything else is a real error.
  assert.deepStrictEqual(errors.filter(e => !/status of 409/.test(e)), [], 'no page errors');
  await browser.close();
  console.log('configurator e2e OK (' + steps.length + ' checks)');
})().catch(e => { console.error(e); process.exit(1); });
