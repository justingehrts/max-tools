// node tests/e2e_public.js <public page url> <screenshot dir>   (run by tests/test_public_page_browser.py)
'use strict';
const { chromium } = require('playwright');
const assert = require('assert');
const [PAGE, SHOTS] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 900 } });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
  const p = await ctx.newPage(); const errors = []; p.on('pageerror', e => errors.push(e.message)); p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  // the river-flood-dots site is another repo (and may not be published yet): answer its status file here
  await ctx.route('https://justingehrts.github.io/river-flood-dots/status.json', r => r.fulfill({ status: 200, contentType: 'application/json',
    headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ updated_utc: new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC', gauges_shown: 6860 }) }));
  await p.goto(PAGE);
  // first visit: the market picker, no login anywhere, the setup box links to the private configurator
  await p.waitForSelector('#picker:not([hidden])');
  assert.strictEqual(await p.getAttribute('.setup a.go', 'href'), 'https://www.justingehrts.com/max/');
  assert.match(await p.textContent('.setup'), /A password is required/);
  assert.strictEqual(await p.evaluate(() => document.activeElement.tagName), 'BODY', 'page load must not steal focus');
  await p.fill('#mq', 'wbns');
  assert.deepStrictEqual(await p.$$eval('#mlist button', b => b.map(x => x.textContent)), ['Columbus, OH']);   // call letters search, names shown
  await p.click('#mlist button');
  assert.strictEqual(await p.isVisible('#chosen'), true);
  assert.strictEqual(await p.textContent('#ffg-title'), 'Flash flood guidance for Columbus, OH');
  assert.deepStrictEqual(await p.$$eval('#ffg-urls button[data-copy]', b => b.map(x => x.getAttribute('data-copy'))),
    ['1', '3', '6'].map(h => PAGE.replace(/index\.html$/, '').replace(/\/$/, '') + '/markets/columbus-oh/Custom_FFG_' + h + 'hr.kmz'));
  await p.click('#ffg-urls tr:nth-child(2) button');
  assert.match(await p.evaluate(() => navigator.clipboard.readText()), /markets\/columbus-oh\/Custom_FFG_3hr\.kmz$/);
  assert.match(await p.getAttribute('#customize', 'href'), /^https:\/\/www\.justingehrts\.com\/max\/\?market=columbus-oh$/);
  await p.screenshot({ path: SHOTS + '/public-market.png', fullPage: true });
  // remembered on this device
  await p.reload(); await p.waitForSelector('#chosen:not([hidden])');
  assert.strictEqual(await p.textContent('#ffg-title'), 'Flash flood guidance for Columbus, OH');
  // change market (keyboard: Enter picks the first match)
  await p.click('#change'); assert.strictEqual(await p.evaluate(() => document.activeElement.id), 'mq');
  await p.fill('#mq', 'seattle'); await p.keyboard.press('Enter');
  assert.match(await p.textContent('#ffg-title'), /Seattle/);
  // record dots: 28 copy buttons + copy all, no market needed
  await p.click('#tab-records');
  assert.strictEqual(await p.$$eval('#rec-urls button[data-copy]', b => b.length), 28);
  await p.click('#copy-all'); assert.strictEqual((await p.evaluate(() => navigator.clipboard.readText())).split('\n').length, 28);
  assert.match(await p.textContent('#panel-records'), /Changing how the dots look in Max/);
  // river flood dots: the address is copyable
  await p.click('#tab-river');
  assert.match(await p.textContent('#panel-river'), /river-flood-dots\/observed_rivers\.kmz/);
  await p.waitForFunction(() => /6860 gauges/.test(document.getElementById('fresh-river').textContent));
  assert.ok(!(await p.getAttribute('#fresh-river', 'class') || '').includes('bad'));
  await p.click('#panel-river button[data-copy]'); assert.strictEqual(await p.evaluate(() => navigator.clipboard.readText()), 'https://justingehrts.github.io/river-flood-dots/observed_rivers.kmz');
  // every app tab, with a link out and loaded screenshots
  for (const [id, url] of [['astrographics', 'https://astrographics.streamlit.app/'], ['graph-maker', 'https://maxgraphmaker.streamlit.app/'], ['gridded-climo', 'https://gridded-climo.streamlit.app/']]) {
    await p.click('#tab-' + id);
    assert.strictEqual(await p.getAttribute('#panel-' + id + ' .open-app', 'href'), url);
    await p.waitForFunction(i => [...document.querySelectorAll('#panel-' + i + ' img')].every(m => m.complete), id);
    assert.strictEqual(await p.$$eval('#panel-' + id + ' img', ims => ims.filter(m => m.naturalWidth === 0).length), 0, id + ' screenshots load');
  }
  // keyboard + deep links
  await p.focus('#tab-ffg'); await p.keyboard.press('End'); assert.strictEqual(await p.evaluate(() => document.activeElement.id), 'tab-gridded-climo');
  const d = await ctx.newPage(); await d.goto(PAGE + (PAGE.includes('#') ? '' : '#record-dots'));
  assert.strictEqual(await d.evaluate(() => document.querySelector('[aria-selected=true]').id), 'tab-records');
  // a market sent from the private configurator (?market=) is used and remembered
  const l = await ctx.newPage(); await l.goto(PAGE + '?market=denver-co');
  assert.match(await l.textContent('#ffg-title'), /Denver/);
  // status strip is fresh, and nothing contacted a login
  for (const id of ['ffg', 'records']) assert.ok(!(await p.getAttribute('#fresh-' + id, 'class')).includes('bad'), await p.textContent('#fresh-' + id));
  // outdated data: a river status 3 hours old is flagged (limit 2 h) with the last successful run; one 100 minutes old is not
  const old = await ctx.newPage();
  const riverAt = min => r => r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' },
    body: JSON.stringify({ updated_utc: new Date(Date.now() - min * 60000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC', gauges_shown: 5 }) });
  await old.route('https://justingehrts.github.io/river-flood-dots/status.json', riverAt(180)); await old.goto(PAGE + '#river-flood-dots');
  await old.waitForFunction(() => /Outdated/.test(document.getElementById('fresh-river').textContent));
  assert.match(await old.textContent('#fresh-river'), /Warning: Outdated data\. Last successful run: .* \(3 hours ago\)/);
  assert.ok((await old.getAttribute('#fresh-river', 'class')).includes('bad'));
  await old.unroute('https://justingehrts.github.io/river-flood-dots/status.json'); await old.route('https://justingehrts.github.io/river-flood-dots/status.json', riverAt(100)); await old.reload();
  await old.waitForFunction(() => /Updated/.test(document.getElementById('fresh-river').textContent));
  // some markets failed to render in the last build: they are named on the FFG tab
  const GRIB = '5kmffg_' + new Date().toISOString().slice(0, 13).replace(/\D/g, '') + '.g2';      // this hour, so the test never ages out
  const part = await ctx.newPage();
  await part.route('**/ffg/status.json', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    generatedUtc: new Date().toISOString().replace(/\.\d+Z$/, 'Z'), grib: GRIB, source: 'WPC hourly ' + GRIB,
    failed: [{ file: 'markets/columbus-oh/Custom_FFG_1hr.kmz', error: 'x' }, { file: 'markets/columbus-oh/Custom_FFG_3hr.kmz', error: 'x' }, { file: 'markets/denver-co/Custom_FFG_1hr.kmz', error: 'x' }] }) }));
  await part.goto(PAGE);
  await part.waitForFunction(() => /using older files/.test(document.getElementById('fresh-ffg').textContent));
  assert.match(await part.textContent('#fresh-ffg'), /2 markets are using older files because the newest build failed for them: Columbus, OH; Denver, CO\./);
  assert.ok((await part.getAttribute('#fresh-ffg', 'class')).includes('warn'));
  // a stranger's invalid ?market= is ignored
  const bad = await ctx.newPage(); await bad.goto(PAGE + '?market=%3Cscript%3E'); await bad.waitForSelector('#chosen:not([hidden])');   // falls back to the remembered market
  // phone: no sideways scrolling on any tab
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const q = await phone.newPage(); await q.goto(PAGE); await q.fill('#mq', 'houston'); await q.click('#mlist button');
  for (const t of ['ffg', 'records', 'river', 'astrographics', 'graph-maker', 'gridded-climo']) {
    await q.click('#tab-' + t); const w = await q.evaluate(() => document.documentElement.scrollWidth); assert.ok(w <= 390, t + ' scrollWidth ' + w);
  }
  await q.click('#tab-ffg'); await q.screenshot({ path: SHOTS + '/public-phone.png', fullPage: true });
  assert.deepStrictEqual(errors, [], 'no page errors');
  await browser.close();
  console.log('public page e2e OK');
})().catch(e => { console.error(e); process.exit(1); });
