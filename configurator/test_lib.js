// node configurator/test_lib.js
'use strict';
var assert = require('assert');
var fs = require('fs');
var path = require('path');
var L = require('./src/lib.js');
var root = path.join(__dirname, '..');
var n = 0;
function t(name, fn) { fn(); n++; }

t('standard colors match the build script', function () {
  var py = fs.readFileSync(path.join(root, 'tools/build_ffg.py'), 'utf8');
  var m = /STANDARD = \[([^\]]+)\]/.exec(py);
  assert.deepStrictEqual(L.STANDARD, JSON.parse('[' + m[1].replace(/'/g, '"') + ']'));
  var b = /BOUNDS = \[([^\]]+)\]/.exec(py);
  assert.deepStrictEqual(L.BOUNDS, JSON.parse('[' + b[1] + ']').slice(0, 7));
});
t('band labels', function () {
  assert.strictEqual(L.bandLabel(0), 'Under 0.50 in');
  assert.strictEqual(L.bandLabel(1), '0.50 to 0.75 in');
  assert.strictEqual(L.bandLabel(6), '3.00 in and up');
});
t('hex normalisation follows the server rules (shared vectors)', function () {
  assert.strictEqual(L.normHex(' A50F15 '), '#a50f15');
  ['#00000g', 'red', '#000000\n0', '#0000000', '', null, 5].forEach(function (v) { assert.strictEqual(L.normHex(v), null, String(v)); });
  var cases = JSON.parse(fs.readFileSync(path.join(root, 'schema/config-test-vectors.json'), 'utf8')).cases;
  cases.forEach(function (c) {
    var cols = c.entry && c.entry.ffg && c.entry.ffg.colors;
    if (!Array.isArray(cols) || cols.length !== 7) return;
    var allOk = cols.every(function (x) { return typeof x === 'string' && /^#[0-9a-fA-F]{6}$/.test(x) && L.normHex(x) === x.toLowerCase(); });
    var pageOk = Object.keys(L.colorErrors(cols)).length === 0 && cols.every(function (x) { return typeof x === 'string' && x.trim() === x; });
    assert.strictEqual(pageOk, allOk, JSON.stringify(cols));
  });
});
t('payload: standard colors are sent as null', function () {
  assert.strictEqual(L.savePayload('columbus-oh', L.STANDARD.map(function (c) { return c.toUpperCase(); })).ffg, null);
  var p = L.savePayload('columbus-oh', ['#ABCDEF'].concat(L.STANDARD.slice(1)), '2026-11-03T00:00:00Z');
  assert.deepStrictEqual(p.ffg.colors[0], '#abcdef'); assert.strictEqual(p.expectUpdatedUtc, '2026-11-03T00:00:00Z');
});
t('server errors map to rows', function () {
  var e = L.serverErrors({ 'ffg.colors[3]': 'bad', market: 'nope' });
  assert.deepStrictEqual(e.rows, { 3: 'bad' }); assert.deepStrictEqual(e.form, ['nope']);
});
t('urls', function () {
  assert.strictEqual(L.ffgUrls('https://x/m', 'columbus-oh')[2].url, 'https://x/m/markets/columbus-oh/Custom_FFG_6hr.kmz');
  var all = L.allRecordUrls('https://x/m');
  assert.strictEqual(all.length, 28); assert.strictEqual(all[0], 'https://x/m/records/default/D1_HIMAX.kmz');
  assert.strictEqual(all[27], 'https://x/m/records/default/D7_LOMIN.kmz');
});
t('staleness', function () {
  var now = Date.parse('2026-11-04T12:00:00Z');
  assert.strictEqual(L.isStale('2026-11-04T10:00:00Z', now), false);
  assert.strictEqual(L.isStale('2026-11-04T08:30:00Z', now), true);
  assert.strictEqual(L.isStale('garbage', now), true);
});
t('recolor', function () {
  var bins = new Uint8ClampedArray([0, 0, 0, 255, 6, 6, 6, 255, 255, 255, 255, 255, 3, 3, 3, 0]);
  var out = L.recolor(bins, L.STANDARD);
  assert.deepStrictEqual(Array.from(out.slice(0, 4)), [0x67, 0x00, 0x0d, 255]);
  assert.deepStrictEqual(Array.from(out.slice(4, 8)), [0xd9, 0xd9, 0xd9, 255]);
  assert.deepStrictEqual(Array.from(out.slice(8, 16)), [0, 0, 0, 0, 0, 0, 0, 0]);
});
t('market filter matches names and call letters', function () {
  var ms = [{ name: 'Columbus, OH', stations: ['WBNS-TV'] }, { name: 'Seattle, WA', stations: ['KING-TV'] }];
  assert.strictEqual(L.filterMarkets(ms, 'wbns')[0].name, 'Columbus, OH');
  assert.strictEqual(L.filterMarkets(ms, 'sea').length, 1);
  assert.strictEqual(L.filterMarkets(ms, '').length, 2);
});
console.log('configurator lib tests OK (' + n + ')');
