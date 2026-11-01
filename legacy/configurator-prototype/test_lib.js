const LIB = require('./src/lib.js');
const fs = require('fs');
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log('FAIL', m); } else console.log('ok  ', m); };

// defaults need station fields
let s = LIB.defaults();
let e = LIB.validate(s);
ok(e['station.name'] && e['station.contactEmail'] && !e['station.maxMachine'], 'empty station name/email flagged, optional machine ok');
ok(Object.keys(e).length === 2, 'defaults otherwise valid: ' + JSON.stringify(Object.keys(e)));

s.station = { name: 'WBNS', contactEmail: 'wx@example.com', maxMachine: 'WBNS-TVDC-2' };
ok(Object.keys(LIB.validate(s)).length === 0, 'filled-in station validates');

// injection / bad input
const bad = (path, val, key) => { const t = LIB.defaults(); t.station = { name: 'WBNS', contactEmail: 'a@b.co', maxMachine: '' }; const parts = path.split('.'); let o = t; parts.slice(0,-1).forEach(p => o = o[p]); o[parts.at(-1)] = val; const r = LIB.validate(t); ok(!!r[key], `rejects ${path}=${JSON.stringify(val)}`); };
bad('station.name', 'WB"; Remove-Item *', 'station.name');
bad('station.contactEmail', 'x@y.com"; calc', 'station.contactEmail');
bad('station.maxMachine', 'bad name', 'station.maxMachine');
bad('recordDots.kmlFolder', 'D:\\a" ; calc ; "', 'recordDots.kmlFolder');
bad('recordDots.kmlFolder', 'relative\\path', 'recordDots.kmlFolder');
bad('recordDots.kmlFolder', 'D:\\$env:TEMP', 'recordDots.kmlFolder');
bad('recordDots.installDir', "C:\\it's", 'recordDots.installDir');
bad('recordDots.taskName', 'x"; y', 'recordDots.taskName');
bad('recordDots.scriptsRef', 'main; calc', 'recordDots.scriptsRef');
bad('recordDots.intervalMinutes', 5, 'recordDots.intervalMinutes');
{ const t = LIB.defaults(); t.station = { name: 'WBNS', contactEmail: 'a@b.co', maxMachine: '' }; t.recordDots.icons.himax.color = 'red'; ok(LIB.validate(t)['recordDots.icons.himax'], 'rejects non-hex color'); t.recordDots.icons.himax = {color:'#ff0000', shape:'star'}; ok(LIB.validate(t)['recordDots.icons.himax'], 'rejects unknown shape'); }
ok(LIB.normalizePath('D:\\x\\y\\\\ ') === 'D:\\x\\y' && LIB.normalizePath('D:\\') === 'D:\\', 'normalizePath trims trailing slashes, keeps drive root');
ok(!LIB.validate((() => { const t = LIB.defaults(); t.station = { name: 'WBNS', contactEmail: 'a@b.co', maxMachine: '' }; t.recordDots.installDir = 'C:\\Program Files (x86)\\Max Tools'; return t; })())['recordDots.installDir'], 'spaces and parentheses in paths allowed');

// config round trip
const cfg = LIB.buildConfig(s);
const back = LIB.fromConfig(JSON.parse(JSON.stringify(cfg)));
ok(JSON.stringify(LIB.buildConfig(back)) === JSON.stringify(cfg), 'config round-trips through JSON');
ok(cfg.recordDots.kmlFolder === 'D:\\WSI\\DigitalMedia\\Custom\\KML\\record-dots', 'default KML folder matches the README');
ok(JSON.stringify(LIB.fromConfig({ junk: 1 })) === JSON.stringify(LIB.defaults()), 'garbage config falls back to defaults');
const prelim = LIB.fromConfig({ station: { name: 5 }, recordDots: { icons: { himax: { shape: 3, color: '#123456' } } } });
ok(prelim.recordDots.icons.himax.color === '#123456' && prelim.recordDots.icons.himax.shape === 'circle', 'partial/odd config keeps good fields only');

// names
const names = LIB.kmzNames();
ok(names.length === 28 && names[0] === 'D1_HIMAX.kmz' && names[27] === 'D7_LOMIN.kmz' && new Set(names).size === 28, '28 unique KMZ names');
ok(LIB.slug('  KSTP / Ch 5 ') === 'KSTP-Ch-5' && LIB.slug('!!!') === 'station', 'slug');

// setup text
const txt = LIB.setupText(s);
ok(txt.includes('\\\\WBNS-TVDC-2\\DigitalMedia\\Custom\\KML\\record-dots\\D1_HIMAX.kmz'), 'SETUP has UNC example from machine name');
ok(!/[^\x00-\x7F]/.test(txt), 'SETUP.txt is ASCII only');
const s2 = LIB.defaults(); s2.station = { name: 'KXYZ', contactEmail: 'a@b.co', maxMachine: '' };
ok(LIB.setupText(s2).includes('<NAME-OF-THIS-PC>'), 'SETUP prompts for PC name when blank');
const s3 = LIB.defaults(); s3.station = { name: 'KXYZ', contactEmail: 'a@b.co', maxMachine: '' }; s3.recordDots.kmlFolder = 'E:\\Max\\kml';
ok(LIB.shareBase(s3) === null && LIB.setupText(s3).includes('written to E:\\Max\\kml'), 'non-default KML folder skips the UNC guess');

// zip -> python verifies
const files = [
  { name: 'config.json', data: LIB.textBytes(JSON.stringify(cfg, null, 2) + '\n', false) },
  { name: 'install.ps1', data: LIB.textBytes(fs.readFileSync('payload/install.ps1', 'utf8'), true) },
  { name: 'icons/himax.png', data: new Uint8Array([137,80,78,71,13,10,26,10]) },
  { name: 'SETUP.txt', data: LIB.textBytes(txt, false) },
];
fs.mkdirSync('out',{recursive:true}); fs.writeFileSync('out/test.zip', LIB.makeZip(files));
fs.writeFileSync('out/test_expected.json', JSON.stringify(files.map(f => ({ name: f.name, hex: Buffer.from(f.data).toString('hex') }))));
console.log(fails ? `\n${fails} FAILED` : '\nall lib checks passed');
process.exit(fails ? 1 : 0);
